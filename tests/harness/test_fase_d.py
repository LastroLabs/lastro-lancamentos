"""Fase D do harness: HX-07 (`hx feature verify <ID>`).

Nenhum teste chama git ou docker de verdade: `harness._executar` (git e docker), `shutil.which`
e `harness._agora` são sempre substituídos. Cada teste monta fichas em tmp_path/features/.
Só dados sintéticos.

Contrato assumido (docs do plano, fase d):
- `harness._agora()` devolve o instante atual como texto ISO 8601 em UTC com Z.
- o commit vem de `git rev-parse --short=12 HEAD`; a árvore limpa, de `git status --porcelain`.
- cada verificação roda via `docker compose run ... dev <comando da ficha>`.
- ordem das checagens: fichas válidas → ID existe → estado permitido → árvore limpa → docker.
- o `hx` não faz commit: só imprime o pedido para o dev fazer.
"""

import copy
import json
import shlex
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import harness  # precisa vir depois do ajuste do sys.path

AGORA = "2026-11-13T14:02:11Z"
COMMIT = "a1b2c3d4e5f6"
CMD_A = "pytest tests/x.py::test_a -q"
CMD_B = "pytest tests/x.py::test_b -q"

EVIDENCIA_ANTIGA = {
    "verificado_em": "2026-11-01T08:00:00Z",
    "commit": "000000000000",
    "resultados": [
        {"criterio": "c1", "comando": CMD_A, "resultado": "ok"},
        {"criterio": "c2", "comando": CMD_B, "resultado": "ok"},
    ],
}

SUJO = " M features/HX-01.json\n"


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------


def _ficha(id_="HX-01", estado="in_progress", verificacao=None, **override):
    """Ficha sintética válida com 2 critérios e 2 verificações. `override` troca campos."""
    ficha = {
        "id": id_,
        "titulo": "Ficha de teste",
        "modulo": "harness",
        "requisitos": [],
        "prioridade": "must",
        "onda": 1,
        "essencial": False,
        "estado": estado,
        "responsavel": "caio",
        "depende_de": [],
        "bloqueada_por": None,
        "tipo_verificacao": "comando",
        "criterios": [
            {"id": "c1", "descricao": "Faz a", "exemplo": {"entrada": "x", "saida": "y"}},
            {"id": "c2", "descricao": "Faz b", "exemplo": {"entrada": "x", "saida": "y"}},
        ],
        "verificacao": verificacao
        or [
            {"criterio": "c1", "comando": CMD_A},
            {"criterio": "c2", "comando": CMD_B},
        ],
        "evidencia": None,
    }
    if estado == "passing":
        ficha["evidencia"] = copy.deepcopy(EVIDENCIA_ANTIGA)
    ficha.update(override)
    return ficha


def _gravar(raiz, ficha):
    """Grava a ficha no formato do harness e devolve o caminho."""
    pasta = Path(raiz) / "features"
    pasta.mkdir(exist_ok=True)
    caminho = pasta / f"{ficha['id']}.json"
    harness.salvar_ficha(caminho, ficha)
    return caminho


def _ler(caminho):
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


class Ambiente:
    """Substitui `_executar`: grava as chamadas e responde por tipo (git, docker info, run).

    Qualquer chamada fora dessa lista (ex.: `git commit`) derruba o teste.
    """

    def __init__(self, sujo="", commit=COMMIT, info=(0, "ok\n"), resultados=None):
        self.sujo = sujo
        self.commit = commit
        self.info = info
        self.resultados = resultados or {}  # comando da ficha -> (código, saída)
        self.chamadas = []  # (tipo, cmd)

    def __call__(self, cmd, cwd):
        cmd = list(cmd)
        if cmd[0] == "git" and "status" in cmd:
            tipo, resposta = "status", (0, self.sujo)
        elif cmd[0] == "git" and "rev-parse" in cmd:
            assert "--short=12" in cmd and "HEAD" in cmd, f"rev-parse fora do contrato: {cmd}"
            tipo, resposta = "rev-parse", (0, self.commit + "\n")
        elif cmd[:2] == ["docker", "info"]:
            tipo, resposta = "info", self.info
        elif cmd[:3] == ["docker", "compose", "run"] and "dev" in cmd:
            comando = " ".join(cmd[cmd.index("dev") + 1 :])
            tipo, resposta = "run", self.resultados.get(comando, (0, "passou\n"))
        else:
            raise AssertionError(f"chamada inesperada: {cmd}")
        self.chamadas.append((tipo, cmd))
        return resposta

    @property
    def tipos(self):
        return [t for t, _ in self.chamadas]

    @property
    def execucoes(self):
        """Comandos da ficha enviados ao container, na ordem, sem o prefixo do docker."""
        return [" ".join(c[c.index("dev") + 1 :]) for t, c in self.chamadas if t == "run"]


