# Plan — DB-04 · Acrescentar à conta contábil o código reduzido e o tipo (sintética ou analítica)

**Status:** aprovado (caio-nascime, 27/11/2026)
**Branch:** feat/DB-04-acrescentar-a-conta-contabil-o-codigo-re · **Data:** 27/11/2026 · **Responsável:** caio-nascime
**Tasks:** planos/DB-04/tasks.md · **Roteiro:** `docs/refatoracoes/DB-04.md` · **Decisões:** `DECISIONS.md` §11 (T6, T12)

## 1. A decidir (humano)
Nenhuma pergunta aberta: as três foram respondidas em 27/11 (ver seção 5). Pendências de terceiros:
- **Aval de camposs04** (responsável pelo `SECURITY.md`) para a resposta 2, no PR ou como DB-04/B1 no `DECISIONS.md`.
- **Revisão de camposs04** (dona da DB-03) para a resposta 1, no PR.

Mudanças sugeridas na ficha (aceitas por caio-nascime em 27/11; o humano aplica em PR, porque o agente não edita `features/`):
- c1 e c4: trocar "head" por "revisão da DB-04 (`0008`)". Hoje `head` é a `0008` e o resultado é o mesmo. Quando uma ficha futura (ex.: CAD-05) acrescentar uma `0009`, `downgrade -1` a partir de `head` desfaria a migração errada e o c1 compararia colunas que não são da DB-04. É a mesma armadilha que a T12 corrige hoje na DB-02 e na DB-03.
- `requisitos`: `BD-02` não existe em `requisitos_lastro.json`. É a decisão de banco "BD-01 a BD-08" do `DECISIONS.md` §1. Sugestão: trocar por `RF-CAD-03` só, ou citar "BD-02 (DECISIONS §1)".

Correções sugeridas em docs (aceitas; o humano aplica fora desta branch ou no PR):
- `docs/refatoracoes/DB-04.md`, tabela "O que muda", 1ª linha: a mesma célula diz `down_revision = "0007"` e depois `down_revision = "0006"`. Vale a `0007` (código, T6, `docs/modulos/registry.md`). Apagar a frase final da célula.
- `requisitos_lastro.json` / `requisitos-v0.2.md`: o RF-CAD-03 ainda diz "por planilha", mas a T1 do §11 já trocou para TXT (regra 9: o escopo muda primeiro em `docs/`). Não afeta esta ficha, que só mexe no esquema.

## 2. Decisões tomadas pelo agente
### D1 · Os testes da DB-04 sobem até uma constante `DB04_REVISION = "0008"`, não até `head`
- **Alternativas:** A) `upgrade head` e `downgrade -1`, como diz a ficha · B) `upgrade 0008` e `downgrade -1` (que dá a `0007`), `upgrade 0008`
- **Escolhida:** B. Hoje o resultado é o mesmo, e B não quebra quando entrar a `0009`, a lição da T12. As restrições da NUC-03 (RLS, `0005`) continuam valendo na `0008`, então o `_act_as` continua necessário.
- **Impacto:** T1; c1 a c4. Depende de a ficha aceitar a troca (seção 1). Sem ela, use A e anote o risco.
- [x] confirmar (caio-nascime, 27/11)

### D2 · O c1 compara o dicionário **inteiro** de colunas de `conta_contabil` (8 da DB-02 + 2), escrito no próprio arquivo novo
- **Alternativas:** A) importar `COLUMNS` de `test_registry_schema.py` · B) duplicar as 8 entradas e somar as 2 novas
- **Escolhida:** B. Importar um módulo de teste por outro acopla dois arquivos, e um deles está sob a T12. B prova "sem mudar as outras colunas" de forma direta. Esperado para as novas: `codigo_reduzido` (`text`, nulo, sem padrão) e `tipo` (`text`, não nulo, padrão `'A'::text`).
- **Impacto:** T1; c1.
- [x] confirmar (caio-nascime, 27/11)

### D3 · O c4 grava 2 contas com reduzido, uma delas com tipo `S`
- **Alternativas:** A) 2 contas sem reduzido e com tipo padrão · B) uma `S` com reduzido e uma `A` com reduzido
- **Escolhida:** B. Prova que as colunas saem de fato no downgrade (os valores voltam `NULL` e `'A'`) e que `id`, `codigo`, `nome` e `plano_id` sobrevivem, sem mudar a saída da ficha ("tipo 'A' nas 2 contas").
- **Impacto:** T1, T6 (o doc diz que o downgrade perde o reduzido e o tipo); c4.
- [x] confirmar (caio-nascime, 27/11)

### D4 · Sem `CHECK` de formato no reduzido (7 dígitos)
- **Alternativas:** A) `CHECK (codigo_reduzido ~ '^[0-9]{7}$')` · B) só `text NULL` e unicidade
- **Escolhida:** B. A ficha e a T6 pedem só texto opcional e único. O formato é validado na leitura do TXT (CAD-02, E2/E2z, "tolerável"), e um check no banco seria escopo novo (regra 9).
- **Impacto:** T4.
- [x] confirmar (caio-nascime, 27/11)

