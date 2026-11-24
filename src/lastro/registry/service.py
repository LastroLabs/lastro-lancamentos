"""Public interface of the registry module (CAD-01, RF-CAD-01).

Pure domain functions exposed to other modules and the API layer.
"""

from lastro.registry.cnpj import validate_cnpj as _validate_cnpj
from lastro.registry.contracts import CnpjValidationResult


def validate_cnpj(cnpj: str) -> CnpjValidationResult:
    """Validate and normalize a client's numeric or alphanumeric CNPJ.

    Args:
        cnpj: Raw CNPJ string, with or without the official mask.

    Returns:
        Validation outcome with the normalized 14-character uppercase CNPJ when
        valid, or a plain-Portuguese refusal message when invalid.
    """
    return _validate_cnpj(cnpj)
