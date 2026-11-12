---
title: Quando algo trava
description: Respostas combinadas para as situações mais comuns, com dono e prazo.
---

Para cada situação comum existe uma resposta combinada, com dono e prazo.

| Situação | O que fazer | Quem resolve | Em quanto tempo | Por que evita gargalo |
|---|---|---|---|---|
| O critério está ambíguo | Pare antes de codar e abra um PR corrigindo a ficha. O dono do módulo aprova. | Você e o dono do módulo | No mesmo dia | Evita testar e construir a coisa errada. |
| Falta uma decisão | Abra uma issue `decisao:`, marque a feature como `blocked` (bloqueada_por: D-xx) e peça outra feature ao líder. | Quem tem autoridade sobre o tema | Resposta em 24 h | Ninguém fica parado e ninguém decide sozinho. |
| O noturno falhou | A feature vira `regressed`. Quem a escreveu conserta antes de começar feature nova. | Autor da feature | Antes da próxima feature | A main continua confiável. |
| Meu PR está sem review | Depois de 24 h, avise no canal. O líder reatribui o revisor. | Líder | 24 h | A fila de revisão não vira gargalo. |
| O agente falhou 2 vezes igual | Pare. Registre a causa no progress e peça ajuda antes de tentar a terceira. | Você, com apoio do dono do módulo | Assim que notar | Evita horas girando em círculo e gastando tokens. |
| Preciso mudar um contrato | Abra uma issue `contrato:`. O dono B decide e versiona. Enquanto isso, siga com outra parte da feature. | Dono B (contratos) | 24 h | Mudar entrada ou saída não quebra os outros módulos. |
| A feature está grande demais | Passou de 2 sessões? Avise e divida em duas fichas, cada uma com seus critérios. | Você e o dono do módulo | Ao perceber | Feature pequena gera PR pequeno e revisão rápida. |
| Quero pegar a feature de outra pessoa | O responsável é único. A troca é um PR na ficha, com aviso ao dono atual. | Os dois, com o líder | Mesmo dia | Evita duas pessoas fazendo a mesma coisa. |
| Meu Docker não sobe | Abra uma issue `harness:` no mesmo dia e peça para parear com quem já roda. | Dono A (processo) | Mesmo dia | Ambiente igual para todos é o que sustenta o resto. |
| Recebi um extrato real | Ele não entra no repositório, que é público. Descreva só a estrutura em `docs/bancos/` e gere uma fixture sintética equivalente. | Guardião de dados | Antes de qualquer commit | Protege os dados de terceiros (LGPD). |

## Prefixos de issue

| Prefixo | Quando usar | Prazo de resposta |
|---|---|---|
| `decisao:` | Falta uma decisão de produto ou negócio (ex.: layout do Domínio) | 24 h |
| `contrato:` | Precisa mudar entrada ou saída entre módulos | 24 h |
| `fixture:` | Falta um extrato sintético ou caso de defeito para testar | 24 h |
| `harness:` | Comando, regra ou documento do harness atrapalhou | 24 h |

Fontes: Fluxo de desenvolvimento do Lastro, seção 07; Lastro: guia do harness v0.1.
