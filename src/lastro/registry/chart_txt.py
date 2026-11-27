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

FIX_ONE_SUFFIX = "Corrija essa linha e envie o arquivo de novo."
FIX_MANY_SUFFIX = "Corrija e envie o arquivo de novo."

# ZIP (.xlsx included) and PDF; a NUL byte also means a binary file.
_NOT_TEXT_SIGNATURES = (b"PK\x03\x04", b"%PDF-")
_MIN_LINE_LENGTH = 68
_LINE_LENGTH = 78
_REDUCED_CODE_LENGTH = 7
_ZERO_REDUCED_CODE = "0000000"
_KINDS = ("S", "A")


@dataclass(frozen=True, slots=True)
class _OwnError:
    """The first error of the table "Erros de linha" found in one line."""

    message: str
    is_tolerable: bool


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


def _own_error(line: _Line) -> _OwnError | None:
    """At most one error per line: the causes come before the tolerable errors.

    So the message points at what really blocks the load (E1, E8, E3, E5 before E2,
    E4).
    """
    cause = _own_cause(line)
    if cause is not None:
        return _OwnError(message=cause, is_tolerable=False)
    tolerable = _own_tolerable_error(line)
    if tolerable is not None:
        return _OwnError(message=tolerable, is_tolerable=True)
    return None


def _own_cause(line: _Line) -> str | None:
    """E1, E8, E3a, E3b, E5a and E5b, in this order; the value is quoted as read."""
    if len(line.text) < _MIN_LINE_LENGTH:
        return "a linha está incompleta."
    if line.text[_LINE_LENGTH:].strip(" "):
        return "a linha tem texto depois da posição 78."
    classification = line.classification
    if not classification:
        return "falta a classificação da conta."
    if not _is_digits(classification):
        return f'a classificação "{classification}" precisa ter só números.'
    kind = line.kind
    if not kind.strip():
        return "falta o tipo da conta (S ou A)."
    if kind not in _KINDS:
        return f'o tipo "{kind}" não é válido. Use S ou A.'
    return None


def _own_tolerable_error(line: _Line) -> str | None:
    """E2 (empty, then not 7 digits), E2z and E4, in this order."""
    reduced_code = line.reduced_code
    if not reduced_code:
        return "falta o código reduzido da conta."
    if len(reduced_code) != _REDUCED_CODE_LENGTH or not _is_digits(reduced_code):
        return f'o código reduzido "{reduced_code}" precisa ter 7 dígitos.'
    if reduced_code == _ZERO_REDUCED_CODE:
        return "o código reduzido não pode ser 0000000."
    if not line.name:
        return "falta o nome da conta."
    return None


def _is_digits(text: str) -> bool:
    """Non-empty and only ASCII digits (`str.isdigit` alone accepts "²" and others)."""
    return text.isascii() and text.isdigit()


def _check_lines(lines: list[_Line]) -> ChartOfAccountsResult:
    """Apply the line rules and build the result."""
    causes = []
    for line in lines:
        error = _own_error(line)
        if error is not None:
            causes.append(_at(line, error.message))
    if causes:
        return _refuse(_refusal_message(causes))
    accepted = lines
    if not any(line.kind == "A" for line in accepted):
        return _refuse(NO_ANALYTIC_MESSAGE)
    accounts = tuple(_entry(line, None) for line in accepted)
    return ChartOfAccountsResult(accounts=accounts, errors=(), warnings=(), refusal=None)


def _at(line: _Line, message: str) -> str:
    return f"Linha {line.number}: {message}"


def _refusal_message(causes: list[str]) -> str:
    """The first cause (lowest line number) and how many other causes there are."""
    others = len(causes) - 1
    if others == 0:
        return f"{causes[0]} {FIX_ONE_SUFFIX}"
    noun = "linha" if others == 1 else "linhas"
    return f"{causes[0]} Há mais {others} {noun} com problema. {FIX_MANY_SUFFIX}"


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
