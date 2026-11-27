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
class _Hierarchy:
    """Hierarchy of the lines with a legible classification (first occurrence only).

    Attributes:
        parents: parent classification of each classification, or `None` at the top.
        causes: hierarchy cause message by line number.
        consequences: lines whose parent is not accepted (the cause is above them).
        with_children: classifications that have at least one line below them.
    """

    parents: dict[str, str | None]
    causes: dict[int, str]
    consequences: frozenset[int]
    with_children: frozenset[str]


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


def _is_valid_reduced_code(reduced_code: str) -> bool:
    """7 ASCII digits and not 0000000 (plan D3: 0000000 is never a repetition)."""
    return (
        len(reduced_code) == _REDUCED_CODE_LENGTH
        and _is_digits(reduced_code)
        and reduced_code != _ZERO_REDUCED_CODE
    )


def _repetitions(lines: list[_Line]) -> dict[int, str]:
    """E6, then E7, in every line, even one with its own error; the first one stays.

    Checking every line is what makes the result independent of the line order.
    """
    first_reduced: dict[str, int] = {}
    first_classification: dict[str, int] = {}
    messages: dict[int, str] = {}
    for line in lines:
        reduced, classification = line.reduced_code, line.classification
        reduced_at = line.number
        if _is_valid_reduced_code(reduced):
            reduced_at = first_reduced.setdefault(reduced, line.number)
        classification_at = line.number
        if _is_digits(classification):
            classification_at = first_classification.setdefault(
                classification, line.number
            )
        if reduced_at != line.number:
            messages[line.number] = (
                f"o código reduzido {reduced} já aparece na linha {reduced_at}."
            )
        elif classification_at != line.number:
            messages[line.number] = (
                f"a classificação {classification} já aparece na linha {classification_at}."
            )
    return messages


def _hierarchy(lines: list[_Line], blocked: set[int]) -> _Hierarchy:
    """Parent of every legible classification, from the shorter to the longer ones.

    It runs on every line with a legible classification, not only the accepted ones:
    otherwise an analytic account with a child would pass when the child has a
    tolerable error. `blocked` holds the lines refused on their own (repetition or
    own error); a line below one that is not accepted is a consequence.
    """
    nodes = _first_by_classification(lines)
    shortest = min((len(classification) for classification in nodes), default=0)
    parents: dict[str, str | None] = {}
    causes: dict[int, str] = {}
    consequences: set[int] = set()
    accepted: set[str] = set()
    for classification in sorted(nodes, key=len):
        line = nodes[classification]
        parent = _parent_of(classification, nodes)
        parents[classification] = parent
        cause = _hierarchy_cause(classification, parent, nodes, shortest)
        if cause is not None:
            causes[line.number] = cause
        elif parent is not None and parent not in accepted:
            consequences.add(line.number)
        elif line.number not in blocked:
            accepted.add(classification)
    with_children = frozenset(
        parent for parent in parents.values() if parent is not None
    )
    return _Hierarchy(parents, causes, frozenset(consequences), with_children)


def _first_by_classification(lines: list[_Line]) -> dict[str, _Line]:
    nodes: dict[str, _Line] = {}
    for line in lines:
        if _is_digits(line.classification):
            nodes.setdefault(line.classification, line)
    return nodes


def _parent_of(classification: str, nodes: dict[str, _Line]) -> str | None:
    """Longest proper prefix present in the file, whatever the mask or the line order."""
    for length in range(len(classification) - 1, 0, -1):
        if classification[:length] in nodes:
            return classification[:length]
    return None


def _hierarchy_cause(
    classification: str, parent: str | None, nodes: dict[str, _Line], shortest: int
) -> str | None:
    """No parent while longer than the shortest classification, or an analytic parent."""
    if parent is None:
        if len(classification) > shortest:
            return f"a conta {classification} não tem conta superior no arquivo."
        return None
    parent_line = nodes[parent]
    if parent_line.kind == "A":
        return (
            f"a conta {classification} está abaixo da conta analítica {parent} "
            f"(linha {parent_line.number})."
        )
    return None


def _check_lines(lines: list[_Line]) -> ChartOfAccountsResult:
    """Apply the line rules and build the result."""
    own_errors = {line.number: _own_error(line) for line in lines}
    repetitions = _repetitions(lines)
    blocked = set(repetitions) | {n for n, error in own_errors.items() if error}
    hierarchy = _hierarchy(lines, blocked)
    causes, tolerated = _sort_out(lines, own_errors, repetitions, hierarchy)
    if causes:
        return _refuse(_refusal_message(causes))
    # Without causes there is no hierarchy cause nor consequence: what is not blocked
    # is accepted.
    accepted = [line for line in lines if line.number not in blocked]
    if not any(line.kind == "A" for line in accepted):
        # The tolerated lines become causes, so the real error shows.
        if tolerated:
            return _refuse(_refusal_message(tolerated))
        return _refuse(NO_ANALYTIC_MESSAGE)
    return _accepted_result(accepted, tolerated, hierarchy)


def _accepted_result(
    accepted: list[_Line], tolerated: list[str], hierarchy: _Hierarchy
) -> ChartOfAccountsResult:
    """Accounts in file order, the tolerated errors and the warnings.

    A synthetic account with nothing below it is a warning. One whose only child was
    tolerated is not: the error of the child already shows.
    """
    accounts = tuple(
        _entry(line, hierarchy.parents[line.classification]) for line in accepted
    )
    warnings = tuple(
        _at(
            line, f"a conta sintética {line.classification} não tem contas abaixo dela."
        )
        for line in accepted
        if line.kind == "S" and line.classification not in hierarchy.with_children
    )
    return ChartOfAccountsResult(
        accounts=accounts, errors=tuple(tolerated), warnings=warnings, refusal=None
    )


def _sort_out(
    lines: list[_Line],
    own_errors: dict[int, _OwnError | None],
    repetitions: dict[int, str],
    hierarchy: _Hierarchy,
) -> tuple[list[str], list[str]]:
    """Causes and tolerated errors, one message per line, in line order.

    Priority: repetition, then hierarchy cause, then own error. A consequence alone
    is neither shown nor counted: the cause is in the line above.
    """
    causes: list[str] = []
    tolerated: list[str] = []
    for line in lines:
        error = own_errors[line.number]
        message = repetitions.get(line.number) or hierarchy.causes.get(line.number)
        if message is not None:
            causes.append(_at(line, message))
        elif error is None:
            continue
        elif error.is_tolerable and _can_tolerate(line, hierarchy):
            tolerated.append(_at(line, error.message))
        else:
            causes.append(_at(line, error.message))
    return causes, tolerated


def _can_tolerate(line: _Line, hierarchy: _Hierarchy) -> bool:
    """Analytic leaf without a hierarchy problem.

    Being the first line with its classification is already granted: a repeated one
    has E7, which comes first.
    """
    return (
        line.kind == "A"
        and line.classification not in hierarchy.with_children
        and line.number not in hierarchy.consequences
    )


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
