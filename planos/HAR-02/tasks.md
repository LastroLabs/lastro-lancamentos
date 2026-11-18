# Tasks — HAR-02 · Filtrar hx state por estado e resumir só o que pede atenção

**Plan:** planos/HAR-02/plan.md · **Ficha:** features/HAR-02.json
**Ordem:** T1 → revisão humana dos testes → commit só-de-testes (anotar o hash) → T2 em diante (sessão nova, sem editar `tests/`)

---

## [ ] T1 · Escrever os testes dos critérios
- **Critérios da ficha:** c1, c2, c3, c4
- **Regra de negócio (em linguagem simples):** quem usa o painel quer ver só as fichas que importam (por estado, ou só as com problema), sem perder a contagem geral no `Resumo`. Estado digitado errado deve ser recusado com uma mensagem que ensina o certo.
- **Critérios de aceite:**
  - [ ] Existem os 6 testes citados na ficha, em `tests/harness/test_state_filtro.py`: `test_filtra_por_um_ou_mais_estados`, `test_estado_invalido_e_recusado`, `test_atencao_lista_blocked_e_regressed`, `test_atencao_sem_nada_avisa`, `test_resumo_conta_todas_as_fichas`, `test_sem_filtro_saida_inalterada`
  - [ ] Todos falham hoje porque as flags não existem (não por erro de import ou de fixture)
  - [ ] Só fichas inventadas (`T-01`...), sem dado real
- **Exemplos:** fichas T-01 (passing), T-02 (in_progress), T-03 (not_started) + `["state","--estado","in_progress","--estado","not_started"]` → linhas de T-02 e T-03, sem T-01. `["state","--estado","pronto"]` → código 2, stderr com `ERRO`, `pronto`, `CORREÇÃO` e os 5 estados, stdout vazio. Sem filtro → texto idêntico ao formato atual (comparar com saída fixa escrita no teste).
- **Arquivos:** `tests/harness/test_state_filtro.py`
- **Reaproveitar:** `ficha_valida`, `gravar`, `rodar_state` de `tests/harness/test_fase_a.py` · **Não criar:** outro gerador de fichas
- **Fora do escopo:** código de produção; teste de `--atencao` com `--estado` (aguarda resposta da pergunta 1)
- **Pronto quando:** `docker compose run --rm dev pytest tests/harness/test_state_filtro.py -q` mostra só falhas esperadas

## [ ] T2 · Aceitar as flags no parser
- **Critérios da ficha:** c1, c3
- **Regra de negócio (em linguagem simples):** o comando passa a reconhecer `--estado` (pode repetir) e `--atencao` (sem valor).
- **Critérios de aceite:**
  - [ ] `--estado` aceita 1 ou mais ocorrências (D2); `--atencao` é um interruptor
  - [ ] `hx state --help` mostra as duas flags em português
  - [ ] Sem flags, o comportamento não muda
- **Exemplos:** `hx state --estado passing --estado blocked` → duas ocorrências lidas; `hx state --atencao` → interruptor ligado.
- **Arquivos:** `tools/harness.py` (`_criar_parser`)
- **Reaproveitar:** `p_state` existente · **Não criar:** novo subcomando
- **Fora do escopo:** filtrar de fato (T4, T5)
- **Decisões relacionadas:** D2 (plan.md)
- **Pronto quando:** `pytest tests/harness/test_fase_a.py tests/harness/test_fase0.py -q` continua verde

## [ ] T3 · Recusar estado inexistente
- **Critérios da ficha:** c2
- **Regra de negócio (em linguagem simples):** se a pessoa digita um estado que não existe, o comando não mostra nada e explica o erro e como corrigir.
- **Critérios de aceite:**
  - [ ] Erro cita o valor digitado (`pronto`), MOTIVO e CORREÇÃO listando os 5 estados de `ESTADOS`
  - [ ] Código de saída 2; stdout vazio
  - [ ] A validação acontece antes de ler as fichas (D3)
  - [ ] Com um válido e um inválido, recusa tudo e cita o inválido
