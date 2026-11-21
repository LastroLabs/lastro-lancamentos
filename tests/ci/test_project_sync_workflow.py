"""HX-12: o workflow `.github/workflows/project-sync.yml` roda o sync do Project sem expor a chave.

Os testes leem o YAML (yaml.safe_load) e conferem as travas combinadas na ficha.
Nada roda no GitHub: só a estrutura do arquivo é provada. Só dados sintéticos.

Contrato assumido (planos/HX-12/plan.md e tasks.md):
- o arquivo é `.github/workflows/project-sync.yml`, com caminho calculado a partir deste teste.
- YAML 1.1 lê a chave `on` como booleano True; o teste aceita `True` ou "on".
- gatilhos: só `push` com `branches: [developer]` e `schedule` com `*/15 * * * *`.
- jobs identificados pelo `if` (`github.event_name == 'push'` ou `'schedule'`); cada um chama
  `tools/project_sync.py --origem developer` (push) ou `--origem agendada` (schedule).
- a chave entra só em `with: private-key:` de actions/create-github-app-token, em job com
  `environment: project-sync`; o segredo nunca vai em `run:`, `env:` nem em echo.
- toda action termina em @ + 40 hex (versão em comentário); client-id vem de vars.APP_CLIENT_ID.
- nenhum checkout tem `ref:` nem `repository:` (nunca código de branch de feature ou de PR).
- dry-run: uma variável (`vars.*DRY_RUN*`) ou input decide; o job tem comando com e sem `--dry-run`.
- linhas de comentário são ignoradas.

Cada regra é uma função `conferir_*(texto)` que levanta AssertionError. Os testes com o nome da
ficha aplicam a função ao arquivo real; os testes `rejeita_*` provam que a função falha com
um texto inválido montado em tmp_path (dados inventados).
"""

import re
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "project-sync.yml"
SHA_FALSO = "0123456789abcdef0123456789abcdef01234567"
ENVIRONMENT = "project-sync"
CHAVE = "APP_PRIVATE_KEY"
ACAO_APP = "actions/create-github-app-token"
CRON = "*/15 * * * *"
ORIGEM_POR_EVENTO = {"push": "developer", "schedule": "agendada"}
FILTROS_DE_PUSH = ("branches-ignore", "paths", "paths-ignore", "tags", "tags-ignore")

VALIDO = """\
name: Project sync
on:
  push:
    branches: [developer]
  schedule:
    - cron: "*/15 * * * *"
permissions:
  contents: read
concurrency:
  group: project-sync
  cancel-in-progress: false
jobs:
  sync-developer:
    if: github.event_name == 'push'
    runs-on: ubuntu-latest
    timeout-minutes: 10
    environment: project-sync
    steps:
      - name: Checkout
        uses: actions/checkout@__SHA__ # v0.0.0
      - name: Token do App
        id: token
        uses: actions/create-github-app-token@__SHA__ # v3.4.0
        with:
          client-id: ${{ vars.APP_CLIENT_ID }}
          private-key: ${{ secrets.APP_PRIVATE_KEY }}
      - name: Sync completo
        env:
          GH_TOKEN: ${{ steps.token.outputs.token }}
          PROJECT_NUMBER: ${{ vars.PROJECT_NUMBER }}
          DRY_RUN: ${{ vars.PROJECT_SYNC_DRY_RUN }}
        run: |
          ARGS=""
          if [ "$DRY_RUN" = "true" ]; then ARGS="--dry-run"; fi
          python3 tools/project_sync.py --origem developer $ARGS
  sync-agendada:
    if: github.event_name == 'schedule'
    runs-on: ubuntu-latest
    timeout-minutes: 10
    environment: project-sync
    steps:
      - name: Checkout da branch padrão
        uses: actions/checkout@__SHA__ # v0.0.0
      - name: Token do App
        id: token
        uses: actions/create-github-app-token@__SHA__ # v3.4.0
        with:
          client-id: ${{ vars.APP_CLIENT_ID }}
          private-key: ${{ secrets.APP_PRIVATE_KEY }}
      - name: Sync das branches
        env:
          GH_TOKEN: ${{ steps.token.outputs.token }}
          PROJECT_NUMBER: ${{ vars.PROJECT_NUMBER }}
          DRY_RUN: ${{ vars.PROJECT_SYNC_DRY_RUN }}
        run: |
          ARGS=""
          if [ "$DRY_RUN" = "true" ]; then ARGS="--dry-run"; fi
          python3 tools/project_sync.py --origem agendada $ARGS
""".replace("__SHA__", SHA_FALSO)


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
    assert isinstance(on, dict), "falta o bloco `on` com push e schedule"
    return on


