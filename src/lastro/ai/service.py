"""Public interface of the `ai` module.

Every text that goes to an LLM passes through `anonymize()` first (ARQ-06, RF-SEG-03, D-03).
The documents call it `anonimizar()`; in the code the name is in English (CODING_STANDARDS §1).
"""

import os
from collections.abc import Mapping, Sequence

from lastro.ai.anonymization import anonymize_batch
from lastro.ai.contracts import InvalidNameProtectionLevelError, NameProtectionLevel

NAME_PROTECTION_VARIABLE = "NAME_PROTECTION_LEVEL"


def load_name_protection_level(environ: Mapping[str, str] | None = None) -> NameProtectionLevel:
    """Read the name protection level from the environment.

    Args:
        environ: variables to read; when None, the process environment.

    Returns:
        The configured level, or `NameProtectionLevel.STRICT` when the variable is absent
        or empty (D-03: on by default).

    Raises:
        InvalidNameProtectionLevelError: if the value is not one of the accepted levels.
    """
    value = (os.environ if environ is None else environ).get(NAME_PROTECTION_VARIABLE, "")
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
