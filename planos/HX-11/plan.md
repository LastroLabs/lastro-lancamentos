# Plan — HX-11 · Espelhar as fichas no Project da organização com issues, responsáveis e bloqueios

**Status:** rascunho (aguardando as novas versões das fichas HX-11 e HX-12) — 0 bloqueantes, 0 perguntas abertas, D1–D7 confirmadas
**Branch:** feat/HX-11-project-sync · **Data:** 20/11/2026 (respostas aplicadas) · **Responsável:** caio-nascime
**Tasks:** planos/HX-11/tasks.md
**Aviso:** a ficha está `not_started`: o `hx feature start HX-11 --owner caio-nascime` ainda não rodou. **T1 só começa com a ficha ajustada** (pedido do responsável).

## 1. A decidir (humano)
Nenhuma pergunta aberta. As 3 atenções do plano foram aceitas com a sugestão (seção 5).

Mudanças na ficha (o responsável aplica, 20/11): c1 e c2 da HX-11, com origens só `developer` e `agendada`, PR consultado por API, sem `pull_request_target`; HX-12 com gatilhos push em developer e schedule. Conferir ao revisar: ordem A FAZER < FAZENDO < EM REVISÃO < FINALIZADA, REGREDIU fora da ordem, exceções ao "nunca recua" (`regressed`, `passing` vindo de REGREDIU, PR fechado sem merge), `blocked` não move, título alterado atualiza o issue.

## 2. Decisões tomadas pelo agente
D1–D6 foram confirmadas (seção 5). Ficou uma:
### D7 · Interface: `--origem {developer,agendada}`, sem origem `pr`
- **Alternativas:** A) duas origens por argumento · B) ler o evento do GitHub
- **Escolhida:** A. `--origem developer` lê `features/` e faz tudo (criar, atualizar título, avançar, reconciliar responsável e bloqueios, fechar e reabrir). `--origem agendada` **não lê `features/`**: consulta pela API as branches `feat/<ID>-*` e seus PRs e move só o Status dos cards. `--dry-run` vale para as duas. **Motivo:** o script não conhece payload do GitHub, e a agendada não depende de nenhum código de branch de feature (regra de segurança do responsável).
- **Impacto:** T1 (contrato: `listar_branches`, `listar_prs`), T3, T6 · c2
- [x] confirmar (20/11, caio-nascime)

## 3. Resumo e abordagem
`tools/project_sync.py` lê `features/*.json`, compara com o remoto (issues, itens do Project e branches) e gera uma lista de mudanças: criar issue, atualizar título, mover coluna, ajustar responsável e bloqueios, fechar ou reabrir. Depois aplica as mudanças, ou só lista com `--dry-run`. Nunca escreve em `features/`.
Ordem: T1 testes (com a ficha nova) → T2 criação e título (c1) → T3 coluna por origem (c2) → T4 reconciliação (c3) → T5 aplicar, dry-run e erros (c4) → T6 cliente real → T7 documentação → T8 verificação.
O workflow, o Environment `project-sync` e o agendamento ficam na **HX-12**. O GitHub App é pré-requisito e não entra nas tasks.

## 4. Contexto encontrado
- **Código relacionado:** `tools/harness.py` (`carregar_fichas`, `HarnessErro`, `mostrar_erro`, padrão de `main`), `tests/ci/test_pr_workflow.py` (estilo), `.github/workflows/pr.yml` (o sync **não** entra nele: c4 da HX-10 só admite o segredo de nomes)
- **Dependências:** nenhuma (`depende_de: []`)
- **Reaproveitar:** as funções do harness acima, só por import · **Não criar:** biblioteca nova, outro leitor de fichas, alteração em `harness.py`
- **Pesquisa externa (acesso em 19/11/2026):**
  - Dependências de issue: https://docs.github.com/en/rest/issues/issue-dependencies (`POST/DELETE .../dependencies/blocked_by`; exige escrita em Issues; tem limite secundário de taxa)
  - Project por GraphQL em 2 passos (adicionar o item, depois definir a coluna pelo ID da opção): https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects
  - Token do App: https://github.com/actions/create-github-app-token (v3.4.0 = `f418cff399f7aef4c2f0ad47e25ca7a6abbdd6fc`, consultado com `gh api`). Usado só na HX-12
- **Observação para a HX-12:** um workflow `schedule` roda na branch padrão (`main`), não na `developer`. A versão do script que a execução agendada usa é a da `main`. Isso vem do meu conhecimento e não verifiquei nesta sessão.

