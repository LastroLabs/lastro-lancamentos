# Plan — DB-03 · Criar as tabelas de competência e de link do cliente

**Status:** aprovado
**Branch:** feat/DB-03-criar-as-tabelas-de-competencia-e-de-lin · **Data:** 25/11/2026 · **Responsável:** camposs04
**Tasks:** planos/DB-03/tasks.md

## 1. A decidir (humano)

| # | Pergunta | Gravidade | Sugestão de padrão | Decide | Situação |
|---|---|---|---|---|---|
| 1 | Os testes precisam gravar escritório, usuário, membro e cliente no banco descartável. As exceções de dado sintético escrito no teste valem só para DB-01 (B3) e DB-02 (B1), e a HAR-03 já está `passing`. O `cadastro.json` de `synthetic_fixtures_dir` não traz CNPJ, que é obrigatório em `cliente`. A DB-03 pode criar esses registros transitórios no próprio teste? | BLOQUEANTE | Sim, nos moldes da DB-02/B1: nomes `*_TESTE_DB03`, CNPJ com DV inválido, hashes `"a"*64`, UUIDs do banco, sem arquivo de fixture. Registrar como DB-03/B1 em `DECISIONS.md` e em `SECURITY.md` §3 antes da T1. | camposs04 (com o dono do `SECURITY.md`) | ✅ respondida — ver §5 |
| 2 | A ficha fixa tabelas e colunas em português (`competencia`, `link_cliente`, `hash_token`...). `CODING_STANDARDS.md` §3 diz que a exceção da DB-01 "não se estende a outros módulos" e não cita a DB-03. | ATENÇÃO | Manter os nomes da ficha (a ficha vale mais que o doc). Classes Python em inglês (D1). Registrar a extensão como DB-03/B2 em `DECISIONS.md`. | camposs04 | ✅ respondida — ver §5 |
| 3 | O c4 diz "tabelas da DB-01 (e da DB-02, se já existir)". A DB-02 está `passing` e a `0003` existe. | ATENÇÃO | O teste confere os dados das tabelas da DB-01 **e** da DB-02 depois do downgrade. Ver mudança sugerida abaixo. | camposs04 | ✅ respondida — ver §5 |
| 4 | O link é buscado pelo hash "sem saber o escritório" (c2). Quando a NUC-03 ligar RLS, essa busca não terá escritório no contexto. | ATENÇÃO | Fora desta ficha. Anotar no `progress/DB-03.md` e avisar o dono da NUC-03 e da ACE-05 (função de busca ou papel específico). | dono da NUC-03 | ✅ respondida — ver §5 |

Mudanças sugeridas na ficha (o humano aplica em PR):
- c4: trocar "(e da DB-02, se já existir)" por "e da DB-02 (plano_contas, conta_contabil, conta_bancaria, socio e as colunas novas de cliente)".
- c1 e c2: citar o arquivo da migração (`migrations/versions/0004_create_period_link_tables.py`, `down_revision = "0003"`).

## 2. Decisões tomadas pelo agente

### D1 · Nomes das classes: `Period` e `ClientLink` em `src/lastro/access/models.py`
- **Alternativas:** A) `Period`/`ClientLink` · B) `Competence`/`ClientLink` · C) `AccountingPeriod`/`UploadLink`
- **Escolhida:** A. **Motivo:** o arquivo de teste da ficha se chama `test_period_link_schema.py`; o glossário (`CODING_STANDARDS.md` §7) não tem os termos. Sugere-se incluí-los lá depois.
- **Fontes:** `features/DB-03.json` (verificacao) · `CODING_STANDARDS.md` §7.
- **Impacto:** T3. Tabelas e colunas ficam com os nomes físicos da ficha.
- [x] confirmar

### D2 · Uma revisão nova `0004`, filha de `0003`, escrita à mão
- **Alternativas:** A) operações Alembic explícitas, `target_metadata = None` (padrão da DB-01/D3 e da DB-02) · B) autogenerate
- **Escolhida:** A. **Motivo:** segue `migrations/env.py` atual; sem importar modelos vivos na revisão. Não editar `0002` nem `0003`.
- **Fontes:** `migrations/env.py:23` · `migrations/versions/0003_create_registry_tables.py`.
- **Impacto:** c1, c2, c4; T2 e T4.
- [x] confirmar

