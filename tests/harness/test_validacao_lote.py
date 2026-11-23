"""HAR-04: regras de 18/11 na validação das fichas (`hx state`) e CNPJ alfanumérico no check-clean.

Cada teste monta um mini-repo em tmp_path com features/*.json e uma cópia de
gitpages/src/data/equipe.ts: é esse arquivo que liga as regras novas (opção A do plan).
Sem ele, o validador se comporta como antes, e os testes antigos não mudam.
Exceção: c1(a) roda o `hx state` na raiz real, só lendo.

ATENÇÃO: o próprio repositório é varrido pelo check-clean. Nenhum CNPJ com DV válido
aparece inteiro neste arquivo: o DV é calculado em tempo de execução e o valor só é
escrito em arquivos de tmp_path. Fichas, handles inventados e CNPJs são sintéticos.
"""

import json
import re
import shutil
import sys
from pathlib import Path

import pytest

RAIZ_REAL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ_REAL / "tools"))

import harness

EQUIPE_TS = Path("gitpages") / "src" / "data" / "equipe.ts"
HANDLE_DA_EQUIPE = "caio-nascime"  # handle citado no exemplo c6(b) da ficha
MODULOS_ACEITOS = (
    "core",
    "access",
    "registry",
    "uploads",
    "parsing",
    "validation",
    "classification",
    "questions",
    "review",
    "export",
    "ai",
    "observability",
    "api",
    "worker",
    "harness",
    "ci",
    "web",
)
TIPO_CNPJ = "CNPJ com dígito verificador válido"


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------


def ficha(id_, **override):
    """Ficha sintética válida pelas regras novas; o nome de teste deriva do ID (único)."""
    nome_teste = "test_" + id_.lower().replace("-", "_")
    dados = {
        "id": id_,
        "titulo": f"Ficha {id_}",
        "modulo": "harness",
        "requisitos": [],
        "prioridade": "must",
        "onda": 1,
        "essencial": False,
        "estado": "not_started",
        "responsavel": HANDLE_DA_EQUIPE,
        "depende_de": [],
        "bloqueada_por": None,
        "tipo_verificacao": "comando",
        "criterios": [
            {"id": "c1", "descricao": "Faz a coisa", "exemplo": {"entrada": "x", "saida": "y"}}
        ],
        "verificacao": [
            {"criterio": "c1", "comando": f"pytest tests/harness/test_inventado.py::{nome_teste} -q"}
        ],
        "evidencia": None,
    }
    dados.update(override)
    return dados


def montar_repo(raiz, fichas):
    """Grava as fichas (arquivo = campo id) e copia o equipe.ts real, que liga as regras."""
    pasta = Path(raiz) / "features"
    pasta.mkdir(parents=True, exist_ok=True)
    for f in fichas:
        texto = json.dumps(f, indent=2, ensure_ascii=False) + "\n"
        (pasta / f"{f['id']}.json").write_bytes(texto.encode("utf-8"))
    destino = Path(raiz) / EQUIPE_TS
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(RAIZ_REAL / EQUIPE_TS, destino)


def ficha_real(id_):
    """Ficha do repositório, como está (só leitura)."""
    return json.loads((RAIZ_REAL / "features" / f"{id_}.json").read_text(encoding="utf-8"))


def rodar_state(raiz, capsys):
    codigo = harness.main(["state"], raiz=raiz)
    saida = capsys.readouterr()
    return codigo, saida.out, saida.err


def cita(err, *termos):
    """True se alguma linha de `err` contém todos os termos (cada um como palavra inteira)."""
    for linha in err.splitlines():
        if all(re.search(rf"(?<![\w-]){re.escape(t)}(?![\w-])", linha) for t in termos):
            return True
    return False


def assert_recusa(codigo, out, err, ids, *citados):
    """Recusa padrão: código 2, ERRO/MOTIVO/CORREÇÃO, cita ficha e campo, não lista fichas."""
    assert codigo == 2, f"esperava código 2, veio {codigo}\nstdout:\n{out}\nstderr:\n{err}"
    for rotulo in ("ERRO:", "MOTIVO:", "CORREÇÃO:"):
        assert rotulo in err, f"faltou '{rotulo}' em stderr:\n{err}"
    assert cita(err, *citados), f"nenhuma linha cita {citados}:\n{err}"
    listados = [i for i in ids if re.search(rf"^{re.escape(i)}\s", out, re.MULTILINE)]
    assert not listados, f"não devia listar fichas, listou {listados}:\n{out}"


def assert_aceita(codigo, out, err):
    assert codigo == 0, f"esperava código 0, veio {codigo}\nstdout:\n{out}\nstderr:\n{err}"


