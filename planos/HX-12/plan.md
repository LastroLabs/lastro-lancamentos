# Plan — HX-12 · Workflow do sync do Project sem expor a chave do GitHub App

**Status:** pronto para revisão — 0 BLOQUEANTES, 5 ATENÇÃO, D1–D6 a confirmar (ficha atualizada em 20/11)
**Branch:** feat/HX-12-<slug> (a criar pelo `hx feature start`) · **Data:** 20/11/2026 · **Responsável:** caio-nascime
**Tasks:** planos/HX-12/tasks.md
**Aviso:** a ficha está `not_started`: o `hx feature start HX-12 --owner caio-nascime` ainda não rodou. Este plano é rascunho.

## 1. A decidir (humano)
| # | Pergunta | Gravidade | Sugestão de padrão | Decide |
|---|---|---|---|---|
| 1 | A HX-11 está `not_started` (o código existe, mas sem commit e sem `passing`) | ATENÇÃO | Os testes da HX-12 só leem o YAML e podem começar. O `hx feature verify HX-12` espera a HX-11 virar `passing` | caio-nascime |
| 2 | O exemplo de c3 ainda diz `@v3` (tag móvel). A HX-10 fixa toda action por SHA de 40 hex com a versão em comentário | ATENÇÃO | Fixar por SHA com `# v3.4.0` (D2). Trocar "(@v3)" por "SHA de 40 hex" no exemplo | caio-nascime |
| 3 | O `docs/modulos/ci.md` chama `APP_CLIENT_ID` de segredo, mas a ficha usa `vars.APP_CLIENT_ID` | ATENÇÃO | Usar a variável (o client ID não é segredo) e corrigir o ci.md na T5 | caio-nascime |
| 4 | Com `cancel-in-progress: false` o GitHub guarda **um só** run pendente por grupo, e um run novo cancela o pendente (seção 4). Um push em developer pendente pode ser trocado por um run agendado | ATENÇÃO | Aceitar: o modo developer é idempotente e o próximo push recupera o que faltou. Registrar no ci.md (T5) | caio-nascime |
| 5 | O Environment `project-sync`, o App e as variáveis ficam fora do repositório. Nenhum teste prova a configuração deles | ATENÇÃO | Checklist manual na T6, conferido por um segundo dono do `.github/` | caio-nascime + camposs04 |

**Mudanças sugeridas na ficha** (o humano aplica em PR): só o c3, trocando "(@v3)" por "fixada por SHA de 40 hex, com a versão em comentário". O resto da ficha nova (20/11) já está alinhado ao SECURITY.md §7 e à HX-11.

## 2. Decisões tomadas pelo agente
### D1 · Testes leem o YAML com `pyyaml`, no estilo de `tests/ci/test_pr_workflow.py`
- **Alternativas:** A) `yaml.safe_load` mais funções `conferir_*` e testes `rejeita_*` com YAML inventado · B) regex no texto · C) `actionlint`
- **Escolhida:** A. **Motivo:** o `pyyaml` já está em `requirements-dev.txt` e o padrão já foi revisado na HX-10. O C traria uma ferramenta nova sem um teste com nome da ficha.
- **Fontes:** repositório (`tests/ci/test_pr_workflow.py`)
- **Impacto:** T1 · c1–c4
- [ ] confirmar

### D2 · `create-github-app-token` fixada por SHA, `# v3.4.0`, com `client-id`
- **Alternativas:** A) SHA `f418cff399f7aef4c2f0ad47e25ca7a6abbdd6fc` com `# v3.4.0` · B) `@v3` · C) `@v3.4.0`
- **Escolhida:** A. **Motivo:** segue a convenção da HX-10; uma tag pode ser movida. `client-id` é o input recomendado e `app-id` está obsoleto desde a v3.1.0. O token sai mascarado e é revogado no fim do job (sem `skip-token-revoke`). Usar `owner: LastroLabs`.
- **Fontes:** https://github.com/actions/create-github-app-token e /releases (acesso em 20/11; v3.4.0 de 18/11 marcada "Latest"). O SHA vem do plano da HX-11 (`gh api`, 19/11): conferir de novo na T3.
- **Impacto:** T3 · c3
- [ ] confirmar

### D3 · `--dry-run` controlado pela variável do repositório `vars.PROJECT_SYNC_DRY_RUN`
- **Alternativas:** A) a variável `'true'` acrescenta `--dry-run` · B) `workflow_dispatch` com input, que a ficha não admite com acesso ao segredo · C) commit com `--dry-run` fixo e outro commit para tirar
- **Escolhida:** A. **Motivo:** não pede gatilho novo nem dois PRs. A variável não é segredo. Começa `true` e um humano troca para `false` depois de ler o log.
- **Impacto:** T4, T6 · c4
- [ ] confirmar

### D4 · Um arquivo com dois jobs: `sync-developer` (push) e `sync-agendada` (schedule)
- **Alternativas:** A) dois jobs com `if: github.event_name == ...` · B) um job que escolhe a origem por expressão
- **Escolhida:** A. **Motivo:** cada job tem um comando fixo e é fácil de testar e revisar. Os dois declaram `environment: project-sync`. Nenhum checkout tem `ref:`: o push usa developer e o schedule usa a branch padrão.
- **Impacto:** T2–T4 · c2, c4
- [ ] confirmar