## 5. Decisões (já resolvidas)
- 20/11 · Project: org `LastroLabs`, número em `vars.PROJECT_NUMBER`, campo `Status`, opções `A FAZER`, `FAZENDO`, `EM REVISÃO`, `FINALIZADA`, `REGREDIU` (pergunta 1 antiga, por caio-nascime)
- 20/11 · Mapa: `not_started`→A FAZER, `in_progress`→FAZENDO, `passing`→FINALIZADA, `regressed`→REGREDIU; `blocked` não move o card, porque o bloqueio nativo já aparece
- 20/11 · Segurança: nada roda com `APP_PRIVATE_KEY` a partir de branch de feature. A chave fica no Environment `project-sync`, restrito à branch padrão e à developer. **Sem `pull_request_target`; o SECURITY.md §7 não muda.** Gatilhos finais da HX-12: push em developer e schedule (~15 min)
- 20/11 · Agendada (workflow da branch padrão, consulta branches e PRs por API): PR aberto de `feat/<ID>-*` → EM REVISÃO; PR fechado sem merge → FAZENDO; branch sem PR com card em A FAZER → FAZENDO
- 20/11 · Ordem de avanço: A FAZER < FAZENDO < EM REVISÃO < FINALIZADA; REGREDIU fora da ordem. Ficha `regressed` em developer → REGREDIU e issue reaberto; ficha de volta a `passing` → FINALIZADA e issue fechado. Exceções ao "nunca recua": essas duas e PR fechado sem merge → FAZENDO
- 20/11 · Cruzamentos aceitos: a agendada só mexe em cards em A FAZER, FAZENDO e EM REVISÃO (FINALIZADA e REGREDIU só mudam em developer); PR fechado sem merge só tira de EM REVISÃO (→ FAZENDO); com mais de um PR na branch vale o mais recente. Em developer, card em REGREDIU ou FINALIZADA com ficha `in_progress` fica como está: só `passing` tira de REGREDIU e só `regressed` tira de FINALIZADA
- 20/11 · A HX-12 ganha um critério de `concurrency` única para agendada e push em developer (o responsável aplica na ficha HX-12)
- 20/11 · D7 confirmada: `--origem {developer,agendada}`
- 20/11 · Casos: PR fechado sem merge → volta a FAZENDO. Card inexistente em evento de branch ou PR → só aviso, porque só developer cria. Título da ficha mudou → atualiza o título do issue, casando pelo ID (pergunta 4 antiga)
- 20/11 · D1 (`urllib`), D2 (action de token, na HX-12), D3 (bloqueio nativo), D4 (argumentos; revisto em D7) confirmadas. Primeiro uso com `--dry-run` como padrão
- 20/11 · D5: casa o issue pela expressão exata `^<ID>: `
- 20/11 · D6: só importar funções do harness; `harness.py` não muda
- 20/11 · `issue_id` do bloqueio é o campo numérico `id` do issue, não o `number` (no exemplo da doc, id 1 e number 1347). Confirmar na T6 com uma chamada real, feita à mão: nenhum teste automático chama a rede
- 20/11 · O workflow fica para a HX-12; o App é pré-requisito, fora das tasks (perguntas 2 e 5 antigas)

## 6. Avaliação da ficha
| # | Achado | Gravidade | Critério |
|---|---|---|---|
| 1 | c1 e c2 em revisão pelo responsável; os testes esperam a nova versão | ATENÇÃO | c1, c2 |
| 2 | Cruzamentos agendada × FINALIZADA/REGREDIU e REGREDIU × `in_progress`: resolvidos em 20/11 (seção 5); a ficha nova deve refleti-los | OK | c2 |
| 3 | Login inexistente: a API de issues ignora sem erro; o script consulta antes. O teste só prova com API falsa | ATENÇÃO | c1 |
| 4 | 4 critérios, 1 módulo: no limite, cabe em 2 sessões | OK | — |
| 5 | Verificações são `pytest`/`ruff` e cobrem cada critério. Dado real: nenhum; testes com IDs e logins inventados | OK | c1–c4 |

## 7. Riscos
- Duas execuções ao mesmo tempo (agendada + push) duplicam issue → só developer cria; a HX-12 precisa de `concurrency` (pergunta 3); o script casa pelo ID antes de criar
- Muitos PRs e branches na consulta da agendada → paginação em `listar_prs` e `listar_branches` (T6)
- Project com muitas páginas → a leitura pagina (T6)
- Limite secundário de taxa → pausa curta entre escritas (T6)
- Texto público nos issues → só `ID: título` e "Ficha: features/<ID>.json"

## 8. Aprovação
- [x] Perguntas BLOQUEANTES respondidas (20/11)
- [x] Atenções respondidas e decisões D1–D7 confirmadas (20/11)
- [ ] Novas versões das fichas HX-11 (c1, c2) e HX-12 aplicadas e conferidas contra este plan
- [ ] Plan e tasks revisados por <nome> em DD/MM
