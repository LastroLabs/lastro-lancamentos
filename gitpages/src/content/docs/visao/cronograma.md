---
title: Cronograma
description: Quatro semanas até a demo ao vivo de 07/12/2026.
---

O cronograma vigente é o da **estratégia de desenvolvimento** (Fluxo de desenvolvimento do Lastro, reunião de 10/11/2026). O progresso é medido em **features que passam**, não em horas. As metas e as datas são proposta.

## Semanas e metas

| Semana | Período | Foco | Meta acumulada (features `passing`) |
|---|---|---|---|
| S1 | 09/11 a 15/11 | Fundação | 6 de 39 |
| S2 | 16/11 a 22/11 | Ritmo | 18 de 39 |
| S3 | 23/11 a 29/11 | Integração | 32 de 39 |
| S4 | 30/11 a 06/12 | Congelamento | 39 de 39 |

### S1 · Fundação

- **11/11:** CI e `init` rodando em pelo menos 5 das 7 máquinas.
- **13/11:** contratos congelados, `AGENTS.md` e features revisados, primeiro PR mesclado.
- **15/11:** gerador de fixtures pronto e a jornada J1 em versão inicial.

### S2 · Ritmo

- Meta acumulada: 18 features `passing`.
- 20/11 é feriado: confirmar se o time trabalha. Isso muda a meta da S2.
- Primeiro uso do gatilho de corte no domingo, se necessário.

### S3 · Integração

- Meta acumulada: 32 features `passing`.
- Jornadas E2E completas rodando no noturno.
- Revisão da lista de itens rebaixados com o time.

### S4 · Congelamento

- Meta acumulada: 39 features `passing`.
- **03/12:** congelamento. Depois disso, só correção.
- **04/12:** ensaio da demo. 05 e 06/12: reserva.
- **07/12:** demo ao vivo para a banca e o AILab.

## Gatilho de corte

Se no domingo o time estiver abaixo da meta acumulada, rebaixa itens da lista combinada. As quatro funcionalidades essenciais nunca saem.

:::caution[Pendência]
A estratégia não diz quais são as **quatro funcionalidades essenciais**. Está registrado como pendência em aberto, sem ID, no [índice de decisões](/lastro-lancamentos/decisoes/#pendências-em-aberto-sem-id).
:::

## A outra versão: roteiro da Arquitetura

O documento Lastro — Arquitetura do Sistema (10/11/2026) planeja **4,5 semanas** para **6 pessoas**. Os Requisitos v0.2 também falam em 4 semanas e meia. A estratégia vigente usa 4 semanas e 7 pessoas. O roteiro abaixo fica como referência da ordem de construção por frente.

A ordem segue o caminho do dado: primeiro alguém entra e envia, depois o sistema lê e confere, depois classifica, por fim revisa e exporta.

| Semana | Plataforma | Frontend | Leitura | Classificação e IA | Jornada demonstrável |
|---|---|---|---|---|---|
| 1 | Compose, CI, migrações base, sessão, RLS, escritório/usuário/cliente | Esqueleto do app, login, design system, cliente da API gerado | Spike ofx-br × ofxparse no gabarito; leitor OFX | Contratos, gateway `ia/` com `anonimizar()` e teste de vazamento | Contador entra e cadastra cliente |
| 2 | Link do cliente, upload, quarentena, fila; plano de contas por planilha | Página de envio no celular; carteira com status | PDF do BB; conferência de saldo linha a linha ou dia a dia | Regras por palavra-chave, transferência interna, sócio | Cliente envia OFX, contador vê "enviado" e saldo conferido |
| 3 | Atribuição e reatribuição com revogação; auditoria | Tela de revisão (três grupos, ações em lote) | PDF do Inter; continuidade e cobertura do mês; dedup por FITID | Histórico, parecidas (`pg_trgm`), IA nas sobras, confiança | Extrato vira sugestões revisáveis |
| 4 | Exportação: fotografia, Excel por YAML, conciliação | Perguntas com um toque; tela de exportação | Avisos em português simples; casos de defeito nas fixtures | Agrupamento de perguntas, aprendizado por cliente | Ciclo completo: envio → pergunta → revisão → planilha |
| 4,5 | Deploy do piloto, backup testado, `check-clean` | Ajustes de usabilidade com a contadora | Correções do gabarito | Calibrar limite de confiança (D-08) | Importação real no Domínio (fecha D-05) |

Fontes: Fluxo de desenvolvimento do Lastro (seção Cronograma); Lastro — Arquitetura do Sistema, seção 10; Requisitos funcionais v0.2.
