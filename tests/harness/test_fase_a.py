"""Fase A do harness: HX-02 (allowlist de comandos e gravação de fichas) e HX-03 (hx state).

Cada teste monta um mini-repo em tmp_path com features/*.json.
Nenhum teste aqui chama git, docker ou rede. Só dados sintéticos.
"""

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from harness import (
    HarnessErro,
    carregar_fichas,
    main,
    salvar_ficha,
    validar_comando,
    validar_fichas,
)

# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------


def ficha_valida(**override):
    """Ficha sintética que passa em todas as regras. `override` troca campos."""
    ficha = {
        "id": "T-01",
        "titulo": "Ficha de teste",
        "modulo": "harness",
        "requisitos": [],
        "prioridade": "must",
        "onda": 1,
        "essencial": False,
        "estado": "not_started",
        "responsavel": "caio",
        "depende_de": [],
        "bloqueada_por": None,
        "tipo_verificacao": "comando",
        "criterios": [
            {
                "id": "c1",
                "descricao": "Faz a coisa",
                "exemplo": {"entrada": "x", "saida": "y"},
            }
        ],
        "verificacao": [
            {"criterio": "c1", "comando": "pytest tests/x.py::test_a -q"},
        ],
        "evidencia": None,
    }
    ficha.update(override)
    return ficha


def gravar(raiz, ficha, nome=None):
    """Grava `ficha` em <raiz>/features/<nome ou id>.json (LF, UTF-8) e devolve o caminho."""
    pasta = Path(raiz) / "features"
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{nome or ficha['id']}.json"
    texto = json.dumps(ficha, indent=2, ensure_ascii=False) + "\n"
    caminho.write_bytes(texto.encode("utf-8"))
    return caminho


def problemas_do_repo(raiz):
    return validar_fichas(carregar_fichas(raiz))


def rodar_state(raiz, capsys):
    codigo = main(["state"], raiz=raiz)
    saida = capsys.readouterr()
    return codigo, saida.out, saida.err


def citam(problemas, id_, *termos):
    """Problemas que citam a ficha `id_` e todos os `termos` (sem diferenciar maiúsculas)."""
    return [
        p for p in problemas if id_ in p and all(t.lower() in p.lower() for t in termos)
    ]


# ---------------------------------------------------------------------------
# HX-02: allowlist de comandos
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "comando",
    [
        "pytest tests/x.py::test_a -q",
        "ruff check src",
        'pytest -k "cpf and dv"',
        # variações cobertas pela mesma regra
        "pytest -x tests/harness",
        "ruff check src tests",
    ],
)
def test_comando_aceito(comando):
    assert validar_comando(comando) is None


@pytest.mark.parametrize(
    "comando",
    [
        "pytest; rm -rf /",
        "python x.py",
        "pytest ../x",
        "pytest /abs",
        "ruff format .",
        "pytest $(id)",
        # variações cobertas pelas mesmas regras
        "pytest C:/x",
        "pytest --cov",
        "ruff check",
        'pytest -k "a;b"',
        "pytest tests/x.py > saida.txt",
        "pytest `id`",
    ],
)
def test_comando_recusado(comando):
    motivo = validar_comando(comando)
    assert isinstance(motivo, str)
    assert motivo.strip()


# ---------------------------------------------------------------------------
# HX-02: gravação de fichas
# ---------------------------------------------------------------------------


def test_salvar_preserva_ordem_e_utf8(tmp_path):
    ficha = {
        "zeta": 1,
        "titulo": "Descrição",
        "alfa": {"z": 2, "a": 1},
        "id": "T-01",
        "lista": ["ação", "é"],
    }
    caminho = tmp_path / "T-01.json"
    caminho.write_bytes(b"conteudo antigo que deve ser substituido")

    salvar_ficha(caminho, ficha)

    texto = caminho.read_bytes().decode("utf-8")
    assert texto == json.dumps(ficha, indent=2, ensure_ascii=False) + "\n"
    assert "Descrição" in texto
    assert "\\u00e7" not in texto  # acento gravado como caractere, não escapado

    relida = json.loads(texto)
    assert list(relida) == ["zeta", "titulo", "alfa", "id", "lista"]
    assert list(relida["alfa"]) == ["z", "a"]
    assert relida["titulo"] == "Descrição"
    assert relida["lista"] == ["ação", "é"]

    # escrita atômica: nenhum arquivo temporário sobra ao lado do destino
    assert sorted(p.name for p in tmp_path.iterdir()) == ["T-01.json"]


def test_salvar_usa_lf(tmp_path):
    caminho = tmp_path / "T-01.json"

    salvar_ficha(caminho, ficha_valida())

    dados = caminho.read_bytes()
    assert dados.count(b"\n") > 1  # a ficha tem várias linhas
    assert dados.endswith(b"\n")
    assert b"\r" not in dados


# ---------------------------------------------------------------------------
# HX-03 c1: listar fichas válidas
# ---------------------------------------------------------------------------


