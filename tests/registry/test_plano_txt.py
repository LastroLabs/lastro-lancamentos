"""CAD-02: read the chart of accounts text file and point out the invalid line (RF-CAD-03).

Each test matches a verification entry in features/CAD-02.json. Every file is built here
at runtime, with invented names (AGENTS.md rule 1). Layout of a line (78 characters):
[0:7] reduced code, [7:27] classification, [27:67] name, [67] kind, [68:78] spaces.
The reading rule is in docs/modulos/registry.md ("Leitura do plano de contas em TXT").

`lastro.registry.service` is imported inside `_read()` (plan D1): while
`read_chart_of_accounts` does not exist yet, each test fails on its own with
AttributeError instead of breaking the collection of the whole suite.
"""

import importlib
import io
import zipfile
from pathlib import Path

NOT_TEXT = (
    "Este arquivo não é um plano de contas em texto. "
    "Envie o plano de contas em arquivo .txt."
)
EMPTY = "O arquivo não tem nenhuma conta."
NO_ANALYTIC = (
    "O arquivo não tem nenhuma conta analítica. "
    "Confira se é o plano de contas do cliente."
)
FIX_ONE = "Corrija essa linha e envie o arquivo de novo."
FIX_MANY = "Corrija e envie o arquivo de novo."


def _read(source: bytes | Path):
    service = importlib.import_module("lastro.registry.service")
    return service.read_chart_of_accounts(source)


def _line(reduced: str, classification: str, name: str, kind: str) -> str:
    """One 78-character line; the test fails here if the layout would be broken."""
    text = f"{reduced:<7}{classification:<20}{name:<40}{kind}" + " " * 10
    assert len(text) == 78, repr(text)
    return text


def _file(*lines: str, newline: str = "\n", encoding: str = "utf-8") -> bytes:
    return (newline.join(lines) + newline).encode(encoding)


# Small valid chart: 2 top groups, 1 subgroup and 3 analytic accounts (criterion c1).
VALID = [
    _line("0000001", "1", "ATIVO", "S"),
    _line("0000002", "11", "ATIVO CIRCULANTE", "S"),
    _line("0000003", "1101", "CAIXA GERAL", "A"),
    _line("0000004", "1102", "BANCO TESTE", "A"),
    _line("0000005", "2", "PASSIVO", "S"),
    _line("0000006", "201", "FORNECEDORES TESTE", "A"),
]


def _summary(result) -> list[tuple]:
    return [
        (
            account.line_number,
            account.reduced_code,
            account.classification,
            account.name,
            account.kind,
            account.parent_classification,
        )
        for account in result.accounts
    ]


def _assert_refused(result, message: str, case: str = "") -> None:
    """A refused file has no accounts, errors or warnings, and exactly this message."""
    assert result.refusal == message, (case, result.refusal)
    assert result.accounts == (), case
    assert result.errors == (), case
    assert result.warnings == (), case


def test_txt_valido_vira_lista_de_contas_com_hierarquia(tmp_path: Path):
    """c1: a valid file becomes the account list, with parents, in line order."""
    result = _read(_file(*VALID))

    assert isinstance(result.accounts, tuple)
    assert _summary(result) == [
        (1, "0000001", "1", "ATIVO", "S", None),
        (2, "0000002", "11", "ATIVO CIRCULANTE", "S", "1"),
        (3, "0000003", "1101", "CAIXA GERAL", "A", "11"),
        (4, "0000004", "1102", "BANCO TESTE", "A", "11"),
        (5, "0000005", "2", "PASSIVO", "S", None),
        (6, "0000006", "201", "FORNECEDORES TESTE", "A", "2"),
    ]
    assert result.errors == ()
    assert result.warnings == ()
    assert result.refusal is None

    path = tmp_path / "plano.txt"
    path.write_bytes(_file(*VALID))
    assert _read(path) == result


def test_nome_de_40_caracteres_colado_no_tipo():
    """c2: a 40-character name glued to the kind is read whole."""
    name = "FORNECEDOR DE MATERIAIS DE TESTE LTDA XY"
    assert len(name) == 40
    line = _line("0000007", "1103", name, "A")
    assert line[27:68] == name + "A"

    result = _read(_file(*VALID, line))

    assert result.refusal is None
    assert _summary(result)[-1] == (7, "0000007", "1103", name, "A", "11")


