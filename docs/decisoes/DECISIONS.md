# Lastro — DECISIONS.md

Registro das decisões do projeto. Uma linha por decisão: ID, data, decisão, motivo em uma linha e fichas afetadas.
Quem decide as perguntas de negócio (D-xx) é a líder. Decisão nova entra aqui antes de entrar no código (AGENTS.md, regras 9 e 12).

Legenda de status: **aprovada** (decidida pela líder) · **assumida** (recomendação da revisão aplicada sem mudar o escopo de nenhum RF; a líder pode reverter) · **pendente**.

## 1. Arquitetura e banco de dados

| ID | Data | Status | Decisão | Motivo | Fichas afetadas |
|---|---|---|---|---|---|
| ARQ-01 a ARQ-08 | 2026-11-18 | aprovada | Arquitetura do sistema como em `gitpages/src/content/docs/decisoes/arquitetura.md`: monólito modular em **Python 3.14** + FastAPI, SPA React, sessão no servidor, fila no PostgreSQL, gateway único de IA, API em `/api/v1`. | Estudo de arquitetura aceito; destrava a fundação da S1. | NUC-01, NUC-02, NUC-03, ACE-01..05, IA-02 |
| BD-01 a BD-08 | 2026-11-18 | aprovada | Banco de dados como em `gitpages/src/content/docs/decisoes/banco-de-dados.md`: **PostgreSQL 18**, migrações versionadas, isolamento por escritório e carteira com RLS, centavos em BIGINT, CI com PostgreSQL e fixtures sintéticas. | Estudo de banco aceito; destrava migrações e isolamento. | NUC-01, NUC-03, HAR-03 |
| BD-07 (emenda) | 2026-11-23 | assumida | O banco de teste do `hx verify` e da CI é um PostgreSQL 18 descartável, criado pelo Testcontainers a cada execução (imagem oficial `postgres:18`), e não um serviço fixo do Compose. O serviço `dev` fala com o Docker só pelo `docker-proxy` (`tecnativa/docker-socket-proxy`, fixado por digest), o **único** container que monta o socket do Docker; os dois ficam no perfil `dev`, e o `docker compose up` sobe só `api` e `db`. O proxy roda com `privileged: true` e monta o socket como somente leitura (`:ro`); o `:ro` não limita a API do Docker, quem limita são as permissões do proxy. O proxy libera só o que o Testcontainers usa (`POST`, `CONTAINERS`, `ALLOW_START`, `ALLOW_STOP`, `EXEC`, `IMAGES`, `NETWORKS`, `INFO`). O Ryuk fica desligado: a fixture remove o container. O banco de teste é alcançado por uma porta publicada no host (`host.docker.internal`). | Banco limpo por execução, sem configuração manual e sem montar o socket no `dev`. Riscos aceitos na NUC-01: o `EXEC` vale para qualquer container do host, a porta do banco de teste fica aberta durante a sessão e o proxy roda com `privileged` (sem o isolamento de SELinux/AppArmor do Docker), que o README do proxy exige. | NUC-01, HAR-03 |
| FER-01 | 2026-11-23 | assumida | Dependências Python com **uv**: `pyproject.toml` (grupo `dev` à parte, PEP 735) e `uv.lock` versionado; o build roda `uv sync --locked` e falha se o lock estiver desatualizado. Um só `Dockerfile`, em estágios `dev` e `runtime` (este sem o grupo dev). Sai o `requirements-dev.txt`. Versão do uv fixada na imagem (`0.13.9`, por digest). | Trava também as dependências transitivas e separa dev de produção sem ferramenta extra. Lock mudou → rebuild da imagem. | NUC-01 e todas as fichas com código Python |

Consequência: o AGENTS.md §1 deixa de listar o banco como "em aberto" e passa a dizer Python 3.14. O `Dockerfile` passou para `python:3.14.10-slim-trixie` na NUC-01; o Python 3.14 está coberto pela c1 e pela c6 da ficha. Ainda falta atualizar a regra 12 do AGENTS.md e a §10 do ARCHITECTURE.md, que citam Python 3.12 (PR separado, resposta 6 do plano da NUC-01).

## 2. Perguntas de negócio (D-xx)