def test_lista_fichas_validas(tmp_path, capsys):
    gravar(
        tmp_path,
        ficha_valida(
            id="T-03", titulo="Terceira ficha", estado="in_progress", responsavel="ana"
        ),
    )
    gravar(
        tmp_path,
        ficha_valida(
            id="T-01",
            titulo="Primeira ficha",
            estado="passing",
            responsavel="bia",
            evidencia="pytest passou",
        ),
    )
    gravar(
        tmp_path,
        ficha_valida(
            id="T-04", titulo="Quarta ficha", estado="not_started", responsavel="caio"
        ),
    )
    gravar(
        tmp_path,
        ficha_valida(
            id="T-02", titulo="Segunda ficha", estado="in_progress", responsavel="dev"
        ),
    )

    # carregar_fichas lê em ordem alfabética do nome do arquivo
    assert [f["id"] for f in carregar_fichas(tmp_path)] == [
        "T-01",
        "T-02",
        "T-03",
        "T-04",
    ]
    assert problemas_do_repo(tmp_path) == []

    codigo, out, err = rodar_state(tmp_path, capsys)

    assert codigo == 0
    assert err == ""
    assert "Lastro — estado das features" in out

    esperado = {
        "T-01": ("passing", "bia", "Primeira ficha"),
        "T-02": ("in_progress", "dev", "Segunda ficha"),
        "T-03": ("in_progress", "ana", "Terceira ficha"),
        "T-04": ("not_started", "caio", "Quarta ficha"),
    }
    linhas = out.splitlines()
    cabecalho = next(linha.split() for linha in linhas if linha.split()[:1] == ["ID"])
    assert cabecalho[:3] == ["ID", "Estado", "Resp."]

    linhas_das_fichas = [
        linha for linha in linhas if linha.split()[:1] and linha.split()[0] in esperado
    ]
    # ordenadas por ID, uma linha por ficha
    assert [linha.split()[0] for linha in linhas_das_fichas] == sorted(esperado)
    for linha in linhas_das_fichas:
        id_, estado, responsavel = linha.split()[:3]
        assert (estado, responsavel) == esperado[id_][:2]
        assert linha.rstrip().endswith(esperado[id_][2])

    resumo = (
        "Resumo: 1 passing · 2 in_progress · 1 not_started · 0 blocked · 0 regressed"
    )
    assert resumo in [linha.strip() for linha in linhas]


# ---------------------------------------------------------------------------
# HX-03 c2: referências inconsistentes entre campos
# ---------------------------------------------------------------------------


def test_id_diferente_do_nome_do_arquivo(tmp_path, capsys):
    # arquivo T-01.json, mas a ficha diz que é T-99
    gravar(tmp_path, ficha_valida(id="T-99"), nome="T-01")

    codigo, out, err = rodar_state(tmp_path, capsys)

    assert codigo == 2
    assert out == ""
    assert "T-01" in err
    assert "T-99" in err
    assert "id" in err.lower()


def test_criterio_sem_verificacao(tmp_path):
    gravar(
        tmp_path,
        ficha_valida(
            criterios=[
                {
                    "id": "c1",
                    "descricao": "um",
                    "exemplo": {"entrada": "a", "saida": "b"},
                },
                {
                    "id": "c2",
                    "descricao": "dois",
                    "exemplo": {"entrada": "a", "saida": "b"},
                },
            ],
            # só o c1 tem verificação
            verificacao=[{"criterio": "c1", "comando": "pytest tests/x.py -q"}],
        ),
    )

    problemas = problemas_do_repo(tmp_path)

    assert len(problemas) == 1
    assert citam(problemas, "T-01", "c2", "verifica")


def test_verificacao_para_criterio_inexistente(tmp_path):
    gravar(
        tmp_path,
        ficha_valida(
            verificacao=[
                {"criterio": "c1", "comando": "pytest tests/x.py -q"},
                {"criterio": "c9", "comando": "pytest tests/y.py -q"},
            ],
        ),
    )

    problemas = problemas_do_repo(tmp_path)

    assert len(problemas) == 1
    assert citam(problemas, "T-01", "c9")


def test_depende_de_inexistente(tmp_path):
    gravar(tmp_path, ficha_valida(depende_de=["T-99"]))

    problemas = problemas_do_repo(tmp_path)

    assert len(problemas) == 1
    assert citam(problemas, "T-01", "T-99")


def test_ciclo_de_dependencia(tmp_path):
    def cita_ciclo(problemas, *ids):
        return [
            p
            for p in problemas
            if any(i in p for i in ids)
            and any(t in p.lower() for t in ("ciclo", "circular"))
        ]

    # controle: dependência em linha reta é válida
    reta = tmp_path / "reta"
    gravar(reta, ficha_valida(id="T-01"))
    gravar(reta, ficha_valida(id="T-02", depende_de=["T-01"]))
    assert problemas_do_repo(reta) == []

    # A -> B -> A
    ciclo = tmp_path / "ciclo"
    gravar(ciclo, ficha_valida(id="T-01", depende_de=["T-02"]))
    gravar(ciclo, ficha_valida(id="T-02", depende_de=["T-01"]))
    problemas = problemas_do_repo(ciclo)
    assert cita_ciclo(problemas, "T-01", "T-02")

    # auto-dependência
    auto = tmp_path / "auto"
    gravar(auto, ficha_valida(id="T-03", depende_de=["T-03"]))
    problemas = problemas_do_repo(auto)
    assert any(
        "T-03" in p
        and any(
            t in p.lower() for t in ("ciclo", "circular", "si mesm", "própria", "auto")
        )
        for p in problemas
    )