def _usa(passo, action):
    return str(passo.get("uses", "")).startswith(action + "@")


def _checkouts(dados):
    return [p for j in _jobs(dados).values() for p in _passos(j) if _usa(p, "actions/checkout")]


# --- c1: gatilhos -----------------------------------------------------------------------------


def conferir_gatilhos(texto):
    on = _gatilhos(_carregar(texto))
    assert set(on) == {"push", "schedule"}, f"`on` deve ter só push e schedule; veio {sorted(map(str, on))}"
    agenda = on["schedule"]
    crons = [a.get("cron") for a in agenda if isinstance(a, dict)] if isinstance(agenda, list) else []
    assert crons == [CRON], f"schedule deve ter um só cron `{CRON}`; veio {crons!r}"


def conferir_sem_push_em_feature(texto):
    push = _gatilhos(_carregar(texto)).get("push")
    assert isinstance(push, dict), "push sem filtro dispara em qualquer branch: falta `branches: [developer]`"
    assert push.get("branches") == ["developer"], f"push só em developer; veio {push.get('branches')!r}"
    achados = [f for f in FILTROS_DE_PUSH if f in push]
    assert not achados, f"push não deve ter {achados}: só `branches: [developer]`"


def conferir_sem_pull_request(texto):
    dados = _carregar(texto)
    assert "pull_request" not in _sem_comentarios(texto), "não usar pull_request nem pull_request_target"
    assert "workflow_dispatch" not in _gatilhos(dados), "workflow_dispatch daria acesso manual ao segredo"


# --- c2: chave, Environment, checkout e log ---------------------------------------------------


def _environment(job):
    env = job.get("environment")
    return env.get("name") if isinstance(env, dict) else env


def conferir_chave_so_com_environment(texto):
    jobs = _jobs(_carregar(texto))
    usam = [n for n, j in jobs.items() if CHAVE in str(j)]
    assert usam, f"nenhum job usa {CHAVE}: o sync não teria como gerar o token"
    for nome in usam:
        assert _environment(jobs[nome]) == ENVIRONMENT, f"job {nome} usa {CHAVE} sem environment: {ENVIRONMENT}"


def conferir_agendada_sem_checkout_de_branch(texto):
    dados = _carregar(texto)
    agendados = [n for n, j in _jobs(dados).items() if "--origem agendada" in str(j)]
    assert agendados, "falta o job que roda `--origem agendada`"
    for passo in _checkouts(dados):
        extras = [k for k in ("ref", "repository") if k in (passo.get("with") or {})]
        assert not extras, f"checkout com {extras}: só pode baixar o código da branch padrão"


def conferir_segredo_fora_do_log(texto):
    dados = _carregar(texto)
    usados = set(re.findall(r"secrets\.([A-Za-z0-9_]+)", _sem_comentarios(texto)))
    assert usados == {CHAVE}, f"o único secrets.* permitido é {CHAVE}; achei {sorted(usados)}"
    assert "secrets." not in str(dados.get("env", "")), "segredo no env do workflow inteiro"
    for nome, job in _jobs(dados).items():
        assert "secrets." not in str(job.get("env", "")), f"job {nome}: segredo no env do job"
        for passo in _passos(job):
            run = str(passo.get("run", ""))
            assert "secrets." not in run and CHAVE not in run, f"job {nome}: segredo em run:"
            assert not re.search(r"\b(echo|printf|printenv)\b[^\n]*(GH_TOKEN|outputs\.token)", run), (
                f"job {nome}: o token não pode ser impresso"
            )
            if _usa(passo, ACAO_APP):
                esperado = "${{ secrets." + CHAVE + " }}"
                assert (passo.get("with") or {}).get("private-key") == esperado
                assert "secrets." not in str(passo.get("env", "")), f"job {nome}: segredo no env do passo"
            else:
                assert "secrets." not in str(passo), f"job {nome}: segredo fora da action de token"


# --- c3: permissões, concurrency e actions ----------------------------------------------------


