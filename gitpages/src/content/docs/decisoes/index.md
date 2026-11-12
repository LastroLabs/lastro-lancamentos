---
title: Índice de decisões
description: Todas as decisões do Lastro, com status, o que destravam e o próximo passo.
---

Cada estudo vira uma decisão registrada e cada decisão em aberto fica visível, com dono e próximo passo.

Os IDs oficiais nascem no `docs/decisoes/DECISIONS.md` quando o grupo aprova. Até lá, nada aqui está aceito: os estudos estão **recomendados, aguardando aprovação** e as D-xx estão **em aberto**.

**Como usar no dia a dia.** Sua feature depende de uma decisão em aberto? Não decida sozinho. Marque a feature como `blocked` e abra uma issue `decisao:` (resposta em 24 h).

## Estudos

| ID | Decisão | Status | O que destrava no desenvolvimento | Página |
|---|---|---|---|---|
| ARQ-01 a ARQ-08 | Arquitetura do sistema: monólito modular em Python, SPA React, sessão no servidor, fila no PostgreSQL, gateway único de IA | Recomendada, aguardando aprovação | Estrutura do repositório, módulos com dono, contratos entre módulos e a fundação da S1 | [Arquitetura do sistema](/lastro-lancamentos/decisoes/arquitetura/) |
| BD-01 a BD-08 | Banco de dados: PostgreSQL relacional, isolamento por escritório e carteira, centavos em BIGINT | Recomendada, aguardando aprovação | Migrações, RLS, deduplicação, aprendizado por cliente e exportação reproduzível | [Banco de dados](/lastro-lancamentos/decisoes/banco-de-dados/) |
| — | Avaliação com LLM e escolha de modelos: código e gabarito onde há resposta certa, juiz LLM só para texto | Recomendada, aguardando aprovação | Métricas no `verify --e2e`, limiares nas fichas, juiz de perguntas validado | [Avaliação com LLM](/lastro-lancamentos/decisoes/avaliacao-llm/) |
| — | UX/UI: fonte Inter, visual limpo, cards espaçados, contraste e responsividade | Recomendada, aguardando aprovação | Design system do frontend (Tailwind e shadcn/ui, fonte Inter) | [UX/UI](/lastro-lancamentos/decisoes/ux-ui/) |

## Decisões em aberto dos requisitos (D-01 a D-09)

Pergunta, requisitos afetados e recomendação copiados dos Requisitos funcionais v0.2. Pelo Fluxo de desenvolvimento, o **Líder** decide as perguntas de negócio (D-xx).

| ID | Decisão | Afeta | Recomendação | Status | Próximo passo |
|---|---|---|---|---|---|
| D-01 | Foto e print entram no MVP? | RF-LEI-06 | Aceitar foto como baixa confiança, sempre com conferência de saldo, se der tempo depois do Must. Hoje está em Should | Em aberto | Reavaliar depois dos Must |
| D-02 | A regra mínima de maquininha entra no MVP? | RF-MAQ-01 | Sim. Sem ela, créditos de cartão viram perguntas inúteis ao cliente. A v2 deixa a maquininha toda fora, então precisa de aprovação | Em aberto | Aprovar ou recusar a recomendação |
| D-03 | Nomes de contrapartes podem ser enviados ao serviço de IA? | RF-SEG-03 | Precisa de decisão da equipe e do termo de uso com os pilotos. Sem nomes, a IA classifica pior | Em aberto | Decisão da equipe e termo de uso com os pilotos |
| D-04 | Qual é o terceiro banco do MVP? | RF-LEI-03 | Sicoob ou Nubank, conforme o que aparecer nos extratos dos pilotos. BB e Inter aparecem nos dois escritórios | Em aberto | Ver os bancos nos extratos dos pilotos |
| D-05 | Qual é o layout exato de importação do Domínio? | RF-EXP-01 | Pedir um exemplo aos dois escritórios e testar a importação na semana 1 | Em aberto | Pedir o exemplo na semana 1 |
| D-06 | Qual o tamanho máximo de arquivo e a validade do link? | RF-ENV-02, RF-SEG-01 | Definir antes de programar o envio | Em aberto | Definir antes da feature de envio |
| D-07 | Contadores do mesmo escritório compartilham carteira? | RF-AUT-02 | Hoje cada contador vê só a sua. Perguntar nos pilotos se isso atende | Em aberto | Perguntar nos pilotos |
| D-08 | Qual o limite de confiança para perguntar ao cliente? | RF-CLA-06, RF-CLA-07 | Calibrar com os dados do gabarito, não por palpite | Em aberto | Calibrar no gabarito |
| D-09 | O chefe também revisa e exporta? Um cliente pode ter mais de um contador ao mesmo tempo? | RF-AUT-02, RF-AUT-03, RF-AUT-04 | Perguntar à colega do grupo e aos pilotos. Enquanto isso, modelar a atribuição para aceitar mais de um contador por cliente, que custa pouco | Em aberto | Perguntar à colega do grupo e aos pilotos |