### D5 · O modelo usa a convenção de nomes da `Base` para o check e o nome explícito para a unicidade
- No modelo: `CheckConstraint(..., name="tipo")`, que a convenção `ck_%(table_name)s_%(constraint_name)s` (`core/models.py`) transforma em `ck_conta_contabil_tipo`. `UniqueConstraint(..., name="uq_conta_contabil_plano_reduzido")` fica explícito, como o `uq_conta_contabil_plano_codigo` que já existe. Na migração, os dois nomes completos, como faz a `0003`. Se o modelo usasse `name="ck_conta_contabil_tipo"`, o nome sairia com o prefixo duplicado.
- **Impacto:** T4, T5; c1.
- [x] confirmar (caio-nascime, 27/11)

## 3. Resumo e abordagem
Uma migração aditiva `0008` (`down_revision = "0007"`) acrescenta `codigo_reduzido` e `tipo` à `conta_contabil`, com check e unicidade. O `LedgerAccount` acompanha a migração. É refatoração porque dois testes `passing` (DB-02 c1, DB-03 c4) fixam o esquema ou o conteúdo **inteiro** e precisam ser fixados na revisão própria, só como a T12 permite.
Ordem (segue o roteiro): (1) testes novos + as duas fixações da T12, num commit só de testes, com o hash anotado. (2) `hx feature verify DB-04` falha nos 4; DB-02 e DB-03 continuam `passing`. (3) Migração `0008`. (4) Modelo. (5) Nota no doc do módulo. (6) `hx feature verify` DB-04, DB-02 e DB-03 (commit entre cada), `pytest` completo, `git diff <hash> -- tests/` vazio. A NUC-03 não exige nada novo: a RLS e os privilégios valem por tabela, então as colunas novas já ficam cobertas.

## 4. Contexto encontrado
- **Planos lidos (`depende_de`):** `planos/DB-02/plan.md` (texto diz "pronto para revisão", mas o §6 do `DECISIONS.md` registra a aprovação de Raissa; D1–D3 valem); `planos/NUC-03/plan.md` ("aguarda aprovação da §8"; D1–D6 confirmadas e R1–R4 no `DECISIONS.md`, que valem); `planos/ACE-02/plan.md` ("pronto para revisão"; F1–F5 aprovadas no `DECISIONS.md`). Achado: o campo Status dos três está desatualizado em relação ao `DECISIONS.md` (ATENÇÃO 6). Fora de `depende_de`: nenhum.
- **Progress:** `progress/DB-04.md` só com o modelo (início 27/11). Não li os progress das dependências: as três estão `passing` e o `DECISIONS.md` cobre o que importa.
- **`DECISIONS.md` lido:** §11 T6 (colunas, `0008` depois da `0007`, `codigo` não muda de nome), T9 (a IA filtra `tipo = 'A'` só numa ficha futura: aqui, nada), T11, T12 (lista fechada de testes que podem mudar e termômetros); §10 NUC-03/R1 (INSERT em tabela com escritório exige `app.firm_id`; tabela **nova** precisaria de RLS, mas aqui não há tabela nova); NUC-03/R2–R4 (não se aplicam: não lê `usuario`); §6 DB-02/B1–B3 (nomes físicos em português, classes em inglês; B1 é restrito à DB-02, daí a pergunta 2); §8 DB-03/B1–B2 (idem); §7 ACE-01/E1–E2 e ACE-02/F1–F5 (sem efeito no esquema da conta); DB-01/B1–B4 (nomes físicos em português); §1 BD-01..08 (PostgreSQL 18, migrações versionadas, RLS).
- **Conferência com o código:**
  - **confere:** `0007_password_created_lookup.py` é o head (`down_revision = "0006"`), também na `origin/developer`, e nenhuma branch remota ocupa a `0008`. `LedgerAccount` (`src/lastro/registry/models.py:137`) tem 8 colunas e `uq_conta_contabil_plano_codigo`. A `0003` cria `conta_contabil` com nomes explícitos. A `0005` põe a RLS por tabela (`conta_contabil` na lista), e os privilégios de `lastro_app` são por tabela (`0001`, default privileges). `test_registry_schema.py` c1 compara `actual == COLUMNS[table]` em `head`. `test_period_link_schema.py` c4 compara `SELECT *` das tabelas da DB-02 antes e depois. `_act_as` existe nos dois arquivos. `hx feature verify/start`, `verify` e `check-clean` existem em `tools/harness.py`.
  - **divergente:** (a) roteiro com `down_revision` "0007" e "0006" na mesma célula: vale a `0007`. (b) a T12 cita a constante `DB03_REVISION`, que **ainda não existe** no arquivo: a T2 a cria. (c) a T12 fala em "head" no singular, mas o teste tem duas chamadas (pergunta 1).
  - **não verificável:** `referencia_simulacao/DB-04_1_testes.patch` e `_2_implementacao.patch` não estão no repositório. A simulação de 26/11 entra como relato, não como prova.
