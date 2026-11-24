"""Contracts of the registry module (CAD-01, RF-CAD-01).

Immutable data exchanged between `registry.service` and the modules that consume
CNPJ validation (such as client registration and the API layer).
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