def conferir_permissoes_minimas(texto):
    dados = _carregar(texto)
    perm = dados.get("permissions")
    assert perm == {"contents": "read"}, f"permissions deve ser só contents: read, veio {perm!r}"
    for nome, job in _jobs(dados).items():
        escrita = [k for k, v in (job.get("permissions") or {}).items() if v == "write"]
        assert not escrita, f"job {nome} pede escrita no GITHUB_TOKEN: {escrita}"


def conferir_concurrency(texto):
    conc = _carregar(texto).get("concurrency")
    assert isinstance(conc, dict), "falta o bloco concurrency"
    grupo = conc.get("group")
    assert isinstance(grupo, str) and grupo and "${{" not in grupo, f"group deve ser fixo; veio {grupo!r}"
    assert conc.get("cancel-in-progress") is False, "cancel-in-progress deve ser false"


def conferir_acoes_fixadas(texto):
    jobs = _jobs(_carregar(texto))
    passos = [p for j in jobs.values() for p in _passos(j) if "uses" in p]
    assert passos, "nenhuma action encontrada"
    for p in passos:
        uso = p["uses"]
        assert re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", str(uso)), f"action não fixada por SHA: {uso}"
    tokens = [p for p in passos if _usa(p, ACAO_APP)]
    assert tokens, f"falta {ACAO_APP}"
    for p in tokens:
        client = (p.get("with") or {}).get("client-id")
        assert client == "${{ vars.APP_CLIENT_ID }}", f"client-id deve vir de vars.APP_CLIENT_ID; veio {client!r}"
    assert re.search(rf"{ACAO_APP}@[0-9a-f]{{40}}\s+#\s*v3", texto), "faltou a versão (# v3...) em comentário"


# --- c4: origem de cada gatilho e dry-run -----------------------------------------------------


def _origens(job):
    runs = "\n".join(str(p.get("run", "")) for p in _passos(job))
    return re.findall(r"tools/project_sync\.py\s+--origem\s+(\S+)", runs)


def conferir_origem_por_gatilho(texto):
    jobs = _jobs(_carregar(texto))
    vistos = {}
    for nome, job in jobs.items():
        origens = _origens(job)
        if not origens:
            continue
        eventos = [e for e in ORIGEM_POR_EVENTO if f"github.event_name == '{e}'" in str(job.get("if", ""))]
        assert len(eventos) == 1, f"job {nome} deve ter `if: github.event_name == '<evento>'` de um só gatilho"
        assert set(origens) == {ORIGEM_POR_EVENTO[eventos[0]]}, (
            f"job {nome} ({eventos[0]}) deve chamar só --origem {ORIGEM_POR_EVENTO[eventos[0]]}; veio {origens}"
        )
        vistos[eventos[0]] = nome
    assert set(vistos) == set(ORIGEM_POR_EVENTO), f"falta job para {set(ORIGEM_POR_EVENTO) - set(vistos)}"


def conferir_dry_run(texto):
    jobs = _jobs(_carregar(texto))
    chamam = {n: j for n, j in jobs.items() if _origens(j)}
    assert chamam, "nenhum job chama o project_sync"
    for nome, job in chamam.items():
        assert re.search(r"(vars|inputs)\.\w*DRY_RUN", str(job)), f"job {nome}: falta variável ou input de dry-run"
        runs = "\n".join(str(p.get("run", "")) for p in _passos(job))
        assert "--dry-run" in runs, f"job {nome}: o comando não aceita --dry-run"
        linhas = [l for l in runs.splitlines() if "project_sync.py" in l]
        assert any("--dry-run" not in l for l in linhas), f"job {nome}: dry-run fixo; deve ser opcional"


# --- testes da ficha, aplicados ao arquivo real -----------------------------------------------


@pytest.fixture
def real():
    assert WORKFLOW.exists(), f"{WORKFLOW} não existe"
    return WORKFLOW.read_text(encoding="utf-8")


def test_gatilhos_permitidos(real):
    conferir_gatilhos(real)


def test_sem_push_em_branch_de_feature(real):
    conferir_sem_push_em_feature(real)


def test_sem_pull_request_nem_pull_request_target(real):
    conferir_sem_pull_request(real)


def test_chave_so_com_environment(real):
    conferir_chave_so_com_environment(real)


def test_agendada_nao_faz_checkout_de_branch(real):
    conferir_agendada_sem_checkout_de_branch(real)


