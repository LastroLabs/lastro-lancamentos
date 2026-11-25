"""CAD-02: read chart of accounts spreadsheet and flag invalid rows (RF-CAD-03).

Each test matches a verification entry in features/CAD-02.json. All spreadsheets
are synthetic and generated in `tmp_path` at runtime.

`lastro.registry.service` is imported inside `_read_spreadsheet()` so that, while
`read_chart_of_accounts_spreadsheet` does not exist yet, every test fails
individually with AttributeError instead of breaking pytest collection.
"""

import importlib
import zipfile
from pathlib import Path

from openpyxl import Workbook

MSG_EMPTY_SPREADSHEET = "A planilha não tem nenhuma conta."
MSG_NOT_A_SPREADSHEET = "Este arquivo não é uma planilha. Envie um arquivo .xlsx."
MSG_MISSING_HEADER = (
    "A planilha precisa ter as colunas 'código' e 'nome' na primeira linha."
)


def _read_spreadsheet(source: bytes | Path):
    service = importlib.import_module("lastro.registry.service")
    return service.read_chart_of_accounts_spreadsheet(source)


def _write_xlsx(path: Path, rows: list[list[object]]) -> Path:
    """Create a synthetic `.xlsx` file with the provided rows on the first sheet."""
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    for row in rows:
        sheet.append(row)
    workbook.save(path)
    workbook.close()
    return path


def _as_pairs(accounts: tuple[object, ...]) -> list[tuple[str, str]]:
    return [(account.code, account.name) for account in accounts]  # type: ignore[attr-defined]


def test_planilha_valida_vira_lista_de_contas(tmp_path: Path):
    basic_path = _write_xlsx(
        tmp_path / "plano_valido.xlsx",
        [
            ["código", "nome"],
            ["1.1.01", "Caixa"],
            ["2.1.05", "Fornecedores"],
            ["9.9.99", "Transitória"],
        ],
    )

    for source in (basic_path, basic_path.read_bytes()):
        result = _read_spreadsheet(source)
        assert isinstance(result.accounts, tuple)
        assert isinstance(result.errors, tuple)
        assert result.errors == ()
        assert _as_pairs(result.accounts) == [
            ("1.1.01", "Caixa"),
            ("2.1.05", "Fornecedores"),
            ("9.9.99", "Transitória"),
        ]

    # Header variations (accent, case, spacing, column order, extra columns),
    # blank lines in the middle, surrounding whitespace, and numeric codes.
    normalized_path = _write_xlsx(
        tmp_path / "plano_variacoes.xlsx",
        [
            ["Observação", "  NOME  ", "Codigo"],
            ["extra", "  Caixa Geral  ", "  01.01  "],
            [None, None, None],
            ["", "   ", ""],
            ["ignorar", "Fornecedores", 101],
            ["ignorar", "Transitória", 205.0],
        ],
    )

    normalized_result = _read_spreadsheet(normalized_path)
    assert normalized_result.errors == ()
    assert _as_pairs(normalized_result.accounts) == [
        ("01.01", "Caixa Geral"),
        ("101", "Fornecedores"),
        ("205", "Transitória"),
    ]


def test_linha_incompleta_rejeitada_com_numero(tmp_path: Path):
    mixed_path = _write_xlsx(
        tmp_path / "plano_incompleto.xlsx",
        [
            ["código", "nome"],
            ["1.1.01", "Caixa"],
            ["2.1.05", None],
            [None, "Bancos"],
            ["9.9.99", "Transitória"],
        ],
    )

    result = _read_spreadsheet(mixed_path)
    assert _as_pairs(result.accounts) == [
        ("1.1.01", "Caixa"),
        ("9.9.99", "Transitória"),
    ]
    assert result.errors == (
        "Linha 3: falta o nome da conta.",
        "Linha 4: falta o código da conta.",
    )

    # Blank row keeps the real Excel row numbers; whitespace-only cells count as missing;
    # a sheet whose data rows are all invalid returns 0 accounts and each row error.
    only_invalid_path = _write_xlsx(
        tmp_path / "plano_so_erros.xlsx",
        [
            ["código", "nome"],
            [None, None],
            ["1.1.01", "   "],
            ["   ", "Bancos"],
        ],
    )

    only_invalid_result = _read_spreadsheet(only_invalid_path)
    assert only_invalid_result.accounts == ()
    assert only_invalid_result.errors == (
        "Linha 3: falta o nome da conta.",
        "Linha 4: falta o código da conta.",
    )


