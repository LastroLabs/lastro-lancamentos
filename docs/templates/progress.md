# {{ID}} · {{TITULO}}

- Responsável: {{RESPONSAVEL}} · Branch: `{{BRANCH}}` · Início: {{DATA}}
- Ficha: `features/{{ID}}.json` (estado e critérios ficam lá; não repita aqui)

<!--
Como preencher (agente, ao encerrar a sessão):
- REESCREVA as seções do topo: Objetivo, Próxima ação, Bloqueios e perguntas.
- ACRESCENTE, sem apagar o que já existe, em Feito, Rodei, Falhou e Decisões.
  Cada linha começa com a data (DD/MM) e a sessão, ex.: "- 14/11 · S2 · ...".
- Registre só o que realmente rodou. Sem dado real, nome de cliente ou segredo.
- Não escreva estado (passing etc.) aqui: ele fica na ficha, gravado pelo script.
-->

## Objetivo
(1 a 2 linhas: o comportamento que esta feature entrega)

## Próxima ação
(a primeira coisa a fazer ao retomar; de preferência um comando ou um arquivo)

## Bloqueios e perguntas
- (nenhum)

## Feito
- DD/MM · S1 ·

## Rodei
- DD/MM · S1 · `comando` → resultado resumido

## Falhou
- DD/MM · S1 · o que falhou e a causa, se souber

## Decisões
- DD/MM · S1 · decisão e o porquê (se for D-xx, registre também em `docs/decisoes/DECISIONS.md`)

## Fim de sessão
- [ ] `hx verify` verde, ou a falha está descrita em "Falhou"
- [ ] Nada quebrado nem pela metade na branch; commit feito
- [ ] "Próxima ação" atualizada
- [ ] Nenhum dado real nem segredo nas anotações