# ---------------------------------------------------------------------------
# c1: campo a mais é recusado
# ---------------------------------------------------------------------------


def test_campo_extra_recusado(tmp_path, capsys):
    # (a) as fichas atuais do repositório passam
    codigo, out, err = rodar_state(RAIZ_REAL, capsys)
    assert_aceita(codigo, out, err)

    # (b) ficha válida que ganhou o campo 'notas'
    fichas = [ficha("HAR-91", notas="lembrar de revisar"), ficha("HAR-92")]
    montar_repo(tmp_path, fichas)
    codigo, out, err = rodar_state(tmp_path, capsys)
    assert_recusa(codigo, out, err, ["HAR-91", "HAR-92"], "HAR-91", "notas")


# ---------------------------------------------------------------------------
# c2: ID segue ^[A-Z]{2,4}-\d{2}$
# ---------------------------------------------------------------------------


def test_id_fora_do_padrao_recusado(tmp_path, capsys):
    # (a) 'ACE-1' em ACE-1.json: id igual ao arquivo, mas fora do padrão
    recusada = tmp_path / "recusada"
    montar_repo(recusada, [ficha("ACE-1", modulo="access"), ficha("HAR-91")])
    codigo, out, err = rodar_state(recusada, capsys)
    assert_recusa(codigo, out, err, ["ACE-1", "HAR-91"], "ACE-1", "id")

    # (b) 'CI-01' com modulo 'ci' e (c) HX-10 como está: aceitas
    aceitas = tmp_path / "aceitas"
    montar_repo(aceitas, [ficha("CI-01", modulo="ci"), ficha_real("HX-10")])
    codigo, out, err = rodar_state(aceitas, capsys)
    assert_aceita(codigo, out, err)


# ---------------------------------------------------------------------------
# c3: módulo é um dos 17 aceitos
# ---------------------------------------------------------------------------


def test_modulo_desconhecido_recusado(tmp_path, capsys):
    montar_repo(tmp_path, [ficha("HAR-91", modulo="financeiro"), ficha("HAR-92")])
    codigo, out, err = rodar_state(tmp_path, capsys)
    assert_recusa(codigo, out, err, ["HAR-91", "HAR-92"], "HAR-91", "modulo")

    correcao = err[err.index("CORREÇÃO:") :]
    faltando = [m for m in MODULOS_ACEITOS if not re.search(rf"\b{m}\b", correcao)]
    assert not faltando, f"a CORREÇÃO não lista {faltando}:\n{correcao}"


# ---------------------------------------------------------------------------
# c4: prioridade must/should/could; onda de 1 a 4
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("override", "campo"),
    [
        ({"prioridade": "urgente"}, "prioridade"),  # (a)
        ({"onda": 5}, "onda"),  # (b)
    ],
    ids=["prioridade_urgente", "onda_5"],
)
def test_prioridade_e_onda_validadas(tmp_path, capsys, override, campo):
    recusada = tmp_path / "recusada"
    montar_repo(recusada, [ficha("HAR-91", **override), ficha("HAR-92")])
    codigo, out, err = rodar_state(recusada, capsys)
    assert_recusa(codigo, out, err, ["HAR-91", "HAR-92"], "HAR-91", campo)

    # (c) prioridade 'should' e onda 2: aceita
    aceita = tmp_path / "aceita"
    montar_repo(aceita, [ficha("HAR-91", prioridade="should", onda=2)])
    codigo, out, err = rodar_state(aceita, capsys)
    assert_aceita(codigo, out, err)


# ---------------------------------------------------------------------------
# c5: essencial false, tipo_verificacao 'comando', bloqueada_por só em blocked
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("override", "campo"),
    [
        ({"essencial": True}, "essencial"),  # (a)
        ({"tipo_verificacao": "manual"}, "tipo_verificacao"),  # (b)
        ({"estado": "not_started", "bloqueada_por": "D-05"}, "bloqueada_por"),  # (c)
    ],
    ids=["essencial_true", "tipo_verificacao_manual", "bloqueada_por_fora_de_blocked"],
)
def test_campos_fixos_validados(tmp_path, capsys, override, campo):
    montar_repo(tmp_path, [ficha("HAR-91", **override), ficha("HAR-92")])
    codigo, out, err = rodar_state(tmp_path, capsys)
    assert_recusa(codigo, out, err, ["HAR-91", "HAR-92"], "HAR-91", campo)


# ---------------------------------------------------------------------------
# c6: responsável é um handle da equipe
# ---------------------------------------------------------------------------