# ---------------------------------------------------------------------------
# HX-03 c3: estado incoerente com os demais campos
# ---------------------------------------------------------------------------


def test_estado_invalido(tmp_path):
    gravar(tmp_path, ficha_valida(estado="feito"))

    problemas = problemas_do_repo(tmp_path)

    assert len(problemas) == 1
    assert citam(problemas, "T-01", "estado")


@pytest.mark.parametrize("bloqueada_por", [None, "", []])
def test_blocked_sem_bloqueada_por(tmp_path, bloqueada_por):
    gravar(tmp_path, ficha_valida(estado="blocked", bloqueada_por=bloqueada_por))

    problemas = problemas_do_repo(tmp_path)

    assert len(problemas) == 1
    assert citam(problemas, "T-01", "bloqueada_por")


@pytest.mark.parametrize("responsavel", [None, ""])
def test_in_progress_sem_responsavel(tmp_path, responsavel):
    gravar(tmp_path, ficha_valida(estado="in_progress", responsavel=responsavel))

    problemas = problemas_do_repo(tmp_path)

    assert len(problemas) == 1
    assert citam(problemas, "T-01", "responsavel")


@pytest.mark.parametrize("evidencia", [None, ""])
def test_passing_sem_evidencia(tmp_path, evidencia):
    gravar(tmp_path, ficha_valida(estado="passing", evidencia=evidencia))

    problemas = problemas_do_repo(tmp_path)

    assert len(problemas) == 1
    assert citam(problemas, "T-01", "evidencia")


def test_not_started_com_evidencia(tmp_path):
    gravar(tmp_path, ficha_valida(estado="not_started", evidencia="pytest passou"))

    problemas = problemas_do_repo(tmp_path)

    assert len(problemas) == 1
    assert citam(problemas, "T-01", "evidencia")


@pytest.mark.parametrize(
    "campo", ["titulo", "modulo", "estado", "criterios", "verificacao"]
)
def test_campo_obrigatorio_ausente(tmp_path, campo):
    ficha = ficha_valida()
    del ficha[campo]
    gravar(tmp_path, ficha)

    problemas = problemas_do_repo(tmp_path)  # não pode estourar KeyError

    assert citam(problemas, "T-01", campo)


# ---------------------------------------------------------------------------
# HX-03 c4: entrada inválida não lista nada e acumula os problemas
# ---------------------------------------------------------------------------


def test_sem_fichas_erra(tmp_path, capsys):
    (tmp_path / "features").mkdir()

    codigo, out, err = rodar_state(tmp_path, capsys)

    assert codigo == 2
    assert out == ""
    assert "ERRO:" in err and "MOTIVO:" in err and "CORREÇÃO:" in err
    assert re.search(r"ficha|features", err, re.IGNORECASE)


def test_json_quebrado_aponta_arquivo(tmp_path, capsys):
    gravar(tmp_path, ficha_valida(id="T-01"))
    # vírgula sobrando na linha 3: o Python 3.12 reclama na linha 4 (a chave) e o 3.13 na 3 (a vírgula)
    quebrado = tmp_path / "features" / "T-02.json"
    quebrado.write_bytes(b'{\n  "id": "T-02",\n  "estado": "not_started",\n}\n')

    with pytest.raises(HarnessErro) as erro:
        carregar_fichas(tmp_path)
    assert "T-02.json" in erro.value.motivo
    assert re.search(r"(linha|line)\s*[34]", erro.value.motivo, re.IGNORECASE)

    codigo, out, err = rodar_state(tmp_path, capsys)

    assert codigo == 2
    assert out == ""
    assert "T-02.json" in err


def test_ficha_invalida_nao_imprime_tabela(tmp_path, capsys):
    gravar(tmp_path, ficha_valida(id="T-01", estado="feito"))
    gravar(tmp_path, ficha_valida(id="T-02"))  # esta é válida, mas não pode aparecer

    codigo, out, err = rodar_state(tmp_path, capsys)

    assert codigo == 2
    assert out == ""
    assert "T-02" not in out
    assert err.startswith("ERRO:")
    assert "rode hx state de novo" in err


def test_acumula_varios_problemas(tmp_path, capsys):
    gravar(tmp_path, ficha_valida(id="T-01", estado="feito"))
    gravar(tmp_path, ficha_valida(id="T-02", estado="blocked", bloqueada_por=None))

    problemas = problemas_do_repo(tmp_path)
    assert len(problemas) == 2
    assert citam(problemas, "T-01", "estado")
    assert citam(problemas, "T-02", "bloqueada_por")

    codigo, out, err = rodar_state(tmp_path, capsys)

    assert codigo == 2
    assert out == ""
    assert re.findall(r"- (T-\d+):", err) == ["T-01", "T-02"]
    assert "CORREÇÃO:" in err
