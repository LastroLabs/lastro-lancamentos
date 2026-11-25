"""Chart of accounts `.xlsx` spreadsheet reader and validator (CAD-02, RF-CAD-03).

Reads the first worksheet in streaming `read_only=True, data_only=True` mode,
validates the row-1 header (`código` and `nome`), accepts valid rows in order,
and collects plain-Portuguese errors for incomplete rows, duplicate codes, empty
spreadsheets, or invalid files.
"""

import io
import math
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
import zlib
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from openpyxl.workbook import Workbook

from lastro.registry.contracts import ChartAccountEntry, ChartSpreadsheetResult

MAX_SPREADSHEET_BYTES = 20 * 1024 * 1024

EMPTY_SPREADSHEET_MESSAGE = "A planilha não tem nenhuma conta."
NOT_A_SPREADSHEET_MESSAGE = "Este arquivo não é uma planilha. Envie um arquivo .xlsx."
MISSING_HEADER_MESSAGE = (
    "A planilha precisa ter as colunas 'código' e 'nome' na primeira linha."
)

_CODE_HEADER = "codigo"
_NAME_HEADER = "nome"

_INVALID_FILE_ERRORS = (
    InvalidFileException,
    zipfile.BadZipFile,
    ET.ParseError,
    KeyError,
    EOFError,
    OSError,
    zlib.error,
)


def _read_chart_of_accounts_spreadsheet(
    source: bytes | Path,
    *,
    max_bytes: int = MAX_SPREADSHEET_BYTES,
) -> ChartSpreadsheetResult:
    """Read an `.xlsx` spreadsheet from bytes or path and validate its rows."""
    try:
        with _open_binary_source(source, max_bytes=max_bytes) as stream:
            if stream is None:
                return _refuse(NOT_A_SPREADSHEET_MESSAGE)
            return _parse_workbook_stream(stream)
    except _INVALID_FILE_ERRORS:
        return _refuse(NOT_A_SPREADSHEET_MESSAGE)


@contextmanager
def _open_binary_source(
    source: bytes | Path,
    *,
    max_bytes: int,
) -> Iterator[BinaryIO | None]:
    """Yield a readable binary stream when `source` exists and fits `max_bytes`."""
    if isinstance(source, bytes):
        if not source or len(source) > max_bytes:
            yield None
            return
        with io.BytesIO(source) as buffer:
            yield buffer
        return

    file_size = source.stat().st_size
    if file_size <= 0 or file_size > max_bytes:
        yield None
        return

    with source.open("rb") as file_handle:
        yield file_handle


def _parse_workbook_stream(stream: BinaryIO) -> ChartSpreadsheetResult:
    """Open an `.xlsx` workbook stream safely and extract validated accounts."""
    workbook: Workbook | None = None
    try:
        workbook = load_workbook(stream, read_only=True, data_only=True)
        if not workbook.worksheets:
            return _refuse(NOT_A_SPREADSHEET_MESSAGE)

        sheet = workbook.worksheets[0]
        rows_iter = iter(sheet.iter_rows(min_row=1, values_only=True))
        header_row = next(rows_iter, None)
        if header_row is None:
            return _refuse(MISSING_HEADER_MESSAGE)

        columns = _locate_header_columns(header_row)
        if columns is None:
            return _refuse(MISSING_HEADER_MESSAGE)

        code_index, name_index = columns
        return _parse_account_rows(rows_iter, code_index, name_index)
    finally:
        if workbook is not None:
            workbook.close()


def _locate_header_columns(header_row: tuple[object, ...]) -> tuple[int, int] | None:
    """Find the zero-based indices of the `codigo` and `nome` columns on row 1."""
    code_index: int | None = None
    name_index: int | None = None

    for index, cell in enumerate(header_row):
        normalized = _normalize_header(cell)
        if normalized == _CODE_HEADER and code_index is None:
            code_index = index
        elif normalized == _NAME_HEADER and name_index is None:
            name_index = index

    if code_index is None or name_index is None:
        return None
    return code_index, name_index


def _parse_account_rows(
    rows_iter: Iterator[tuple[object, ...]],
    code_index: int,
    name_index: int,
) -> ChartSpreadsheetResult:
    """Validate data rows starting at Excel row 2, keeping valid accounts in order."""
    accounts: list[ChartAccountEntry] = []
    errors: list[str] = []
    seen_codes: dict[str, int] = {}

    for row_number, row in enumerate(rows_iter, start=2):
        code = _cell_to_text(_get_cell(row, code_index))
        name = _cell_to_text(_get_cell(row, name_index))

        if not code and not name:
            continue

        if not code:
            errors.append(f"Linha {row_number}: falta o código da conta.")
            continue

        if not name:
            errors.append(f"Linha {row_number}: falta o nome da conta.")
            continue

        first_row = seen_codes.get(code)
        if first_row is not None:
            errors.append(
                f"Linha {row_number}: o código {code} já apareceu na linha {first_row}."
            )
            continue

        seen_codes[code] = row_number
        accounts.append(ChartAccountEntry(code=code, name=name))

    if not accounts and not errors:
        return _refuse(EMPTY_SPREADSHEET_MESSAGE)

    return ChartSpreadsheetResult(accounts=tuple(accounts), errors=tuple(errors))


def _normalize_header(value: object) -> str:
    """Normalize a header cell to lowercase ASCII without accents or outer spaces."""
    text = _cell_to_text(value)
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return without_accents.casefold()


def _cell_to_text(value: object) -> str:
    """Convert an Excel cell value to stripped text, preserving exact string codes."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isfinite(value) and value.is_integer():
            return str(int(value))
        return str(value)
    return str(value).strip()


def _get_cell(row: tuple[object, ...], index: int) -> object:
    """Return the cell at `index`, or `None` if the row is shorter than `index`."""
    return row[index] if index < len(row) else None


def _refuse(message: str) -> ChartSpreadsheetResult:
    """Build a whole-spreadsheet refusal result with zero accounts."""
    return ChartSpreadsheetResult(accounts=(), errors=(message,))
