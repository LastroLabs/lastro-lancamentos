"""Pure validation of a client's bank account data (CAD-04, c2, c4, c5, c6; plan D3-D5).

No database and no HTTP here. Every function raises `InvalidBankAccountDataError` with the
plain-Portuguese message of the ficha. `validate_new_account` runs the checks in the order of
plan answer P5: bank empty, nickname empty, bank format, bank in the list, nickname length,
months. The repeated nickname (409) is checked later, against the database.
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import date

from lastro.registry.banks import bank_name
from lastro.registry.contracts import InvalidBankAccountDataError

NICKNAME_MAX_LENGTH = 255
NO_BANK_MESSAGE = "Informe o banco da conta."
NO_NICKNAME_MESSAGE = "Dê um apelido para a conta."
BANK_FORMAT_MESSAGE = "O código do banco tem 3 números. Confira e tente de novo."
BANK_UNKNOWN_MESSAGE = "Não encontramos um banco com este código. Confira o número."
LONG_NICKNAME_MESSAGE = (
    f"O apelido deve ter no máximo {NICKNAME_MAX_LENGTH} caracteres."
)
MONTH_FORMAT_MESSAGE = "Informe o mês no formato AAAA-MM, por exemplo 2026-10."
MONTH_ORDER_MESSAGE = "O último mês não pode ser antes do primeiro."
BANK_CHANGE_MESSAGE = (
    "O banco de uma conta não pode ser trocado. Cadastre uma nova conta."
)

_MONTH = re.compile(r"([0-9]{4})-(0[1-9]|1[0-2])")


@dataclass(frozen=True, slots=True)
class ValidAccount:
    """Bank account data that passed every pure check."""

    bank: str
    nickname: str
    first_month: date | None
    last_month: date | None


def clean_nickname(raw: str | None) -> str:
    """Nickname without spaces at the ends; refused when empty."""
    nickname = (raw or "").strip()
    if not nickname:
        raise InvalidBankAccountDataError(NO_NICKNAME_MESSAGE)
    return nickname


def check_nickname_length(nickname: str) -> None:
    if len(nickname) > NICKNAME_MAX_LENGTH:
        raise InvalidBankAccountDataError(LONG_NICKNAME_MESSAGE)


def normalize_nickname(nickname: str) -> str:
    """Form used to compare nicknames: no accents, lower case, inner spaces reduced to one."""
    decomposed = unicodedata.normalize("NFKD", nickname)
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(plain.casefold().split())


def check_bank_format(bank: str) -> None:
    """Refuse a code that is not 3 ASCII digits (D4: `isdigit` alone accepts other scripts)."""
    if len(bank) != 3 or not (bank.isascii() and bank.isdigit()):
        raise InvalidBankAccountDataError(BANK_FORMAT_MESSAGE)


def check_bank_in_list(bank: str) -> None:
    if bank_name(bank) is None:
        raise InvalidBankAccountDataError(BANK_UNKNOWN_MESSAGE)


def parse_month(raw: str | None) -> date | None:
    """`AAAA-MM` to the first day of that month; None or blank means no month (D5)."""
    if raw is None or not raw.strip():
        return None
    match = _MONTH.fullmatch(raw.strip())
    if match is None:
        raise InvalidBankAccountDataError(MONTH_FORMAT_MESSAGE)
    try:
        return date(int(match[1]), int(match[2]), 1)
    except ValueError as error:  # year 0000
        raise InvalidBankAccountDataError(MONTH_FORMAT_MESSAGE) from error


def check_month_order(first_month: date | None, last_month: date | None) -> None:
    if first_month and last_month and last_month < first_month:
        raise InvalidBankAccountDataError(MONTH_ORDER_MESSAGE)


def format_month(month: date | None) -> str | None:
    return None if month is None else f"{month.year:04d}-{month.month:02d}"


def validate_new_account(
    bank: str | None,
    nickname: str | None,
    first_month: str | None,
    last_month: str | None,
) -> ValidAccount:
    """Run every pure check of a new account in the order of plan answer P5."""
    clean_bank = (bank or "").strip()
    if not clean_bank:
        raise InvalidBankAccountDataError(NO_BANK_MESSAGE)
    clean = clean_nickname(nickname)
    check_bank_format(clean_bank)
    check_bank_in_list(clean_bank)
    check_nickname_length(clean)
    first = parse_month(first_month)
    last = parse_month(last_month)
    check_month_order(first, last)
    return ValidAccount(clean_bank, clean, first, last)