- **Exemplos:** `--estado pronto` → `ERRO: estado 'pronto' não existe.` + CORREÇÃO com `not_started, in_progress, passing, blocked, regressed`; `--estado passing --estado xyz` → recusa citando `xyz`. (Texto exato: o da T1; manter simples e em português.)
- **Arquivos:** `tools/harness.py` (`cmd_state`)
- **Reaproveitar:** `ESTADOS`, `HarnessErro`, `main` · **Não criar:** segunda lista de estados
- **Fora do escopo:** mensagens de `--atencao`
- **Decisões relacionadas:** D1, D3
- **Pronto quando:** `pytest tests/harness/test_state_filtro.py::test_estado_invalido_e_recusado -q` passa

## [ ] T4 · Filtrar por estado mantendo o Resumo completo
- **Critérios da ficha:** c1, c4
- **Regra de negócio (em linguagem simples):** a tabela mostra só as fichas dos estados pedidos; a linha `Resumo` continua dizendo quantas fichas existem em cada estado no projeto todo.
- **Critérios de aceite:**
  - [ ] Só as fichas dos estados pedidos aparecem, na ordem natural de ID
  - [ ] `Resumo` calculado sobre todas as fichas, com o mesmo formato de hoje
  - [ ] Sem flags, saída idêntica à atual (nenhum teste da fase A altera)
  - [ ] Filtro sem resultado: cabeçalho, nenhuma linha, `Resumo` (padrão da pergunta 2)
- **Exemplos:** A (passing), B (in_progress); `--estado in_progress` → linha de B e `Resumo: 1 passing · 1 in_progress · 0 not_started · 0 blocked · 0 regressed`; `--estado blocked` → só cabeçalho e Resumo.
- **Arquivos:** `tools/harness.py` (`cmd_state`)
- **Reaproveitar:** `_chave_natural`, `_texto`, `formatar`, cálculo de `contagem` atual (usar a lista completa) · **Não criar:** segundo formatador de tabela
- **Fora do escopo:** `--atencao`; mudar larguras ou colunas
- **Pronto quando:** `pytest tests/harness/test_state_filtro.py -k "um_ou_mais or resumo or inalterada" -q` passa

## [ ] T5 · `--atencao`
- **Critérios da ficha:** c3
- **Regra de negócio (em linguagem simples):** atalho para ver só o que está travado ou quebrou (blocked e regressed). Se estiver tudo bem, diz isso em uma frase.
- **Critérios de aceite:**
  - [ ] Lista só fichas `blocked` e `regressed`
  - [ ] Sem nenhuma: imprime exatamente `Nada pede atenção.` (e o `Resumo`, padrão da pergunta 3)
  - [ ] `--atencao` junto com `--estado` é recusado (padrão da pergunta 1) com ERRO/MOTIVO/CORREÇÃO e código 2
- **Exemplos:** A (passing), B (blocked), C (regressed) → linhas de B e C; só A (passing) → `Nada pede atenção.`
- **Arquivos:** `tools/harness.py` (`cmd_state`)
- **Reaproveitar:** o filtro da T4 (`--atencao` = filtro `{blocked, regressed}`) · **Não criar:** caminho de impressão separado
- **Fora do escopo:** atualizar `AGENTS.md` (pergunta 4, PR do humano)
- **Pronto quando:** `pytest tests/harness/test_state_filtro.py -k atencao -q` passa

## [ ] T6 · Verificação final
- **Critérios de aceite:**
  - [ ] `git diff <hash-dos-testes> -- tests/` vazio
  - [ ] `ruff check .` limpo
  - [ ] `hx check-clean` e `hx verify` em OK (exige Docker ligado; se não rodar, registrar em `progress/HAR-02.md`)
  - [ ] `hx feature verify HAR-02` grava `passing`
- **Pronto quando:** `hx check-clean`, `hx verify` e `hx feature verify HAR-02` terminam com código 0
