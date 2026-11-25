"""Contracts of the registry module (CAD-01, CAD-02).

Immutable data exchanged between `registry.service` and the modules that consume
registry domain operations (such as client registration, chart of accounts
import, and the API layer).
"""

from dataclasses import dataclass


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
class ChartAccountEntry:
    """A validated ledger account entry parsed from a chart spreadsheet.

    Attributes:
        code: Account code normalized as text (preserving leading zeros and dots).
        name: Account name with leading and trailing whitespace removed.
    """

    code: str
    name: str


@dataclass(frozen=True, slots=True)
class ChartSpreadsheetResult:
    """Outcome of reading and validating a chart of accounts `.xlsx` spreadsheet.

    Attributes:
        accounts: Accepted ledger accounts in the exact order they appeared in
            the spreadsheet.
        errors: Plain-Portuguese messages pointing out invalid rows, duplicate
            codes, or whole-file refusal reasons.
    """

    accounts: tuple[ChartAccountEntry, ...]
    errors: tuple[str, ...]
