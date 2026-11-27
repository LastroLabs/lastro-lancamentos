# Tasks — DB-04 · Acrescentar à conta contábil o código reduzido e o tipo (sintética ou analítica)

**Plan:** planos/DB-04/plan.md · **Ficha:** features/DB-04.json · **Roteiro:** docs/refatoracoes/DB-04.md
**Ordem:** T1 + T2 → revisão humana dos testes → T3 (commit só de testes, anotar o hash) → T4 em diante (sessão nova, sem editar `tests/`)

---

## [ ] T1 · Escrever os 4 testes da DB-04
- **Critérios da ficha:** c1, c2, c3, c4
- **Regra de negócio (em linguagem simples):** o programa contábil dá a cada conta um **código reduzido** de 7 dígitos, que é o código usado na exportação, e diz se a conta é **grupo** (`S`, sintética, só soma as de baixo) ou **analítica** (`A`, recebe lançamento). O banco precisa guardar os dois. Dentro de um mesmo plano, dois reduzidos iguais indicam arquivo errado, então o banco recusa. Em outro plano (nova versão) ou em outro cliente, o mesmo número é normal. Conta antiga, sem a informação, vira analítica.
- **Critérios de aceite:**
  - [ ] Arquivo novo `tests/registry/test_conta_contabil_db04.py` com exatamente os 4 nomes da `verificacao`: `test_migracao_db04_acrescenta_reduzido_e_tipo`, `test_db04_reduzido_unico_por_plano`, `test_db04_tipo_so_aceita_s_ou_a`, `test_db04_migracao_reversivel`
  - [ ] Constante `DB04_REVISION = "0008"`; os testes sobem até ela, não até `head` (D1)
  - [ ] c1: dicionário completo de colunas de `conta_contabil` = as 8 da DB-02 + `codigo_reduzido` (`text`, nulo, sem padrão) + `tipo` (`text`, não nulo, `'A'::text`) (D2). Check `ck_conta_contabil_tipo` com `S` e `A`; unicidade `(escritorio_id, cliente_id, plano_id, codigo_reduzido)`; `LedgerAccount` tem `codigo_reduzido` e `tipo`
  - [ ] c2: segunda `0000123` em P1 → `UniqueViolation`; a de P2 (mesmo cliente), a de P3 (outro cliente) e duas sem reduzido em P1 → aceitas
  - [ ] c3: `'S'` e `'A'` aceitos; `'X'` → `CheckViolation`; `NULL` explícito → `NotNullViolation`; INSERT sem a coluna → `tipo = 'A'`
  - [ ] c4: `upgrade 0008`, 2 contas (uma `S` e uma `A`, ambas com reduzido) (D3); `downgrade -1` → versão `0007`, as 2 contas com o mesmo `id`, `codigo`, `nome` e `plano_id`, e as colunas ausentes em `information_schema.columns`; `upgrade 0008` → `tipo = 'A'` e `codigo_reduzido IS NULL` nas 2
  - [ ] INSERTs como `lastro_app`, com `_act_as(conn, firm)` antes (NUC-03/R1); leitura após o downgrade como `lastro_owner`, como o c4 da DB-02
  - [ ] Hoje os 4 falham pelo motivo certo (revisão `0008` inexistente ou coluna ausente), não por erro de fixture
  - [ ] Só dados inventados (pergunta 2 do plan): `ESCRITORIO_TESTE_DB04`, `EMP-1`/`EMP-2`, CNPJ com DV inválido, reduzidos sem forma de CPF/CNPJ
- **Exemplos:** P1 `(codigo='1101', reduzido='0000123')` + `(codigo='1102', reduzido='0000123')` → recusa; P1 `(codigo='1103', reduzido=NULL)` ×2 → aceitas; `tipo='X'` → recusa; INSERT sem `tipo` → `'A'`.
- **Arquivos:** `tests/registry/test_conta_contabil_db04.py` (novo)
- **Reaproveitar:** `fresh_database` e `sys.modules["_lastro_db02_core_fixtures"]` (`tests/registry/conftest.py`); copiar o padrão de `_run_alembic`, `_insert`, `_act_as` e `_reject` de `test_registry_schema.py` · **Não criar:** conftest novo, fixture em `fixtures/`, import de outro módulo de teste
- **Fora do escopo:** código de produção; outros arquivos de teste (vão na T2)
- **Pronto quando:** `docker compose run --rm dev pytest tests/registry/test_conta_contabil_db04.py -q` mostra 4 falhas esperadas

