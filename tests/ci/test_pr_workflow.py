"""HX-10: o workflow `.github/workflows/pr.yml` roda verify e check-clean na CI.

Os testes leem o YAML do workflow (yaml.safe_load) e conferem as travas combinadas na ficha.
Nada roda no GitHub: só a estrutura do arquivo é provada. Só dados sintéticos.

Contrato assumido (plano D1-D5, tasks T1):
- o arquivo é `.github/workflows/pr.yml`, com caminho calculado a partir deste teste.
- YAML 1.1 lê a chave `on` como booleano True; o teste aceita `True` ou "on".
- jobs `verify` e `check-clean` (nomes fixos), cada um com `sh tools/hx <comando>`.
- único `secrets.*` é LASTRO_NOMES_PROIBIDOS; todo `uses:` termina em @ + 40 hex.
- c5: passo anterior à varredura emite `::warning::` quando a variável está vazia
  e nunca imprime o valor do segredo.
- linhas de comentário são ignoradas (ex.: "# não usar pull_request_target" não conta como uso).

Cada regra é uma função `conferir_*(texto)` que levanta AssertionError. Os testes com o nome da
ficha aplicam a função ao arquivo real; os testes `rejeita_*` provam que a função falha com
um texto inválido montado em tmp_path (dados inventados).
"""

import re
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "pr.yml"
SEGREDO = "LASTRO_NOMES_PROIBIDOS"
SHA_FALSO = "0123456789abcdef0123456789abcdef01234567"
FILTROS = ("branches", "branches-ignore", "paths", "paths-ignore", "tags", "tags-ignore")

VALIDO = f"""\
name: PR
on:
  push:
  pull_request:
permissions:
  contents: read
jobs:
  verify:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@{SHA_FALSO} # v0.0.0
      - run: sh tools/hx verify
  check-clean:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    env:
      {SEGREDO}: ${{{{ secrets.{SEGREDO} }}}}
    steps:
      - uses: actions/checkout@{SHA_FALSO} # v0.0.0
      - name: Avisar se faltar o segredo
        run: |
          if [ -z "${SEGREDO}" ]; then
            echo "::warning::Varredura de nomes pulada: segredo indisponivel (PR de fork?)."
          fi
      - run: sh tools/hx check-clean
"""


def _sem_comentarios(texto):
    return "\n".join(l for l in texto.splitlines() if not l.lstrip().startswith("#"))


def _carregar(texto):
    dados = yaml.safe_load(texto)
    assert isinstance(dados, dict), "workflow vazio ou inválido: o YAML não é um mapa"
    return dados


def _jobs(dados):
    jobs = dados.get("jobs")
    assert isinstance(jobs, dict) and jobs, "workflow sem jobs"
    return jobs


def _passos(job):
    return [p for p in (job.get("steps") or []) if isinstance(p, dict)]


def _gatilhos(dados):
    on = dados.get("on", dados.get(True))
    assert isinstance(on, dict), "falta o bloco `on` com push e pull_request"
    return on


def conferir_gatilhos(texto):
    on = _gatilhos(_carregar(texto))
    for nome in ("push", "pull_request"):
        assert nome in on, f"falta o gatilho {nome}"
        cfg = on[nome]
        if isinstance(cfg, dict):
            achados = [f for f in FILTROS if f in cfg]
            assert not achados, f"{nome} tem filtro {achados}: deve valer para qualquer branch"


def conferir_sem_pull_request_target(texto):
    _carregar(texto)  # arquivo vazio não pode passar por "não ter nada"
    assert "pull_request_target" not in _sem_comentarios(texto)


def conferir_permissoes(texto):
    perm = _carregar(texto).get("permissions")
    assert perm == {"contents": "read"}, f"permissions deve ser só contents: read, veio {perm!r}"


def conferir_timeouts(texto):
    for nome, job in _jobs(_carregar(texto)).items():
        t = job.get("timeout-minutes")
        assert isinstance(t, int) and not isinstance(t, bool) and t > 0, f"job {nome} sem timeout-minutes"


def _executa(job, comando):
    return any(comando in str(p.get("run", "")) for p in _passos(job))


def conferir_jobs(texto):
    jobs = _jobs(_carregar(texto))
    for nome, comando, outro in (
        ("verify", "hx verify", "hx check-clean"),
        ("check-clean", "hx check-clean", "hx verify"),
    ):
        assert nome in jobs, f"falta o job {nome}"
        assert _executa(jobs[nome], comando), f"job {nome} não executa `{comando}`"
        assert not _executa(jobs[nome], outro), f"job {nome} não deve executar `{outro}`"


def conferir_segredos(texto):
    _carregar(texto)
    achados = set(re.findall(r"secrets\.([A-Za-z0-9_]+)", _sem_comentarios(texto)))
    assert achados == {SEGREDO}, f"o único secrets.* permitido é {SEGREDO}; achei {sorted(achados)}"


def conferir_actions_fixadas(texto):
    jobs = _jobs(_carregar(texto))
    usos = [p["uses"] for j in jobs.values() for p in _passos(j) if "uses" in p]
    assert usos, "nenhuma action encontrada (esperado ao menos o checkout)"
    for uso in usos:
        assert re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", str(uso)), f"action não fixada por SHA: {uso}"


def _segredo_no_env(job, passo):
    for env in (job.get("env"), passo.get("env")):
        if isinstance(env, dict) and f"secrets.{SEGREDO}" in str(env.get(SEGREDO, "")):
            return True
    return False