def test_segredo_nao_vai_para_log(real):
    conferir_segredo_fora_do_log(real)


def test_permissoes_minimas(real):
    conferir_permissoes_minimas(real)


def test_concurrency_serializa(real):
    conferir_concurrency(real)


def test_acoes_fixadas(real):
    conferir_acoes_fixadas(real)


def test_cada_gatilho_chama_a_origem_certa(real):
    conferir_origem_por_gatilho(real)


def test_dry_run_disponivel_no_primeiro_uso(real):
    conferir_dry_run(real)


# --- as regras recusam texto inválido (e aceitam o válido) ------------------------------------

REGRAS = [
    conferir_gatilhos,
    conferir_sem_push_em_feature,
    conferir_sem_pull_request,
    conferir_chave_so_com_environment,
    conferir_agendada_sem_checkout_de_branch,
    conferir_segredo_fora_do_log,
    conferir_permissoes_minimas,
    conferir_concurrency,
    conferir_acoes_fixadas,
    conferir_origem_por_gatilho,
    conferir_dry_run,
]

PASSO_DE_SYNC = "      - name: Sync completo\n"
ENV_DO_JOB = "    environment: project-sync\n"
CHECKOUT = f"        uses: actions/checkout@{SHA_FALSO} # v0.0.0\n"
TOKEN = f"actions/create-github-app-token@{SHA_FALSO} # v3.4.0"
TIMEOUT = "    timeout-minutes: 10\n"
LINHA_ARGS = '          if [ "$DRY_RUN" = "true" ]; then ARGS="--dry-run"; fi\n'
DRY_ENV = "          DRY_RUN: ${{ vars.PROJECT_SYNC_DRY_RUN }}\n"


def _com_checkout(extra):
    return VALIDO.replace(CHECKOUT, CHECKOUT + "        with:\n" + extra)


