"""Contracts of the `ai` module (plan IA-01, D1).

Only data and errors live here; the behavior is in `service.py`.
"""

from enum import StrEnum


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