### D3 · CHECK do primeiro dia com conversão explícita para `timestamp`
- **Alternativas:** A) `mes = date_trunc('month', mes::timestamp)` · B) `mes = date_trunc('month', mes)` literal da ficha · C) `extract(day from mes) = 1`
- **Escolhida:** A. **Motivo:** a documentação diz que `date` é convertido para `timestamp`, mas `date_trunc` também tem a variante `timestamptz`, que depende do `TimeZone` da sessão; e o PostgreSQL assume que um CHECK dá sempre o mesmo resultado. A conversão explícita elimina a dúvida sobre qual variante é escolhida, sem mudar a regra da ficha. O teste prova o comportamento (caso d), não o texto do CHECK.
- **Fontes:** [Date/Time Functions, §9.9.2](https://www.postgresql.org/docs/18/functions-datetime.html) e [Check Constraints, §5.5.1](https://www.postgresql.org/docs/18/ddl-constraints.html) (acesso em 25/11/2026).
- **Impacto:** c1; T1 (caso d também com a sessão em outro fuso) e T2.
- [x] confirmar

### D4 · Nomes de restrição: convenção D2 da DB-01, com um nome curto onde passa de 63
- **Alternativas:** A) D2 completo; nome explícito curto só quando passa de 63 caracteres · B) nomes curtos em tudo, como a DB-02 (`fk_<tabela>_cliente`) · C) deixar o SQLAlchemy truncar com hash
- **Escolhida:** A. A FK do link para competência teria 67 caracteres (`fk_link_cliente_escritorio_id_cliente_id_competencia_id_competencia`) e vira `fk_link_cliente_competencia`. Os demais cabem: `uq_competencia_escritorio_id_cliente_id_mes` (43), `fk_link_cliente_escritorio_id_criado_por_membro` (47), `uq_link_cliente_hash_token` (26).
- **Motivo:** a DB-03 é do módulo `access`, que usa D2; o PostgreSQL corta nomes acima de 63 em silêncio (NAMEDATALEN).
- **Fontes:** `planos/DB-01/plan.md` D2 · `src/lastro/core/models.py` · [Identifiers, §4.1.1](https://www.postgresql.org/docs/18/sql-syntax-lexical.html) (acesso em 25/11/2026).
- **Impacto:** T2 e T3 (modelo e migração com o mesmo nome).
- [x] confirmar

### D5 · Índices: o UNIQUE do hash já serve à busca; um auxiliar por FK não coberta
- **Escolhida:** sem índice extra para `hash_token` (o UNIQUE cria um índice global, que atende "buscar sem saber o escritório"). Auxiliares não únicos, como na DB-01/F5: `ix_link_cliente_escritorio_id_cliente_id_competencia_id` (55) e `ix_link_cliente_escritorio_id_criado_por` (40). A FK de `competencia` para `cliente` já é prefixo da PK.
- **Alternativas:** A) só o UNIQUE + auxiliares · B) índice adicional em `hash_token` · C) sem auxiliares.
- **Motivo:** índice duplicado não ajuda; FK sem índice pesa no `DELETE` do pai.
- **Fontes:** [Unique Indexes, §11.6](https://www.postgresql.org/docs/18/indexes-unique.html) (acesso em 25/11/2026) · `gitpages/src/content/docs/modelagem/modelo-fisico.md` F5.
- **Impacto:** c2; T1 confere o índice pelo catálogo.
- [x] confirmar

### D6 · Sem FK direta de `link_cliente` para `cliente`, sem duração fixa e sem default em `expira_em`
- **Motivo:** a FK composta para `competencia` já garante o cliente; a DB-01/c2 proíbe FK redundante. O prazo de 7 dias é exemplo (modelagem: "padrão atual, configurável"); a ACE-05 calcula. Todas as FKs `NO ACTION`/`NOT DEFERRABLE`, sem cascata.
- **Fontes:** `features/DB-01.json` c2 · `modelagem/entidades.md` (LINK_CLIENTE) · `features/ACE-05.json` c2.
- **Impacto:** c2, c3; T2.
- [x] confirmar

## 3. Resumo e abordagem

Criar `competencia` (uma por cliente e mês) e `link_cliente` (só o hash do código, com validade e revogação) com integridade no banco. Sem rota, serviço, geração de código nem RLS.
Ordem: T1 escreve os quatro testes da ficha em `tests/access/test_period_link_schema.py`, com fixture própria que aplica `head` (a `migrated_database` de `tests/access/conftest.py` fica presa em `0002` e não deve mudar). Revisão humana e commit só de testes. Em sessão nova: T2 escreve a `0004` com upgrade; T3 os modelos; T4 o downgrade; T5 o registro em `docs/modulos/access.md` e o aviso à NUC-03; T6 a verificação final.

## 4. Contexto encontrado

- **Planos lidos:** `planos/DB-01/plan.md` (**aprovado**, dependência). `planos/DB-02/plan.md` (arquivo diz "pronto para revisão", mas `DECISIONS.md` §6 registra a aprovação em 23/11; lido fora de `depende_de` porque a DB-03 encadeia na `0003` e reusa o mesmo padrão de teste). Plano da ACE-05 não existe.
- **Conferência DB-01 (herdadas):** D1 UUID v4 `gen_random_uuid()` — **confere** (`0002`, `access/models.py`). D2 Base e convenção em `core/models.py` — **confere**. D3 migração explícita, `target_metadata = None` — **confere** (`migrations/env.py:23`). B2 RLS na NUC-03 — **confere** (`SECURITY.md` §8; NUC-03 `not_started`).
- **Conferência DB-02 (intenção, não herdada):** D1 `0003` filha de `0002` — **confere**. Nomes de FK: o código usa `fk_<tabela>_cliente`, **divergente** da D2 da DB-01 (ATENÇÃO; motivou a D4). Sugestão: registrar a variação em `modelo-fisico.md`.
- **Dependências:** DB-01 `passing` (evidência de 23/11, commit `71fb62f57bfd`, não reexecutada). DB-02 `passing`. HAR-03 `passing`. NUC-03 `not_started`.
- **Reaproveitar:** `tests/access/conftest.py` (`fresh_database`, `connect`, `APP_ROLE`, `OWNER_ROLE`, `process_output`); padrão `_insert`/`_reject`/`_run_alembic` de `tests/registry/test_registry_schema.py`; checagem "sem coluna token/codigo" de `tests/access/test_identity_schema.py:507`; `Base` de `lastro.core.models`.
- **Não criar:** nova Base, nova convenção, conftest duplicado do core, fixture em `fixtures/`, serviço de link (ACE-05), tabela de arquivo ou resposta.
- **Testes existentes que tocam o esquema:** `test_migracoes.py` (snapshot), `test_office_admin.py` e `test_login.py` (`upgrade head`), `test_registry_schema.py` c4 (`downgrade 0002` a partir de `head`). Todos precisam seguir verdes com a `0004`, sem edição.
- **Docs:** `docs/modulos/access.md` existe; `docs/modules/` só tem `registry.md` (duas pastas para a mesma coisa; fora desta ficha).
- **Arquitetura:** `ARCHITECTURE.md` põe "link do cliente" em `access/` e "status por cliente e mês" em `uploads/`. A ficha põe a tabela `competencia` em `access`; status continua calculado fora (modelagem). Sem conflito no esquema.
- **Pesquisa externa:** só a documentação do PostgreSQL 18 citada em D3–D5. Sem biblioteca nova.

## 5. Decisões (já resolvidas)

- 25/11 · P1: sim; os testes da DB-03 criam escritório, usuário, membro e cliente transitórios no próprio teste, nos moldes da DB-02/B1 (por camposs04). Registrada como DB-03/B1 em `docs/decisoes/DECISIONS.md` §8 e como frase-link em `docs/SECURITY.md` §3. Aval dado por camposs04 em 25/11/2026, como responsável pelo `SECURITY.md`.
- 25/11 · P2: manter os nomes físicos em português da ficha e as classes Python em inglês (por camposs04). Registrada como DB-03/B2 em `docs/decisoes/DECISIONS.md` §8.
- 25/11 · P3: depois do downgrade, o teste do c4 confere os dados das tabelas da DB-01 e da DB-02 (`plano_contas`, `conta_contabil`, `conta_bancaria`, `socio` e as colunas novas de `cliente`) (por camposs04). Registrada neste plano e na T1.
- 25/11 · P4: fora desta ficha (por camposs04). Fica como pendência em `progress/DB-03.md` para os donos da NUC-03 e da ACE-05; a decisão é deles.

## 6. Avaliação da ficha

| # | Achado | Gravidade | Critério |
|---|---|---|---|
| A1 | Dados transitórios nos testes: resolvido por DB-03/B1 | BLOQUEANTE (resolvido) | c1–c4 (pergunta 1) |
| A2 | Nomes físicos em português: resolvido por DB-03/B2 | ATENÇÃO (resolvido) | c1, c2 (pergunta 2) |
| A3 | "DB-02, se já existir" ficou vago: ela existe | ATENÇÃO | c4 (pergunta 3) |
| A4 | O CHECK literal da ficha depende da variante de `date_trunc` escolhida | ATENÇÃO | c1 (D3) |
| A5 | O nome D2 da FK do link para competência passa de 63 caracteres | ATENÇÃO | c3 (D4) |
| A6 | O esquema não garante que `criado_por` é o responsável ativo (P-09); fica para a ACE-05 | ATENÇÃO | c3 |
| A7 | `migrated_database` do `tests/access` fica presa em `0002`; os testes da DB-03 precisam de fixture própria em `head` | ATENÇÃO | c1–c4 |
| A8 | 4 critérios, 1 módulo, 2 tabelas: tamanho adequado | — | — |

## 7. Riscos

- Downgrade da `0004` quebrar o c4 da DB-02 (que desce até `0002`) → T4 roda o teste da DB-02 junto.
- Nome de restrição truncado em silêncio → D4 e T1 comparam os nomes pelo catálogo.
- Hash em claro ou código salvo por engano → T1 confere que só existe `hash_token` e que o CHECK recusa texto fora de 64 hexadecimais.
- Tabelas sem RLS → NUC-03 obrigatória antes de dado de piloto; não criar política permissiva.
- Dado real em teste → só valores inventados; `hx check-clean` antes do PR.

## 8. Aprovação

- [x] Pergunta 1 (BLOQUEANTE) respondida e registrada
- [x] Perguntas 2–4 respondidas
- [x] D1–D6 confirmadas
- [x] Plan e tasks revisados por camposs04 em 25/11