def conferir_aviso(texto):
    job = _jobs(_carregar(texto)).get("check-clean")
    assert job is not None, "falta o job check-clean"
    passos = _passos(job)
    varredura = next((i for i, p in enumerate(passos) if "hx check-clean" in str(p.get("run", ""))), None)
    assert varredura is not None, "job check-clean não executa a varredura"
    teste_vazio = r"-z\s+[\"']?\$\{?" + SEGREDO + r"\}?[\"']?"
    for passo in passos[:varredura]:
        run = str(passo.get("run", ""))
        if "::warning::" not in run:
            continue
        assert re.search(teste_vazio, run), "o aviso deve testar se a variável está vazia"
        assert _segredo_no_env(job, passo), "o segredo deve chegar ao passo do aviso por env"
        resto = re.sub(teste_vazio, "", run)
        assert f"${SEGREDO}" not in resto and f"${{{SEGREDO}" not in resto, "o aviso não pode imprimir o valor"
        assert "secrets." not in run, "o valor do segredo não pode ir direto no script"
        return
    raise AssertionError("falta passo com ::warning:: antes da varredura de nomes")


# --- testes da ficha, aplicados ao arquivo real ---------------------------------------------


@pytest.fixture
def real():
    assert WORKFLOW.exists(), f"{WORKFLOW} não existe"
    return WORKFLOW.read_text(encoding="utf-8")


def test_dispara_em_push_e_pull_request_sem_filtro(real):
    conferir_gatilhos(real)


def test_nao_usa_pull_request_target(real):
    conferir_sem_pull_request_target(real)


def test_permissoes_somente_leitura(real):
    conferir_permissoes(real)


def test_todo_job_tem_timeout(real):
    conferir_timeouts(real)


def test_jobs_verify_e_check_clean(real):
    conferir_jobs(real)


def test_unico_segredo_e_nomes_proibidos(real):
    conferir_segredos(real)


def test_actions_fixadas_por_sha(real):
    conferir_actions_fixadas(real)


def test_avisa_quando_falta_o_segredo_de_nomes(real):
    conferir_aviso(real)


# --- as regras recusam texto inválido (e aceitam o válido) ------------------------------------

REGRAS = [
    conferir_gatilhos,
    conferir_sem_pull_request_target,
    conferir_permissoes,
    conferir_timeouts,
    conferir_jobs,
    conferir_segredos,
    conferir_actions_fixadas,
    conferir_aviso,
]

_SEM_AVISO = VALIDO.replace('echo "::warning::', 'echo "')

INVALIDOS = {
    conferir_gatilhos: [
        VALIDO.replace("  push:\n", "  push:\n    branches: [main]\n"),
        VALIDO.replace("  pull_request:\n", "  pull_request:\n    paths: ['src/**']\n"),
        VALIDO.replace("  push:\n", ""),
        "",
    ],
    conferir_sem_pull_request_target: [
        VALIDO.replace("  pull_request:\n", "  pull_request_target:\n"),
        VALIDO.replace("  pull_request:\n", "  pull_request:\n  pull_request_target:\n"),
        "",
    ],
    conferir_permissoes: [
        VALIDO.replace("contents: read", "contents: write"),
        VALIDO.replace("permissions:\n  contents: read\n", ""),
        VALIDO.replace("contents: read", "contents: read\n  issues: write"),
    ],
    conferir_timeouts: [
        VALIDO.replace("    timeout-minutes: 15\n", ""),
        VALIDO.replace("    timeout-minutes: 5\n", ""),
    ],
    conferir_jobs: [
        VALIDO.replace("  verify:", "  testes:"),
        VALIDO.replace("  check-clean:", "  limpeza:"),
        VALIDO.replace("sh tools/hx verify", "echo ok"),
        VALIDO.replace("sh tools/hx check-clean", "echo ok"),
    ],
    conferir_segredos: [
        VALIDO.replace(
            "      - run: sh tools/hx verify",
            "      - run: sh tools/hx verify\n        env:\n          X: ${{ secrets.CHAVE_FALSA }}",
        ),
        VALIDO.replace(f"secrets.{SEGREDO}", "secrets.GITHUB_TOKEN"),
        VALIDO.replace(f"${{{{ secrets.{SEGREDO} }}}}", "vazio"),
    ],
    conferir_actions_fixadas: [
        VALIDO.replace(f"@{SHA_FALSO}", "@v7", 1),
        VALIDO.replace(f"@{SHA_FALSO}", "@" + SHA_FALSO[:39]),
        VALIDO.replace(f"@{SHA_FALSO}", "@" + SHA_FALSO.upper()),
        VALIDO.replace(f"      - uses: actions/checkout@{SHA_FALSO} # v0.0.0\n", ""),
    ],
    conferir_aviso: [
        _SEM_AVISO,
        VALIDO.replace("::warning::", "::notice::"),
        VALIDO.replace(f'if [ -z "${SEGREDO}" ]; then', "if true; then"),
        VALIDO.replace('echo "::warning::', f'echo "${SEGREDO} ::warning::'),
        VALIDO.replace(f"      {SEGREDO}: ${{{{ secrets.{SEGREDO} }}}}", f"      {SEGREDO}: vazio"),
    ],
}


def test_regras_aceitam_o_workflow_valido_de_exemplo():
    for regra in REGRAS:
        regra(VALIDO)


def test_comentario_com_pull_request_target_nao_conta_como_uso():
    conferir_sem_pull_request_target("# não usar pull_request_target\n" + VALIDO)


@pytest.mark.parametrize(
    "regra,texto",
    [(r, t) for r, ts in INVALIDOS.items() for t in ts],
    ids=lambda v: v.__name__ if callable(v) else None,
)
def test_rejeita_workflow_invalido(regra, texto, tmp_path):
    arquivo = tmp_path / "pr.yml"
    arquivo.write_text(texto, encoding="utf-8")
    with pytest.raises(AssertionError):
        regra(arquivo.read_text(encoding="utf-8"))