- **Outros testes que leem `conta_contabil`:** `tests/core/test_isolamento_banco.py:149` (INSERT sem `tipo`: o padrão `'A'` resolve); `test_registry_schema.py` c2–c4 (INSERT sem as colunas novas; o c4 desce até a `0002` passando pela `0008`). Nenhum outro compara colunas de `conta_contabil`.
- **Reaproveitar:** fixtures `fresh_database` e o módulo `_lastro_db02_core_fixtures` (`tests/registry/conftest.py`); o padrão de `_run_alembic`, `_insert`, `_act_as` e `_reject` de `test_registry_schema.py` (copiar para o arquivo novo, sem importar); o estilo da `0003` (nomes completos).
- **Não criar:** tabela, política RLS, função, papel, `utils.py`, dependência nova; não renomear `codigo` (T6).
- **Pesquisa externa:** sem pesquisa externa necessária. "Nulos não conflitam em `UNIQUE`" é o comportamento padrão do PostgreSQL, já decidido no roteiro, e o próprio c2 o prova.

## 5. Decisões (já resolvidas)
- 26/11 · T6: colunas, nomes de restrição, `0008` depois da `0007`, `codigo` mantido (caio-nascime, líder).
- 26/11 · T12: só os c1 da DB-02 e c4 da DB-03 mudam, no commit de testes desta ficha, sem mudar o corpo (caio-nascime).
- 27/11 · Pergunta 1: as **duas** chamadas `upgrade head` de `test_db03_migracao_reversivel` passam a `DB03_REVISION = "0004"` (caio-nascime; falta a revisão de camposs04 no PR).
- 27/11 · Pergunta 2: os testes da DB-04 criam registros sintéticos transitórios no próprio teste (`*_TESTE_DB04`, `EMP-1`/`EMP-2`, CNPJ com DV inválido, nada em `fixtures/`) (caio-nascime; falta o aval de camposs04 pelo `SECURITY.md`).
- 27/11 · Pergunta 3: o PR vai para a `developer` (caio-nascime).
- 27/11 · D1 a D5 confirmadas e mudanças sugeridas na ficha e nos docs aceitas (caio-nascime). Até a ficha ser editada, ela ainda diz `head` em c1 e c4; os testes seguem a D1.

## 6. Avaliação da ficha
| # | Achado | Gravidade | Critério |
|---|---|---|---|
| 1 | "head" em c1/c4 fica frágil quando surgir a `0009` (D1 e sugestão de ficha) | ATENÇÃO | c1, c4 |
| 2 | Escopo da fixação do c4 da DB-03 (pergunta 1) | ATENÇÃO | T12 |
| 3 | Dados transitórios em teste novo sem exceção nominal (pergunta 2) | ATENÇÃO | c2–c4 |
| 4 | `requisitos` cita `BD-02`, que não é RF | ATENÇÃO | — |
| 5 | Roteiro com `down_revision` contraditório; patches da simulação ausentes | ATENÇÃO | c1, c4 |
| 6 | Status dos plans de DB-02, NUC-03 e ACE-02 desatualizado em relação ao `DECISIONS.md` | ATENÇÃO | — |
| 7 | c3: o exemplo não diz qual erro esperar. O padrão é `CheckViolation` para `'X'` e `NotNullViolation` para `NULL` explícito (padrão não se aplica a nulo explícito) | ATENÇÃO | c3 |

Tamanho adequado: 4 critérios, um módulo, uma sessão. Dependências `passing`. Sem risco de dado real além da pergunta 2.

## 7. Riscos
- **Duas cabeças no Alembic** se outra ficha mergear uma `0008` antes → a T7 confere `alembic heads` (uma só) e o `down_revision` contra a `developer` antes do PR; renumerar, se preciso.
- **Enfraquecer um teste antigo** além do que a T12 permite → a T2 muda só a revisão de subida; o corpo dos testes não muda. O PR marca `git diff <hash> -- tests/` como "mudou", com o link da T12. Revisão: dona da DB-02 (Raissa) e dona da DB-03 (camposs04).
- **Termômetros quebrando** (`test_isolamento_banco.py`, DB-01, CAD-03, IA-02, `tests/conftest.py`) → `pytest` completo na T7. Qualquer falha fora da lista da T12 é erro na implementação, não autorização (T12).
- **Downgrade perde reduzido e tipo** → aceito pela ficha (c4); a T6 registra no `docs/modulos/registry.md`, como a DB-02 fez com a `0003`.
- **ORM diferente do banco** (nome do check com prefixo duplicado) → D5; o c1 confere o modelo.

## 8. Aprovação
- [x] Perguntas 1 a 3 respondidas
- [x] Decisões D1 a D5 confirmadas
- [x] Plan e tasks revisados por caio-nascime em 27/11
- [ ] Aval de camposs04 para a resposta 2 e revisão da fixação da DB-03 (no PR)