def test_responsavel_fora_da_equipe_recusado(tmp_path, capsys):
    # (a) handle inventado, fora da equipe
    recusada = tmp_path / "recusada"
    montar_repo(recusada, [ficha("HAR-91", responsavel="fulano-inexistente"), ficha("HAR-92")])
    codigo, out, err = rodar_state(recusada, capsys)
    assert_recusa(codigo, out, err, ["HAR-91", "HAR-92"], "HAR-91", "responsavel")

    # (b) handle da equipe: aceita
    aceita = tmp_path / "aceita"
    montar_repo(aceita, [ficha("HAR-91", responsavel=HANDLE_DA_EQUIPE)])
    codigo, out, err = rodar_state(aceita, capsys)
    assert_aceita(codigo, out, err)


# ---------------------------------------------------------------------------
# c7: nome de teste não se repete entre fichas
# ---------------------------------------------------------------------------


def test_nome_de_teste_repetido_entre_fichas_recusado(tmp_path, capsys):
    comando = "pytest tests/harness/test_inventado.py::test_faz_a_mesma_coisa -q"
    repetida = [{"criterio": "c1", "comando": comando}]
    fichas = [
        ficha("HAR-91", verificacao=repetida),
        ficha("HAR-92", verificacao=repetida),
        ficha("HAR-93"),
    ]
    montar_repo(tmp_path, fichas)
    codigo, out, err = rodar_state(tmp_path, capsys)
    assert_recusa(
        codigo, out, err, ["HAR-91", "HAR-92", "HAR-93"], "HAR-91", "HAR-92", "verificacao"
    )


# ---------------------------------------------------------------------------
# c9: check-clean detecta CNPJ alfanumérico com DV válido
# ---------------------------------------------------------------------------

PESOS_DV1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
PESOS_DV2 = (6, *PESOS_DV1)
BASE_ALFANUMERICA = "QX7KM2" + "WZ9P01"  # 12 caracteres inventados


def _dv(valores, pesos):
    resto = sum(v * p for v, p in zip(valores, pesos)) % 11
    return 0 if resto < 2 else 11 - resto


def dvs_do_cnpj(base):
    """Os 2 DVs de uma base de 12 caracteres: cada caractere vale ord(c) - 48 (A = 17)."""
    valores = [ord(c) - 48 for c in base.upper()]
    dv1 = _dv(valores, PESOS_DV1)
    dv2 = _dv([*valores, dv1], PESOS_DV2)
    return f"{dv1}{dv2}"


def mascarar(base, dvs):
    return f"{base[:2]}.{base[2:5]}.{base[5:8]}/{base[8:12]}-{dvs}"


@pytest.fixture
def sem_git_e_sem_nomes(monkeypatch):
    """Varredura pela árvore (sem git real) e sem a lista de nomes da máquina de quem roda."""
    monkeypatch.delenv("LASTRO_NOMES_PROIBIDOS", raising=False)

    def sem_git(cmd, cwd):
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr(harness, "_executar", sem_git)


def test_check_clean_detecta_cnpj_alfanumerico(tmp_path, capsys, sem_git_e_sem_nomes):
    dvs = dvs_do_cnpj(BASE_ALFANUMERICA)
    dvs_errados = f"{(int(dvs[0]) + 1) % 10}{dvs[1]}"
    sem_mascara = BASE_ALFANUMERICA + dvs
    com_mascara_minuscula = mascarar(BASE_ALFANUMERICA, dvs).lower()
    dv_errado = BASE_ALFANUMERICA + dvs_errados

    (tmp_path / "a.txt").write_text(f"linha um\nempresa {sem_mascara} fim\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text(
        f"1\n2\n3\n4\nempresa {com_mascara_minuscula} fim\n", encoding="utf-8"
    )
    (tmp_path / "c.txt").write_text(f"empresa {dv_errado} fim\n", encoding="utf-8")

    codigo = harness.main(["check-clean"], raiz=tmp_path)
    saida = capsys.readouterr()
    out, err = saida.out, saida.err

    achados = re.findall(r"^\s+(\S+):(\d+)\s+(.+?)\s*$", out, re.MULTILINE)
    assert codigo == 1, f"esperava código 1, veio {codigo}\n{out}"
    assert sorted(achados) == [("a.txt", "2", TIPO_CNPJ), ("b.txt", "5", TIPO_CNPJ)], out

    texto = (out + err).upper()
    for valor in (sem_mascara, com_mascara_minuscula, BASE_ALFANUMERICA):
        assert valor.upper() not in texto, "o valor do CNPJ apareceu na saída"