Padrões provisórios e configuráveis, tirados de "Encaminhamento proposto pelos estudos" (`gitpages/src/content/docs/decisoes/index.md`). Valem até o piloto mostrar o contrário.

| ID | Data | Status | Decisão | Motivo | Fichas afetadas |
|---|---|---|---|---|---|
| D-02 | 2026-11-18 | aprovada (provisória) | Regra mínima de adquirente prevista, mas **desativada** até a confirmação; leitores extensíveis. | Padrão dos estudos; não muda o escopo agora. | — (nenhuma neste lote) |
| D-03 | 2026-11-18 | aprovada | **Todo** nome de contraparte, pessoa ou empresa, é pseudonimizado antes de ir à IA (`PESSOA_nnn` / `EMPRESA_nnn`). Ligado por padrão e configurável. Fecha a P-06 da revisão. | Protege dado de terceiros sem depender de lista de nomes. | IA-01, IA-02 |
| D-04 | 2026-11-18 | aprovada (provisória) | Terceiro banco parametrizado; nenhum banco novo como entrega confirmada. | Padrão dos estudos. | — |
| D-05 | 2026-11-18 | aprovada (provisória) | Layout do Domínio provisório (`layouts/dominio.yaml` marcado PROVISORIO) até o teste real de importação. | Padrão dos estudos. | — |
| D-06 | 2026-11-18 | aprovada (provisória) | Link do cliente vale **7 dias**; arquivo de no máximo **20 MiB**. Os dois configuráveis. | Padrão dos estudos, medido no piloto. | ACE-05 |
| D-07 | 2026-11-18 | aprovada (provisória) | Carteira individual: cada contador vê só os clientes atribuídos a ele. | Padrão dos estudos. | NUC-02, ACE-03, ACE-04, CAD-04..07, ACE-05 |
| D-09 | 2026-11-18 | aprovada (provisória) | Um responsável ativo por cliente (o modelo aceita vários vínculos); o chefe vê o escritório inteiro. | Padrão dos estudos. | NUC-02, ACE-02, ACE-03, ACE-04 |

D-01 e D-08 continuam pendentes.

## 3. Processo

| ID | Data | Status | Decisão | Motivo | Fichas afetadas |
|---|---|---|---|---|---|
| PROC-01 | 2026-11-18 | aprovada | Branch da verdade = `developer` (base das branches `feat/*`). | Alinha com o `hx feature start`. | todas |
| PROC-02 | 2026-11-18 | aprovada | Identidade = `HX_USUARIO` = handle do GitHub (o mesmo de `responsavel`). | Um só identificador entre ficha, harness e GitHub. | todas |
| PROC-03 | 2026-11-18 | aprovada | Onda = semana, de 1 a 4. | Planejamento até 07/12. | todas |
| PROC-04 | 2026-11-18 | aprovada | `verificacao` lista 100% dos testes da ficha. | A evidência do `hx feature verify` cobre a ficha inteira. | todas |

## 4. Revisão das fichas da onda S1 (P-xx)

