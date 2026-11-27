"""Internals of the gateway to the AI service (IA-02, RF-SEG-03, D-03).

Pure helpers used by `service.suggest_accounts`: group the items by client, build the request
only from text already anonymized, and check each answer against the client's accounts. The
anonymization itself is IA-01's (`service.anonymize`, `anonymization.replace_identifiers`).

Nothing here logs or stores the original text, and no exception carries it (SECURITY.md §5).
"""

import re
from collections.abc import Iterable, Sequence

from lastro.ai.anonymization import fold, replace_identifiers
from lastro.ai.contracts import (
    CandidateAccount,
    ClientDescription,
    InvalidLLMResponseError,
    LLMRequest,
    RequestEntry,
)

ClientKey = tuple[str, str]
"""`(firm_id, client_id)`: two firms never share a request, even with the same client id."""

_EDGE_PUNCTUATION = ".,;:!?()\"'*-"


def group_by_client(items: Sequence[ClientDescription]) -> dict[ClientKey, list[int]]:
    """Positions of the items of each client, clients in order of first appearance."""
    groups: dict[ClientKey, list[int]] = {}
    for position, item in enumerate(items):
        groups.setdefault((item.firm_id, item.client_id), []).append(position)
    return groups


def _words(text: str) -> list[tuple[int, int, str]]:
    """(start, end, folded word) of each word, edge punctuation ignored in the comparison."""
    return [
        (m.start(), m.end(), fold(m.group(0).strip(_EDGE_PUNCTUATION)))
        for m in re.finditer(r"\S+", text)
    ]


def _replace_partners(name: str, partners: Sequence[tuple[str, str]]) -> str:
    """Replace each registered partner name inside an account name (plan IA-02, D7).

    Args:
        name: account name, documents already replaced.
        partners: (partner name, its anonymized form in this batch) pairs.

    Returns:
        The name with each partner, compared word by word without case or accents, replaced
        by the same text the partner got in the descriptions; the other words stay as they are.
    """
    patterns = sorted(
        (
            (tuple(w for _, _, w in _words(partner)), anonymized)
            for partner, anonymized in partners
        ),
        key=lambda pattern: len(pattern[0]),
        reverse=True,  # the longest partner name wins when one contains another
    )
    words = _words(name)
    pieces: list[str] = []
    cursor = index = 0
    while index < len(words):
        for pattern, anonymized in patterns:
            size = len(pattern)
            if size and tuple(w for _, _, w in words[index : index + size]) == pattern:
                pieces += [name[cursor : words[index][0]], anonymized]
                cursor = words[index + size - 1][1]
                index += size
                break
        else:
            index += 1
    pieces.append(name[cursor:])
    return "".join(pieces)


def anonymize_accounts(
    accounts: Iterable[CandidateAccount], partners: Sequence[tuple[str, str]]
) -> tuple[CandidateAccount, ...]:
    """Account names without documents, branch, account or partner names (D7, option B).

    The code is never changed: the answer is checked against the original codes.
    """
    return tuple(
        CandidateAccount(
            code=account.code,
            name=_replace_partners(replace_identifiers(account.name), partners),
        )
        for account in accounts
    )


def build_request(
    descriptions: Sequence[str],
    amounts_cents: Sequence[int],
    accounts: tuple[CandidateAccount, ...],
) -> LLMRequest:
    """Request of one client, from anonymized descriptions and already cleaned accounts."""
    return LLMRequest(
        entries=tuple(
            RequestEntry(description=description, amount_cents=amount)
            for description, amount in zip(descriptions, amounts_cents, strict=True)
        ),
        accounts=accounts,
    )


def accept_answers(
    answers: Sequence[str | None], expected: int, accounts: Iterable[CandidateAccount]
) -> list[str | None]:
    """Keep only codes of the client's accounts; any other answer becomes None ("não sei").

    Raises:
        InvalidLLMResponseError: if there is not exactly one answer per entry.
    """
    if len(answers) != expected:
        raise InvalidLLMResponseError(expected=expected, received=len(answers))
    codes = {account.code for account in accounts}
    return [answer if answer in codes else None for answer in answers]
