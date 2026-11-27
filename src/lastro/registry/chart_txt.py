"""Chart of accounts text file reader (CAD-02, RF-CAD-03; contract v1).

The accounting program (Dominio) exports the chart as fixed-width text, one account per
line of 78 characters: [0:7] reduced code, [7:27] classification, [27:67] name, [67]
kind (S or A), [68:78] spaces. The rule, applied here in the same order, is in
docs/modulos/registry.md ("Leitura do plano de contas em TXT"). Bad content never
raises: it becomes a refusal, or a message in `errors` or `warnings`.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from lastro.registry.contracts import ChartAccountEntry, ChartOfAccountsResult

MAX_CHART_BYTES = 20 * 1024 * 1024

EMPTY_MESSAGE = "O arquivo não tem nenhuma conta."
NOT_TEXT_MESSAGE = (
    "Este arquivo não é um plano de contas em texto. "
    "Envie o plano de contas em arquivo .txt."
)
NO_ANALYTIC_MESSAGE = (
    "O arquivo não tem nenhuma conta analítica. "
    "Confira se é o plano de contas do cliente."
)

# ZIP (.xlsx included) and PDF; a NUL byte also means a binary file.
_NOT_TEXT_SIGNATURES = (b"PK\x03\x04", b"%PDF-")


@dataclass(frozen=True, slots=True)
class _Line:
    """A non-blank line of the file, with its real position (blank lines count)."""

    number: int
    text: str

    @property
    def reduced_code(self) -> str:
        return self.text[0:7].strip()

    @property
    def classification(self) -> str:
        return self.text[7:27].strip()

    @property
    def name(self) -> str:
        return self.text[27:67].strip()

    @property
    def kind(self) -> str:
        return self.text[67:68]


def _read_chart_of_accounts(source: bytes | Path) -> ChartOfAccountsResult:
    """Read the chart from bytes or a path (raises `OSError` only for the path)."""
    data = source if isinstance(source, bytes) else _read_file(source)
    refusal = _file_refusal(data)
    if refusal is not None:
        return _refuse(refusal)
    lines = _content_lines(_decode(data))
    if not lines:
        return _refuse(EMPTY_MESSAGE)
    return _check_lines(lines)


def _read_file(path: Path) -> bytes | None:
    """Bytes of the file, or `None` when it is over the limit (checked before reading)."""
    if path.stat().st_size > MAX_CHART_BYTES:
        return None
    return path.read_bytes()


def _file_refusal(data: bytes | None) -> str | None:
    """Refusal of the whole file before looking at its lines, in the order of the rule."""
    if data is None:
        return NOT_TEXT_MESSAGE
    if not data:
        return EMPTY_MESSAGE
    if (
        len(data) > MAX_CHART_BYTES
        or data.startswith(_NOT_TEXT_SIGNATURES)
        or b"\x00" in data
    ):
        return NOT_TEXT_MESSAGE
    return None


def _decode(data: bytes) -> str:
    """UTF-8 with or without BOM; otherwise Windows-1252, replacing undefined bytes.

    Plain cp1252 raises on 0x81, 0x8D, 0x8F, 0x90 and 0x9D, hence `errors="replace"`.
    """
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def _content_lines(text: str) -> list[_Line]:
    """Non-blank lines, sliced after decoding.

    `split("\\n")` and not `splitlines()`, which also breaks on other characters.
    """
    lines = []
    for number, raw in enumerate(text.split("\n"), start=1):
        line = raw.rstrip("\r")
        if line.strip():
            lines.append(_Line(number=number, text=line))
    return lines


def _check_lines(lines: list[_Line]) -> ChartOfAccountsResult:
    """Apply the line rules and build the result."""
    accepted = lines
    if not any(line.kind == "A" for line in accepted):
        return _refuse(NO_ANALYTIC_MESSAGE)
    accounts = tuple(_entry(line, None) for line in accepted)
    return ChartOfAccountsResult(accounts=accounts, errors=(), warnings=(), refusal=None)


def _entry(line: _Line, parent: str | None) -> ChartAccountEntry:
    return ChartAccountEntry(
        line_number=line.number,
        reduced_code=line.reduced_code,
        classification=line.classification,
        name=line.name,
        kind=cast(Literal["S", "A"], line.kind),
        parent_classification=parent,
    )


def _refuse(message: str) -> ChartOfAccountsResult:
    return ChartOfAccountsResult(accounts=(), errors=(), warnings=(), refusal=message)
