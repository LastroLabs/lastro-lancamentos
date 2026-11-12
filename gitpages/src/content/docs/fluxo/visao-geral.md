---
title: Por que um harness
description: Como o time vai construir o Lastro rápido e sem retrabalho.
---

Sete pessoas, quatro semanas, uma demo ao vivo em 07/12. O **harness** é o conjunto de documentos, scripts e regras que mantém o time e os agentes de IA trabalhando na mesma direção. Ele evita que as pessoas esperem umas pelas outras e que alguém quebre o que já funciona.

O **repositório é a única fonte da verdade**. Se algo não está escrito nele, o agente não sabe e a próxima pessoa também não.

| Número | Valor |
|---|---|
| Pessoas, todas codando | 7 |
| Semanas de sprint | 4 |
| Demo ao vivo na banca | 07/12 |
| Fonte da verdade | 1: o repositório |

## Cinco coisas que costumam dar errado

Sem método, quanto mais gente e mais IA, mais rápido o projeto acumula erro e espera. Cada problema tem um mecanismo que o evita.

| Problema | O que acontece | O harness resolve com | Exemplo |
|---|---|---|---|
| O agente não sabe o que o time decidiu | Cada sessão recomeça do zero. Duas pessoas pedem a mesma coisa e recebem soluções diferentes. | `AGENTS.md` curto, `progress/` por feature e `DECISIONS.md`. | Um agente usou decimal em vez de centavos e o saldo não fechou. Com a regra no `AGENTS.md`, o agente já começa sabendo. |
| O agente corrige a própria prova | Ele escreve o código e os testes juntos. Tudo passa, mas o comportamento está errado. | Testes antes do código, em sessão separada, com gabarito sintético independente e revisão por outra pessoa. | Com teste primeiro, o critério da ficha exige tratar duplicados e o teste falha até o código fazer isso. |
| Ninguém sabe o que está pronto | "Quase pronto" por dias. A demo chega e ninguém sabe o que funciona. | Estado só muda por script. `passing` significa comando verde. A rotina noturna reverifica tudo. | Uma mudança em outro módulo quebrou a leitura OFX. O noturno detecta de madrugada e a ficha volta para `regressed`. |
| Esperas e conflitos entre pessoas | PR parado, decisão em aberto, duas pessoas mexendo no mesmo arquivo. | Módulos com dono, WIP=1, issues com prazo de 24 h, feature `blocked` e troca de feature em vez de esperar. | Falta o layout do Domínio: a exportação fica `blocked` por D-05 e a pessoa pega outra feature. |
| Dado sensível vazando | O repositório é público e extratos reais têm dados de terceiros (LGPD). | Só dados sintéticos, `anonimizar()` antes de qualquer LLM e `check-clean` antes de cada PR. | Um trecho de extrato real num teste: o `check-clean` acusa no PR e o revisor bloqueia pela rubrica. |

## Onde está cada parte

- [O ritmo da semana](/lastro-lancamentos/fluxo/semana/): os sete momentos e a única reunião.
- [Ciclo de uma feature](/lastro-lancamentos/fluxo/ciclo-da-feature/): da ficha ao merge e a estratégia de testes.
- [Quando algo trava](/lastro-lancamentos/fluxo/quando-trava/): respostas combinadas, com dono e prazo.
- [Equipe](/lastro-lancamentos/home/equipe/): os seis papéis e quem assume cada um.
- [Harness](/lastro-lancamentos/harness/documentos-e-comandos/): documentos do repositório e comandos.

Fonte: Fluxo de desenvolvimento do Lastro, proposta v0.1 para a reunião de 10/11/2026. Os comandos e saídas citados são exemplos ilustrativos do fluxo, a ajustar na primeira semana.
