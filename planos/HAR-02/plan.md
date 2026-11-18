# Plan — HAR-02 · Filtrar hx state por estado e resumir só o que pede atenção

**Status:** pronto para revisão
**Branch:** feat/HAR-02-filtrar-hx-state-por-estado-e-resumir-so · **Data:** 17/11/2026 · **Responsável:** caio-nascime
**Tasks:** planos/HAR-02/tasks.md

## 1. A decidir (humano)
Nenhuma é BLOQUEANTE: todas têm padrão sugerido e o plano segue com ele se ninguém responder.
| # | Pergunta | Gravidade | Sugestão de padrão | Decide |
|---|---|---|---|---|
| 1 | `--atencao` junto com `--estado` pode? A ficha não diz. | ATENÇÃO | Recusar com ERRO/MOTIVO/CORREÇÃO ("use um ou outro"), código 2. Evita combinação ambígua (união ou interseção?). | caio-nascime |
| 2 | Filtro `--estado` que não casa com nenhuma ficha: o que imprimir? A ficha só cobre o caso de `--atencao` ("Nada pede atenção."). | ATENÇÃO | Imprimir cabeçalho do painel sem linhas, e `Resumo` completo. Sem mensagem nova (não inventar texto). | caio-nascime |
| 3 | Em `--atencao` sem nada, além de "Nada pede atenção." mostra a linha `Resumo`? | ATENÇÃO | Sim: título, "Nada pede atenção.", `Resumo` (coerente com c4: Resumo sempre presente). | caio-nascime |
| 4 | O `AGENTS.md` (seção 2) descreve `hx state` sem as flags. Atualizar? | ATENÇÃO | Sim, uma linha, em PR separado ou no mesmo PR; fora do escopo desta sessão de código. | caio-nascime |

Mudanças sugeridas na ficha (o humano aplica em PR): incluir um critério/exemplo para as perguntas 1 e 2 se a resposta for diferente do padrão; opcional: acrescentar teste `test_estado_e_atencao_juntos_sao_recusados`.

## 2. Decisões tomadas pelo agente
### D1 · Validar `--estado` à mão, não com `choices` do argparse
- **Alternativas:** A) `choices=ESTADOS` do argparse · B) validar dentro de `cmd_state` e levantar `HarnessErro`
- **Escolhida:** B — **motivo:** `choices` gera a mensagem padrão do argparse (sem ERRO/MOTIVO/CORREÇÃO), contrariando c2. B reaproveita `HarnessErro` e `mostrar_erro`.
- **Fontes:** `tools/harness.py` (`HarnessErro`, `main`); sem pesquisa externa.
- **Impacto:** T3 (c2).
- [ ] confirmar

### D2 · `--estado` com `action="append"` (repetir a flag)
- **Alternativas:** A) repetir `--estado X --estado Y` · B) lista separada por vírgula · C) `nargs="+"`
- **Escolhida:** A — **motivo:** é o formato do exemplo da ficha (c1). Vírgula/`nargs` não são pedidos.
- **Fontes:** ficha c1.
- **Impacto:** T2, T4.
- [ ] confirmar

### D3 · Validar os argumentos antes de ler as fichas
- **Escolhida:** estado inválido é recusado antes de carregar fichas — **motivo:** c2 pede "sem listar nada" e o erro de uso não deve depender de as fichas estarem válidas. Alternativa (ler antes) esconderia o erro de uso atrás de erro de ficha.
- [ ] confirmar

### D4 · Sem biblioteca nova
- Só `argparse` da biblioteca padrão. [ ] confirmar

## 3. Resumo e abordagem
`hx state` ganha dois filtros de exibição: `--estado` (repetível) e `--atencao` (atalho para blocked + regressed). O `Resumo` continua contando todas as fichas.
1. Em `_criar_parser`, adicionar as flags ao `p_state`.
2. Em `cmd_state`, validar os estados antes de carregar as fichas (D3) usando `ESTADOS`.
3. Depois de `_carregar_fichas_validas` e da ordenação, filtrar só a lista de linhas; calcular `contagem` sobre a lista completa.
4. `--atencao` equivale a filtro `{blocked, regressed}`; se não sobrar linha, imprime "Nada pede atenção.".
5. Sem flags, o caminho de impressão atual não muda (c4, saída idêntica).

## 4. Contexto encontrado
- **Código relacionado:** `tools/harness.py` — `cmd_state` (linha ~408), `ESTADOS` (~163), `_criar_parser` (~1171), `main` (devolve 2 em `HarnessErro`).
- **Dependências:** nenhuma (`depende_de` vazio).
- **Reaproveitar:** `ESTADOS`, `HarnessErro`/`mostrar_erro`, `_carregar_fichas_validas`, `_chave_natural`, helpers de teste `ficha_valida`, `gravar`, `rodar_state` em `tests/harness/test_fase_a.py` (importar ou replicar; hoje não há `conftest` — conferir na T1).
- **Não criar:** segundo formatador de tabela, segunda lista de estados, novo tipo de erro.
- **Testes existentes que protegem c4:** `test_fase_a.py` (~220-249) verifica linha Resumo e tabela; `test_fase0.py` chama `main(["state"])`.
- **Docs:** não há `docs/modulos/harness.md`. `tools/` exige aprovação do dono (CODEOWNERS, SECURITY.md §7).
- **Pesquisa externa:** sem pesquisa externa necessária.

## 5. Decisões (já resolvidas)
- (nenhuma ainda)

## 6. Avaliação da ficha
| # | Achado | Gravidade | Critério |
|---|---|---|---|
| 1 | `--atencao` + `--estado` não definido | ATENÇÃO | c1/c3 |
| 2 | Filtro sem resultado não definido | ATENÇÃO | c1 |
| 3 | Se `Resumo` aparece com "Nada pede atenção." não está explícito | ATENÇÃO | c3/c4 |
| 4 | c4 "saída idêntica à atual" depende dos testes da fase A, que já a cobrem; `test_sem_filtro_saida_inalterada` deve comparar com saída esperada fixa, não com a função nova | ATENÇÃO | c4 |
| 5 | c2: "código de saída diferente de 0" — `main` já devolve 2; testar `== 2`, coerente com o resto do harness | ATENÇÃO | c2 |
| 6 | Verificação por `pytest` direto prova cada critério; sem dado real; sem requisitos RF vinculados (`requisitos: []`) | OK | todos |
| 7 | Tamanho: 4 critérios, 1 módulo, 1 arquivo de produção | OK | — |

## 7. Riscos
- Regressão da saída sem filtro → T1 inclui teste com saída fixa; testes da fase A seguem rodando em `hx verify`.
- Fichas de teste com dado realista → só IDs `T-01` etc. e títulos genéricos (SECURITY.md §3).
- `hx verify` exige Docker (falhou na S1 por daemon desligado) → ligar o Docker antes da T5; se não der, registrar como "não rodou".
- Editar `tools/harness.py` exige aprovação do dono no PR (CODEOWNERS).

## 8. Aprovação
- [ ] Perguntas BLOQUEANTES respondidas (nenhuma aberta)
- [ ] Decisões do agente confirmadas (D1 a D4)
- [ ] Plan e tasks revisados por <nome> em DD/MM
