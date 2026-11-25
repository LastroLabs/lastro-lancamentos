# Tasks — DB-03 · Criar as tabelas de competência e de link do cliente

**Plan:** planos/DB-03/plan.md · **Ficha:** features/DB-03.json
**Ordem:** T1 → revisão humana dos testes → commit só de testes (anotar o hash) → T2 em diante (sessão nova, sem editar `tests/`)

---

## [ ] T1 · Escrever os testes dos critérios
- **Critérios da ficha:** c1, c2, c3, c4
- **Regra de negócio (em linguagem simples):** a competência é o "mês de trabalho" de um cliente: só pode existir uma por cliente e mês, e o mês é guardado sempre como dia 1. O link do cliente é a chave que o contador manda por mensagem: o banco guarda só a impressão digital (hash) do código, nunca o código, e o link pertence a um cliente, a uma competência desse cliente e a um membro do mesmo escritório.
- **Critérios de aceite:**
  - [ ] `tests/access/test_period_link_schema.py` tem exatamente os quatro testes da ficha: `test_migracao_db03_cria_competencia_unica_por_cliente_e_mes`, `test_migracao_db03_cria_link_que_guarda_so_o_hash`, `test_db03_link_nao_cruza_cliente_nem_escritorio`, `test_db03_migracao_reversivel`
  - [ ] Fixture própria do arquivo aplica `alembic upgrade head` sobre `fresh_database`; `tests/access/conftest.py` não é alterado
  - [ ] c1: catálogo confere colunas, tipos, nulabilidade e defaults de `competencia`, a PK `(escritorio_id, cliente_id, id)`, o UNIQUE `(escritorio_id, cliente_id, mes)`, a FK para `cliente` e os CHECKs; casos (a)–(d) da ficha
  - [ ] c1 (D3): o caso (d) é recusado também com a sessão em `SET TIME ZONE 'America/Sao_Paulo'` e em `'UTC'`
  - [ ] c2: catálogo confere as colunas de `link_cliente`, o UNIQUE e o CHECK de `hash_token`, os dois CHECKs de data; nenhuma coluna além de `hash_token` contém `token` ou `codigo`; existe índice cuja primeira coluna é `hash_token`
  - [ ] c3: os quatro casos são recusados, cada um em transação própria (`_reject`), e a contagem de `link_cliente` não muda; FKs conferidas com colunas, alvo, `NO ACTION` e `NOT DEFERRABLE`
  - [ ] c4: com dados em `escritorio`, `cliente`, `competencia` e nas tabelas da DB-02, `downgrade 0003` remove só as duas tabelas, mantém a versão `0003` e os mesmos dados em `escritorio`, `usuario`, `membro`, `cliente` (inclusive as colunas novas da DB-02), `plano_contas`, `conta_contabil`, `conta_bancaria` e `socio` (P3); `upgrade head` recria tudo igual a c1/c2
  - [ ] Nomes de restrição conferidos pelo catálogo (D4), inclusive `fk_link_cliente_competencia`
  - [ ] Todos falham hoje pelo motivo certo (tabela ausente), não por erro de fixture
  - [ ] Só dados inventados, conforme DB-03/B1: nomes `*_TESTE_DB03`, CNPJ com DV inválido, hashes `"a"*64`, UUIDs do banco, nenhum arquivo em `fixtures/`
- **Exemplos:** ESC_TESTE_DB03_1 com CLIENTE_TESTE_DB03_1 e CLIENTE_TESTE_DB03_2 (CNPJ `11122233000100`, DV inválido); competência de CLIENTE_1 em `2026-10-01` → aceita; outra igual → `UniqueViolation`; `2026-10-15` → `CheckViolation`; link com `hash_token = "a"*64`, `expira_em = criado_em + 7 dias` → aceito; `hash_token = "abc"` → `CheckViolation`
- **Arquivos:** `tests/access/test_period_link_schema.py`
- **Reaproveitar:** `fresh_database`, `connect`, `APP_ROLE`, `OWNER_ROLE`, `process_output` de `tests/access/conftest.py`; padrão `_insert`/`_reject`/`_run_alembic` de `tests/registry/test_registry_schema.py` · **Não criar:** conftest novo, arquivo em `fixtures/`, cópia da infraestrutura do core
- **Fora do escopo:** código de produção, RLS, regras da ACE-05
- **Pronto quando:** `docker compose run --rm dev pytest tests/access/test_period_link_schema.py -q` mostra 4 falhas esperadas

## [ ] T2 · Migração `0004`: upgrade
- **Critérios da ficha:** c1, c2, c3
- **Regra de negócio (em linguagem simples):** o banco é quem recusa competência duplicada, mês fora do dia 1, link que aponta para o mês de outro cliente, link criado por gente de outro escritório e link que vence no mesmo instante em que nasce. Assim nenhum bug da aplicação consegue gravar isso.
- **Critérios de aceite:**
  - [ ] `migrations/versions/0004_create_period_link_tables.py` com `revision = "0004"`, `down_revision = "0003"`, sem importar modelos
  - [ ] `competencia` e `link_cliente` com as colunas exatas da ficha; `id` com `gen_random_uuid()`; `criada_em`/`criado_em` com `now()`; `expira_em` sem default
  - [ ] CHECK do mês com conversão explícita (D3); CHECKs de `versao_conjunto >= 0`, hash, validade e revogação
  - [ ] FKs compostas `NO ACTION`/`NOT DEFERRABLE`, sem FK direta de link para cliente (D6)
  - [ ] Índices auxiliares da D5; nenhum índice extra em `hash_token`
  - [ ] Nomes conforme D4, todos com até 63 caracteres
  - [ ] Sem `GRANT` (os privilégios padrão da `0001` cobrem o papel da aplicação)
