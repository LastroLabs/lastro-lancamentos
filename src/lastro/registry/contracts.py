"""Contracts of the registry module (CAD-01, CAD-02).

Immutable data exchanged between `registry.service` and the modules that consume
registry domain operations (such as client registration, chart of accounts
import, and the API layer).
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class CnpjValidationResult:
    """Outcome of validating and normalizing a numeric or alphanumeric CNPJ.

    Attributes:
        is_valid: Whether the input passed format and check-digit validation.
        normalized: 14-character uppercase CNPJ without mask when valid; `None`
            otherwise.
        error_message: Plain-Portuguese message explaining why the input was
            refused when invalid; `None` when valid.
    """

    is_valid: bool
    normalized: str | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class ClientSummary:
    """Client of the signed-in member's firm, as shown in the list and when opened (CAD-03).

    Contract in version 0 (plan CAD-03, D5). The firm id is never part of it.

    Attributes:
        client_id: id of the client.
        name: name of the client, without surrounding spaces.
        cnpj: 14-character uppercase CNPJ without mask.
    """

    client_id: str
    name: str
    cnpj: str


class InvalidClientDataError(Exception):
    """The name or the CNPJ of the client was refused; nothing was written.

    Attributes:
        message: plain-Portuguese message that says what to fix.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ManagerOnlyError(Exception):
    """Only the manager of the firm may do this (P-02); nothing was written."""


class ClientNotFoundError(Exception):
    """The client does not exist or belongs to another firm; both look the same (P-01)."""


class ClientNotAssignedError(Exception):
    """The manager of the same firm is not the responsible member of the client (P-09)."""


class DuplicateCnpjError(Exception):
    """The firm already has a client with this CNPJ; nothing was written."""


@dataclass(frozen=True, slots=True)
class ChartAccountEntry:
    """An accepted account of the chart of accounts text file (CAD-02, contract v1).

    Attributes:
        line_number: position of the line in the file; blank lines count.
        reduced_code: 7-digit code assigned by the accounting program.
        classification: digits only; the hierarchy comes from it.
        name: account name without surrounding spaces.
        kind: "S" (group, synthetic) or "A" (receives entries, analytic).
        parent_classification: longest proper prefix of `classification` present
            in the file; `None` for top-level accounts.
    """

    line_number: int
    reduced_code: str
    classification: str
    name: str
    kind: Literal["S", "A"]
    parent_classification: str | None


@dataclass(frozen=True, slots=True)
class ChartOfAccountsResult:
    """Outcome of reading the chart of accounts text file (CAD-02, contract v1).

    `api/` decides by `refusal`: filled means 422 (P-13) with the message; `None`
    means success, with `errors` and `warnings` in the response.

    Attributes:
        accounts: accepted accounts in file order; `()` when refused.
        errors: plain-Portuguese messages of tolerated lines, left out of
            `accounts`; `()` when refused.
        warnings: plain-Portuguese messages that do not block the load; `()` when
            refused.
        refusal: single plain-Portuguese refusal message; `None` when accepted.
    """

    accounts: tuple[ChartAccountEntry, ...]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    refusal: str | None
