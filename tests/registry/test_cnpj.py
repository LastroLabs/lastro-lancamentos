"""CAD-01: numeric and alphanumeric CNPJ validation (RF-CAD-01).

Each test matches a verification entry in features/CAD-01.json. Valid CNPJs are
generated at runtime with an independent Module 11 helper (IN RFB 2.229/2024)
so no valid CNPJ literal is committed to the repository.

`lastro.registry.service` is imported inside `_validate()` so that, while the
production module does not exist yet, every test fails individually with
ModuleNotFoundError instead of breaking collection.
"""

import importlib

MSG_EMPTY = "Informe o CNPJ do cliente."
MSG_INVALID = "O CNPJ informado não é válido. Confira os números."

_WEIGHTS_FIRST = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_WEIGHTS_SECOND = (6, *_WEIGHTS_FIRST)


def _validate(cnpj: str):
    service = importlib.import_module("lastro.registry.service")
    return service.validate_cnpj(cnpj)


def _check_digit(chars: str, weights: tuple[int, ...]) -> str:
    total = sum(
        (ord(char) - 48) * weight for char, weight in zip(chars, weights, strict=True)
    )
    remainder = total % 11
    return "0" if remainder < 2 else str(11 - remainder)


def _build_valid_cnpj(base: str) -> str:
    """Build a 14-char valid CNPJ (numeric or alphanumeric) from a 12-char base."""
    upper_base = base.upper()
    first = _check_digit(upper_base, _WEIGHTS_FIRST)
    second = _check_digit(f"{upper_base}{first}", _WEIGHTS_SECOND)
    return f"{upper_base}{first}{second}"


def _format_mask(cnpj: str) -> str:
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


def _flip_digit(cnpj: str, index: int) -> str:
    replacement = str((int(cnpj[index]) + 1) % 10)
    return f"{cnpj[:index]}{replacement}{cnpj[index + 1 :]}"


def test_cnpj_numerico_valido_aceito_com_e_sem_mascara():
    raw = _build_valid_cnpj("112223330001")
    masked = _format_mask(raw)

    result_raw = _validate(raw)
    result_masked = _validate(masked)
    result_trimmed = _validate(f"  {masked}  ")

    for result in (result_raw, result_masked, result_trimmed):
        assert result.is_valid is True
        assert result.error_message is None
        assert result.normalized is not None
        assert len(result.normalized) == 14
        assert result.normalized == raw

    assert result_raw.normalized == result_masked.normalized


def test_cnpj_com_digito_errado_recusado():
    valid = _build_valid_cnpj("112223330001")
    wrong_last = _flip_digit(valid, 13)
    wrong_first = _flip_digit(valid, 12)

    for invalid in (wrong_last, _format_mask(wrong_last), wrong_first):
        result = _validate(invalid)
        assert result.is_valid is False
        assert result.normalized is None
        assert result.error_message == MSG_INVALID


def test_cnpj_alfanumerico_valido_aceito():
    for base in ("12ABC34501DE", "12IOUQF501AB"):
        upper = _build_valid_cnpj(base)
        lower = upper.lower()
        masked_upper = _format_mask(upper)
        masked_lower = _format_mask(lower)

        for candidate in (upper, lower, masked_upper, f"  {masked_lower}  "):
            result = _validate(candidate)
            assert result.is_valid is True
            assert result.error_message is None
            assert result.normalized is not None
            assert len(result.normalized) == 14
            assert result.normalized == upper


def test_cnpj_alfanumerico_com_digito_errado_recusado():
    valid = _build_valid_cnpj("12ABC34501DE")
    wrong_last = _flip_digit(valid, 13)
    wrong_first = _flip_digit(valid, 12)

    for invalid in (
        wrong_last,
        wrong_last.lower(),
        _format_mask(wrong_last),
        wrong_first,
    ):
        result = _validate(invalid)
        assert result.is_valid is False
        assert result.normalized is None
        assert result.error_message == MSG_INVALID


def test_cnpj_vazio_ou_fora_do_padrao_recusado():
    for empty in ("", "   "):
        result = _validate(empty)
        assert result.is_valid is False
        assert result.normalized is None
        assert result.error_message == MSG_EMPTY

    valid_numeric = _build_valid_cnpj("112223330001")
    misplaced_mask = (
        f"{valid_numeric[:3]}.{valid_numeric[3:6]}.{valid_numeric[6:8]}"
        f"/{valid_numeric[8:12]}-{valid_numeric[12:]}"
    )

    invalid_cases = [
        "1234567890123",  # 13 chars
        "123456789012345",  # 15 chars
        "123456#8901234",  # invalid symbol '#'
        misplaced_mask,  # valid digits, wrong mask placement
        "12ABC34501DEAB",  # letters in check-digit positions
        "12ÁBC34501DE00",  # non-ASCII letter
        "0" * 14,  # all identical digits
        "00.000.000/0000-00",  # all identical digits with mask
        "1" * 14,  # all identical non-zero digits
    ]

    for invalid in invalid_cases:
        result = _validate(invalid)
        assert result.is_valid is False
        assert result.normalized is None
        assert result.error_message == MSG_INVALID