- **Exemplos:** link de CLIENTE_1 com `competencia_id` de CLIENTE_2 → `ForeignKeyViolation`; `revogado_em` antes de `criado_em` → `CheckViolation`; `revogado_em` nulo → aceito
- **Arquivos:** `migrations/versions/0004_create_period_link_tables.py`
- **Reaproveitar:** auxiliares `_uuid`, `_id`, `_fk`, `_pk` como padrão de `0003` (copiar o padrão; não importar a revisão antiga) · **Não criar:** trigger, cascata, função SQL
- **Fora do escopo:** RLS, prazo padrão do link, status da competência
- **Decisões relacionadas:** D2, D3, D4, D5, D6
- **Pronto quando:** `pytest tests/access/test_period_link_schema.py::test_migracao_db03_cria_competencia_unica_por_cliente_e_mes tests/access/test_period_link_schema.py::test_migracao_db03_cria_link_que_guarda_so_o_hash tests/access/test_period_link_schema.py::test_db03_link_nao_cruza_cliente_nem_escritorio -q` passa

## [ ] T3 · Modelos `Period` e `ClientLink`
- **Critérios da ficha:** c1 (o modelo fica em `src/lastro/access/models.py`)
- **Regra de negócio (em linguagem simples):** o código Python descreve as mesmas tabelas que a migração criou, para que as próximas features (ACE-05, envio) leiam e gravem sem SQL solto. Quem cria a tabela é só a migração.
- **Critérios de aceite:**
  - [ ] `Period` (`__tablename__ = "competencia"`) e `ClientLink` (`"link_cliente"`) na mesma `Base` de `lastro.core.models`
  - [ ] Colunas, chaves, CHECKs e índices iguais aos da `0004`, com os mesmos nomes (D4: `fk_link_cliente_competencia` explícito)
  - [ ] Importar o módulo não abre conexão; `access/models.py` não importa `registry/models.py` (FK para `cliente` por string)
  - [ ] Docstrings curtas em inglês, como as classes existentes
- **Exemplos:** `Period.__table__.c.mes` é `Date` não nulo; `ClientLink.__table__.c.revogado_em` é nulável
- **Arquivos:** `src/lastro/access/models.py`
- **Reaproveitar:** `Base`, `ForeignKeyConstraint`, `CheckConstraint`, `Index` como nas classes da DB-01 · **Não criar:** nova Base, `create_all()`, repositório ou serviço
- **Fora do escopo:** consultas, geração de código, cálculo de `expira_em`
- **Decisões relacionadas:** D1, D4
- **Pronto quando:** `pytest tests/access -q` passa e `ruff check src/lastro/access/models.py` limpo

## [ ] T4 · Migração `0004`: downgrade reversível
- **Critérios da ficha:** c4
- **Regra de negócio (em linguagem simples):** se for preciso voltar a versão do banco, saem só as duas tabelas novas. Escritórios, clientes, membros e os planos de contas da DB-02 ficam como estavam.
- **Critérios de aceite:**
  - [ ] `downgrade()` remove `link_cliente` e depois `competencia`, sem `CASCADE` e sem mexer em privilégios
  - [ ] Depois do downgrade, `alembic_version` é `0003`; depois do upgrade, `head` volta a `0004`
  - [ ] O c4 da DB-02 (que desce até `0002` a partir de `head`) continua verde
- **Exemplos:** banco com ESC_TESTE_DB03_1, CLIENTE_TESTE_DB03_1 e competência `2026-10-01` → downgrade → `to_regclass('public.competencia')` é nulo e o cliente continua lá
- **Arquivos:** `migrations/versions/0004_create_period_link_tables.py`
- **Reaproveitar:** forma do `downgrade()` da `0003` · **Não criar:** backup ou cópia de dados no downgrade
- **Fora do escopo:** migração de dados
- **Pronto quando:** `pytest tests/access/test_period_link_schema.py::test_db03_migracao_reversivel tests/registry/test_registry_schema.py tests/core/test_migracoes.py -q` passa

## [ ] T5 · Registrar regras do módulo e avisar a NUC-03
- **Critérios da ficha:** apoio a c2 e c4 (sem critério novo)
- **Regra de negócio (em linguagem simples):** quem for escrever a ACE-05 e a NUC-03 precisa saber o que o banco já garante e o que ainda não garante (responsável ativo, prazo, RLS, busca pelo hash sem escritório).
- **Critérios de aceite:**
  - [ ] `docs/modulos/access.md` ganha seção curta "Tabelas da DB-03": o que o banco garante, o que fica para a ACE-05 (P-09, prazo D-06) e para a NUC-03 (RLS e busca por hash)
  - [ ] Respostas das perguntas 1 e 2 registradas em `docs/decisoes/DECISIONS.md` (feito pelo humano ou com a autorização dele)
  - [ ] `progress/DB-03.md` atualizado com o aviso à NUC-03
- **Arquivos:** `docs/modulos/access.md`, `progress/DB-03.md`
- **Não criar:** `docs/modules/access.md` (a pasta usada pelo módulo é `docs/modulos/`)
- **Fora do escopo:** mudar a ficha da NUC-03 ou da ACE-05; abrir issue `contrato:` (o esquema não é contrato publicado entre módulos)
- **Pronto quando:** `hx check-clean` em OK

## [ ] T6 · Verificação final
- **Critérios de aceite:**
  - [ ] `git diff <hash-dos-testes> -- tests/` vazio
  - [ ] `ruff check .` limpo
  - [ ] `hx check-clean` e `hx verify` em OK
  - [ ] `hx feature verify DB-03` grava `passing` (árvore limpa, commit feito antes)
- **Pronto quando:** os três comandos do `hx` terminam com código 0