@pytest.fixture
def ambiente(monkeypatch):
    """Docker no PATH, relógio fixo e `_executar` falso. Devolve `instalar(**opções)`."""
    monkeypatch.setattr(shutil, "which", lambda nome, *a, **k: f"/usr/bin/{nome}")
    monkeypatch.setattr(harness, "_agora", lambda: AGORA)

    def instalar(**opcoes):
        fake = Ambiente(**opcoes)
        monkeypatch.setattr(harness, "_executar", fake)
        return fake

    return instalar


def _verificar(tmp_path, capsys, id_="HX-01"):
    codigo = harness.main(["feature", "verify", id_], raiz=tmp_path)
    saida = capsys.readouterr()
    return codigo, saida.out, saida.err


def _linha_com(texto, trecho):
    """Primeira linha da saída que contém `trecho` (ou falha mostrando a saída)."""
    for linha in texto.splitlines():
        if trecho in linha:
            return linha
    raise AssertionError(f"nenhuma linha com {trecho!r} em:\n{texto}")


def _confere_erro(err):
    assert "ERRO:" in err
    assert "MOTIVO:" in err
    assert "CORREÇÃO:" in err


# ---------------------------------------------------------------------------
# c1: pré-condições impedem a verificação (exit 2, ficha intacta, nada executado)
# ---------------------------------------------------------------------------


def test_id_inexistente(tmp_path, capsys, ambiente):
    fake = ambiente()
    a = _gravar(tmp_path, _ficha("HX-01"))
    b = _gravar(tmp_path, _ficha("HX-02"))
    antes = (a.read_bytes(), b.read_bytes())

    codigo, _, err = _verificar(tmp_path, capsys, "ZZ-99")

    assert codigo == 2
    _confere_erro(err)
    assert "ZZ-99" in err
    assert "HX-01" in err and "HX-02" in err  # lista os IDs disponíveis
    assert fake.execucoes == []
    assert (a.read_bytes(), b.read_bytes()) == antes


def test_not_started_manda_rodar_start(tmp_path, capsys, ambiente):
    fake = ambiente()
    caminho = _gravar(tmp_path, _ficha(estado="not_started"))
    antes = caminho.read_bytes()

    codigo, _, err = _verificar(tmp_path, capsys)

    assert codigo == 2
    _confere_erro(err)
    assert "not_started" in err
    assert "hx feature start HX-01" in err
    assert fake.execucoes == []
    assert caminho.read_bytes() == antes


def test_blocked_mostra_bloqueio(tmp_path, capsys, ambiente):
    fake = ambiente()
    caminho = _gravar(tmp_path, _ficha(estado="blocked", bloqueada_por="D-05"))
    antes = caminho.read_bytes()

    codigo, _, err = _verificar(tmp_path, capsys)

    assert codigo == 2
    _confere_erro(err)
    assert "D-05" in err  # cita bloqueada_por
    assert fake.execucoes == []
    assert caminho.read_bytes() == antes


def test_arvore_suja_recusa(tmp_path, capsys, ambiente):
    fake = ambiente(sujo=SUJO)
    caminho = _gravar(tmp_path, _ficha())
    antes = caminho.read_bytes()

    codigo, _, err = _verificar(tmp_path, capsys)

    assert codigo == 2
    _confere_erro(err)
    assert "status" in fake.tipos  # perguntou ao git
    assert fake.execucoes == []  # evidência de árvore suja não é reproduzível
    assert caminho.read_bytes() == antes