def test_codigo_repetido_rejeitado_com_as_duas_linhas(tmp_path: Path):
    duplicate_path = _write_xlsx(
        tmp_path / "plano_repetido.xlsx",
        [
            ["código", "nome"],
            ["1.1.01", "Caixa"],
            ["2.1.05", "Fornecedores"],
            ["1.1.01", "Caixa geral"],
        ],
    )

    result = _read_spreadsheet(duplicate_path)
    assert _as_pairs(result.accounts) == [
        ("1.1.01", "Caixa"),
        ("2.1.05", "Fornecedores"),
    ]
    assert result.errors == ("Linha 4: o código 1.1.01 já apareceu na linha 2.",)

    # Duplicate detection after trimming whitespace, repeated occurrences always point
    # to the first row, and subsequent valid rows remain accepted.
    trimmed_duplicate_path = _write_xlsx(
        tmp_path / "plano_repetido_espacos.xlsx",
        [
            ["código", "nome"],
            ["1.1.01", "Caixa"],
            ["  1.1.01  ", "Caixa filial"],
            ["1.1.01", "Caixa matriz"],
            ["9.9.99", "Transitória"],
        ],
    )

    trimmed_result = _read_spreadsheet(trimmed_duplicate_path)
    assert _as_pairs(trimmed_result.accounts) == [
        ("1.1.01", "Caixa"),
        ("9.9.99", "Transitória"),
    ]
    assert trimmed_result.errors == (
        "Linha 3: o código 1.1.01 já apareceu na linha 2.",
        "Linha 4: o código 1.1.01 já apareceu na linha 2.",
    )


def test_planilha_sem_contas_recusada(tmp_path: Path):
    header_only_path = _write_xlsx(
        tmp_path / "plano_vazio.xlsx",
        [["código", "nome"]],
    )

    result = _read_spreadsheet(header_only_path)
    assert result.accounts == ()
    assert result.errors == (MSG_EMPTY_SPREADSHEET,)

    blank_rows_path = _write_xlsx(
        tmp_path / "plano_linhas_em_branco.xlsx",
        [
            ["código", "nome"],
            [None, None],
            ["", "   "],
        ],
    )

    blank_rows_result = _read_spreadsheet(blank_rows_path)
    assert blank_rows_result.accounts == ()
    assert blank_rows_result.errors == (MSG_EMPTY_SPREADSHEET,)

    for filename, header in (
        ("sem_nome.xlsx", ["código", "descrição"]),
        ("sem_codigo.xlsx", ["conta", "nome"]),
    ):
        missing_header_path = _write_xlsx(
            tmp_path / filename,
            [
                header,
                ["1.1.01", "Caixa"],
            ],
        )
        header_result = _read_spreadsheet(missing_header_path)
        assert header_result.accounts == ()
        assert header_result.errors == (MSG_MISSING_HEADER,)


def test_arquivo_que_nao_e_planilha_recusado(tmp_path: Path):
    fake_xlsx_path = tmp_path / "texto_disfarcado.xlsx"
    fake_xlsx_path.write_text("codigo,nome\n1.1.01,Caixa\n", encoding="utf-8")

    for source in (fake_xlsx_path, fake_xlsx_path.read_bytes(), b""):
        result = _read_spreadsheet(source)
        assert result.accounts == ()
        assert result.errors == (MSG_NOT_A_SPREADSHEET,)

    non_xlsx_zip_path = tmp_path / "zip_comum.xlsx"
    with zipfile.ZipFile(non_xlsx_zip_path, "w") as archive:
        archive.writestr("notas.txt", "arquivo compactado qualquer")

    zip_result = _read_spreadsheet(non_xlsx_zip_path)
    assert zip_result.accounts == ()
    assert zip_result.errors == (MSG_NOT_A_SPREADSHEET,)
