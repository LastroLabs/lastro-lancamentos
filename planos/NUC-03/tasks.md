# Tasks — NUC-03 · Isolar no banco os dados de cada escritório

**Plan:** planos/NUC-03/plan.md · **Ficha:** features/NUC-03.json
**Ordem:** T1 → revisão humana dos testes → commit só-de-testes (anotar o hash) → T2 em diante (sessão nova, sem editar `tests/`)
**Respostas do plan (26/11):** P1 quarta função + privilégio por coluna; P2 RLS nas 12 tabelas; P3 T1 adapta testes de DB-02, DB-03 e ADM-01.

---

## [x] T1 · Escrever os testes dos critérios
- **Critérios da ficha:** c1 a c7
- **Regra de negócio:** o banco, e não só o código, deve esconder as linhas de outro escritório; sem escritório definido, não se vê nada, e o escritório de uma transação nunca passa para a seguinte.
- **Critérios de aceite:**
  - [x] Existem, em `tests/core/test_isolamento_banco.py`, os 8 testes citados em `verificacao` (`test_consulta_sem_filtro_ve_so_o_proprio_escritorio`, `test_consulta_sem_escritorio_nao_ve_nada`, `test_gravar_em_outro_escritorio_e_recusado`, `test_alterar_cliente_de_outro_escritorio_nao_altera`, `test_escritorio_nao_vaza_entre_transacoes`, `test_rls_em_todas_as_tabelas_da_db01`, `test_buscas_sem_escritorio_por_funcoes_restritas`, `test_login_continua_funcionando_com_rls`)
  - [x] Todos falham hoje pelo motivo certo (sem RLS, sem funções)
  - [x] Seed feito como superusuário; as consultas dos critérios, como `lastro_app`
  - [x] Só dados inventados (ESC-1, ESC-2, EMP-1, EMP-2, EMP-9, contador_a, contador_x)
  - [x] Testes de DB-02, DB-03 e ADM-01 adaptados (abrir a transação com o escritório definido), sem mudar o que provam; teste extra: `lastro_app` não lê `credencial_hash` por consulta direta
- **Exemplos:** transação de ESC-1 lista clientes → EMP-1 e EMP-2; sem escritório → 0 linhas, sem erro; ESC-1 tenta gravar EMP-10 marcado como ESC-2 → recusado; mesma conexão, transação 2 sem escritório → 0 linhas
- **Arquivos:** `tests/core/test_isolamento_banco.py` (novo); `tests/registry/test_registry_schema.py`, `tests/access/test_period_link_schema.py`, `tests/access/test_office_admin.py` (resposta 3: sim)
- **Reaproveitar:** `tests/core/conftest.py` (`fresh_database`, `FreshDatabase.conninfo`), `tests/access/test_login.py` (seed e `TestClient` com `base_url="https://testserver"`) · **Não criar:** outro Testcontainers
- **Fora do escopo:** código de produção
- **Pronto quando:** `docker compose run --rm dev pytest tests/core/test_isolamento_banco.py -q` mostra só falhas esperadas

## [x] T2 · Migração `0005`: RLS forçada e políticas
- **Critérios da ficha:** c1, c2, c3, c5
- **Regra de negócio:** cada linha só aparece e só pode ser gravada por quem está atendendo o escritório dono dela; quem não informou escritório não vê nada, sem erro.
- **Critérios de aceite:**
  - [x] `ENABLE` e `FORCE ROW LEVEL SECURITY` em `escritorio`, `membro`, `sessao`, `convite`, `cliente`, `atribuicao` e nas 6 de DB-02/DB-03 (`plano_contas`, `conta_contabil`, `conta_bancaria`, `socio`, `competencia`, `link_cliente`); `usuario` sem RLS
  - [x] Uma política por tabela, com `USING` e `WITH CHECK`, no formato de D3; política do dono conforme D2
  - [x] `REVOKE SELECT (credencial_hash) ON usuario FROM lastro_app` (e `GRANT SELECT` nas demais colunas); `INSERT` e `UPDATE` mantidos
  - [x] `lastro_app` continua sem ser dono e sem `BYPASSRLS`
  - [x] Migração reversível (`downgrade` desliga e apaga tudo) e `alembic upgrade head` limpo
- **Exemplos:** ESC-1 vê 2 clientes; EMP-9 não aparece; `UPDATE` do nome de EMP-9 em nome de ESC-1 → 0 linhas
- **Arquivos:** `migrations/versions/0005_enable_row_level_security.py`
- **Reaproveitar:** padrão de `0004` e `op.execute` · **Não criar:** política permissiva, papel novo
- **Fora do escopo:** funções (T3), código da aplicação
- **Decisões relacionadas:** D2, D3 · **Pronto quando:** `pytest tests/core/test_isolamento_banco.py -k "sem_filtro or sem_escritorio or gravar or alterar or todas_as_tabelas" -q` passa

