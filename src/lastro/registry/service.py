"""Public interface of the registry module (CAD-01, CAD-02).

Pure domain functions exposed to other modules and the API layer.
"""

from pathlib import Path

from lastro.registry.chart_spreadsheet import _read_chart_of_accounts_spreadsheet
from lastro.registry.cnpj import _validate_cnpj
from lastro.registry.contracts import ChartSpreadsheetResult, CnpjValidationResult


def validate_cnpj(cnpj: str) -> CnpjValidationResult:
    """Validate and normalize a client's numeric or alphanumeric CNPJ.

    Args:
        cnpj: Raw CNPJ string, with or without the official mask.

    Returns:
        Validation outcome with the normalized 14-character uppercase CNPJ when
        valid, or a plain-Portuguese refusal message when invalid.
    """
    return _validate_cnpj(cnpj)


def read_chart_of_accounts_spreadsheet(source: bytes | Path) -> ChartSpreadsheetResult:
    """Read and validate a client's chart of accounts `.xlsx` spreadsheet.

    Args:
        source: Raw `.xlsx` bytes or filesystem path to the spreadsheet file.

    Returns:
        Structured result containing the accepted accounts in row order and any
        plain-Portuguese row or file-level error messages.
    """
    return _read_chart_of_accounts_spreadsheet(source)