def test_ficha_invalida_em_outra_feature_recusa(tmp_path, capsys, ambiente):
    fake = ambiente()
    boa = _gravar(tmp_path, _ficha("HX-01"))
    ruim = _gravar(tmp_path, _ficha("HX-02", estado="estado_que_nao_existe"))
    antes = (boa.read_bytes(), ruim.read_bytes())

    codigo, _, err = _verificar(tmp_path, capsys, "HX-01")

    assert codigo == 2  # a validação é global, não só da ficha pedida
    _confere_erro(err)
    assert "HX-02" in err
    assert fake.execucoes == []
    assert (boa.read_bytes(), ruim.read_bytes()) == antes


def test_docker_indisponivel_exit_2(tmp_path, capsys, ambiente):
    fake = ambiente(info=(1, "Cannot connect to the Docker daemon\n"))
    caminho = _gravar(tmp_path, _ficha())
    antes = caminho.read_bytes()

    codigo, _, err = _verificar(tmp_path, capsys)

    assert codigo == 2  # erro de ambiente, não falha de código
    assert "ERRO: Docker indisponível" in err  # reuso da fase c
    _confere_erro(err)
    assert fake.execucoes == []
    assert caminho.read_bytes() == antes


# ---------------------------------------------------------------------------
# c2: todas as verificações passam
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("estado", ["in_progress", "regressed"])
def test_todas_ok_marca_passing_e_grava_evidencia(tmp_path, capsys, ambiente, estado):
    ambiente()
    caminho = _gravar(tmp_path, _ficha(estado=estado))

    codigo, out, _ = _verificar(tmp_path, capsys)

    assert codigo == 0
    depois = _ler(caminho)
    assert depois["estado"] == "passing"
    assert depois["evidencia"] == {
        "verificado_em": AGORA,  # relógio injetado
        "commit": COMMIT,  # 12 caracteres, de git rev-parse --short=12 HEAD
        "resultados": [
            {"criterio": "c1", "comando": CMD_A, "resultado": "ok"},
            {"criterio": "c2", "comando": CMD_B, "resultado": "ok"},
        ],
    }
    assert "Ficha atualizada" in out
    assert "features/HX-01.json" in out  # pede o commit da ficha
    for criterio, comando in (("c1", CMD_A), ("c2", CMD_B)):
        linha = _linha_com(out, comando)
        assert criterio in linha and "OK" in linha and "FALHOU" not in linha


def test_executa_cada_verificacao_na_ordem(tmp_path, capsys, ambiente):
    fake = ambiente()
    verificacao = [
        {"criterio": "c2", "comando": CMD_B},  # ordem da ficha, não a dos critérios
        {"criterio": "c1", "comando": CMD_A},
        {"criterio": "c1", "comando": "ruff check src"},
    ]
    _gravar(tmp_path, _ficha(verificacao=verificacao))

    codigo, _, _ = _verificar(tmp_path, capsys)

    assert codigo == 0
    assert fake.execucoes == [CMD_B, CMD_A, "ruff check src"]
    # cada comando vai ao container (docker compose run ... dev), um argumento por token, sem shell
    rodadas = [cmd for tipo, cmd in fake.chamadas if tipo == "run"]
    assert [c[c.index("dev") + 1 :] for c in rodadas] == [
        shlex.split(CMD_B), shlex.split(CMD_A), ["ruff", "check", "src"],
    ]  # fmt: skip
    # primeiro a árvore, depois o docker, só então as verificações
    assert fake.tipos.index("status") < fake.tipos.index("info") < fake.tipos.index("run")