## [x] T3 · Funções `SECURITY DEFINER` das buscas anteriores ao escritório
- **Critérios da ficha:** c6
- **Regra de negócio:** antes de saber o escritório, a aplicação só pode perguntar "de quem é esta sessão, este usuário ou este convite?" e receber o mínimo; hash inexistente, vencido, usado ou cancelado dá 0 linhas, sem erro.
- **Critérios de aceite:**
  - [x] Funções conforme D4 (e a quarta, `buscar_usuario_por_login`), dona `lastro_owner`, `search_path` fixo, `EXECUTE` só para `lastro_app`
  - [x] Retornos exatamente os de c6; nenhuma devolve nome, `credencial_hash` (exceto a quarta) nem `hash_token`
  - [x] `lastro_app` consulta `sessao` e `convite` direto sem escritório → 0 linhas; tentar `ALTER`/`DROP` da função → recusado
  - [x] `downgrade` apaga as funções
- **Exemplos:** hash da sessão de contador_a → 1 linha (escritório, membro, `expira_em`, `encerrada_em`); hash inexistente → 0 linhas; convite usado → 0 linhas
- **Arquivos:** `migrations/versions/0005_enable_row_level_security.py` (mesmo arquivo)
- **Fora do escopo:** função do link do cliente (ACE-05, pergunta 4)
- **Decisões relacionadas:** D2, D4 · **Pronto quando:** `pytest tests/core/test_isolamento_banco.py::test_buscas_sem_escritorio_por_funcoes_restritas -q` passa

## [x] T4 · Contexto de escritório em `core/`
- **Critérios da ficha:** c1, c2, c4
- **Regra de negócio:** o servidor diz ao banco "estou atendendo o escritório X" no começo de cada transação; terminou a transação, o aviso some.
- **Critérios de aceite:**
  - [x] Função em `core/` que guarda o escritório na sessão do banco e o aplica a cada transação (D1), com `set_config(..., true)`
  - [x] Sem escritório guardado, nada é aplicado (0 linhas, sem erro)
  - [x] Na mesma conexão, transação 2 sem escritório não vê o de transação 1
- **Exemplos:** sessão com ESC-1 abre 2 transações seguidas → ambas veem ESC-1; sessão nova na mesma conexão → nada
- **Arquivos:** `src/lastro/core/db.py` (ou `core/rls.py`, conforme `ARCHITECTURE.md`)
- **Reaproveitar:** `Database`, `get_session` · **Não criar:** outro pool ou engine
- **Fora do escopo:** quem chama (T5)
- **Decisões relacionadas:** D1 · **Pronto quando:** `pytest tests/core/test_isolamento_banco.py::test_escritorio_nao_vaza_entre_transacoes -q` passa

## [x] T5 · Login e `identify` pelas funções; `criar-escritorio` sob RLS
- **Critérios da ficha:** c7
- **Regra de negócio:** entrar e se identificar continuam iguais para o usuário; por baixo, as buscas sem escritório usam as funções e o resto roda já em nome do escritório.
- **Critérios de aceite:**
  - [x] `find_session`, `find_active_memberships` e a busca do login (`find_users_by_login`, pela quarta função) usam as funções e definem o escritório com o resultado
  - [x] `sign_in`, `identify`, `sign_out` mantêm as mesmas respostas e mensagens (401 "Sua sessão terminou. Entre de novo.")
  - [x] `insert_firm_with_manager` conforme D5; `tests/access/test_office_admin.py` verde
  - [x] Nenhuma consulta direta a `sessao`/`convite` sem escritório no código
- **Exemplos:** contador_a entra, pede a identificação (contador_a, contador, ESC-1), sai e pede de novo → 401
- **Arquivos:** `src/lastro/access/repository.py`, `src/lastro/access/service.py`
- **Reaproveitar:** `SessionRow`, `MembershipRow` · **Não criar:** contrato novo sem issue `contrato:` (regra 11)
- **Fora do escopo:** aceite de convite (ACE-02)
- **Decisões relacionadas:** D1, D4, D5 · **Pronto quando:** `pytest tests/core/test_isolamento_banco.py::test_login_continua_funcionando_com_rls -q` passa

## [x] T6 · Conferir as rotas de cliente sob RLS
- **Critérios da ficha:** c1, c7
- **Regra de negócio:** cadastrar e listar clientes pela API continuam funcionando, agora com o banco como segunda barreira.
- **Critérios de aceite:**
  - [x] `POST /clients`, `GET /clients`, `GET /clients/{id}` passam em `tests/registry/test_cliente.py`, sem editá-lo
  - [x] Cliente de outro escritório continua dando o mesmo 404
