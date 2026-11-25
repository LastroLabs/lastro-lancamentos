"""Contracts of the `ai` module (plan IA-01, D1; plan IA-02, D1 to D3).

Only data and errors live here; the behavior is in `service.py`.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class NameProtectionLevel(StrEnum):
    """How counterparty names are protected before text leaves the system (D-03).

    The values are the words an operator writes in the `NAME_PROTECTION_LEVEL` variable.

    Attributes:
        STRICT: every counterparty name, person or company, becomes a pseudonym (default).
        PEOPLE_PROTECTED: operation and activity words stay in clear; the rest of the
            counterparty becomes a pseudonym.
        OFF: names stay in clear. CPF, CNPJ, branch and account are still replaced.
    """

    STRICT = "estrito"
    PEOPLE_PROTECTED = "pessoas_protegidas"
    OFF = "desligado"


class InvalidNameProtectionLevelError(ValueError):
    """The configured name protection level is not one of `NameProtectionLevel`.

    The message is shown to whoever starts the application, so it says what was wrong and
    which values are accepted.
    """

    def __init__(self, value: str) -> None:
        self.value = value
        accepted = ", ".join(level.value for level in NameProtectionLevel)
        accepted = accepted.rsplit(", ", 1)
        super().__init__(
            f"Nível de proteção de nomes inválido: {value}. Use {' ou '.join(accepted)}."
        )


# --- IA-02: gateway to the AI service (plan IA-02, D1 to D3, D8) -----------------------------


def _require_cents(value: object) -> None:
    """Money is an int in cents (AGENTS.md, rule 8); float and bool are refused."""
    if type(value) is not int:
        raise TypeError(
            "Valor da movimentação inválido: use um número inteiro em centavos, com sinal "
            "(ex.: -4590 para uma saída de R$ 45,90)."
        )


@dataclass(frozen=True, slots=True)
class ClientDescription:
    """One statement description to classify, tagged with its firm and client.

    Attributes:
        firm_id: firm (escritório) that owns the client.
        client_id: client inside that firm. Requests are grouped by `(firm_id, client_id)`.
        description: original description, as read from the statement.
        amount_cents: signed amount in cents (negative is an outflow).

    Raises:
        TypeError: if `amount_cents` is not an `int` (float and bool included).
    """

    firm_id: str
    client_id: str
    description: str
    amount_cents: int

    def __post_init__(self) -> None:
        _require_cents(self.amount_cents)


@dataclass(frozen=True, slots=True)
class CandidateAccount:
    """One account of the client's chart of accounts that the AI may choose.

    Attributes:
        code: account code; the answer of the AI must be one of these codes.
        name: account name, shown to the AI to help it choose.
    """

    code: str
    name: str


@dataclass(frozen=True, slots=True)
class RequestEntry:
    """One anonymized description and its amount, as sent to the AI service.

    Raises:
        TypeError: if `amount_cents` is not an `int` (float and bool included).
    """

    description: str
    amount_cents: int

    def __post_init__(self) -> None:
        _require_cents(self.amount_cents)


@dataclass(frozen=True, slots=True)
class LLMRequest:
    """What reaches the AI service: entries and candidate accounts of a single client.

    There is no firm or client id on purpose (plan IA-02, D3): only the minimum to classify.

    Attributes:
        entries: anonymized descriptions with their amounts, in the order of the batch.
        accounts: candidate accounts, names without documents nor partner names (D7).
    """

    entries: tuple[RequestEntry, ...]
    accounts: tuple[CandidateAccount, ...]


class LLMClient(Protocol):
    """Port to the AI service. A provider adapter implements it; tests use a fake."""

    def suggest(self, request: LLMRequest) -> list[str | None]:
        """Return one account code per entry, in order, or None for "não sei"."""
        ...


class InvalidLLMResponseError(ValueError):
    """The AI service answered a number of suggestions different from the entries sent.

    Without one answer per entry there is no way to give each suggestion back to its
    description. The message never carries the original text.
    """

    def __init__(self, expected: int, received: int) -> None:
        self.expected = expected
        self.received = received
        super().__init__(
            f"O serviço de IA devolveu {received} sugestões para {expected} descrições. "
            "Nenhuma sugestão foi usada; tente de novo e, se repetir, avise o responsável "
            "pelo módulo de IA."
        )
