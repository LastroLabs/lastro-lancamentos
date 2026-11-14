"""Fase C do harness: HX-06 (`hx verify`: ruff e pytest no container).

Nenhum teste chama docker de verdade: `harness._executar` e `shutil.which` são sempre
substituídos. O fake de `_executar` grava cada chamada e responde conforme o passo
(docker info, ruff ou pytest), identificado pelo que vem depois de `dev` no comando.
"""

import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import harness  # precisa vir depois do ajuste do sys.path

OK = (0, "tudo certo\n")


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------


def _passo(cmd):
    """Nome legível do passo: o que vem depois de `dev` (ou o comando inteiro, ex.: docker info)."""
    cmd = list(cmd)
    if "dev" in cmd:
        return " ".join(cmd[cmd.index("dev") + 1 :])
    return " ".join(cmd)


class Docker:
    """Substitui `_executar`: grava as chamadas e devolve (código, saída) por passo."""

    def __init__(self, info=OK, ruff=OK, pytest_=OK):
        self.respostas = {"docker info": info, "ruff check .": ruff, "pytest -q": pytest_}
        self.chamadas = []

    def __call__(self, cmd, cwd):
        self.chamadas.append(list(cmd))
        passo = _passo(cmd)
        if passo not in self.respostas:
            raise AssertionError(f"chamada inesperada: {cmd}")
        return self.respostas[passo]

    @property
    def passos(self):
        """Passos chamados, sem o `docker info` da checagem de ambiente."""
        return [_passo(c) for c in self.chamadas if _passo(c) != "docker info"]


@pytest.fixture
def docker_ok(monkeypatch):
    """Docker presente no PATH; devolve uma função para instalar o fake de `_executar`."""
    monkeypatch.setattr(shutil, "which", lambda nome, *a, **k: f"/usr/bin/{nome}")

    def instalar(**respostas):
        fake = Docker(**respostas)
        monkeypatch.setattr(harness, "_executar", fake)
        return fake

    return instalar


def _verify(tmp_path, capsys):
    codigo = harness.main(["verify"], raiz=tmp_path)
    saida = capsys.readouterr()
    return codigo, saida.out, saida.err


# ---------------------------------------------------------------------------
# c1: montagem do comando (função pura)
# ---------------------------------------------------------------------------


def test_montar_comando_posix_com_user():
    cmd = harness.montar_comando_docker(["pytest", "-q"], True, 1000, 1000)
    assert cmd == [
        "docker", "compose", "run", "--rm", "-T", "--user", "1000:1000", "dev", "pytest", "-q",
    ]  # fmt: skip
    # --user fica entre -T e dev
    assert cmd.index("-T") < cmd.index("--user") < cmd.index("dev")


def test_montar_comando_windows_sem_user():
    cmd = harness.montar_comando_docker(["ruff", "check", "."], False)
    assert cmd == ["docker", "compose", "run", "--rm", "-T", "dev", "ruff", "check", "."]
    assert "--user" not in cmd


# ---------------------------------------------------------------------------
# c2: ordem e falhas
# ---------------------------------------------------------------------------


def test_ordem_ruff_antes_de_pytest(tmp_path, capsys, docker_ok):
    fake = docker_ok()
    codigo, _, _ = _verify(tmp_path, capsys)
    assert codigo == 0
    assert fake.passos == ["ruff check .", "pytest -q"]


def test_ruff_falha_ainda_roda_pytest(tmp_path, capsys, docker_ok):
    fake = docker_ok(ruff=(1, "E501 linha longa\n"))
    codigo, _, _ = _verify(tmp_path, capsys)
    assert fake.passos == ["ruff check .", "pytest -q"]  # pytest roda mesmo com o ruff vermelho
    assert codigo == 1


def test_pytest_falha_exit_1(tmp_path, capsys, docker_ok):
    fake = docker_ok(pytest_=(1, "1 failed\n"))
    codigo, _, _ = _verify(tmp_path, capsys)
    assert fake.passos == ["ruff check .", "pytest -q"]
    assert codigo == 1


def test_pytest_nenhum_teste_coletado_e_falha(tmp_path, capsys, docker_ok):
    docker_ok(pytest_=(5, "no tests ran\n"))
    codigo, out, err = _verify(tmp_path, capsys)
    assert codigo == 1  # código 5 do pytest conta como falha, não como sucesso
    assert "nenhum teste" in (out + err).lower()  # mensagem própria, não só a saída crua


# ---------------------------------------------------------------------------
# c3: Docker ausente ou desligado é erro de ambiente (código 2)
# ---------------------------------------------------------------------------


def _confere_erro_de_docker(err):
    assert "ERRO: Docker indisponível" in err
    assert "MOTIVO:" in err
    assert "docker info" in err
    assert "CORREÇÃO:" in err


def test_docker_ausente_exit_2(tmp_path, capsys, monkeypatch):
    chamadas = []
    monkeypatch.setattr(shutil, "which", lambda nome, *a, **k: None)
    monkeypatch.setattr(harness, "_executar", lambda cmd, cwd: chamadas.append(cmd) or OK)
    codigo, _, err = _verify(tmp_path, capsys)
    assert codigo == 2  # erro de ambiente, não falha de código
    _confere_erro_de_docker(err)
    assert not any("ruff" in c or "pytest" in c for chamada in chamadas for c in chamada)


def test_docker_daemon_desligado_exit_2(tmp_path, capsys, docker_ok):
    fake = docker_ok(info=(1, "Cannot connect to the Docker daemon\n"))
    codigo, _, err = _verify(tmp_path, capsys)
    assert codigo == 2
    _confere_erro_de_docker(err)
    assert fake.passos == []  # nem ruff nem pytest chegaram a rodar


# ---------------------------------------------------------------------------
# c4: resumo e cauda da saída
# ---------------------------------------------------------------------------


def test_tudo_ok_exit_0_e_mostra_pulados(tmp_path, capsys, docker_ok):
    docker_ok()
    codigo, out, _ = _verify(tmp_path, capsys)
    assert codigo == 0
    assert "[1/2] ruff check ." in out
    assert "[2/2] pytest -q" in out
    assert "Arquitetura: PULADO (ainda não implementado)" in out
    assert "E2E: PULADO (ainda não implementado)" in out
    assert "RESULTADO: OK" in out


def test_falha_mostra_cauda_da_saida(tmp_path, capsys, docker_ok):
    cem_linhas = "".join(f"SAIDA-{i:03d}\n" for i in range(1, 101))
    docker_ok(pytest_=(1, cem_linhas))
    codigo, out, err = _verify(tmp_path, capsys)
    tudo = out + err
    assert codigo == 1
    mostradas = [i for i in range(1, 101) if f"SAIDA-{i:03d}" in tudo]
    assert mostradas == list(range(61, 101))  # só as últimas 40 linhas