def test_erro_em_analitica_e_tolerado_com_numero_da_linha():
    """c3: an error on an analytic account with nothing below it is tolerated."""
    result = _read(
        _file(
            *VALID,
            _line("0000008", "1103", "", "A"),
            _line("12A4567", "1104", "OUTRO BANCO TESTE", "A"),
            _line("0000000", "1105", "MAIS UM BANCO TESTE", "A"),
            _line("", "1106", "BANCO SEM REDUZIDO", "A"),
        )
    )

    assert result.refusal is None
    assert [a.classification for a in result.accounts] == ["1", "11", "1101", "1102", "2", "201"]
    assert result.errors == (
        "Linha 7: falta o nome da conta.",
        'Linha 8: o código reduzido "12A4567" precisa ter 7 dígitos.',
        "Linha 9: o código reduzido não pode ser 0000000.",
        "Linha 10: falta o código reduzido da conta.",
    )
    assert result.warnings == ()


def test_erro_em_grupo_recusa_o_arquivo_inteiro():
    """c4: an error on a group, or a non-tolerable error, refuses the whole file."""
    # (a) Group 11 without a name: 1101 and 1102 are consequences and are not counted.
    group_11 = _line("0000002", "11", "", "S")
    _assert_refused(
        _read(_file(VALID[0], group_11, *VALID[2:])),
        f"Linha 2: falta o nome da conta. {FIX_ONE}",
        "(a)",
    )

    # (b) Groups 11 and 2 without a name: two independent causes.
    group_2 = _line("0000005", "2", "", "S")
    _assert_refused(
        _read(_file(VALID[0], group_11, *VALID[2:4], group_2, VALID[5])),
        f"Linha 2: falta o nome da conta. Há mais 1 linha com problema. {FIX_MANY}",
        "(b)",
    )

    # (c) Errors that are always a cause, even on an analytic leaf.
    good = _line("0000007", "1103", "CONTA TESTE", "A")
    cases = [
        ("tipo em branco", _line("0000007", "1103", "CONTA TESTE", " "),
         "Linha 7: falta o tipo da conta (S ou A)."),
        ("tipo X", _line("0000007", "1103", "CONTA TESTE", "X"),
         'Linha 7: o tipo "X" não é válido. Use S ou A.'),
        ("classificação com ponto", _line("0000007", "11.03", "CONTA TESTE", "A"),
         'Linha 7: a classificação "11.03" precisa ter só números.'),
        ("classificação vazia", _line("0000007", "", "CONTA TESTE", "A"),
         "Linha 7: falta a classificação da conta."),
        ("linha de 60 caracteres", good[:60],
         "Linha 7: a linha está incompleta."),
        ("texto depois da posição 78", good + "  X",
         "Linha 7: a linha tem texto depois da posição 78."),
    ]
    for case, line, message in cases:
        _assert_refused(_read(_file(*VALID, line)), f"{message} {FIX_ONE}", f"(c) {case}")


def test_hierarquia_invalida_recusa_o_arquivo_inteiro():
    """c5: no parent in the file, or a parent that is analytic, refuses the file."""
    orphan = f"Linha 7: a conta 3101 não tem conta superior no arquivo. {FIX_ONE}"
    under_analytic = (
        f"Linha 7: a conta 110101 está abaixo da conta analítica 1101 (linha 3). {FIX_ONE}"
    )
    cases = [
        ("(a) órfã", _line("0000007", "3101", "CONTA TESTE", "A"), orphan),
        ("(b) órfã sem nome", _line("0000007", "3101", "", "A"), orphan),
        ("(c) abaixo de analítica", _line("0000007", "110101", "SUBCONTA TESTE", "A"),
         under_analytic),
        ("(d) abaixo de analítica, sem nome", _line("0000007", "110101", "", "A"),
         under_analytic),
    ]
    for case, line, message in cases:
        _assert_refused(_read(_file(*VALID, line)), message, case)


def test_repeticao_recusa_em_qualquer_ordem():
    """c6: a repeated reduced code or classification refuses the file, in any line order."""
    group_3 = _line("0000009", "3", "GRUPO TESTE", "S")
    analytic_301 = _line("0000009", "301", "CONTA TESTE", "A")
    unnamed_202 = _line("0000006", "202", "", "A")
    cases = [
        ("(a) grupo antes da analítica", [*VALID, group_3, analytic_301],
         "Linha 8: o código reduzido 0000009 já aparece na linha 7."),
        ("(b) analítica antes do grupo", [*VALID, analytic_301, group_3],
         "Linha 8: o código reduzido 0000009 já aparece na linha 7."),
        ("(c) duas analíticas",
         [*VALID, _line("0000007", "1103", "CONTA TESTE", "A"),
          _line("0000007", "1104", "OUTRA CONTA TESTE", "A")],
         "Linha 8: o código reduzido 0000007 já aparece na linha 7."),
        ("(d) analítica sem nome depois da linha 6", [*VALID, unnamed_202],
         "Linha 7: o código reduzido 0000006 já aparece na linha 6."),
        ("(d) analítica sem nome antes da linha 6", [*VALID[:5], unnamed_202, VALID[5]],
         "Linha 7: o código reduzido 0000006 já aparece na linha 6."),
        ("(e) classificação repetida",
         [*VALID, _line("0000011", "1102", "BANCO TESTE DOIS", "A")],
         "Linha 7: a classificação 1102 já aparece na linha 4."),
    ]
    for case, lines, message in cases:
        _assert_refused(_read(_file(*lines)), f"{message} {FIX_ONE}", case)


