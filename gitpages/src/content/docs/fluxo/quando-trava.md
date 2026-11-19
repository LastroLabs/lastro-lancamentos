---
title: Quando algo trava
description: Respostas combinadas para as situações mais comuns, com dono e prazo.
---

Para cada situação comum existe uma resposta combinada, com dono e prazo.

| Situação | O que fazer | Quem resolve | Em quanto tempo | Por que evita gargalo |
|---|---|---|---|---|
| O critério está ambíguo | Pare antes de codar e abra um PR corrigindo a ficha. O dono do módulo aprova. | Você e o dono do módulo | No mesmo dia | Evita testar e construir a coisa errada. |
| Falta uma decisão | Abra uma issue `decisao:` e peça outra feature à líder. A ficha vira `blocked` (bloqueada_por: D-xx) por PR do dono do harness; nenhum comando grava `blocked` ainda. | A líder, que decide as D-xx | Resposta em 24 h | Ninguém fica parado e ninguém decide sozinho. |
| Uma feature `passing` voltou a falhar | O `hx feature verify` a grava como `regressed`. Quem a escreveu conserta antes de começar feature nova (`hx feature start` aceita `regressed`). | Autor da feature | Antes da próxima feature | A `developer` continua confiável. |
| Meu PR está sem review | Depois de 24 h, avise no canal. A líder reatribui o revisor. | Líder | 24 h | A fila de revisão não vira gargalo. |
| O agente falhou 2 vezes igual | Pare. Registre a causa no progress e peça ajuda antes de tentar a terceira. | Você, com apoio do dono do módulo | Assim que notar | Evita horas girando em círculo e gastando tokens. |
| Preciso mudar um contrato | Abra uma issue `contrato:` e avise o dono do módulo (AGENTS.md, regra 11). Enquanto isso, siga com outra parte da feature. | Dono do módulo | 24 h | Mudar entrada ou saída não quebra os outros módulos. |
| A feature está grande demais | Passou de 2 sessões? Avise e divida em duas fichas, cada uma com seus critérios. | Você e o dono do módulo | Ao perceber | Feature pequena gera PR pequeno e revisão rápida. |
| Quero pegar a feature de outra pessoa | O responsável é único. A troca é um PR na ficha mudando o `responsavel`, com aviso ao dono atual. O `hx` só deixa iniciar quem tem `HX_USUARIO` igual ao `responsavel`. | Os dois, com a líder | Mesmo dia | Evita duas pessoas fazendo a mesma coisa. |
| Meu Docker não sobe | Abra uma issue `harness:` no mesmo dia e peça para parear com quem já roda. Sem Docker, o `hx verify` e o `hx feature verify` param com ERRO; `hx state` e `hx check-clean` continuam funcionando. | Caio (harness e CI) | Mesmo dia | Ambiente igual para todos é o que sustenta o resto. |
| Recebi um extrato real | Ele não entra no repositório, que é público. Descreva só a estrutura (a pasta `docs/bancos/` ainda não existe) e gere uma fixture sintética equivalente. | Guardião de dados | Antes de qualquer commit | Protege os dados de terceiros (LGPD). |

## Prefixos de issue

| Prefixo | Quando usar | Prazo de resposta |
|---|---|---|
| `decisao:` | Falta uma decisão de produto ou negócio (ex.: layout do Domínio) | 24 h |
| `contrato:` | Precisa mudar entrada ou saída entre módulos | 24 h |
| `fixture:` | Falta um extrato sintético ou caso de defeito para testar | 24 h |
| `harness:` | Comando, regra ou documento do harness atrapalhou | 24 h |

Fontes: Fluxo de desenvolvimento do Lastro, seção 07; `tools/harness.py` e `AGENTS.md` (branch `developer`); `docs/decisoes/DECISIONS.md` (18/11/2026).
