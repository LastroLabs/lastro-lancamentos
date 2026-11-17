# Plan — {{ID}} · {{TITULO}}

<!--
Gerado por /planejar. Máximo 150 linhas. Sem código.
Quem muda o Status para "aprovado" é o humano, nunca o agente.
Apague este comentário ao preencher.
-->

**Status:** rascunho (aguardando respostas) | pronto para revisão | aprovado
**Branch:** {{BRANCH}} · **Data:** {{DATA}} · **Responsável:** {{RESPONSAVEL}}
**Tasks:** planos/{{ID}}/tasks.md

## 1. A decidir (humano)
Tudo que bloqueia ou depende de uma pessoa. Resolvida → mova para "5. Decisões".
| # | Pergunta | Gravidade | Sugestão de padrão | Decide |
|---|---|---|---|---|
| 1 | <pergunta> | BLOQUEANTE / ATENÇÃO | <padrão> | <pessoa> |

Mudanças sugeridas na ficha (o humano aplica em PR): <lista ou "nenhuma">

## 2. Decisões tomadas pelo agente
Cada uma precisa de confirmação humana.
### D1 · <decisão em uma frase>
- **Alternativas:** A) <…> · B) <…> · C) <…>
- **Escolhida:** <A> — **motivo:** <por quê>
- **Fontes:** <link> (acesso em DD/MM) · <link>
- **Impacto:** <tasks e critérios afetados>
- [ ] confirmar

## 3. Resumo e abordagem
<Resumo em 1 ou 2 frases. Abordagem em 5 a 10 linhas: onde a mudança entra e em que ordem. Sem código.>

## 4. Contexto encontrado
- **Código relacionado:** `caminho` (função ou classe)
- **Dependências:** `<ID>` (passing/…) expõe `<o quê>`
- **Reaproveitar:** `<o que já existe>`
- **Não criar:** `<o que não deve ser duplicado>`
- **Pesquisa externa:** <resumida, ou "sem pesquisa externa necessária">

## 5. Decisões (já resolvidas)
- DD/MM · <decisão> (resposta à pergunta N, por <pessoa>)

## 6. Avaliação da ficha
| # | Achado | Gravidade | Critério |
|---|---|---|---|

## 7. Riscos
- <risco> → <como o plano lida com ele>

## 8. Aprovação
- [ ] Perguntas BLOQUEANTES respondidas
- [ ] Decisões do agente confirmadas
- [ ] Plan e tasks revisados por <nome> em DD/MM
