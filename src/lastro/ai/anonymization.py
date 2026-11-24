"""Anonymization of bank statement descriptions (IA-01, RF-SEG-03, D-03).

Two steps, always in this order:

1. Identifiers: CPF, CNPJ (numeric and alphanumeric, any check digit), branch and account
   numbers become `[CPF]`, `[CNPJ]`, `[AGENCIA]` and `[CONTA]`, in every level (plan, D2 and D3).
2. Names: each counterparty (a run of words that are not operation words, numbers, dates,
   amounts or markers) becomes `PESSOA_nnn` or `EMPRESA_nnn`, stable within one batch
   (plan, D4 to D6). In level `pessoas_protegidas` the activity words stay in clear.

The word lists come from `preservation_lists.yaml` (plan, D7). Nothing here logs or stores the
original text.
"""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import yaml

from lastro.ai.contracts import NameProtectionLevel

LISTS_FILE = Path(__file__).with_name("preservation_lists.yaml")

CPF_MARKER = "[CPF]"
CNPJ_MARKER = "[CNPJ]"
BRANCH_MARKER = "[AGENCIA]"
ACCOUNT_MARKER = "[CONTA]"
MARKERS = frozenset({CPF_MARKER, CNPJ_MARKER, BRANCH_MARKER, ACCOUNT_MARKER})

PERSON_PREFIX = "PESSOA"
COMPANY_PREFIX = "EMPRESA"
MIN_PARTNER_PREFIX = 6  # shortest truncated partner name that still matches (plan, D6)

# --- step 1: identifiers ---------------------------------------------------------------------

_ALNUM = "0-9A-Za-z"
# Masked CNPJ, numeric or alphanumeric: XX.XXX.XXX/XXXX-DD, check digit right or wrong.
_CNPJ_MASKED = re.compile(
    rf"(?<![{_ALNUM}])[{_ALNUM}]{{2}}\.[{_ALNUM}]{{3}}\.[{_ALNUM}]{{3}}/[{_ALNUM}]{{4}}-\d{{2}}"
    rf"(?![{_ALNUM}])"
)
# Masked CPF, also the partial mask some banks print (***.123.456-**).
_CPF_MASKED = re.compile(r"(?<![\d*])[\d*]{3}\.[\d*]{3}\.[\d*]{3}-[\d*]{2}(?![\d*])")
_CNPJ_DIGITS = re.compile(r"(?<!\d)\d{14}(?!\d)")
_CNPJ_ALPHANUMERIC = re.compile(rf"(?<![{_ALNUM}])[{_ALNUM}]{{12}}\d{{2}}(?![{_ALNUM}])")
_CPF_DIGITS = re.compile(r"(?<!\d)\d{11}(?!\d)")

_BRANCH = re.compile(
    r"\b(?:AG[EÊ]NCIA|AG)\b\.?\s*:?\s*\d{1,6}(?:-[\dX])?(?![\d-])",
    re.IGNORECASE,
)
_ACCOUNT = re.compile(
    r"(?:\bC/[CP]|\bC\.C\.?|\bCC\b|\bCTA\b|\bCONTA(?:\s+CORRENTE|\s+POUPAN[CÇ]A)?\b)"
    r"\.?\s*:?\s*\d[\d.]{0,14}(?:-[\dX])?(?![\d-])",
    re.IGNORECASE,
)

_CNPJ_WEIGHTS_1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_CNPJ_WEIGHTS_2 = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)


def _mod11_digit(values: Sequence[int], weights: Sequence[int]) -> int:
    remainder = sum(v * w for v, w in zip(values, weights, strict=True)) % 11
    return 0 if remainder < 2 else 11 - remainder


def _has_valid_cnpj_check_digits(cnpj: str) -> bool:
    """Alphanumeric CNPJ rule: each character is worth `ord(c) - 48`."""
    values = [ord(c) - 48 for c in cnpj.upper()]
    first = _mod11_digit(values[:12], _CNPJ_WEIGHTS_1)
    second = _mod11_digit([*values[:12], first], _CNPJ_WEIGHTS_2)
    return values[12:] == [first, second]


def _replace_alphanumeric_cnpj(match: re.Match[str]) -> str:
    """Unmasked 14 characters: a CNPJ only if the base mixes letters and digits, or the
    check digits are right. Keeps ordinary words ending in two digits (plan, D3)."""
    candidate = match.group(0)
    base = candidate[:12]
    if not any(c.isalpha() for c in base):
        return candidate  # numeric: handled by _CNPJ_DIGITS
    if any(c.isdigit() for c in base) or _has_valid_cnpj_check_digits(candidate):
        return CNPJ_MARKER
    return candidate


