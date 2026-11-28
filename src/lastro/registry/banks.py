"""Versioned list of banks the registry accepts (CAD-04, c4; plan D2).

The list is `data/bancos.csv`: the participants of the STR with a code, from the open data of
the Banco Central do Brasil (ODbL). The name of a bank always comes from this file, never
from the user. The file is read once.
"""

import csv
from functools import cache
from pathlib import Path

BANKS_FILE = Path(__file__).resolve().parent / "data" / "bancos.csv"


@cache
def _banks() -> dict[str, str]:
    with BANKS_FILE.open(encoding="utf-8", newline="") as handle:
        return {row["codigo"]: row["nome"] for row in csv.DictReader(handle)}


def bank_name(code: str) -> str | None:
    """Name of the bank with this 3-digit code, or None when it is not in the list."""
    return _banks().get(code)