def test_sintetica_sem_filha_vira_aviso():
    """c7: a synthetic account with nothing below it is a warning, not a refusal."""
    # (a) Group 12 without accounts below it.
    empty_group = _read(_file(*VALID, _line("0000007", "12", "GRUPO VAZIO", "S")))
    assert empty_group.refusal is None
    assert len(empty_group.accounts) == 7
    assert empty_group.errors == ()
    assert empty_group.warnings == ("Linha 7: a conta sintética 12 não tem contas abaixo dela.",)

    # (b) The only child was tolerated: its error already shows, so no warning.
    tolerated_child = _read(
        _file(
            *VALID,
            _line("0000007", "12", "GRUPO TESTE", "S"),
            _line("0000008", "1201", "", "A"),
        )
    )
    assert tolerated_child.refusal is None
    assert tolerated_child.warnings == ()
    assert tolerated_child.errors == ("Linha 8: falta o nome da conta.",)


def test_mesmo_plano_em_utf8_windows_1252_e_crlf():
    """c8: UTF-8, UTF-8 with BOM, Windows-1252 and CRLF give the same result."""
    lines = [*VALID, _line("0000007", "1103", "APLICAÇÃO FINANCEIRA", "A")]
    base = _read(_file(*lines))
    assert base.refusal is None
    assert base.accounts[-1].name == "APLICAÇÃO FINANCEIRA"

    variants = {
        "UTF-8 + CRLF": _file(*lines, newline="\r\n"),
        "UTF-8 com BOM": b"\xef\xbb\xbf" + _file(*lines),
        "Windows-1252": _file(*lines, encoding="cp1252"),
        "Windows-1252 + CRLF": _file(*lines, newline="\r\n", encoding="cp1252"),
    }
    for case, data in variants.items():
        result = _read(data)
        assert result.refusal is None, case
        assert _summary(result) == _summary(base), case

    # A blank line is skipped, but the accounts keep the line number of the file.
    with_blank = _read(_file(lines[0], "", *lines[1:]))
    assert [a.line_number for a in with_blank.accounts] == [1, 3, 4, 5, 6, 7, 8]

    # Almost all UTF-8 with 1 invalid byte: read as Windows-1252, each accented letter
    # takes 2 characters, the kind of line 7 moves out of place and the file is refused.
    mixed = _file(*lines).replace(b"BANCO TESTE", b"BANCO TES\x81E", 1)
    _assert_refused(_read(mixed), f"Linha 7: falta o tipo da conta (S ou A). {FIX_ONE}")


def test_arquivo_que_nao_e_o_plano_recusado_sem_excecao():
    """c9: a file that is not the chart in text is refused in plain Portuguese, never raises."""
    text = _file(*VALID)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("xl/workbook.xml", "<workbook/>")
    not_text = {
        "(a) .xlsx ou outro ZIP": buffer.getvalue(),
        "(b) PDF sem byte nulo": b"%PDF-1.7\n" + text,
        "(c) byte nulo": text[:100] + b"\x00" + text[100:],
        "(d) acima de 20 MiB": text * (20 * 1024 * 1024 // len(text) + 1),
    }
    for case, data in not_text.items():
        _assert_refused(_read(data), NOT_TEXT, case)

    for case, data in {"(e) vazio": b"", "(e) só linhas em branco": b"\n\n   \r\n"}.items():
        _assert_refused(_read(data), EMPTY, case)


def test_arquivo_sem_conta_analitica_recusado():
    """c10: a file without any accepted analytic account is refused."""
    # (a) Only groups.
    _assert_refused(_read(_file(VALID[0], VALID[1], VALID[4])), NO_ANALYTIC, "(a)")

    # (b) Every analytic account was tolerated: the real error shows instead.
    _assert_refused(
        _read(
            _file(
                VALID[0],
                VALID[1],
                _line("0000003", "1101", "", "A"),
                _line("0000004", "1102", "", "A"),
            )
        ),
        f"Linha 3: falta o nome da conta. Há mais 1 linha com problema. {FIX_MANY}",
        "(b)",
    )
