"""HAR-02: filtros do `hx state` (--estado e --atencao) e Resumo sempre completo.

Cada teste monta um mini-repo em tmp_path com features/*.json.
Nenhum teste chama git, docker ou rede. Só dados sintéticos.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from harness import main

ESTADOS_VALIDOS = ["not_started", "in_progress", "passing", "blocked", "regressed"]


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------


def ficha(id_, estado, **override):
    """Ficha sintética válida no `estado` pedido (preenche o que o estado exige)."""
    dados = {
        "id": id_,
        "titulo": f"Ficha {id_}",
        "modulo": "harness",
        "requisitos": [],
        "prioridade": "must",
        "onda": 1,
        "essencial": False,
        "estado": estado,
        "responsavel": "dev",
        "depende_de": [],
        "bloqueada_por": "D-99" if estado == "blocked" else None,
        "tipo_verificacao": "comando",
        "criterios": [
            {"id": "c1", "descricao": "Faz a coisa", "exemplo": {"entrada": "x", "saida": "y"}}
        ],
        "verificacao": [{"criterio": "c1", "comando": "pytest tests/x.py::test_a -q"}],
        "evidencia": "pytest passou" if estado in ("passing", "regressed") else None,
    }
    dados.update(override)
    return dados


def gravar_todas(raiz, fichas):
    pasta = Path(raiz) / "features"
    pasta.mkdir(parents=True, exist_ok=True)
    for f in fichas:
        texto = json.dumps(f, indent=2, ensure_ascii=False) + "\n"
        (pasta / f"{f['id']}.json").write_bytes(texto.encode("utf-8"))


def rodar_state(raiz, capsys, *flags):
    codigo = main(["state", *flags], raiz=raiz)
    saida = capsys.readouterr()
    return codigo, saida.out, saida.err


def ids_listados(out, ids):
    """IDs que aparecem como primeira palavra de alguma linha da saída, na ordem."""
    return [linha.split()[0] for linha in out.splitlines() if linha.split()[:1] and linha.split()[0] in ids]


def linha_resumo(out):
    return [linha.strip() for linha in out.splitlines() if linha.startswith("Resumo:")]


# ---------------------------------------------------------------------------
# c1: --estado aceita um ou mais estados
# ---------------------------------------------------------------------------


def test_filtra_por_um_ou_mais_estados(tmp_path, capsys):
    gravar_todas(
        tmp_path,
        [ficha("A-01", "passing"), ficha("B-01", "in_progress"), ficha("C-01", "not_started")],
    )
    todos = {"A-01", "B-01", "C-01"}

    codigo, out, err = rodar_state(
        tmp_path, capsys, "--estado", "in_progress", "--estado", "not_started"
    )
    assert codigo == 0
    assert err == ""
    assert ids_listados(out, todos) == ["B-01", "C-01"]  # A-01 (passing) não aparece

    codigo, out, err = rodar_state(tmp_path, capsys, "--estado", "passing")
    assert codigo == 0
    assert ids_listados(out, todos) == ["A-01"]


# ---------------------------------------------------------------------------
# c2: estado inexistente é recusado
# ---------------------------------------------------------------------------


def test_estado_invalido_e_recusado(tmp_path, capsys):
    gravar_todas(tmp_path, [ficha("A-01", "passing"), ficha("B-01", "in_progress")])

    codigo, out, err = rodar_state(tmp_path, capsys, "--estado", "pronto")

    assert codigo == 2
    assert out == ""  # não lista nada
    assert "ERRO" in err
    assert "MOTIVO" in err
    assert "CORREÇÃO" in err
    erro_linha = next(linha for linha in err.splitlines() if linha.startswith("ERRO"))
    assert "pronto" in erro_linha
    correcao = err[err.index("CORREÇÃO") :]
    for estado in ESTADOS_VALIDOS:
        assert estado in correcao

    # um válido junto com um inválido: recusa tudo, sem listar nada
    codigo, out, err = rodar_state(
        tmp_path, capsys, "--estado", "passing", "--estado", "pronto"
    )
    assert codigo == 2
    assert out == ""
    assert "pronto" in err


# ---------------------------------------------------------------------------
# c3: --atencao
# ---------------------------------------------------------------------------


def test_atencao_lista_blocked_e_regressed(tmp_path, capsys):
    gravar_todas(
        tmp_path,
        [
            ficha("A-01", "passing"),
            ficha("B-01", "blocked"),
            ficha("C-01", "regressed"),
            ficha("D-01", "in_progress"),
            ficha("E-01", "not_started"),
        ],
    )
    todos = {"A-01", "B-01", "C-01", "D-01", "E-01"}

    codigo, out, err = rodar_state(tmp_path, capsys, "--atencao")

    assert codigo == 0
    assert err == ""
    assert ids_listados(out, todos) == ["B-01", "C-01"]
    assert "Nada pede atenção." not in out


def test_atencao_sem_nada_avisa(tmp_path, capsys):
    gravar_todas(tmp_path, [ficha("A-01", "passing")])

    codigo, out, err = rodar_state(tmp_path, capsys, "--atencao")

    assert codigo == 0
    assert err == ""
    assert "Nada pede atenção." in [linha.strip() for linha in out.splitlines()]
    assert ids_listados(out, {"A-01"}) == []  # nenhuma linha de ficha


# ---------------------------------------------------------------------------
# c4: Resumo conta tudo; sem filtro nada muda
# ---------------------------------------------------------------------------

RESUMO_TUDO = "Resumo: 1 passing · 1 in_progress · 0 not_started · 0 blocked · 0 regressed"


def test_resumo_conta_todas_as_fichas(tmp_path, capsys):
    gravar_todas(tmp_path, [ficha("A-01", "passing"), ficha("B-01", "in_progress")])

    codigo, out, err = rodar_state(tmp_path, capsys, "--estado", "in_progress")
    assert codigo == 0
    assert err == ""
    assert ids_listados(out, {"A-01", "B-01"}) == ["B-01"]
    assert linha_resumo(out) == [RESUMO_TUDO]  # conta A-01 também

    # --atencao também não reduz a contagem
    codigo, out, err = rodar_state(tmp_path, capsys, "--atencao")
    assert codigo == 0
    assert linha_resumo(out) == [RESUMO_TUDO]


def test_sem_filtro_saida_inalterada(tmp_path, capsys):
    gravar_todas(
        tmp_path,
        [
            ficha("T-01", "passing", responsavel="ana", titulo="Primeira ficha"),
            ficha("T-02", "in_progress", responsavel="bia", prioridade="should", titulo="Segunda ficha"),
        ],
    )

    codigo, out, err = rodar_state(tmp_path, capsys)

    # Saída fixa no formato de hoje (colunas alinhadas, duas colunas de espaço).
    esperado = "\n".join(
        [
            "Lastro — estado das features",
            "ID    Estado       Resp.  Prior.  Título",
            "T-01  passing      ana    must    Primeira ficha",
            "T-02  in_progress  bia    should  Segunda ficha",
            RESUMO_TUDO,
        ]
    )
    assert codigo == 0
    assert err == ""
    assert out == esperado + "\n"
