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
| P-10 | 2026-11-18 | substituída (§11 T1) | Planilha do plano: cabeçalho `código` e `nome` na linha 1. É uma **suposição**, a confirmar com os pilotos. | Destrava CAD-02 sem esperar o modelo dos pilotos. | CAD-02, CAD-05, HAR-03 |
| P-11 | 2026-11-18 | assumida | Uma nova carga do plano **substitui** o plano anterior; se a conta transitória não estiver no plano novo, o cliente fica sem transitória. | Mais simples e auditável; segue o critério do RF-CAD-04 ("a conta precisa existir no plano"). | CAD-05, CAD-06 |
| P-12 | 2026-11-18 | assumida em parte | Criada a HAR-04 (alinhamento do validador e do check-clean). **Não** criada ficha de CI de banco: o banco de teste no ambiente de verificação entra na NUC-01 (c6). | Evita uma ficha nova; BD-07 fica coberta pela NUC-01. | HAR-04, NUC-01 |
| P-09 | 2026-11-22 | aprovada | **Chefe vê a lista; só o responsável acessa.** (1) **Lista:** o chefe vê todos os clientes do escritório, só com `id`, nome, CNPJ e responsável ativo (ou "sem responsável"); o contador vê só a própria carteira. (2) **Acessar** (abrir o cliente, ler o cadastro, alterar, gerar ou invalidar link e, no futuro, revisar e exportar) é **só do responsável ativo**, seja contador ou chefe. (3) O chefe pode **atribuir um cliente a si mesmo**; cliente sem responsável não é acessado por ninguém. (4) Chefe do mesmo escritório que não é o responsável recebe **403** "Atribua este cliente a você para fazer isso.", sem dado do cliente. (5) Ordem ao acessar: 401 sem sessão → 404 inexistente ou de outro escritório → permitido se responsável ativo → 403 se chefe do mesmo escritório → 404 nos demais; 403 e 404 saem antes de validar o corpo. (6) **Gestão de atribuição** (atribuir, consultar o responsável, reatribuir) só exige ser chefe do mesmo escritório, sem ser o responsável. (7) `GET /api/v1/contadores` passa a listar também o chefe, para ele poder se escolher como responsável. Exceção à P-01 só no caso (4). | Os estudos já diziam "o chefe revisa e exporta quando estiver atribuído"; resolve o escritório de uma pessoa só (P-02). | NUC-02, ACE-02, ACE-03, ACE-04, DB-01, CAD-04..07, ACE-05; consome a regra: CAD-03 e as futuras fichas de revisão e exportação |
| P-13 | 2026-11-25 | aprovada | Recusa por dado inválido (ex.: CNPJ inválido, nome vazio, conta fora do plano) é **422**, em RFC 9457 (`application/problem+json`), com a mensagem que diz o que corrigir. Decidido por caio-nascime no plano da CAD-03 (pergunta 1). Fichas com `[definir P-13]` passam a usar 422. | Surgiu ao aplicar a P-01. 422 separa dado recusado pela regra de pedido malformado. | CAD-03, CAD-04, CAD-06, CAD-07 |

## 5. Revisão documental da DB-01 — 23/11/2026

Decisões explícitas do responsável pela DB-01 nesta data. Não constituem aprovação do plano, nem mudança de critérios, estados ou evidências das fichas.

