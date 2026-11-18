# HAR-02 · Filtrar hx state por estado e resumir só o que pede atenção

- Responsável: caio-nascime · Branch: `feat/HAR-02-filtrar-hx-state-por-estado-e-resumir-so` · Início: 18/11/2026
- Ficha: `features/HAR-02.json` (estado e critérios ficam lá; não repita aqui)

<!--
Como preencher (agente, ao encerrar a sessão):
- REESCREVA as seções do topo: Objetivo, Próxima ação, Bloqueios e perguntas.
- ACRESCENTE, sem apagar o que já existe, em Feito, Rodei, Falhou e Decisões.
  Cada linha começa com a data (DD/MM) e a sessão, ex.: "- 14/11 · S2 · ...".
- Registre só o que realmente rodou. Sem dado real, nome de cliente ou segredo.
- Não escreva estado (passing etc.) aqui: ele fica na ficha, gravado pelo script.
-->

## Objetivo
`hx state` passa a aceitar `--estado` (um ou mais) e `--atencao` (blocked e regressed), com erro padronizado para estado inválido e `Resumo` sempre contando todas as fichas.


## Próxima ação
Rodar `/planejar HAR-02` em sessão nova, revisar `planos/HAR-02/plan.md` (humano aprova) e só então gerar os testes de `tests/harness/test_state_filtro.py`.


## Bloqueios e perguntas
- (nenhum)

## Feito

- 18/11 · S1 · ficha `features/HAR-02.json` criada (rascunho de 4 critérios, revisado pelo dev), mesclada na `developer`; feature aberta com `hx feature start`.

## Rodei

- 18/11 · S1 · `py tools/harness.py state` → ficha válida, HAR-02 `not_started` e HX-10 `passing` (antes do start)
- 18/11 · S1 · `hx verify` → não rodou: Docker indisponível (daemon desligado)

## Falhou

- 18/11 · S1 · `hx verify` recusado: Docker Desktop desligado. Nenhum código foi escrito nesta sessão, então não há regressão conhecida.

## Decisões

- 18/11 · S1 · prioridade `should` e dependências vazias na ficha (HX-09 do storytelling não existe no repo); critérios c2 a c4 definidos como rascunho e aprovados pelo dev.

## Fim de sessão
- [ ] `hx verify` verde, ou a falha está descrita em "Falhou"
- [ ] Nada quebrado nem pela metade na branch; commit feito
- [ ] "Próxima ação" atualizada
- [ ] Nenhum dado real nem segredo nas anotações