| ID | Data | Status | Decisão | Motivo | Fichas afetadas |
|---|---|---|---|---|---|
| P-01 | 2026-11-18 | aprovada | Status HTTP: **401** sem sessão ou com sessão encerrada; **403** com sessão, mas o papel não permite; **404** para recurso de outra carteira, de outro escritório ou inexistente, com corpo idêntico ao de um recurso inexistente, inclusive em rotas que alteram dados. | Impede descobrir se um recurso de outro escritório existe. | ACE-01..05, CAD-03..07 |
| P-02 | 2026-11-18 | aprovada | **Só o chefe cadastra cliente.** Um contador sozinho no escritório é o próprio chefe. | RF-AUT-03 (mais recente) e D-09. | ACE-02, CAD-03 |
| P-02a | 2026-11-18 | aprovada | **Releitura do RF-CAD-01:** "o chefe deve poder cadastrar um cliente com nome e CNPJ"; o critério passa a ser "o cliente aparece no escritório depois de salvo e, atribuído, na carteira do contador". | Consequência da P-02. | CAD-03 |
| P-03 | 2026-11-18 | aprovada | "Fichas encadeadas na mesma onda" conta só a dependência **direta**. CAD-04, CAD-05, CAD-07 e ACE-05 dependem de NUC-02 + ACE-02, e não de ACE-03. | ACE-03 é a tela de listagem; as outras só precisam da regra e da atribuição. | CAD-03..07, ACE-05 |
| P-05 | 2026-11-18 | superada | Python 3.14 (ARQ-08 aprovada). | Decidido acima. | NUC-01 |
| P-06 | 2026-11-18 | aprovada | Ver D-03. | — | IA-01, IA-02 |
| P-07 | 2026-11-18 | assumida | "Onda 1 = 6 fichas" conta só as fichas novas; as preexistentes passing não contam. | A líder já disse o mesmo na rodada 2. | HAR-02, HX-10 |
| P-08 | 2026-11-18 | assumida | HX-10 mantém o ID (preexistente); novas fichas de CI usam `CI-nn`. O validador trata HX-10 como exceção. | Renomear mexe em evidência e branch. | HX-10, HAR-04 |
| P-10 | 2026-11-18 | assumida | Planilha do plano: cabeçalho `código` e `nome` na linha 1. É uma **suposição**, a confirmar com os pilotos. | Destrava CAD-02 sem esperar o modelo dos pilotos. | CAD-02, CAD-05, HAR-03 |
| P-11 | 2026-11-18 | assumida | Uma nova carga do plano **substitui** o plano anterior; se a conta transitória não estiver no plano novo, o cliente fica sem transitória. | Mais simples e auditável; segue o critério do RF-CAD-04 ("a conta precisa existir no plano"). | CAD-05, CAD-06 |
| P-12 | 2026-11-18 | assumida em parte | Criada a HAR-04 (alinhamento do validador e do check-clean). **Não** criada ficha de CI de banco: o banco de teste no ambiente de verificação entra na NUC-01 (c6). | Evita uma ficha nova; BD-07 fica coberta pela NUC-01. | HAR-04, NUC-01 |
| P-09 | 2026-11-22 | aprovada | **Chefe vê a lista; só o responsável acessa.** (1) **Lista:** o chefe vê todos os clientes do escritório, só com `id`, nome, CNPJ e responsável ativo (ou "sem responsável"); o contador vê só a própria carteira. (2) **Acessar** (abrir o cliente, ler o cadastro, alterar, gerar ou invalidar link e, no futuro, revisar e exportar) é **só do responsável ativo**, seja contador ou chefe. (3) O chefe pode **atribuir um cliente a si mesmo**; cliente sem responsável não é acessado por ninguém. (4) Chefe do mesmo escritório que não é o responsável recebe **403** "Atribua este cliente a você para fazer isso.", sem dado do cliente. (5) Ordem ao acessar: 401 sem sessão → 404 inexistente ou de outro escritório → permitido se responsável ativo → 403 se chefe do mesmo escritório → 404 nos demais; 403 e 404 saem antes de validar o corpo. (6) **Gestão de atribuição** (atribuir, consultar o responsável, reatribuir) só exige ser chefe do mesmo escritório, sem ser o responsável. (7) `GET /api/v1/contadores` passa a listar também o chefe, para ele poder se escolher como responsável. Exceção à P-01 só no caso (4). | Os estudos já diziam "o chefe revisa e exporta quando estiver atribuído"; resolve o escritório de uma pessoa só (P-02). | NUC-02, ACE-02, ACE-03, ACE-04, DB-01, CAD-04..07, ACE-05; consome a regra: CAD-03 e as futuras fichas de revisão e exportação |
| P-13 | — | **pendente** | Status HTTP de recusa por dado inválido (ex.: CNPJ inválido, nome vazio, conta fora do plano): 400 ou 422? A P-01 não cobre esse caso. As fichas usam `[definir P-13]`. | Surgiu ao aplicar a P-01. | CAD-03, CAD-04, CAD-06, CAD-07 |

## 5. Revisão documental da DB-01 — 23/11/2026

Decisões explícitas do responsável pela DB-01 nesta data. Não constituem aprovação do plano, nem mudança de critérios, estados ou evidências das fichas.