## [ ] T2 · Fixar os dois testes antigos na revisão própria (exceção T12)
- **Critérios da ficha:** nenhum da DB-04; mantém `passing` o c1 da DB-02 e o c4 da DB-03 (`DECISIONS.md` §11, T12)
- **Regra de negócio (em linguagem simples):** esses dois testes conferem o esquema "inteiro" no `head`, então qualquer coluna nova os quebra, mesmo sem nada errado. Fixá-los na revisão da própria ficha faz cada teste provar só o que a ficha dele entrega. A T12 autoriza **apenas** isto, só neste commit, sem mudar o corpo.
- **Critérios de aceite:**
  - [ ] `tests/registry/test_registry_schema.py`: fixture local `database_at_db02` (sobe até a `0003`); só `test_migracao_db02_cria_tabelas_de_cadastro_com_colunas_e_chaves` passa a usá-la no lugar de `migrated_database`; o corpo não muda
  - [ ] `tests/access/test_period_link_schema.py`: constante nova `DB03_REVISION = "0004"`; em `test_db03_migracao_reversivel`, os dois `upgrade head` (linhas ~603 e ~637) passam a `DB03_REVISION` (pergunta 1 do plan); o resto não muda
  - [ ] Nenhum outro teste, auxiliar ou asserção muda (`git diff` mostra só essas linhas)
  - [ ] Antes da migração nova, os dois testes continuam passando
- **Exemplos:** antes: `head` → `conta_contabil` com 8 colunas; depois da DB-04, `head` teria 10 e o c1 da DB-02 falharia. Fixado na `0003`, continua com 8.
- **Arquivos:** `tests/registry/test_registry_schema.py`, `tests/access/test_period_link_schema.py`
- **Reaproveitar:** `_run_alembic` de cada arquivo · **Não criar:** helper compartilhado entre os arquivos
- **Fora do escopo:** outros testes da DB-02/DB-03; `head_database` da DB-03 (c1–c3 só olham tabelas da DB-03)
- **Decisões relacionadas:** T12 (`DECISIONS.md`), pergunta 1
- **Pronto quando:** `docker compose run --rm dev pytest tests/registry/test_registry_schema.py tests/access/test_period_link_schema.py -q` passa

## [ ] T3 · Commit só de testes e prova do estado inicial
- **Critérios da ficha:** todos (registro da prova)
- **Regra de negócio (em linguagem simples):** o commit só de testes trava a prova antes do código; o hash dele é a referência do `git diff` no fim.
- **Critérios de aceite:**
  - [ ] Revisão humana dos testes de T1 e T2 feita
  - [ ] Commit só com os 3 arquivos de `tests/`; hash anotado em `progress/DB-04.md`
  - [ ] `hx feature verify DB-04` falha nos 4 critérios
  - [ ] `hx feature verify DB-02` e `hx feature verify DB-03` continuam `passing`; commit das fichas que o `hx` regravou (estado e evidência só pelo `hx`, regra 2)
- **Arquivos:** `tests/…` (já escritos), `progress/DB-04.md`; `features/DB-0{2,3,4}.json` só pelo `hx`
- **Fora do escopo:** qualquer arquivo em `src/` ou `migrations/`
- **Pronto quando:** `git show --stat HEAD~1` lista só `tests/` e `hx feature verify DB-02` / `DB-03` terminam com código 0

## [ ] T4 · Migração `0008`
- **Critérios da ficha:** c1, c2, c3, c4
- **Regra de negócio (em linguagem simples):** acrescenta as duas colunas sem mexer nas outras. As contas que já existem ficam analíticas (`A`) e sem reduzido. Desfazer a migração tira só o que ela pôs.
- **Critérios de aceite:**
  - [ ] `migrations/versions/0008_…py` com `revision = "0008"`, `down_revision = "0007"` e docstring no padrão da `0007`
  - [ ] `upgrade()`: `codigo_reduzido text NULL`; `tipo text NOT NULL DEFAULT 'A'`; `ck_conta_contabil_tipo` (`tipo IN ('S','A')`); `uq_conta_contabil_plano_reduzido` em `(escritorio_id, cliente_id, plano_id, codigo_reduzido)`, um `UNIQUE` simples, sem `NULLS NOT DISTINCT`
  - [ ] `downgrade()`: tira a unicidade, o check e as duas colunas, nada mais
  - [ ] Sem `CHECK` de formato no reduzido (D4); sem RLS, grant ou função nova (já cobertos por tabela)
  - [ ] `alembic heads` mostra uma só cabeça, `0008`
