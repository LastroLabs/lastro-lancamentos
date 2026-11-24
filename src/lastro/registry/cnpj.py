"""Numeric and alphanumeric CNPJ validation (CAD-01, RF-CAD-01).

Implements the official Receita Federal Module 11 algorithm defined by
IN RFB 2.229/2024 (effective July 2026), unifying numeric and alphanumeric
CNPJs via `ord(char) - 48`.
"""

import re

from lastro.registry.contracts import CnpjValidationResult

EMPTY_CNPJ_MESSAGE = "Informe o CNPJ do cliente."
INVALID_CNPJ_MESSAGE = "O CNPJ informado não é válido. Confira os números."

_RAW_CNPJ_PATTERN = re.compile(r"[A-Z0-9]{12}[0-9]{2}", re.ASCII)
_MASKED_CNPJ_PATTERN = re.compile(
    r"[A-Z0-9]{2}\.[A-Z0-9]{3}\.[A-Z0-9]{3}/[A-Z0-9]{4}-[0-9]{2}",
    re.ASCII,
)
_FIRST_DIGIT_WEIGHTS = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_SECOND_DIGIT_WEIGHTS = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)


def _validate_cnpj(cnpj: str) -> CnpjValidationResult:
    """Validate and normalize a numeric or alphanumeric CNPJ.

    Leading and trailing whitespace are stripped before checking emptiness.
    Accepted formats are either 14 raw ASCII characters (`12` alphanumeric
    characters followed by `2` numeric check digits) or the official mask
    `XX.XXX.XXX/XXXX-XX`.

    Args:
        cnpj: Raw CNPJ text supplied by the caller.

    Returns:
        A `CnpjValidationResult` with the 14-character uppercase unmasked value
        when valid, or a user-facing error message when refused.
    """
    cleaned = cnpj.strip()
    if not cleaned:
        return _invalid(EMPTY_CNPJ_MESSAGE)

    normalized = _normalize(cleaned)
    if normalized is None:
        return _invalid(INVALID_CNPJ_MESSAGE)

    if not _has_valid_check_digits(normalized):
        return _invalid(INVALID_CNPJ_MESSAGE)

    return CnpjValidationResult(
        is_valid=True, normalized=normalized, error_message=None
    )


def _normalize(cleaned: str) -> str | None:
    """Check ASCII format, remove the official mask, and reject repeated chars."""
    if not cleaned.isascii():
        return None

    upper = cleaned.upper()
    if _RAW_CNPJ_PATTERN.fullmatch(upper):
        normalized = upper
    elif _MASKED_CNPJ_PATTERN.fullmatch(upper):
        normalized = upper.replace(".", "").replace("/", "").replace("-", "")
    else:
        return None

    if len(set(normalized)) == 1:
        return None

    return normalized


def _has_valid_check_digits(normalized: str) -> bool:
    """Verify both Module 11 check digits using the ASCII - 48 rule."""
    base = normalized[:12]
    first_digit = _compute_check_digit(base, _FIRST_DIGIT_WEIGHTS)
    second_digit = _compute_check_digit(f"{base}{first_digit}", _SECOND_DIGIT_WEIGHTS)
    return normalized[12:] == f"{first_digit}{second_digit}"


def _compute_check_digit(chars: str, weights: tuple[int, ...]) -> str:
    """Compute a single Module 11 check digit for the given characters and weights."""
    total = sum(
        (ord(char) - 48) * weight for char, weight in zip(chars, weights, strict=True)
    )
    remainder = total % 11
    return "0" if remainder < 2 else str(11 - remainder)


def _invalid(message: str) -> CnpjValidationResult:
    """Build a failed validation result with the given error message."""
    return CnpjValidationResult(is_valid=False, normalized=None, error_message=message)