| Referência | Situação | Decisão e alcance |
|---|---|---|
| DB-01/B1 | Decidida pelo responsável | Manter os nomes físicos definidos na ficha DB-01; exceção ao inglês/plural do CODING_STANDARDS.md. Classes Python não foram nomeadas por essa decisão. |
| DB-01/B2 | Decidida pelo responsável | Políticas RLS na NUC-03; sua conclusão é obrigatória antes de usar dados de piloto. Não criar políticas permissivas de contorno. DB-01 não prova isolamento completo de acesso. |
| DB-01/B3 | Decidida pelo responsável | Enquanto `hx fixtures build` estiver indisponível, permitir dados sintéticos determinísticos nos testes DB-01: nomes fictícios, hashes inventados e CNPJs com DV inválido nos casos sem validação fiscal. |
| DB-01/B4 | Confirmada pelo responsável | Modelagem completada, incluindo CONVITE; F1–F5 confirmados em 23/11/2026, conforme linhas abaixo. |
| DB-01/testes | Decidida pelo responsável | Exigir os seis nomes de teste de `verificacao` da ficha, permitindo testes adicionais. Não alterar critérios sem apresentar proposta. |

Detalhes de DDL confirmados: `gitpages/src/content/docs/modelagem/modelo-fisico.md`, seção “Recorte físico da DB-01”. Escolhas técnicas D1–D3 confirmadas e proposta separada de critérios: `planos/DB-01/plan.md`.

### Confirmações da revisão final — 23/11/2026

| Referência | Decisão confirmada pelo responsável |
|---|---|
| F1 | NOT NULL em membro.usuario_id, sessao.membro_id/criada_em/expira_em e atribuicao.membro_id/atribuido_por. |
| F2 | Sem defaults temporais adicionais; manter somente os explícitos na ficha. |
| F3 | FKs diretas membro.escritorio_id e cliente.escritorio_id → escritorio(id); sem duplicar relações garantidas por FKs compostas. |
| F4 | Todas as FKs com ON DELETE/UPDATE NO ACTION e NOT DEFERRABLE, sem cascata. |
| F5 | Seis índices auxiliares listados no modelo físico e convenção D2; sem unicidade global adicional de id. |
| D1 | UUID v4 no banco com gen_random_uuid(). |
| D2 | Base declarativa comum, classes e convenção de nomes descritas no plano; caminhos confirmados em A1. |
| D3 | Migração explícita independente dos modelos vivos. |
| A1 | Modelos em access/models.py e registry/models.py, base em core/models.py e revisão em migrations/versions/ autorizados. |
| A2 | Ficha única; sessões separadas de testes e implementação. |
| A3 | Revogar convite expirado ainda pendente antes de reemitir; 48 h é apenas exemplo. |
| A4 | Cobertura ampliada; preservar seis testes obrigatórios, permitindo adicionais. |
| A5 | Sincronizar CONVITE nos dados e diagramas interativos, preservando o restante da modelagem. |

Confirmações não aprovam o plano inteiro. Em 23/11/2026, após autorização explícita do responsável, os complementos propostos de c1/c2/c5/c6 foram aplicados à ficha (R1), preservando c3/c4, os seis comandos de teste, estado e evidência. R2 atualizou o verificador para 28 entidades e presença explícita de CONVITE, preservando as demais checagens. As verificações estruturais e de interações passaram; nenhum teste DB-01 ou código de produto foi escrito.

**Aprovação posterior — 23/11/2026:** `guin409` aprovou explicitamente o plano e as tasks da DB-01 com as decisões registradas e autorizou o commit do material revisado. A aprovação consta em `planos/DB-01/plan.md`; esta sessão permanece sem escrita de testes ou implementação. O estado e a evidência da ficha não foram alterados.

### Complemento D2/F5 — nomes dos índices de convite — 23/11/2026

O responsável definiu os nomes abaixo e autorizou registrar este complemento no plano e na documentação, ajustar os testes e reexecutar as verificações para revisão antes do commit:

- Auxiliar: `ix_convite_escritorio_id_membro_id`, não único, em `(escritorio_id, membro_id)`, sem predicado.
- Único parcial: `uq_convite_escritorio_id_membro_id_pendente`, `UNIQUE` em `(escritorio_id, membro_id)` com `WHERE usado_em IS NULL AND revogado_em IS NULL`.

Somente os nomes distinguem os dois índices; suas colunas, unicidade e predicados permanecem como aprovados. A decisão não autoriza implementação, migrações ou commit nesta etapa e não altera critérios, estado ou evidência da ficha.
