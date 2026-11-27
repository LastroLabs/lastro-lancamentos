"""HAR-05: the generated synthetic chart is a safe fixed-width TXT file."""

import importlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import harness


def _build(tmp_path: Path, capsys) -> Path:
    """Build synthetic fixtures through the public harness command."""
    result = harness.main(["fixtures", "build"], raiz=tmp_path)
    captured = capsys.readouterr()
    assert result == 0, f"build failed: {captured.out}\n{captured.err}"
    return tmp_path / "fixtures"


def _clients(catalog: dict) -> list[dict]:
    """Return every client in the generated catalog."""
    return [client for firm in catalog["escritorios"] for client in firm["clientes"]]


def _catalog(folder: Path) -> dict:
    """Read the generated synthetic catalog."""
    return json.loads((folder / "cadastro.json").read_text(encoding="utf-8"))


def test_build_gera_plano_txt_por_cliente(tmp_path, capsys):
    folder = _build(tmp_path, capsys)
    clients = _clients(_catalog(folder))
    assert clients

    for client in clients:
        assert "plano_planilha" not in client
        relative = client["plano_txt"]
        assert relative.startswith("planos/") and relative.endswith(".txt")
        chart_path = folder / relative
        assert chart_path.is_file()
        data = chart_path.read_bytes()
        assert data.endswith(b"\r\n")
        assert b"\n" not in data.replace(b"\r\n", b"")
        lines = data.decode("utf-8").split("\r\n")[:-1]
        assert len(lines) == len(client["plano"])
        for line, account in zip(lines, client["plano"], strict=True):
            assert len(line) == 78
            assert line[0:7] == account["reduzido"]
            assert line[7:27].strip() == account["classificacao"]
            assert line[27:67].strip() == account["nome"]
            assert line[67] == account["tipo"]
            assert line[68:78] == " " * 10

    assert not list(folder.rglob("*.xlsx"))


def test_plano_sintetico_tem_grupos_e_analiticas():
    generator = importlib.import_module("fixtures_sinteticas")
    files = generator.gerar_arquivos()
    catalog = json.loads(files["cadastro.json"].decode("utf-8"))
    clients = _clients(catalog)
    assert clients

    for client in clients:
        chart = client["plano"]
        assert len(chart) == 23
        by_classification = {item["classificacao"]: item for item in chart}
        assert len(by_classification) == len(chart)
        assert sum(item["tipo"] == "S" for item in chart) == 10
        assert sum(item["tipo"] == "A" for item in chart) == 13
        assert sum(item["transitoria"] for item in chart) == 1
        assert any(
            item["codigo"] == "9.9.99" and item["tipo"] == "A" and item["transitoria"]
            for item in chart
        )

        reduced_codes = [item["reduzido"] for item in chart]
        assert all(re.fullmatch(r"[0-9]{7}", code) for code in reduced_codes)
        assert len(set(reduced_codes)) == len(reduced_codes)
        for item in chart:
            assert item["classificacao"] == item["codigo"].replace(".", "")
            assert item["tipo"] in ("S", "A")
            ancestors = [
                other
                for other in chart
                if item["classificacao"].startswith(other["classificacao"])
                and len(other["classificacao"]) < len(item["classificacao"])
            ]
            if ancestors:
                parent = max(ancestors, key=lambda other: len(other["classificacao"]))
                assert parent["tipo"] == "S"
                assert chart.index(parent) < chart.index(item)
            else:
                assert len(item["classificacao"]) == 1

        analytic_codes = {item["codigo"] for item in chart if item["tipo"] == "A"}
        for bank_account in client["contas_bancarias"]:
            answer_key = json.loads(files[bank_account["gabarito"]].decode("utf-8"))
            assert all(
                movement["conta_correta"] in analytic_codes
                for movement in answer_key["movimentacoes"]
            )


def test_plano_txt_sem_documento_em_50_sementes():
    generator = importlib.import_module("fixtures_sinteticas")
    checked = 0
    for seed in range(1, 51):
        files = generator.gerar_arquivos(seed)
        charts = [
            data
            for path, data in files.items()
            if path.startswith("planos/") and path.endswith(".txt")
        ]
        assert len(charts) == 3, f"seed {seed} generated {len(charts)} charts"
        for chart in charts:
            lines = chart.decode("utf-8").splitlines()
            assert lines
            for line in lines:
                assert not harness.tipos_da_linha(line, []), (
                    f"unsafe line in seed {seed}"
                )
            checked += 1
    assert checked == 150