### D5 · Python do runner (`python3`), sem `actions/setup-python`
- **Alternativas:** A) `python3` do `ubuntu-latest` · B) `setup-python` fixada por SHA
- **Escolhida:** A. **Motivo:** o script só usa a biblioteca padrão e assim entra uma action a menos com acesso ao token. **Risco:** a versão do runner muda. Se o script exigir mais que a 3.12, trocar para B.
- **Impacto:** T4
- [ ] confirmar

### D6 · O segredo só entra em `with: private-key:` da action. O script recebe só o `GH_TOKEN` de curta duração, por `env:`
- **Alternativas:** A) assim · B) passar a chave ao script
- **Escolhida:** A. **Motivo:** a chave nunca chega a `run:` nem ao Python. `timeout-minutes: 10` em cada job.
- **Impacto:** T3, T4 · c2
- [ ] confirmar

## 3. Resumo e abordagem
Criar `.github/workflows/project-sync.yml`, que roda `tools/project_sync.py` (HX-11) no push em developer (`--origem developer`) e a cada 15 minutos (`--origem agendada`). Usa um token do App criado dentro do Environment `project-sync`, com `contents: read`, `concurrency` fixa e actions fixadas por SHA.
Ordem: T1 testes → T2 gatilhos, permissões e concurrency (c1, c3) → T3 jobs com Environment, checkout e token (c2, c3) → T4 comando por gatilho e dry-run (c4) → T5 documentação → T6 configuração manual e primeiro uso → T7 verificação.

## 4. Contexto encontrado
- **Código relacionado:** `tools/project_sync.py` (`main`, `_criar_parser`: `--origem {developer,agendada}`, `--dry-run`; lê `GH_TOKEN`, `GITHUB_REPOSITORY`, `PROJECT_NUMBER`, `PROJECT_ORG`; importa `harness`, por isso roda com `python3 tools/project_sync.py`) · `.github/workflows/pr.yml` (checkout `3d3c42e…` `# v7.0.1`) · `tests/ci/test_pr_workflow.py` · `docs/modulos/ci.md`
- **Dependências:** `HX-11` está `not_started` (código e testes ainda sem commit na branch `feat/HX-11-project-sync`)
- **Reaproveitar:** o padrão e os helpers de `test_pr_workflow.py`, copiados para o arquivo novo (teste não importa teste) e o SHA do checkout do `pr.yml` · **Não criar:** mudança em `project_sync.py` ou `pr.yml`, uma origem `pr`, o `workflow_dispatch`
- **Pesquisa externa (acesso em 20/11/2026):**
  - Token do App: https://github.com/actions/create-github-app-token (inputs `client-id`, `private-key`, `owner`, `permission-*`; token mascarado e revogado no fim do job)
  - Schedule: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows. Roda no último commit da branch padrão, com intervalo mínimo de 5 min. Em repositório público é desativado após 60 dias sem atividade. Os dois últimos itens vieram de resumo, não de texto literal.
  - Concurrency: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax (no máximo um run pendente por grupo; o novo cancela o pendente. Também veio de resumo.)
  - **Não verificado:** restrição de branches do Environment e segredo disponível só a jobs que o declaram. A página consultada deu 404. Conferir na T6.

## 5. Decisões (já resolvidas)
- 20/11 · (herdado do plano da HX-11) Sem `pull_request_target`. A chave fica no Environment `project-sync`, restrito à branch padrão e à developer. Gatilhos: push em developer e schedule (~15 min). Uma `concurrency` única. Primeiro uso com `--dry-run`. - 20/11 · Ficha HX-12 atualizada pelo responsável: sem `pull_request_target`, 2 gatilhos, testes renomeados (`test_sem_pull_request_nem_pull_request_target`, `test_agendada_nao_faz_checkout_de_branch`, `test_cada_gatilho_chama_a_origem_certa`, `test_dry_run_disponivel_no_primeiro_uso`). O bloqueante anterior (`pull_request_target`) deixou de existir.

## 6. Avaliação da ficha
| # | Achado | Gravidade | Critério |
|---|---|---|---|
| 1 | Exemplo `@v3` contradiz a fixação por SHA da HX-10 | ATENÇÃO | c3 |
| 2 | O filtro `feat/<ID>-*` e a consulta por API estão no script (HX-11). O workflow só prova `--origem agendada` e o checkout sem `feat/*` | ATENÇÃO | c2, c4 |
| 3 | Dependência HX-11 não está `passing` | ATENÇÃO | — |
| 4 | Environment e App não são testáveis no repositório | ATENÇÃO | c2 |
| 5 | "Input ou variável" para o dry-run: a ficha deixa aberto; D3 escolhe a variável | OK | c4 |
| 6 | 4 critérios, 1 módulo, 1 arquivo: cabe em 1 sessão. Comandos só `pytest`. Sem dado real | OK | — |

## 7. Riscos
- O schedule roda o YAML e o script **da main** → até o merge developer→main, a execução agendada não existe (T6 avisa)
- O run pendente de developer é trocado pelo agendado → pergunta 4; o próximo push recupera
- Fork ou branch de feature com acesso ao segredo → não há gatilho de PR; o Environment fica restrito a main e developer (T6); revisão do `.github/` por CODEOWNERS
- Token impresso no log → só a action vê a chave; o token sai mascarado; o teste `test_segredo_nao_vai_para_log` barra `secrets.` em `run:`
- Agendamento desativado após 60 dias sem atividade → nota no ci.md (T5)

## 8. Aprovação
- [x] Sem perguntas BLOQUEANTES (ficha nova aplicada em 20/11)
- [ ] Atenções 1–5 respondidas e D1–D6 confirmadas
- [ ] Plan e tasks revisados por <nome> em DD/MM