def replace_identifiers(text: str) -> str:
    """Replace CPF, CNPJ, branch and account numbers by markers."""
    text = _CNPJ_MASKED.sub(CNPJ_MARKER, text)
    text = _CPF_MASKED.sub(CPF_MARKER, text)
    text = _CNPJ_DIGITS.sub(CNPJ_MARKER, text)
    text = _CNPJ_ALPHANUMERIC.sub(_replace_alphanumeric_cnpj, text)
    text = _CPF_DIGITS.sub(CPF_MARKER, text)
    text = _BRANCH.sub(BRANCH_MARKER, text)
    return _ACCOUNT.sub(ACCOUNT_MARKER, text)


# --- word lists ------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PreservationLists:
    """Words read from `preservation_lists.yaml`, already folded (uppercase, no accents)."""

    operation: frozenset[str]
    activity: frozenset[str]
    conflict: frozenset[str]
    connectors: frozenset[str]
    company_suffixes: frozenset[str]
    individual_suffixes: frozenset[str]


def fold(text: str) -> str:
    """Uppercase without accents, for comparisons only (never for output)."""
    decomposed = unicodedata.normalize("NFKD", text.upper())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


@cache
def load_preservation_lists(path: Path = LISTS_FILE) -> PreservationLists:
    """Read the lists once per process.

    Raises:
        KeyError: if a required list is missing from the file.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    def words(name: str) -> frozenset[str]:
        return frozenset(
            fold(item["palavra"] if isinstance(item, dict) else str(item)) for item in raw[name]
        )

    conflict = words("conflito")
    return PreservationLists(
        operation=words("operacao") - conflict,
        activity=words("atividade") - conflict,
        conflict=conflict,
        connectors=words("conector"),
        company_suffixes=words("sufixo_empresa"),
        individual_suffixes=words("sufixo_individual"),
    )


# --- step 2: counterparties ------------------------------------------------------------------

_KEEP, _NAME, _CONNECTOR = "keep", "name", "connector"
_EDGE_PUNCTUATION = ".,;:!?()\"'*-"
_MONEY = re.compile(r"^R\$[\d.,]*$", re.IGNORECASE)
_SUFFIX_NOISE = re.compile(r"[./]")


@dataclass(frozen=True, slots=True)
class _Token:
    text: str
    start: int
    end: int
    word: str  # folded core, without edge punctuation


@dataclass(slots=True)
class _Run:
    """One counterparty inside one description."""

    description: int
    tokens: list[_Token]
    activity: list[_Token] = field(default_factory=list)
    person_key: str = ""
    company_key: str = ""
    is_company_evidence: bool = False
    partner_key: str | None = None


def _classify(token: _Token, lists: PreservationLists) -> str:
    if token.text in MARKERS or token.text.strip(_EDGE_PUNCTUATION) in MARKERS:
        return _KEEP
    if not any(c.isalpha() for c in token.word) or _MONEY.match(token.text):
        return _KEEP
    if token.word in lists.operation:
        return _KEEP
    if token.word in lists.connectors:
        return _CONNECTOR
    return _NAME


def _tokens(text: str) -> list[_Token]:
    return [
        _Token(m.group(0), m.start(), m.end(), fold(m.group(0).strip(_EDGE_PUNCTUATION)))
        for m in re.finditer(r"\S+", text)
    ]


def _runs_of(description: int, text: str, lists: PreservationLists) -> list[list[_Token]]:
    """Group name words (and connectors between them) into counterparties."""
    runs: list[list[_Token]] = []
    current: list[_Token] = []
    for token in _tokens(text):
        kind = _classify(token, lists)
        if kind == _KEEP:
            runs.append(current)
            current = []
        elif kind == _CONNECTOR and not current:
            continue  # a connector on the left edge stays in clear
        else:
            current.append(token)
    runs.append(current)

    trimmed = []
    for run in runs:
        while run and _classify(run[-1], lists) == _CONNECTOR:
            run = run[:-1]  # a connector on the right edge stays in clear
        if run:
            trimmed.append(run)
    return trimmed


def _suffix_word(token: _Token) -> str:
    return _SUFFIX_NOISE.sub("", token.word)


def _describe_run(
    description: int,
    tokens: list[_Token],
    lists: PreservationLists,
    partners: dict[str, str],
) -> _Run | None:
    """Split a run into activity words, name words and suffixes. None if it has no name."""
    run = _Run(description, tokens)
    words = list(tokens)
    has_company_suffix = False
    while words and _suffix_word(words[-1]) in (
        lists.company_suffixes | lists.individual_suffixes
    ):
        has_company_suffix |= _suffix_word(words[-1]) in lists.company_suffixes
        words.pop()
    if not words:
        return None  # only suffixes, like a lone "LTDA": nothing that identifies anyone

    run.activity = [t for t in words if t.word in lists.activity]
    name_words = [t.word for t in words if t.word not in lists.activity]
    run.person_key = " ".join(name_words)
    run.company_key = " ".join(t.word for t in words)
    run.is_company_evidence = has_company_suffix or bool(run.activity)
    run.partner_key = _match_partner(run.person_key, partners)
    return run


def _match_partner(name: str, partners: dict[str, str]) -> str | None:
    """Truncated names match by prefix, in either direction (plan, D6)."""
    if not name:
        return None
    for partner in partners:
        shorter = min(len(name), len(partner))
        if shorter >= MIN_PARTNER_PREFIX and (
            partner.startswith(name) or name.startswith(partner)
        ):
            return partner
    return None


class _Pseudonyms:
    """Counters by type, numbered in order of first appearance (plan, D5)."""

    def __init__(self) -> None:
        self._assigned: dict[tuple[str, str], str] = {}
        self._count = {PERSON_PREFIX: 0, COMPANY_PREFIX: 0}

    def of(self, prefix: str, key: str) -> str:
        if (prefix, key) not in self._assigned:
            self._count[prefix] += 1
            self._assigned[prefix, key] = f"{prefix}_{self._count[prefix]:03d}"
        return self._assigned[prefix, key]


def _normalize_name(name: str) -> str:
    return " ".join(fold(name).split())


def _pseudonym_for(run: _Run, people: set[str], pseudonyms: _Pseudonyms) -> str:
    if run.partner_key is not None:
        return pseudonyms.of(PERSON_PREFIX, "partner:" + run.partner_key)
    if run.person_key and run.person_key in people:
        return pseudonyms.of(PERSON_PREFIX, run.person_key)
    if run.is_company_evidence:
        return pseudonyms.of(COMPANY_PREFIX, run.company_key)
    return pseudonyms.of(PERSON_PREFIX, run.person_key)


def _render(run: _Run, pseudonym: str, level: NameProtectionLevel) -> str:
    if level is NameProtectionLevel.PEOPLE_PROTECTED and run.activity:
        kept = " ".join(t.text for t in run.activity)
        return kept if not run.person_key else f"{kept} {pseudonym}"
    return pseudonym


def replace_names(
    texts: Sequence[str], partners: Sequence[str], level: NameProtectionLevel
) -> list[str]:
    """Replace each counterparty by a pseudonym stable within `texts` (plan, D4 to D6)."""
    if level is NameProtectionLevel.OFF:
        return list(texts)
    lists = load_preservation_lists()
    known_partners = {_normalize_name(p): p for p in partners if p.strip()}

    runs = [
        described
        for index, text in enumerate(texts)
        for tokens in _runs_of(index, text, lists)
        if (described := _describe_run(index, tokens, lists, known_partners)) is not None
    ]
    # A name seen on its own anywhere in the batch is a person everywhere (plan, D4).
    people = {run.person_key for run in runs if not run.is_company_evidence and run.person_key}

    pseudonyms = _Pseudonyms()
    replacements: dict[int, list[tuple[int, int, str]]] = {}
    for run in runs:
        text = _render(run, _pseudonym_for(run, people, pseudonyms), level)
        replacements.setdefault(run.description, []).append(
            (run.tokens[0].start, run.tokens[-1].end, text)
        )

    result = list(texts)
    for index, spans in replacements.items():
        text = result[index]
        for start, end, new in sorted(spans, reverse=True):
            text = text[:start] + new + text[end:]
        result[index] = text
    return result


def anonymize_batch(
    descriptions: Sequence[str], partners: Sequence[str], level: NameProtectionLevel
) -> list[str]:
    """Identifiers first, then names; the output keeps the input order."""
    return replace_names([replace_identifiers(d) for d in descriptions], partners, level)
