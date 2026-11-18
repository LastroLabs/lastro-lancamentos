---
title: Índice de decisões
description: Todas as decisões do Lastro, com status, data, o que destravam e o próximo passo.
---

Cada estudo vira uma decisão registrada e cada decisão pendente fica visível, com dono e próximo passo.

A fonte de verdade é o `docs/decisoes/DECISIONS.md` do repositório. Este índice resume o que está lá. Em 18/11/2026 a líder fechou a arquitetura (ARQ), o banco de dados (BD), os padrões provisórios das D-xx e as regras de processo e de revisão das fichas.

Legenda de status, como no `DECISIONS.md`:

- **aprovada:** decidida pela líder;
- **aprovada (provisória):** padrão configurável que vale até o piloto mostrar o contrário;
- **assumida:** recomendação da revisão aplicada sem mudar o escopo de nenhum RF (a líder pode reverter);
- **pendente:** ainda sem decisão.

**Como usar no dia a dia.** Sua feature depende de uma decisão pendente? Não decida sozinho. Abra uma issue `decisao:` (resposta em 24 h) e pegue outra feature. Uma ficha bloqueada fica com `estado: blocked` e `bloqueada_por: "D-xx"`. Ver [Orquestração](/lastro-lancamentos/fluxo/orquestracao/#máquina-de-estados).

## Estudos

| ID | Decisão | Status | Data | O que destrava no desenvolvimento | Página |
|---|---|---|---|---|---|
| ARQ-01 a ARQ-08 | Arquitetura do sistema: monólito modular em Python 3.14 + FastAPI, SPA React, sessão no servidor, fila no PostgreSQL, gateway único de IA, API em `/api/v1` | Aprovada | 18/11/2026 | Estrutura do repositório, módulos com dono, contratos entre módulos e a fundação da S1 | [Arquitetura do sistema](/lastro-lancamentos/decisoes/arquitetura/) |
| BD-01 a BD-08 | Banco de dados: PostgreSQL 18, migrações versionadas, isolamento por escritório e carteira com RLS, centavos em BIGINT, CI com PostgreSQL e fixtures sintéticas | Aprovada | 18/11/2026 | Migrações, RLS, deduplicação, aprendizado por cliente e exportação reproduzível | [Banco de dados](/lastro-lancamentos/decisoes/banco-de-dados/) |
| — | Avaliação com LLM e escolha de modelos: código e gabarito onde há resposta certa, juiz LLM só para texto | Recomendada, aguardando aprovação | — | Métricas de avaliação, limiares nas fichas, juiz de perguntas validado | [Avaliação com LLM](/lastro-lancamentos/decisoes/avaliacao-llm/) |
| — | UX/UI: fonte Inter, visual limpo, cards espaçados, contraste e responsividade | Recomendada, aguardando aprovação | — | Design system do frontend (Tailwind e shadcn/ui, fonte Inter) | [UX/UI](/lastro-lancamentos/decisoes/ux-ui/) |

Fonte: `DECISIONS.md`, seção 1. A avaliação com LLM e o UX/UI não aparecem no `DECISIONS.md` e continuam como recomendação.

## Decisões dos requisitos (D-01 a D-09)

Pergunta, requisitos afetados e recomendação copiados dos Requisitos funcionais v0.2. Quem decide as perguntas de negócio é a líder. A coluna "Decisão em 18/11" vem do `DECISIONS.md`, seção 2.

| ID | Decisão | Afeta | Recomendação dos requisitos | Status | Decisão em 18/11 |
|---|---|---|---|---|---|
| D-01 | Foto e print entram no MVP? | RF-LEI-06 | Aceitar foto como baixa confiança, sempre com conferência de saldo, se der tempo depois do Must. Hoje está em Should | Pendente | — |
| D-02 | A regra mínima de maquininha entra no MVP? | RF-MAQ-01 | Sim. Sem ela, créditos de cartão viram perguntas inúteis ao cliente. A v2 deixa a maquininha toda fora, então precisa de aprovação | Aprovada (provisória), 18/11 | Regra mínima de adquirente prevista, mas **desativada** até a confirmação; leitores extensíveis |
| D-03 | Nomes de contrapartes podem ser enviados ao serviço de IA? | RF-SEG-03 | Precisa de decisão da equipe e do termo de uso com os pilotos. Sem nomes, a IA classifica pior | Aprovada, 18/11 | **Todo** nome de contraparte, pessoa ou empresa, é pseudonimizado antes de ir à IA (`PESSOA_nnn` / `EMPRESA_nnn`). Ligado por padrão e configurável |
| D-04 | Qual é o terceiro banco do MVP? | RF-LEI-03 | Sicoob ou Nubank, conforme o que aparecer nos extratos dos pilotos. BB e Inter aparecem nos dois escritórios | Aprovada (provisória), 18/11 | BB e Inter; terceiro banco parametrizado, sem banco novo como entrega confirmada |
| D-05 | Qual é o layout exato de importação do Domínio? | RF-EXP-01 | Pedir um exemplo aos dois escritórios e testar a importação na semana 1 | Aprovada (provisória), 18/11 | Layout provisório (`layouts/dominio.yaml` marcado PROVISORIO) até o teste real de importação |
| D-06 | Qual o tamanho máximo de arquivo e a validade do link? | RF-ENV-02, RF-SEG-01 | Definir antes de programar o envio | Aprovada (provisória), 18/11 | Link vale **7 dias**; arquivo de no máximo **20 MiB**; os dois configuráveis |
| D-07 | Contadores do mesmo escritório compartilham carteira? | RF-AUT-02 | Hoje cada contador vê só a sua. Perguntar nos pilotos se isso atende | Aprovada (provisória), 18/11 | Carteira individual: cada contador vê só os clientes atribuídos a ele |
| D-08 | Qual o limite de confiança para perguntar ao cliente? | RF-CLA-06, RF-CLA-07 | Calibrar com os dados do gabarito, não por palpite | Pendente | — |
| D-09 | O chefe também revisa e exporta? Um cliente pode ter mais de um contador ao mesmo tempo? | RF-AUT-02, RF-AUT-03, RF-AUT-04 | Perguntar à colega do grupo e aos pilotos. Enquanto isso, modelar a atribuição para aceitar mais de um contador por cliente, que custa pouco | Aprovada (provisória), 18/11 | Um responsável ativo por cliente (o modelo aceita vários vínculos); o chefe vê o escritório inteiro |

### O que cada uma muda no desenvolvimento

| ID | Efeito |
|---|---|
| D-01 | Pendente: leitura de foto e print (Should) continua fora até decidir |
| D-02 | A regra de adquirente existe no código, mas vem desligada |
| D-03 | `anonimizar()` pseudonimiza todo nome de contraparte, e não só CPF, CNPJ, agência e conta |
| D-04 | O terceiro leitor de PDF fica parametrizado, sem entrega confirmada |
| D-05 | A exportação lê `layouts/dominio.yaml`, marcado PROVISORIO, até a importação real no Domínio |
| D-06 | Limites do envio e do link em configuração: 7 dias e 20 MiB |
| D-07 | A carteira é individual; o contador só vê os clientes atribuídos a ele |
| D-08 | Pendente: quando uma sugestão vira pergunta ao cliente |
| D-09 | Um responsável ativo por cliente; o chefe vê todos os clientes do escritório |

## Processo (PROC)

Regras do fluxo de trabalho com o harness. Fonte: `DECISIONS.md`, seção 3. Detalhes em [Decisão: processo e fichas](/lastro-lancamentos/decisoes/processo/).

| ID | Status | Data | Decisão |
|---|---|---|---|
| PROC-01 | Aprovada | 18/11/2026 | Branch da verdade = `developer`: é a base das branches `feat/*`. A `main` fica para release e para este site |
| PROC-02 | Aprovada | 18/11/2026 | Identidade da dev = variável `HX_USUARIO` com o handle do GitHub, o mesmo do campo `responsavel` da ficha |
| PROC-03 | Aprovada | 18/11/2026 | Onda = semana do cronograma, de 1 a 4 |
| PROC-04 | Aprovada | 18/11/2026 | `verificacao` lista 100% dos testes da ficha |

## Revisão das fichas da onda S1 (P-xx)

Decisões tomadas na revisão do primeiro lote de fichas. Fonte: `DECISIONS.md`, seção 4. As de acesso e cadastro têm página própria: [Decisão: acesso e cadastro](/lastro-lancamentos/decisoes/acesso-e-cadastro/).

| ID | Status | Data | Decisão |
|---|---|---|---|
| P-01 | Aprovada | 18/11/2026 | Status HTTP de recusa: **401** sem sessão ou com sessão encerrada; **403** com sessão, mas o papel não permite; **404** para recurso de outra carteira, de outro escritório ou inexistente, com corpo idêntico |
| P-02 | Aprovada | 18/11/2026 | Só o chefe cadastra cliente. Um contador sozinho no escritório é o próprio chefe |
| P-02a | Aprovada | 18/11/2026 | Releitura do RF-CAD-01: "o chefe deve poder cadastrar um cliente com nome e CNPJ" |
| P-03 | Aprovada | 18/11/2026 | "Fichas encadeadas na mesma onda" conta só a dependência **direta** |
| P-05 | Superada | 18/11/2026 | Python 3.14 (coberto pela ARQ-08) |
| P-06 | Aprovada | 18/11/2026 | Ver D-03 |
| P-07 | Assumida | 18/11/2026 | "Onda 1 = 6 fichas" conta só as fichas novas; as preexistentes `passing` não contam |
| P-08 | Assumida | 18/11/2026 | HX-10 mantém o ID; novas fichas de CI usam `CI-nn` |
| P-10 | Assumida | 18/11/2026 | Planilha do plano de contas: cabeçalho `código` e `nome` na linha 1 (suposição, a confirmar com os pilotos) |
| P-11 | Assumida | 18/11/2026 | Nova carga do plano substitui o anterior; se a transitória não estiver no plano novo, o cliente fica sem transitória |
| P-12 | Assumida em parte | 18/11/2026 | Criada a HAR-04 (alinhamento do validador e do `check-clean`); o banco de teste no ambiente de verificação entra na NUC-01 |
| P-09 | **Pendente** | — | O chefe edita o cadastro de um cliente e gera link mesmo sem estar atribuído? |
| P-13 | **Pendente** | — | Status HTTP da recusa por dado inválido: 400 ou 422? As fichas usam `[definir P-13]` |

## Pendências em aberto, sem ID

Pontos que as fontes deixam abertos e que ainda não têm número. Ganham ID no `DECISIONS.md` quando o grupo registrar.

| Pendência | Status | Dono, quando a fonte diz | Fonte |
|---|---|---|---|
| Modelo da tarefa e do juiz (API ou local) | Em aberto, sem ID | Responsável pelo harness de avaliação | Avaliação com LLM; Arquitetura do Sistema |
| Provedor de LLM | Em aberto, sem ID | — | AGENTS.md, seção 1 |
| Valores dos limiares de métrica nas features | Em aberto, sem ID | Quem abre a feature | Avaliação com LLM |
| Orçamento mensal de API e frequência do juiz | Em aberto, sem ID | Responsável pelo harness | Avaliação com LLM |
| Onde guardar os rótulos reais da contadora (ex.: pasta privada do grupo) | Em aberto, sem ID | Responsável pelo harness de avaliação | Avaliação com LLM |
| Provedor do piloto (hospedagem): Supabase ou Fly Managed Postgres, ambos em São Paulo; decidir pelo backup verificável e pelo orçamento | Em aberto, sem ID | — | Arquitetura do Sistema; AGENTS.md |
| Quais são as quatro funcionalidades essenciais que nunca saem no gatilho de corte | Em aberto, sem ID | — | Fluxo de desenvolvimento |
| Horários dos rituais: planejamento na segunda (45 min), fechamento no domingo (30 min), sexta sem reunião | Em aberto, sem ID | Time | Fluxo de desenvolvimento |
| Feriado de 20/11: o time trabalha ou não? Isso muda a meta da S2 | Em aberto, sem ID | Time | Fluxo de desenvolvimento |
| Dados para teste: quem pede ao escritório um ou dois extratos anonimizados, só para estudar a estrutura, fora do repositório | Em aberto, sem ID | Time | Fluxo de desenvolvimento |

Saíram desta lista, porque foram resolvidos:

- os seis itens da rubrica de PR, que estão no `docs/rubrica-revisao.md`;
- React ou Vue: React, pela ARQ-02;
- a regra do repositório público, que está no `AGENTS.md`, regra 1, e no `docs/SECURITY.md`;
- quem assume cada frente, definido pela líder em 18/11 (ver [Equipe](/lastro-lancamentos/home/equipe/)).

Fontes: `docs/decisoes/DECISIONS.md` (18/11/2026); Requisitos funcionais v0.2; Lastro — Arquitetura do Sistema; Banco de dados para o Lastro v1.0; Estudo de Avaliação com LLM; Estudo de UX/UI; Fluxo de desenvolvimento do Lastro.
