"""Fase 0 do harness (HX-01): esqueleto do hx, erros padronizados e códigos de saída.

Nenhum teste aqui chama git, docker ou rede.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import harness  # precisa vir depois do ajuste do sys.path


def test_sem_subcomando_sai_com_2():
    with pytest.raises(SystemExit) as saida:
        harness.main([])
    assert saida.value.code == 2


def test_subcomando_desconhecido_sai_com_2():
    with pytest.raises(SystemExit) as saida:
        harness.main(["zzz"])
    assert saida.value.code == 2


def test_harness_erro_vira_codigo_2(tmp_path):
    # tmp_path está vazio (sem features/): `state` não tem o que ler e falha com HarnessErro.
    codigo = harness.main(["state"], raiz=tmp_path)
    assert codigo == 2


def test_formato_do_erro(tmp_path, capsys):
    harness.main(["state"], raiz=tmp_path)
    linhas = [linha for linha in capsys.readouterr().err.splitlines() if linha.strip()]
    assert len(linhas) == 3
    assert linhas[0].startswith("ERRO:")
    assert linhas[1].startswith("MOTIVO:")
    assert linhas[2].startswith("CORREÇÃO:")


def test_main_nao_chama_sys_exit(tmp_path):
    try:
        codigo = harness.main(["state"], raiz=tmp_path)
    except SystemExit:  # pragma: no cover - é justamente o que não pode acontecer
        pytest.fail("main não pode chamar sys.exit para erro de negócio")
    assert isinstance(codigo, int)
    assert not isinstance(codigo, bool)


def test_executar_devolve_codigo_e_saida(tmp_path):
    resultado = harness._executar([sys.executable, "-c", "print(1)"], tmp_path)
    assert resultado == (0, "1\n")


def test_executar_comando_inexistente_levanta(tmp_path):
    with pytest.raises(FileNotFoundError):
        harness._executar(["comando-que-nao-existe-lastro-xyz"], tmp_path)