- **Exemplos:** banco com 2 contas na `0007` → `upgrade` → as 2 com `tipo='A'` e `codigo_reduzido=NULL`; `downgrade -1` → colunas somem, contas ficam.
- **Arquivos:** `migrations/versions/0008_add_ledger_account_short_code_and_kind.py` (nome sugerido, em inglês como as outras)
- **Reaproveitar:** estilo da `0003` (nomes completos de restrição) · **Não criar:** mudança na `0003` ou em outra migração
- **Fora do escopo:** renomear `codigo` (T6); leitor do TXT (CAD-02); carga do plano (CAD-05)
- **Decisões relacionadas:** D4, D5; T6 (`DECISIONS.md`)
- **Pronto quando:** `docker compose run --rm dev pytest tests/registry/test_conta_contabil_db04.py -k "reduzido_unico or tipo_so_aceita or reversivel" -q` passa

## [ ] T5 · Modelo `LedgerAccount` acompanha a migração
- **Critérios da ficha:** c1
- **Regra de negócio (em linguagem simples):** o código Python precisa descrever a tabela como ela é, para as próximas fichas (CAD-05) gravarem reduzido e tipo pelo ORM.
- **Critérios de aceite:**
  - [ ] `codigo_reduzido: Mapped[str | None]` (`Text`) e `tipo: Mapped[str]` (`Text`, `server_default` `'A'`)
  - [ ] `__table_args__` ganha `CheckConstraint("tipo IN ('S', 'A')", name="tipo")` (a convenção gera `ck_conta_contabil_tipo`) e `UniqueConstraint(..., name="uq_conta_contabil_plano_reduzido")` (D5)
  - [ ] Nada mais muda no arquivo
- **Arquivos:** `src/lastro/registry/models.py`
- **Reaproveitar:** `Base` e a convenção de `core/models.py`; o padrão de `ChartOfAccounts` (`CheckConstraint` com nome curto) · **Não criar:** enum Python, validador, serviço
- **Fora do escopo:** usar as colunas em `service.py` ou `api/`
- **Decisões relacionadas:** D5
- **Pronto quando:** `docker compose run --rm dev pytest tests/registry/test_conta_contabil_db04.py -q` passa (os 4)

## [ ] T6 · Registrar o downgrade no doc do módulo
- **Critérios da ficha:** c4 (documenta a consequência)
- **Regra de negócio (em linguagem simples):** quem desfaz a `0008` perde os reduzidos e os tipos gravados. Quem opera o banco precisa saber disso antes, como a DB-02 já avisa para a `0003`.
- **Critérios de aceite:**
  - [ ] Em `docs/modulos/registry.md`, na seção da DB-04: uma frase dizendo que o downgrade da `0008` apaga `codigo_reduzido` e `tipo`, e que no upgrade seguinte as contas voltam como `A`, sem reduzido
  - [ ] Nenhuma outra mudança no doc (a seção da DB-04 já está correta)
- **Arquivos:** `docs/modulos/registry.md`
- **Fora do escopo:** corrigir `docs/refatoracoes/DB-04.md`, o RF-CAD-03 ou a ficha (sugestões do plan, por humano)
- **Pronto quando:** `git diff -- docs/modulos/registry.md` mostra só a frase nova

## [ ] T7 · Verificação final
- **Critérios de aceite:**
  - [ ] `git diff <hash-da-T3> -- tests/` vazio
  - [ ] `alembic heads` com uma só cabeça; a `0008` aponta para o head da `origin/developer` (renumerar, se outra migração tiver entrado)
  - [ ] `docker compose run --rm dev pytest -q` completo verde, incluindo os termômetros da T12 (`tests/core/test_isolamento_banco.py`, DB-01, CAD-03, IA-02, `tests/conftest.py`, `tests/harness/test_session_fixture.py`)
  - [ ] `ruff check .` limpo
  - [ ] `hx check-clean` e `hx verify` em OK
  - [ ] `hx feature verify DB-04` grava `passing`; depois `hx feature verify DB-02` e `hx feature verify DB-03` continuam `passing`, com commit entre um e outro
  - [ ] `progress/DB-04.md` atualizado; PR para a `developer` (pergunta 3) com `git diff <hash> -- tests/` marcado "mudou", com o link da T12 e o hash, e revisão das donas da DB-02 e da DB-03
- **Pronto quando:** `hx verify`, `hx check-clean` e os três `hx feature verify` terminam com código 0