def test_so_estado_e_evidencia_mudam(tmp_path, capsys, ambiente):
    fake = ambiente()
    caminho = _gravar(tmp_path, _ficha())
    antes = _ler(caminho)

    assert _verificar(tmp_path, capsys)[0] == 0
    depois = _ler(caminho)

    assert list(depois) == list(antes)  # mesmas chaves, na mesma ordem
    mudaram = {k for k in antes if antes[k] != depois[k]}
    assert mudaram == {"estado", "evidencia"}

    # o mesmo vale quando a verificação falha numa ficha passing
    fake.resultados[CMD_B] = (1, "1 failed\n")
    antes = _ler(caminho)
    assert _verificar(tmp_path, capsys)[0] == 1
    depois = _ler(caminho)
    assert list(depois) == list(antes)
    assert {k for k in antes if antes[k] != depois[k]} == {"estado"}


# ---------------------------------------------------------------------------
# c3: verificação que falha
# ---------------------------------------------------------------------------


def test_falha_em_in_progress_nao_altera_ficha(tmp_path, capsys, ambiente):
    ambiente(resultados={CMD_B: (1, "1 failed\n")})
    caminho = _gravar(tmp_path, _ficha(estado="in_progress"))
    antes = caminho.read_bytes()

    codigo, out, _ = _verificar(tmp_path, capsys)

    assert codigo == 1  # falha esperada, não erro de uso
    assert caminho.read_bytes() == antes  # mesmos bytes
    assert "OK" in _linha_com(out, CMD_A)
    linha_ruim = _linha_com(out, CMD_B)
    assert "c2" in linha_ruim and "FALHOU" in linha_ruim  # lista o critério que falhou


def test_falha_em_passing_vira_regressed(tmp_path, capsys, ambiente):
    ambiente(resultados={CMD_A: (1, "1 failed\n")})
    caminho = _gravar(tmp_path, _ficha(estado="passing"))

    codigo, out, _ = _verificar(tmp_path, capsys)

    assert codigo == 1
    depois = _ler(caminho)
    assert depois["estado"] == "regressed"
    assert depois["evidencia"] == EVIDENCIA_ANTIGA  # fica, para auditoria
    linha_ruim = _linha_com(out, CMD_A)
    assert "c1" in linha_ruim and "FALHOU" in linha_ruim


# ---------------------------------------------------------------------------
# c4: reverificar e allowlist
# ---------------------------------------------------------------------------


def test_reverifica_passing_atualiza_evidencia(tmp_path, capsys, ambiente, monkeypatch):
    ambiente(commit="ffffeeee1111")
    nova_data = "2026-11-14T09:30:00Z"
    monkeypatch.setattr(harness, "_agora", lambda: nova_data)
    caminho = _gravar(tmp_path, _ficha(estado="passing"))

    codigo, _, _ = _verificar(tmp_path, capsys)

    assert codigo == 0
    depois = _ler(caminho)
    assert depois["estado"] == "passing"
    assert depois["evidencia"]["verificado_em"] == nova_data
    assert depois["evidencia"]["commit"] == "ffffeeee1111"
    assert depois["evidencia"] != EVIDENCIA_ANTIGA
    assert [r["resultado"] for r in depois["evidencia"]["resultados"]] == ["ok", "ok"]


def test_comando_fora_da_allowlist_recusado(tmp_path, capsys, ambiente, monkeypatch):
    fake = ambiente()
    motivo = "MOTIVO-FALSO-DA-ALLOWLIST"
    original = harness.validar_comando
    vistos = []

    def validar(cmd):
        # 1ª vez (validação global das fichas): ok. Depois (defesa em profundidade): recusa.
        vistos.append(cmd)
        return None if vistos.count(cmd) == 1 else motivo

    monkeypatch.setattr(harness, "validar_comando", validar)
    caminho = _gravar(
        tmp_path, _ficha(verificacao=[{"criterio": "c1", "comando": CMD_A}, {"criterio": "c2", "comando": CMD_B}])
    )
    antes = caminho.read_bytes()
    assert original(CMD_A) is None  # a ficha é mesmo válida de verdade

    codigo, _, err = _verificar(tmp_path, capsys)

    assert vistos.count(CMD_A) >= 2  # validou de novo na hora de executar
    assert codigo == 2
    _confere_erro(err)
    assert motivo in err
    assert fake.execucoes == []  # recusado antes de executar
    assert caminho.read_bytes() == antes