INVALIDOS = {
    conferir_gatilhos: [
        VALIDO.replace("  schedule:\n", "  pull_request:\n  schedule:\n"),
        VALIDO.replace("  schedule:\n", "  workflow_dispatch:\n  schedule:\n"),
        VALIDO.replace("*/15 * * * *", "0 * * * *"),
        VALIDO.replace('  schedule:\n    - cron: "*/15 * * * *"\n', ""),
        VALIDO.replace("  push:\n    branches: [developer]\n", ""),
        "",
    ],
    conferir_sem_push_em_feature: [
        VALIDO.replace("    branches: [developer]\n", ""),
        VALIDO.replace("[developer]", "['**']"),
        VALIDO.replace("[developer]", "[developer, 'feat/**']"),
        VALIDO.replace("    branches: [developer]\n", "    branches-ignore: [main]\n"),
        VALIDO.replace("    branches: [developer]\n", "    branches: [developer]\n    tags: ['v*']\n"),
        "",
    ],
    conferir_sem_pull_request: [
        VALIDO.replace("  schedule:\n", "  pull_request:\n  schedule:\n"),
        VALIDO.replace("  schedule:\n", "  pull_request_target:\n  schedule:\n"),
        VALIDO.replace("  schedule:\n", "  workflow_dispatch:\n  schedule:\n"),
        "",
    ],
    conferir_chave_so_com_environment: [
        VALIDO.replace(ENV_DO_JOB, ""),
        VALIDO.replace(ENV_DO_JOB, "", 1),
        VALIDO.replace(ENV_DO_JOB, "    environment: producao\n"),
        VALIDO.replace("${{ secrets.APP_PRIVATE_KEY }}", "vazio"),
    ],
    conferir_agendada_sem_checkout_de_branch: [
        _com_checkout("          ref: ${{ github.head_ref }}\n"),
        _com_checkout("          ref: feat/XX-99-teste\n"),
        _com_checkout("          ref: ${{ github.event.pull_request.head.sha }}\n"),
        _com_checkout("          repository: ORG_FALSA/repo-falso\n"),
        VALIDO.replace("--origem agendada", "--origem outra"),
    ],
    conferir_segredo_fora_do_log: [
        VALIDO.replace(PASSO_DE_SYNC, "      - run: echo ${{ secrets.APP_PRIVATE_KEY }}\n" + PASSO_DE_SYNC),
        VALIDO.replace(PASSO_DE_SYNC, '      - run: echo "$GH_TOKEN"\n' + PASSO_DE_SYNC),
        VALIDO.replace(PASSO_DE_SYNC, "      - run: echo ${{ steps.token.outputs.token }}\n" + PASSO_DE_SYNC),
        VALIDO.replace(DRY_ENV, DRY_ENV + "          X: ${{ secrets.APP_PRIVATE_KEY }}\n", 1),
        VALIDO.replace(TIMEOUT, TIMEOUT + "    env:\n      X: ${{ secrets.APP_PRIVATE_KEY }}\n", 1),
        VALIDO.replace("secrets.APP_PRIVATE_KEY", "secrets.OUTRA_CHAVE_FALSA"),
    ],
    conferir_permissoes_minimas: [
        VALIDO.replace("contents: read", "contents: write"),
        VALIDO.replace("permissions:\n  contents: read\n", ""),
        VALIDO.replace("contents: read", "contents: read\n  issues: write"),
        VALIDO.replace(TIMEOUT, TIMEOUT + "    permissions:\n      issues: write\n", 1),
    ],
    conferir_concurrency: [
        VALIDO.replace("cancel-in-progress: false", "cancel-in-progress: true"),
        VALIDO.replace("  cancel-in-progress: false\n", ""),
        VALIDO.replace("group: project-sync", "group: ${{ github.ref }}"),
        VALIDO.replace("concurrency:\n  group: project-sync\n  cancel-in-progress: false\n", ""),
    ],
    conferir_acoes_fixadas: [
        VALIDO.replace(f"create-github-app-token@{SHA_FALSO}", "create-github-app-token@v3"),
        VALIDO.replace(f"actions/checkout@{SHA_FALSO}", "actions/checkout@v7"),
        VALIDO.replace(f"@{SHA_FALSO}", "@" + SHA_FALSO[:39], 1),
        VALIDO.replace("client-id: ${{ vars.APP_CLIENT_ID }}", "app-id: ${{ vars.APP_CLIENT_ID }}"),
        VALIDO.replace("client-id: ${{ vars.APP_CLIENT_ID }}", "client-id: Iv1.0000000000000000"),
        VALIDO.replace(TOKEN, TOKEN.replace(" # v3.4.0", "")),
    ],
    conferir_origem_por_gatilho: [
        VALIDO.replace("--origem developer", "--origem agendada"),
        VALIDO.replace("--origem agendada", "--origem developer"),
        VALIDO.replace("--origem developer", "--origem pr"),
        VALIDO.replace("    if: github.event_name == 'push'\n", ""),
        VALIDO.replace("github.event_name == 'schedule'", "github.event_name == 'push'"),
        VALIDO.replace("python3 tools/project_sync.py --origem agendada", "python3 tools/outro.py --origem agendada"),
    ],
    conferir_dry_run: [
        VALIDO.replace(DRY_ENV, ""),
        VALIDO.replace('ARGS="--dry-run"', 'ARGS="--verboso"'),
        VALIDO.replace("$ARGS", "--dry-run"),
        VALIDO.replace("vars.PROJECT_SYNC_DRY_RUN", "vars.PROJECT_NUMBER"),
    ],
}


def test_regras_aceitam_o_workflow_valido_de_exemplo():
    for regra in REGRAS:
        regra(VALIDO)


def test_todas_as_regras_tem_casos_invalidos():
    assert set(INVALIDOS) == set(REGRAS)
    for regra, textos in INVALIDOS.items():
        assert all(t != VALIDO for t in textos), f"{regra.__name__}: um caso inválido é igual ao válido"


def test_comentario_com_pull_request_target_nao_conta_como_uso():
    conferir_sem_pull_request("# não usar pull_request_target\n" + VALIDO)


def test_input_de_dry_run_tambem_vale():
    conferir_dry_run(VALIDO.replace("vars.PROJECT_SYNC_DRY_RUN", "inputs.dry_run_falso_DRY_RUN"))


@pytest.mark.parametrize(
    "regra,texto",
    [(r, t) for r, ts in INVALIDOS.items() for t in ts],
    ids=lambda v: v.__name__ if callable(v) else None,
)
def test_rejeita_workflow_invalido(regra, texto, tmp_path):
    arquivo = tmp_path / "project-sync.yml"
    arquivo.write_text(texto, encoding="utf-8")
    with pytest.raises(AssertionError):
        regra(arquivo.read_text(encoding="utf-8"))