| Referência | Situação | Decisão e alcance |
|---|---|---|
| DB-01/B1 | Decidida pelo responsável | Manter os nomes físicos definidos na ficha DB-01; exceção ao inglês/plural do CODING_STANDARDS.md. Classes Python não foram nomeadas por essa decisão. |
| DB-01/B2 | Decidida pelo responsável | Políticas RLS na NUC-03; sua conclusão é obrigatória antes de usar dados de piloto. Não criar políticas permissivas de contorno. DB-01 não prova isolamento completo de acesso. |
| DB-01/B3 | Decidida pelo responsável | Enquanto `hx fixtures build` estiver indisponível, permitir dados sintéticos determinísticos nos testes DB-01: nomes fictícios, hashes inventados e CNPJs com DV inválido nos casos sem validação fiscal. **Atualização de 24/11/2026.** A exceção se encerra quando a HAR-03 (PR #58) disponibilizar o comando na `developer`. A partir daí, testes novos que precisarem de cadastro ou extrato completos usam a fixture de sessão `synthetic_fixtures_dir`. Os testes existentes da DB-01 não precisam migrar e mantêm seus dados sintéticos atuais. Proposta de 25/11/2026, a confirmar pelo responsável da DB-01. A exceção da DB-02/B1 (§6) é separada. Ver [Dados de teste](../SECURITY.md#3-dados-de-teste). |
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

## 6. Decisões da DB-02 — 23/11/2026

Raissa aprovou o plano e as tarefas da DB-02 nesta data, incluindo as escolhas D1–D3 e os pontos abaixo:

| Referência | Decisão e alcance |
|---|---|
| DB-02/B1 | Enquanto HAR-03 não gerar fixtures, os testes de esquema da DB-02 podem criar apenas registros sintéticos transitórios no banco descartável, com nomes fictícios e CNPJ de verificador inválido. Nenhum dado real ou fixture persistida. **Atualização de 24/11/2026 (decisão da responsável).** A exceção se encerra quando a HAR-03 (PR #58) disponibilizar `hx fixtures build` na `developer`. A partir daí, testes novos da DB-02 que precisarem de dados de fixture usam o comando. Cada teste existente da DB-02 pode manter os registros sintéticos transitórios até a próxima alteração de seus dados, quando migra para `hx fixtures build`. |
| DB-02/B2 | Preservar os nomes físicos em português e os quatro nomes de teste definidos pela ficha; classes e auxiliares Python seguem a convenção em inglês. |
| DB-02/B3 | A DB-02 entrega as restrições do esquema. As políticas RLS seguem na NUC-03, cuja conclusão é obrigatória antes de dados de piloto. |

## 7. Decisões da ACE-01 — 24/11/2026

Respostas às perguntas 1 e 2 do plano da ACE-01, dadas por caio-nascime (dono da ACE-02) na revisão do PR #57. Valem para o MVP.

| Referência | Decisão e alcance |
|---|---|
| ACE-01/E1 | **Prazo da sessão:** a sessão cai depois de 2 h sem uso e nunca passa de 12 h desde a entrada. Cada pedido aceito renova `sessao.expira_em` (agora + 2 h, limitado a `criada_em` + 12 h); o token não muda. Detalhe em `planos/ACE-01/plan.md`, D9. |
| ACE-01/E2 | **Um escritório por usuário:** entrar exige um único vínculo ativo, em escritório ativo. Quem trabalha em dois escritórios usa um usuário em cada. Se houver dois vínculos, a entrada responde 409 "Este usuário está em mais de um escritório. Peça ao chefe um usuário para cada escritório.", só depois da senha certa (com a senha errada, continua a 401 de sempre). Escolher o escritório na entrada foi descartado: muda a lógica do convite (ACE-02) e não cabe no prazo. Detalhe em `planos/ACE-01/plan.md`, D10. |

## 8. Decisões da DB-03 — 25/11/2026

Respostas de camposs04 (responsável da DB-03) às perguntas 1 e 2 de `planos/DB-03/plan.md`. A responsável aceitou a sugestão de padrão do plano nas duas. camposs04 aprovou o plano e as tarefas da DB-03 nesta data, incluindo as escolhas D1–D6.

| Referência | Decisão e alcance |
|---|---|
| DB-03/B1 | Os testes de esquema da DB-03 podem criar escritório, usuário, membro e cliente transitórios no próprio teste, no banco descartável, nos moldes da DB-02/B1: nomes fictícios `*_TESTE_DB03`, CNPJ com dígito verificador inválido, hashes inventados (`"a"*64`), UUIDs gerados pelo banco e nenhum arquivo em `fixtures/`. Motivo: o `cadastro.json` de `synthetic_fixtures_dir` (HAR-03) não traz CNPJ, que é obrigatório em `cliente`. Nenhum dado real. A exceção vale só para os testes da DB-03. Aval dado por camposs04 em 25/11/2026, como responsável pelo `SECURITY.md`. Ver [Dados de teste](../SECURITY.md#3-dados-de-teste). |
| DB-03/B2 | Estende a exceção de nomes da DB-01 às tabelas da DB-03 no módulo `access`. Os nomes físicos de tabelas e colunas ficam em português, exatamente como na ficha (`competencia`, `link_cliente`, `hash_token`...), assim como os quatro nomes de teste. As classes Python seguem em inglês (`Period` e `ClientLink`, D1 do plano). |

## 9. Anonimização de telefone, e-mail e chave Pix — 26/11/2026

Decisão de camposs04 (líder) sobre a issue #69, aberta na revisão do PR #67 (IA-02, item 3 de "Para o humano decidir"). Amplia o escopo do RF-SEG-03, que hoje cobre só CPF, CNPJ, agência e conta.

| Referência | Decisão e alcance |
|---|---|
| RF-SEG-03/A1 | **Aprovada.** A anonimização passa a cobrir também telefone, e-mail e chave Pix, com os marcadores `[TELEFONE]`, `[EMAIL]` e `[CHAVE_PIX]`, além dos atuais `[CPF]`, `[CNPJ]`, `[AGENCIA]` e `[CONTA]`. Motivo: dado pessoal não pode ir para o LLM nem para logs (regra 1 do AGENTS.md e promessa de LGPD aos pilotos). Exemplos fictícios: `TED TEL (00) 00000-0000` → `TED TEL [TELEFONE]`; `PIX exemplo@exemplo.com` → `PIX [EMAIL]`. |
| RF-SEG-03/A2 | **Pendente.** Uma chave Pix pode ser CPF, CNPJ, e-mail, telefone ou chave aleatória (EVP). A implementação precisa definir a precedência entre `[CHAVE_PIX]` e os marcadores de CPF, CNPJ, e-mail e telefone (por exemplo, se um CNPJ usado como chave Pix vira `[CNPJ]` ou `[CHAVE_PIX]`). Fica em aberto; decidir no plano da implementação. |

Consequência: `src/lastro/ai/anonymization.py` passa a precisar dessas regras, a implementar em PR separado (a #69 segue aberta para isso). Pela regra 9 do AGENTS.md, antes do código o RF-SEG-03 (`gitpages/src/data/fonte/requisitos-v0.2.md` e o JSON gerado), o `docs/SECURITY.md` §5 e a ficha da feature precisam ser atualizados.

## 10. Decisões da NUC-03 — 26/11/2026

Plano em `planos/NUC-03/plan.md`. D1 a D5 confirmadas por jvsauma; P4 revista, P5 e P6 respondidas por caio-nascime na revisão do PR #76, com a concordância de jvsauma. Valem para toda ficha que lê ou grava tabela com escritório.

| Referência | Decisão e alcance |
|---|---|
| NUC-03/R1 | **RLS forçada** em todas as tabelas com escritório (12 hoje). O escritório vai ao banco por `set_config('app.firm_id', …, true)`, reaplicado a cada transação por `use_firm` (`core/db.py`). Sem escritório, a aplicação não vê nem grava nada, sem erro. Tabela nova com `escritorio_id` precisa de `ENABLE` e `FORCE`, da política da aplicação e da política do dono na própria migração. Sem `BYPASSRLS` e sem política aberta para `lastro_app`. Plano D1 a D3. |
| NUC-03/R2 | **Buscas antes de se saber o escritório** só por funções `SECURITY DEFINER` (dona `lastro_owner`, `search_path` fixo, `EXECUTE` só para `lastro_app`, retorno mínimo): `buscar_sessao_por_hash`, `buscar_vinculos_do_usuario`, `buscar_convite_por_hash`, `buscar_usuario_por_login` (`0005`) e `buscar_link_por_hash` (`0006`). Nome e retorno são contrato v0 (regra 11). A aplicação não lê `usuario.credencial_hash` direto. Plano D2, D4 e D6. |
| NUC-03/R3 | **Link do cliente:** `buscar_link_por_hash` filtra o link invalidado e devolve escritório, link, cliente, competência e `expira_em`. O vencido é recusado pelo **app**, com o próprio relógio e a mesma recusa do inexistente (P5 = A), para a ACE-05 poder testar o segundo exato. A RLS isola por escritório, não por cliente: quem abre o link só vê o cliente e a competência que a função devolveu (ACE-05, c8). |
| NUC-03/R4 | **Nunca ler `usuario` inteiro pelo ORM.** Vale para toda ficha que lê `usuario` (nome ou login de uma pessoa, responsável de um cliente, lista de contadores). O app não tem leitura de `credencial_hash` (R2), e o modelo `User` mapeia essa coluna: `db.get(User, …)`, `select(User)` ou um relacionamento que carregue `User` montam um `SELECT` com ela, e o banco recusa a consulta inteira (`permission denied for table usuario`). Ler só as colunas necessárias (`select(User.id, User.identificador_login, User.nome)`, como `access/repository.py` já faz). Gravar a senha continua permitido, com `update(User).where(User.id == …).values(credencial_hash=…)`, sem carregar o objeto e sem `RETURNING` da coluna. Recomendado: marcar a coluna em `access/models.py` com `deferred=True, deferred_raiseload=True`, para o ORM nunca carregá-la sozinho e o erro, se houver, sair no Python apontando o campo. Aprovada por caio-nascime em 26/11/2026, a partir da ACE-02/F2. |

### Pendências para a ACE-05 [definir]

Sem resposta, os testes da ACE-05 teriam de inventar regra (regra 12). Decidir antes do `/planejar` da ACE-05.

| Referência | Pergunta | Sugestão (não é decisão) |
|---|---|---|
| ACE-05/Q1 | **Quem cria a competência?** O link exige `competencia_id`, a DB-03 só cria a tabela e nenhuma ficha grava a linha. Opções: (a) gerar o link cria a competência se ela não existir; (b) outra ficha cria; (c) só semente de teste, o que deixa o fluxo real sem caminho. [definir] | (a): é o único caminho que não pede ficha nova. |
| ACE-05/Q2 | **Onde se configura a validade do link?** A D-06 diz "configurável" e o RF-SEG-01 diz "[definir]"; o c2(2) da ACE-05 pede "validade configurada para 1 dia". Opções: variável de ambiente, configuração por escritório ou parâmetro da rota. [definir] | Variável de ambiente com padrão de 7 dias: é a mais simples, e a D-06 é provisória. |
| ACE-05/N1 | **Nota para o plano (não é pergunta):** `link_cliente.criado_em` tem `now()` do banco como padrão e a `0004` exige `expira_em > criado_em`. Se o app calcular `expira_em` com o próprio relógio, um teste que atrase esse relógio na geração quebra a restrição, e "exatamente 7 dias após a geração" deixa de ser exato. O app deve gravar também `criado_em` e fazer `expira_em = criado_em + validade`, os dois do mesmo relógio. | — |

### Decisões para a ACE-02

Aprovadas por caio-nascime (responsável da ACE-02) em 26/11/2026, para alinhar a ACE-02 à NUC-03. F1: a NUC-03/R2 tirou do app a leitura de `usuario.credencial_hash`, mas a ACE-02 precisa saber quem já criou a senha (situação na lista em c1, c2 e c5; recusa "Este contador já criou a senha." em c5 (5)). O convite não resolve: o chefe da ADM-01 e os contadores da semente têm senha sem nunca ter tido convite.

| Referência | Decisão e alcance |
|---|---|
| ACE-02/F1 | **Função `usuarios_com_senha(uuid[])`**, no padrão da NUC-03/R2 (`SECURITY DEFINER`, dona `lastro_owner`, `search_path` fixo, `EXECUTE` só para `lastro_app`). Recebe ids de usuário e devolve só `usuario_id` e `tem_senha` (booleano), nunca o hash. Responde só por quem é membro do escritório definido na transação (`app.firm_id`); sem escritório, 0 linhas. Criada em migração própria da ACE-02, a seguinte à `0006`. Critério c10 da ACE-02. Nome e retorno são contrato v0 (regra 11), registrado em `ARCHITECTURE.md` (seção 6) e em `docs/modulos/access.md`; sem issue separada, por decisão do responsável em 26/11/2026. Alternativas descartadas: coluna legível nova em `usuario` (muda o modelo da DB-01) e usar `buscar_usuario_por_login` na lista (traz o hash para um código que não precisa dele). |
| ACE-02/F2 | **Aplica a NUC-03/R4** (nunca ler `usuario` inteiro pelo ORM). Na ACE-02, os pontos que leem `usuario` são a lista de contadores (c1), a conferência do login no aceite (c2 e c3 (e)) e a checagem de usuário repetido (c4); todos leem só colunas. A senha do aceite é gravada por `update(User)` direto, sem carregar o usuário (c2). |
| ACE-02/F3 | **O convite vencido é decidido pelo relógio do banco.** `buscar_convite_por_hash` filtra com `expira_em > now()` (`0005`), então o aceite segue o relógio do banco. A situação `convite_vencido` da lista usa a mesma regra (`expira_em <= now()` na consulta), para nunca discordar do aceite. Nos testes, o convite vencido é criado no banco com `expira_em` no passado; adiantar o relógio do app não tem efeito. **Diferença intencional** em relação ao link do cliente, que é decidido pelo relógio do app (NUC-03/R3): cada uma segue o que a sua função já faz; não "uniformizar" sem mudar a função, os testes e as fichas. Critérios c3 (b) e c5 da ACE-02. |
| ACE-02/F4 | **O aceite passa pela função e gasta o convite uma vez só.** O aceite acha o convite por `buscar_convite_por_hash`, nunca por consulta direta a `convite` (com a RLS, ela devolve 0 linhas), e define o escritório da transação com o que a função devolveu (`use_firm`). Como a função só lê, sem travar a linha, dois aceites simultâneos podem passar por ela. Por isso, na mesma transação e nesta ordem: (1) `UPDATE convite SET usado_em = now() WHERE id = … AND usado_em IS NULL AND revogado_em IS NULL AND expira_em > now()`; (2) se mudou 0 linhas, desfazer e responder com a recusa de c3; (3) só então gravar a senha (F2). O segundo aceite espera a trava da linha, reavalia o `WHERE` depois do commit do primeiro e muda 0 linhas. Critérios c2 e c11 da ACE-02. |
| ACE-02/F5 | **Nomes e respostas da API, decididos pelo responsável em 26/11/2026.** Rotas e campos em inglês (`/accountants`, `/accountants/{id}/invitation`, `/invitations/accept`, `/clients/{id}/assignment`; campos `id`, `name`, `username`, `role`, `status`, `invitation_code`, `invitation_path`, `expires_at`). O `id` de uma pessoa é o id do membro. Dado inválido é 422 (P-13). `DELETE` de convite sem convite pendente é 204; 404 só se a pessoa não existe. `GET` da atribuição sem responsável é 200 com `responsible: null`. O `access` não lê `cliente`: a existência do cliente vem de `registry.service.client_exists`, passada pela `api/`. O aceite recusa quem já tem senha. Os contratos novos do `access` e o `client_exists` são versão 0, registrados em `ARCHITECTURE.md` e `docs/modulos/access.md`. |

### Avisos para a ACE-03 e a ACE-04

Para ler ao rodar `/planejar` dessas fichas. Nenhum critério muda; os avisos evitam um erro de permissão que os testes só mostrariam como erro 500.

| Referência | Aviso |
|---|---|
| ACE-03/A1 | **Aplica a NUC-03/R4.** A lista do chefe traz o responsável de cada cliente com id, nome e usuário (c6 e c8). Ler esses campos com `select(User.id, User.nome, User.identificador_login)` junto de `atribuicao` e `membro`, nunca com `select(User)`, `db.get(User, …)` ou relacionamento que carregue o objeto `User`. |
| ACE-04/A1 | **Aplica a NUC-03/R4.** A consulta do responsável depois da troca (c2, c6 e c7) e a lista do chefe com o novo responsável (c7) leem nome e usuário de uma pessoa: só colunas, como na ACE-03/A1. A reatribuição grava em `atribuicao` e não precisa ler `usuario`. |

## 11. Plano de contas em TXT — 26/11/2026

A contadora confirmou que o plano chega do Domínio como **texto de largura fixa** (`.txt`), não como planilha. O leitor `.xlsx` da CAD-02 nunca entrou na `developer`. Esta seção troca o formato, mantém a substituição da P-11 e autoriza, por escrito, a mudança de testes de fichas já `passing` (exceção à regra 3 do `AGENTS.md`). Formato, regra de leitura e contrato: `docs/modulos/registry.md`. Roteiro de cada ficha: `docs/refatoracoes/<ID>.md`. Fluxo simulado de ponta a ponta numa cópia do repositório em 26/11 (NUC-03, CAD-02, HAR-05 e DB-04 em `passing`; `check-clean` sem achados).

| # | Data | Status | Decisão | Por quê | Afeta |
|---|---|---|---|---|---|
| T1 | 2026-11-26 | aprovada | O plano de contas entra só como TXT de 78 colunas: reduzido `[0:7]`, classificação `[7:27]`, nome `[27:67]`, tipo S/A `[67]`. Planilha `.xlsx` deixa de ser aceita; o `openpyxl` sai. **Substitui a P-10.** | É o formato que o programa contábil exporta; a contadora confirmou. Um formato só é menos código e menos teste. | CAD-02, CAD-05, HAR-05 |
| T2 | 2026-11-26 | aprovada | A hierarquia vem do maior prefixo próprio da classificação presente no arquivo, sem depender da máscara nem da ordem das linhas. | Os dois planos de teste têm máscaras diferentes (`1.1.2.3.3` e `1.1.1.2.5`) e a mesma regra serve aos dois. | CAD-02 |
| T3 | 2026-11-26 | aprovada | Erro numa analítica sem contas abaixo dela (reduzido inválido ou `0000000`, nome vazio) é tolerado: a linha fica de fora e aparece com o número. Qualquer outro erro (grupo, tipo, classificação, hierarquia, repetição, linha incompleta ou longa) recusa o arquivo inteiro com **uma** mensagem: a primeira causa e quantas outras há. | Um erro num grupo derruba até 41% do plano em cascata (medido nos planos de teste); aceitar o resto entregaria plano mutilado sem aviso. | CAD-02, CAD-05 |
| T4 | 2026-11-26 | aprovada | Reduzido ou classificação repetidos recusam o arquivo, em qualquer ordem das linhas, citando as duas linhas. | O programa contábil não repete reduzido; repetição indica arquivo corrompido ou misturado. A regra não pode depender da ordem. | CAD-02 |
| T5 | 2026-11-26 | aprovada | Contrato `ChartOfAccountsResult(accounts, errors, warnings, refusal)` em `lastro.registry.contracts`; `read_chart_of_accounts(bytes \| Path)` em `lastro.registry.service`. `refusal` preenchido → 422 (P-13). | A `api/` decide o status sem deduzir pela lista vazia. | CAD-02, CAD-05 |
| T6 | 2026-11-26 | aprovada | `conta_contabil.codigo` continua com esse nome e guarda a classificação em dígitos. Entram `codigo_reduzido text NULL` (único por plano) e `tipo text NOT NULL DEFAULT 'A'` (S ou A), na migração `0008`, seguinte à `0007` da ACE-02 (a NUC-03 ocupa a `0005` e a `0006`). | Renomear `codigo` quebraria testes `passing` da DB-02 e da DB-03 sem ganho. O reduzido é o código da exportação (D-05). | DB-04, CAD-05 |
| T7 | 2026-11-26 | aprovada | A P-11 continua: nova carga **substitui** o plano atual (versão nova; a anterior fica `substituido`). A transitória e as contas de sócio passam à conta do plano novo com a mesma classificação, ou ficam vazias se ela não existir, no mesmo `UPDATE` que troca o plano. Arquivo recusado não muda nada. | O banco exige (FK das contas de configuração com o plano atual). Recarregar o mesmo plano não pode apagar a transitória. | CAD-05, CAD-06 |
| T8 | 2026-11-26 | aprovada | A fixture sintética passa a gerar `planos/<cliente>.txt` no lugar da `.xlsx`, com grupos (S) e analíticas (A); `cadastro.json` troca `plano_planilha` por `plano_txt` e cada conta ganha `classificacao`, `reduzido` e `tipo` (contrato c6 da HAR-03, versão 1). O gerador refaz o reduzido quando a linha vira CPF ou CNPJ válido; o `check-clean` não é afrouxado. | Os testes da CAD-05 precisam do mesmo formato que chega do contador. | HAR-05, HAR-03, CAD-05, IA-02 |
| T9 | 2026-11-26 | aprovada | A IA continua recebendo o plano inteiro (grupos inclusos) até a ficha de IA nova, que filtra `tipo = 'A'` e pseudonimiza os nomes. Hoje nenhum código monta as candidatas a partir do banco. | Não mexer na IA-02 agora; o filtro fica registrado para não se perder. | IA-02, ficha de IA futura |
| T10 | 2026-11-26 | aprovada | A pasta oficial de documentação de módulo é `docs/modulos/`. O conteúdo de `docs/modules/` (`registry.md` da DB-02 e `harness.md`) vai para lá e a pasta sai; as referências em `AGENTS.md`, `ARCHITECTURE.md`, `docs/rubrica-revisao.md` e `gitpages/.../visao-geral.mdx` passam a `docs/modulos/`. | Já é a pasta usada por access, ai, ci, registry e web; duas pastas confundem quem procura. | todas |
| T11 | 2026-11-26 | aprovada | Fichas: **CAD-02** refeita na própria branch (ainda não mergeada); **HAR-05** e **DB-04** novas; **CAD-05** e **CAD-06** editadas antes de iniciar. Roteiro de cada uma em `docs/refatoracoes/<ID>.md`. | Menos PRs: só duas fichas novas, e só onde há código `passing` a mudar. | CAD-02, HAR-05, DB-04, CAD-05, CAD-06 |
| T12 | 2026-11-26 | aprovada por caio-nascime (líder) | **Exceção escrita à regra 3.** Só os testes da tabela abaixo podem mudar, só no commit de testes da ficha indicada e só como descrito. Qualquer outro teste que falhar é sinal de erro na implementação, não autorização. Revisão do PR: dono da ficha original e, em `tools/`, o dono do harness (CODEOWNERS). No template do PR, marcar `git diff <hash> -- tests/` como "mudou" com o link desta linha. | Mudar o formato exige mudar o que os testes antigos fixavam; a lista fechada impede enfraquecer outros testes. | HAR-03, DB-02, DB-03 |
| T13 | 2026-11-27 | aprovada por caio-nascime (líder) | **O registro aqui substitui a issue `contrato:` (regra 11) para o contrato do plano da CAD-02.** Ele passa de v0 (`ChartAccountEntry(code, name)`, `ChartSpreadsheetResult(accounts, errors)`, `read_chart_of_accounts_spreadsheet`) para v1 (`ChartAccountEntry(line_number, reduced_code, classification, name, kind, parent_classification)`, `ChartOfAccountsResult(accounts, errors, warnings, refusal)`, `read_chart_of_accounts(bytes \| Path)`), como em T5 e em `docs/modulos/registry.md`. Arquivo inexistente ou ilegível passado como `Path` levanta `OSError`: "nunca levanta" vale para conteúdo ruim. | O contrato v0 nunca chegou à `developer` e não tem consumidor; a CAD-05, única consumidora futura, já foi escrita para o v1. Uma issue só repetiria esta seção. | CAD-02, CAD-05 |

### T12 — testes autorizados a mudar

| Arquivo | Teste | Ficha dona | Muda na branch de | Mudança permitida |
|---|---|---|---|---|
| `tests/registry/test_planilha_plano.py` | os 5 | CAD-02 | CAD-02 | apagar o arquivo (o leitor `.xlsx` sai; a ficha é reescrita) |
| `tests/harness/test_fixtures.py` | `test_build_gera_planilha_do_plano_por_cliente` | HAR-03 | HAR-05 | apagar e tirar da `verificacao` da HAR-03; o `test_build_gera_plano_txt_por_cliente` da HAR-05 o substitui |
| `tests/harness/test_fixtures.py` | `test_mesma_semente_gera_saida_identica` | HAR-03 | HAR-05 | trocar o bloco das planilhas `.xlsx` por "há planos `.txt`"; o resto fica |
| `tests/harness/test_fixtures.py` | `test_formato_do_cadastro_e_do_gabarito` | HAR-03 | HAR-05 | `plano_planilha` → `plano_txt`; acrescentar as asserções de `classificacao`, `reduzido` e `tipo`; nenhuma asserção sai |
| `tests/harness/test_fixtures.py` | `test_planilha_sem_compressao_e_data_fixa` | HAR-03 | HAR-05 | apagar (só vale para ZIP; não está na `verificacao`) |
| `tests/harness/test_fixtures.py` | auxiliares `ler_planilha` e o ramo `.xlsx` de `textos_gerados`, imports `zipfile` e `ElementTree` | HAR-03 | HAR-05 | apagar (código morto) |
| `features/HAR-03.json` | c1, c6 e `verificacao` | HAR-03 | HAR-05 | c1 e c6: "planilha .xlsx" → "TXT"; `verificacao` perde a linha do teste apagado. `estado` e `evidencia`, só pelo `hx` |
| `tests/registry/test_registry_schema.py` | `test_migracao_db02_cria_tabelas_de_cadastro_com_colunas_e_chaves` (c1) | DB-02 | DB-04 | fixture local que sobe até a `0003` no lugar de `migrated_database`; o corpo não muda |
| `tests/access/test_period_link_schema.py` | `test_db03_migracao_reversivel` (c4) | DB-03 | DB-04 | subir até a `0004` no lugar de `head` (constante `DB03_REVISION`); o corpo não muda |

Não mudam e servem de termômetro (o `pytest` completo tem de passar sem tocá-los): os outros testes da DB-02, DB-03, DB-01, CAD-03, IA-02 (`tests/ai/test_gateway_vazamento.py`, que passa a ver os grupos sem quebrar), NUC-03 (`tests/core/test_isolamento_banco.py`), `tests/conftest.py`, `tests/harness/test_session_fixture.py` e `test_build_aborta_se_linha_tiver_documento_valido` (este obriga o gerador a ter limite de tentativas).