### O que destrava cada uma

| ID | O que fica bloqueado enquanto estiver aberta |
|---|---|
| D-01 | Leitura de foto e print (Should) |
| D-02 | Regra de adquirentes; os estudos a mantêm desativada até a confirmação |
| D-03 | Se `anonimizar()` pseudonimiza nomes; até lá, pseudonimiza |
| D-04 | O terceiro leitor de PDF |
| D-05 | A exportação final; até lá, `layouts/dominio.yaml` fica marcado PROVISORIO |
| D-06 | Os limites do envio e do link |
| D-07 | A regra de visibilidade da carteira |
| D-08 | Quando uma sugestão vira pergunta |
| D-09 | O papel do chefe na revisão e na exportação |

### Encaminhamento proposto pelos estudos

Estas são propostas dos estudos, não decisões. Elas não substituem as recomendações dos requisitos.

| ID | Proposta | Fonte |
|---|---|---|
| D-01, D-02, D-04 | Leitores extensíveis, regra de adquirente desativada e terceiro banco parametrizado. Não incluir OCR nem novos bancos como entrega confirmada | Banco de dados v1.0 |
| D-03 | Pseudonimizar nomes por padrão (ex.: `PESSOA_017`) | Banco de dados v1.0; Arquitetura do Sistema |
| D-05 | Layout provisório até teste real com as contadoras. Fechar com a importação real no Domínio na semana 4,5 | Banco de dados v1.0; Arquitetura do Sistema |
| D-06 | 7 dias de validade e 20 MiB por arquivo, configuráveis e medidos no piloto | Banco de dados v1.0; Arquitetura do Sistema |
| D-07, D-09 | Carteira individual. O modelo aceita vários vínculos, mas limita a um responsável ativo no início. O chefe revisa e exporta quando estiver atribuído | Banco de dados v1.0 |
| D-08 | Calibrar a confiança com o gabarito e não apresentar percentual arbitrário como acurácia comprovada | Banco de dados v1.0 |

## Pendências em aberto, sem ID

Pontos que as fontes deixam abertos e que ainda não têm número. Ganham ID no `DECISIONS.md` quando o grupo registrar.

| Pendência | Status | Dono, quando a fonte diz | Fonte |
|---|---|---|---|
| Modelo da tarefa e do juiz (API ou local) | Em aberto, sem ID | Responsável pelo harness de avaliação | Avaliação com LLM; Arquitetura do Sistema |
| Valores dos limiares de métrica nas features | Em aberto, sem ID | Quem abre a feature | Avaliação com LLM |
| Orçamento mensal de API e se o juiz roda toda noite ou só quando os prompts mudarem | Em aberto, sem ID | Responsável pelo harness | Avaliação com LLM |
| Onde guardar os rótulos reais da contadora (ex.: pasta privada do grupo) | Em aberto, sem ID | Responsável pelo harness de avaliação | Avaliação com LLM |
| Provedor do piloto: Supabase ou Fly Managed Postgres, ambos em São Paulo; decidir pelo backup verificável e pelo orçamento | Em aberto, sem ID | — | Arquitetura do Sistema |
| Quais são as quatro funcionalidades essenciais que nunca saem no gatilho de corte | Em aberto, sem ID | — | Fluxo de desenvolvimento |
| Os três itens da rubrica de PR além de correção, verificação e escopo | Em aberto, sem ID | Donos do harness | Fluxo de desenvolvimento; Guia do harness |
| Quem assume cada papel (Líder, A, B, G, Front, F4b) e os suplentes. Há uma [proposta](/lastro-lancamentos/home/equipe/) para confirmar no planejamento de segunda | Em aberto, sem ID | Time | Fluxo de desenvolvimento |
| React ou Vue no frontend. A Arquitetura recomenda React; aguardando confirmação. Critério do Fluxo: pelo menos 3 pessoas conseguem revisar o código | Em aberto, sem ID | Time, em até 48 h após 10/11 | Fluxo de desenvolvimento; Arquitetura do Sistema |
| Horários dos rituais: planejamento na segunda (45 min), fechamento no domingo (30 min), sexta sem reunião | Em aberto, sem ID | Time | Fluxo de desenvolvimento |
| Feriado de 20/11: o time trabalha ou não? Isso muda a meta da S2 | Em aberto, sem ID | Time | Fluxo de desenvolvimento |
| Regra do repositório público: nenhum dado real, nome de escritório ou segredo entra, nem em teste | Em aberto, sem ID | Time | Fluxo de desenvolvimento |
| Dados para teste: quem pede ao escritório um ou dois extratos anonimizados, só para estudar a estrutura, fora do repositório | Em aberto, sem ID | Time | Fluxo de desenvolvimento |

Fontes: Requisitos funcionais v0.2; Lastro — Arquitetura do Sistema; Banco de dados para o Lastro v1.0; Estudo de Avaliação com LLM; Estudo de UX/UI; Fluxo de desenvolvimento do Lastro.
