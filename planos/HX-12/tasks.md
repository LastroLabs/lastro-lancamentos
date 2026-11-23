# Tasks — HX-12 · Workflow do sync do Project sem expor a chave do GitHub App

**Plan:** planos/HX-12/plan.md · **Ficha:** features/HX-12.json
**Ordem:** T1 → revisão humana dos testes → commit só-de-testes (anotar o hash) → T2 em diante (sessão nova, sem editar `tests/`)

---

## [ ] T1 · Escrever os testes dos critérios
- **Critérios da ficha:** c1, c2, c3, c4
- **Regra de negócio:** o workflow tem a chave que escreve no Project da organização. Ele só pode rodar a partir de código já revisado (developer e a branch padrão), nunca de uma branch de feature ou de um PR. A chave nunca pode aparecer no log.
- **Critérios de aceite:**
  - [ ] Existe um teste para cada nome em `verificacao` da ficha, em `tests/ci/test_project_sync_workflow.py`
  - [ ] Cada regra é uma função `conferir_*(texto)` com um teste `rejeita_*` que monta um YAML inválido inventado em `tmp_path` (padrão da HX-10)
  - [ ] Os testes aceitam a chave `on` lida como `True` (YAML 1.1) e ignoram linhas de comentário
  - [ ] Todos falham hoje porque `.github/workflows/project-sync.yml` não existe
  - [ ] Só dados inventados (SHA falso `0123…4567`, nada de ID real de App)
- **Exemplos:** `on: {push: {branches: [developer]}, schedule: [{cron: "*/15 * * * *"}]}` → passa · `on: {push: {}}` → falha "push sem filtro de branch" · `run: echo ${{ secrets.APP_PRIVATE_KEY }}` → falha "segredo em run:" · `uses: actions/create-github-app-token@v3` → falha "action sem SHA"
- **Arquivos:** `tests/ci/test_project_sync_workflow.py`
- **Reaproveitar:** helpers de `tests/ci/test_pr_workflow.py` (`_sem_comentarios`, `_carregar`, `_jobs`, `_passos`), **copiados** · **Não criar:** conftest novo, dependência nova
- **Fora do escopo:** o YAML do workflow
- **Pronto quando:** `docker compose run --rm dev pytest tests/ci/test_project_sync_workflow.py -q` mostra só as falhas esperadas, e os `rejeita_*` passam

## [ ] T2 · Gatilhos, permissões e concurrency
- **Critérios da ficha:** c1, c3 (parte)
- **Regra de negócio:** só dois eventos disparam o sync, o push em developer e o relógio a cada 15 minutos. Dois syncs nunca rodam juntos, porque podem duplicar issue ou mover card em ordem errada.
- **Critérios de aceite:**
  - [ ] `on` tem só `push` (`branches: [developer]`) e `schedule` (`*/15 * * * *`)
  - [ ] Não aparecem `pull_request`, `pull_request_target` nem `workflow_dispatch`
  - [ ] `permissions: contents: read` no topo e nenhum job com permissão de escrita
  - [ ] `concurrency` com `group` fixo (ex.: `project-sync`, sem `${{ }}`) e `cancel-in-progress: false`
- **Exemplos:** push em `feat/XX-99-teste` → não dispara · push em `developer` → dispara · dois eventos juntos → o segundo espera
- **Arquivos:** `.github/workflows/project-sync.yml` (novo)
- **Reaproveitar:** cabeçalho comentado no estilo do `pr.yml` · **Não criar:** filtro `paths`
- **Fora do escopo:** jobs e comandos
- **Decisões relacionadas:** pergunta 6 (pendente substituído)
- **Pronto quando:** `pytest tests/ci/test_project_sync_workflow.py::test_gatilhos_permitidos tests/ci/test_project_sync_workflow.py::test_sem_push_em_branch_de_feature tests/ci/test_project_sync_workflow.py::test_sem_pull_request_nem_pull_request_target tests/ci/test_project_sync_workflow.py::test_permissoes_minimas tests/ci/test_project_sync_workflow.py::test_concurrency_serializa -q` passa

## [ ] T3 · Jobs no Environment, checkout e token do App
- **Critérios da ficha:** c2, c3 (actions fixadas)
- **Regra de negócio:** a chave privada mora no Environment `project-sync`, que só libera a chave para jobs de branches permitidas. Só a action de token lê a chave e devolve um token curto, mascarado e revogado no fim do job.
- **Critérios de aceite:**
  - [ ] Jobs `sync-developer` (`if: github.event_name == 'push'`) e `sync-agendada` (`if: github.event_name == 'schedule'`), os dois com `environment: project-sync` e `timeout-minutes: 10`
  - [ ] `secrets.APP_PRIVATE_KEY` aparece só em `with: private-key:` de `actions/create-github-app-token`, com `client-id: ${{ vars.APP_CLIENT_ID }}` e `owner: LastroLabs`
  - [ ] Todo `uses:` é fixado por SHA de 40 hex com a versão em comentário (checkout como no `pr.yml`; token com `# v3.4.0`, SHA conferido de novo com `gh api`)
  - [ ] Nenhum `actions/checkout` tem `ref:`