- **Arquivos:** só se faltar o escritório no contexto: `src/lastro/api/routes.py`
- **Fora do escopo:** regra de carteira (NUC-02/ACE-03)
- **Pronto quando:** `docker compose run --rm dev pytest tests/registry/test_cliente.py -q` passa

## [x] T7 · Documentação
- **Critérios da ficha:** todos
- **Regra de negócio:** quem vem depois precisa saber o que mudou e o que ficou fora.
- **Critérios de aceite:**
  - [x] `docs/modulos/access.md` e `docs/modulos/registry.md`: trocar os avisos "fica para a NUC-03" pelo que existe (a busca do link foi feita no c8; P4 revista)
  - [x] `docs/SECURITY.md` §8 e `ARCHITECTURE.md`: divisão DB-01/NUC-03 atualizada
  - [x] Decisões D1–D5 em `DECISIONS.md` só se afetarem mais de uma feature (D2 e D4 afetam ACE-02 e ACE-05)
- **Arquivos:** os de cima · **Fora do escopo:** código
- **Pronto quando:** `hx check-clean` sem achados

## [x] T8 · Verificação final
- **Critérios de aceite:**
  - [x] `git diff <hash-dos-testes> -- tests/` vazio
  - [x] `ruff check .` limpo
  - [x] `hx check-clean` e `hx verify` em OK
  - [x] `hx feature verify NUC-03` grava `passing`
- **Pronto quando:** os três comandos do `hx` terminam com código 0

---

**Acréscimo de 26/11 (c8, plan D6).** Só começa com P5 e P6 respondidas. Ordem: T9 → revisão humana dos testes → commit só-de-testes (anotar o hash) → T10 e T11 (sem editar `tests/`).

## [x] T9 · Escrever o teste da função do link
- **Critérios da ficha:** c8
- **Regra de negócio:** o cliente final abre o link sem login; antes de saber o escritório, o app só pode perguntar "de quem é este código?" e receber o mínimo. Código inexistente ou invalidado dá 0 linhas, sem erro.
- **Critérios de aceite:**
  - [x] `test_busca_do_link_sem_escritorio_por_funcao_restrita` em `tests/core/test_isolamento_banco.py`, cobrindo (1) e (2a) a (2f) do c8
  - [x] Seed como superusuário com L1 (no prazo), L2 (vencido), L3 (invalidado) em ESC-1 e L9 em ESC-2; consultas como `lastro_app`
  - [x] Confere `prosecdef`, `search_path`, dona e `EXECUTE`, como o teste de c6
  - [x] Falha hoje pelo motivo certo (função não existe)
- **Arquivos:** `tests/core/test_isolamento_banco.py`
- **Reaproveitar:** `_seed_firm`, `_lookup`, `_assert_minimal`, a consulta a `pg_proc` do teste de c6 · **Não criar:** outro seed nem outro Testcontainers
- **Pronto quando:** o teste falha só por falta da função

## [x] T10 · Migração `0006`: `buscar_link_por_hash`
- **Critérios da ficha:** c8
- **Critérios de aceite:**
  - [x] `migrations/versions/0006_client_link_lookup.py`, `down_revision = "0005"`
  - [x] Função conforme D6 e a resposta da P5; filtra `revogado_em IS NULL`; busca exata por `hash_token`
  - [x] `REVOKE ALL … FROM PUBLIC`, `GRANT EXECUTE` só a `lastro_app`; `downgrade` apaga a função
- **Reaproveitar:** o formato de `CREATE_FUNCTIONS` da `0005` · **Não criar:** política nova, código em `src/`
- **Pronto quando:** `pytest tests/core/test_isolamento_banco.py -q` e `pytest tests/core/test_migracoes.py -q` passam

## [x] T11 · Documentação e nova verificação
- **Critérios de aceite:**
  - [x] `docs/modulos/access.md`: a busca do link existe; como a ACE-05 a usa (chamar a função, depois `use_firm`)
  - [x] Issue `contrato:` com as cinco funções e `use_firm` (#82), avisando camposs04 (ACE-05) e caio-nascime (ACE-02)
  - [x] Ficha da ACE-05 (autorizado por caio-nascime em 26/11): NUC-03 em `depende_de`; c7 (abrir o link pela função, vencido decidido pelo relógio do app) e c8 (o link mostra só o próprio cliente e competência)
  - [x] `hx check-clean`, `hx verify` e `hx feature verify NUC-03` (regrava `estado` e `evidencia` com o c8)
- **Pronto quando:** os três comandos do `hx` terminam com código 0
