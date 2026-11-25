"""Public interface of the `ai` module.

Every text that goes to an LLM passes through `anonymize()` first (ARQ-06, RF-SEG-03, D-03).
The documents call it `anonimizar()`; in the code the name is in English (CODING_STANDARDS §1).
`suggest_accounts()` is the only way to ask the AI service for an account (IA-02).
"""

import os
from collections.abc import Mapping, Sequence

from lastro.ai import gateway
from lastro.ai.anonymization import anonymize_batch
from lastro.ai.contracts import (
    CandidateAccount,
    ClientDescription,
    InvalidNameProtectionLevelError,
    LLMClient,
    NameProtectionLevel,
)

NAME_PROTECTION_VARIABLE = "NAME_PROTECTION_LEVEL"


def load_name_protection_level(
    environ: Mapping[str, str] | None = None,
) -> NameProtectionLevel:
    """Read the name protection level from the environment.

    Args:
        environ: variables to read; when None, the process environment.

    Returns:
        The configured level, or `NameProtectionLevel.STRICT` when the variable is absent
        or empty (D-03: on by default).

    Raises:
        InvalidNameProtectionLevelError: if the value is not one of the accepted levels.
    """
    value = (os.environ if environ is None else environ).get(
        NAME_PROTECTION_VARIABLE, ""
    )
    value = value.strip()
    if not value:
        return NameProtectionLevel.STRICT
    try:
        return NameProtectionLevel(value)
    except ValueError:
        raise InvalidNameProtectionLevelError(value) from None


def anonymize(
    descriptions: Sequence[str],
    *,
    partners: Sequence[str] = (),
    level: NameProtectionLevel | None = None,
) -> list[str]:
    """Anonymize the descriptions of one client, as one batch.

    CPF, CNPJ, branch and account become `[CPF]`, `[CNPJ]`, `[AGENCIA]` and `[CONTA]` in every
    level. Unless the level is `desligado`, each counterparty becomes `PESSOA_nnn` or
    `EMPRESA_nnn`, the same for the same name within this call.

    Args:
        descriptions: descriptions of a single client, in any order.
        partners: registered partner names of that client; truncated forms in the
            descriptions get the partner's pseudonym.
        level: name protection level; when None, read with `load_name_protection_level()`.

    Returns:
        The anonymized descriptions, in the input order.

    Raises:
        InvalidNameProtectionLevelError: if `level` is None and the configured value is invalid.
    """
    if level is None:
        level = load_name_protection_level()
    return anonymize_batch(descriptions, partners, level)


def suggest_accounts(
    items: Sequence[ClientDescription],
    *,
    llm_client: LLMClient,
    accounts_by_client: Mapping[tuple[str, str], Sequence[CandidateAccount]],
    partners_by_client: Mapping[tuple[str, str], Sequence[str]] | None = None,
    level: NameProtectionLevel | None = None,
) -> list[str | None]:
    """Ask the AI service for the account of each description, sending only anonymized text.

    Items are grouped by `(firm_id, client_id)`; each client gets one `anonymize()` and one
    request, so no request mixes two clients. The request carries the anonymized
    descriptions, their amounts in cents and the client's accounts (names without documents
    nor partner names), and no firm or client id. Each answer is checked in code against the
    accounts of that client: an unknown code becomes None ("não sei"). Nothing is logged.

    Args:
        items: descriptions to classify, of one or more clients, in any order.
        llm_client: port to the AI service.
        accounts_by_client: candidate accounts of each client, by `(firm_id, client_id)`.
            A client without accounts is not sent and gets None.
        partners_by_client: registered partner names of each client; missing means none.
        level: name protection level; when None, read once with
            `load_name_protection_level()`, before any request.

    Returns:
        One account code or None per item, in the order of `items`. An empty list returns
        an empty list without calling the service.

    Raises:
        InvalidNameProtectionLevelError: if `level` is None and the configured value is
            invalid; no request is made.
        InvalidLLMResponseError: if the service does not answer once per description of any
            client. All or nothing: the whole call fails, and the suggestions already obtained
            for other clients of the same call are discarded. To lose less, call once per
            client.
    """
    if level is None:
        level = load_name_protection_level()
    partners_by_client = partners_by_client or {}
    results: list[str | None] = [None] * len(items)

    for key, positions in gateway.group_by_client(items).items():
        accounts = tuple(accounts_by_client.get(key, ()))
        if not accounts:
            continue  # nothing the AI could choose: "não sei", without a request
        partners = tuple(partners_by_client.get(key, ()))
        descriptions = [items[position].description for position in positions]
        # Partners go in the same batch, after the descriptions: they get the same pseudonym
        # as in the descriptions, which is then used inside the account names (D7).
        anonymized = anonymize(
            [*descriptions, *partners], partners=partners, level=level
        )
        request = gateway.build_request(
            anonymized[: len(descriptions)],
            [items[position].amount_cents for position in positions],
            gateway.anonymize_accounts(
                accounts,
                list(zip(partners, anonymized[len(descriptions) :], strict=True)),
            ),
        )
        answers = gateway.accept_answers(
            llm_client.suggest(request), len(positions), accounts
        )
        for position, answer in zip(positions, answers, strict=True):
            results[position] = answer
    return results