- **Exemplos:** job sem `environment` usando o segredo → teste falha · `ref: ${{ github.head_ref }}` → teste falha
- **Arquivos:** `.github/workflows/project-sync.yml`
- **Reaproveitar:** SHA do checkout em `.github/workflows/pr.yml` · **Não criar:** `setup-python` (D5), passo que imprime variáveis
- **Fora do escopo:** configurar o Environment no GitHub (T6)
- **Decisões relacionadas:** D2, D4, D6
- **Pronto quando:** `pytest tests/ci/test_project_sync_workflow.py::test_chave_so_com_environment tests/ci/test_project_sync_workflow.py::test_agendada_nao_faz_checkout_de_branch tests/ci/test_project_sync_workflow.py::test_segredo_nao_vai_para_log tests/ci/test_project_sync_workflow.py::test_acoes_fixadas -q` passa

## [ ] T4 · Comando por gatilho e dry-run
- **Critérios da ficha:** c4
- **Regra de negócio:** o push em developer faz o sync completo a partir das fichas. O relógio só olha branches `feat/<ID>-*` e PRs pela API, sem baixar código dessas branches. No primeiro uso nada é escrito: o log só lista o que mudaria.
- **Critérios de aceite:**
  - [ ] `sync-developer` roda `python3 tools/project_sync.py --origem developer`
  - [ ] `sync-agendada` roda `python3 tools/project_sync.py --origem agendada`
  - [ ] `--dry-run` é acrescentado quando `vars.PROJECT_SYNC_DRY_RUN == 'true'`
  - [ ] `env:` do passo: `GH_TOKEN` (saída da action de token), `PROJECT_NUMBER: ${{ vars.PROJECT_NUMBER }}`; nenhum `secrets.` em `run:`
- **Exemplos:** variável `true` → log "N mudanças pendentes (dry-run: nada foi escrito)." · variável ausente ou `false` → aplica
- **Arquivos:** `.github/workflows/project-sync.yml`
- **Reaproveitar:** a interface do `tools/project_sync.py` como está · **Não criar:** origem `pr`, mudança no script
- **Fora do escopo:** o filtro `feat/` (provado na HX-11)
- **Decisões relacionadas:** D3, D5
- **Pronto quando:** `pytest tests/ci/test_project_sync_workflow.py::test_cada_gatilho_chama_a_origem_certa tests/ci/test_project_sync_workflow.py::test_dry_run_disponivel_no_primeiro_uso -q` passa

## [ ] T5 · Documentação do módulo
- **Critérios da ficha:** apoio a c2–c4
- **Regra de negócio:** quem configura o App e o Environment precisa saber o que criar, onde, e por que o agendamento depende da main.
- **Critérios de aceite:**
  - [ ] `docs/modulos/ci.md`: `APP_CLIENT_ID` como **variável** e `APP_PRIVATE_KEY` como segredo **do Environment**; `PROJECT_SYNC_DRY_RUN`
  - [ ] Notas: o schedule roda o YAML e o script da branch padrão; um run pendente pode ser substituído; o agendamento é desativado após 60 dias sem atividade
  - [ ] O SECURITY.md §7 não muda (continua "nunca `pull_request_target`")
- **Arquivos:** `docs/modulos/ci.md`
- **Fora do escopo:** `AGENTS.md`, `SECURITY.md`
- **Pronto quando:** `ruff check .` limpo e revisão humana do texto no PR

## [ ] T6 · Configuração fora do repositório e primeiro uso (manual)
- **Critérios da ficha:** c2 (parte que o teste não prova)
- **Regra de negócio:** o YAML só é seguro se o Environment restringe as branches. Isso é configuração do GitHub e não aparece no código.
- **Critérios de aceite:**
  - [ ] App instalado na org com escrita só em Issues e Projects; `APP_PRIVATE_KEY` só como segredo do Environment `project-sync`
  - [ ] Environment restrito a `main` e `developer`. Conferir na doc oficial que o segredo só chega a jobs que o declaram (não verificado no plano)
  - [ ] `vars.APP_CLIENT_ID`, `vars.PROJECT_NUMBER` e `vars.PROJECT_SYNC_DRY_RUN=true` criadas
  - [ ] Primeiro run em developer com dry-run, log lido por um 2º dono do `.github/`; só então `PROJECT_SYNC_DRY_RUN=false`
  - [ ] Nada de ID do App, chave ou print com dado no PR
- **Fora do escopo:** merge developer→main (o agendamento só começa depois dele)
- **Pronto quando:** `gh run list --workflow project-sync.yml --limit 1` mostra `success` no push em developer

## [ ] T7 · Verificação final
- **Critérios de aceite:**
  - [ ] `git diff <hash-dos-testes> -- tests/` vazio
  - [ ] `ruff check .` limpo
  - [ ] `hx check-clean` e `hx verify` em OK
  - [ ] `hx feature verify HX-12` grava `passing` (só depois da HX-11 `passing`)
- **Pronto quando:** os três comandos do `hx` terminam com código 0
