# Tasks — perf-93 · `hx verify` de ~18 min para 3–4 min

**Plan:** planos/perf-93/plan.md · **Issue:** #93 · **Ficha:** nenhuma
**Ordem:** T1 → T2 → T3 (sem tocar em `tests/`) → T4 (exceção aprovada por humano) → T5 → T6 → T7 (paralelo) → T8. Um commit por task. Medir depois de cada uma.

> Sem ficha não há testes novos a escrever primeiro: o comportamento (o que cada teste prova) não muda. A T1 troca o "testes antes" por "medição antes", e a prova de cada task é a suíte inteira verde **com o mesmo número de testes** (524 nesta branch, base `developer` de 27/11; 528 depois do rebase com o #92).

---

## [x] T1 · Medição de base
- **Regra (em linguagem simples):** sem o número de antes, não dá para saber se cada passo ajudou.
- **Critérios de aceite:**
  - [ ] Na branch, sem mudanças: `pytest -q --durations=25` completo no container `dev`; anotar o total, os 25 mais lentos e o número de testes
  - [ ] Tempo do `hx verify` no host (Windows) e do job `verify` da última execução do `pr.yml`
  - [ ] Números registrados num comentário na issue #93 (sem dado real)
- **Arquivos:** nenhum no repositório
- **Pronto quando:** o comentário com a base está na #93

## [x] T2 (critério de 1,6 s não atingido: 1,8–2,4 s) · Bytecode pré-compilado na imagem (D1)
- **Regra (em linguagem simples):** hoje cada processo Python recompila as bibliotecas do zero (~2,5 s). Compilando uma vez, no build, cada processo começa mais rápido. Nenhum teste muda.
- **Critérios de aceite:**
  - [ ] `Dockerfile`, estágio `base`: `UV_COMPILE_BYTECODE=1` vale para os `uv sync` de `dev` e de `runtime`; o `PYTHONDONTWRITEBYTECODE=1` fica
  - [ ] Depois do rebuild, o `site-packages` de `/opt/venv` tem `.pyc` (hoje: 0)
  - [ ] `python -c "import sqlalchemy, alembic, psycopg"` no `dev` leva menos de 1,6 s (hoje 2,4–2,6 s)
  - [ ] `pytest tests/core/test_ambiente.py -q` passa (lê o Dockerfile)
- **Exemplos:** `alembic heads` 2,3 s → ~1,5 s.
- **Arquivos:** `Dockerfile`
- **Não criar:** passo `compileall` separado; mudança no `docker-compose.yml`
- **Fora do escopo:** compilar a biblioteca padrão do Python (`python -c pass` já leva 0,14 s)
- **Pronto quando:** `docker compose build dev` e `pytest -q --durations=25` verdes, com o mesmo número da T1; tempo anotado na #93

## [ ] T3 (falta só a CI verde no push) · `node_modules` do front num volume nomeado (D2)
- **Regra (em linguagem simples):** o build e o Vitest leem milhares de arquivos do `node_modules`. Pela pasta compartilhada com o Windows isso é lento; num volume do Docker é rápido. Os 4 testes do front continuam rodando tudo.
- **Critérios de aceite:**
  - [ ] `docker-compose.yml`: o serviço `dev` monta um volume nomeado em `/app/web/node_modules`, declarado em `volumes:` no fim do arquivo, com comentário do motivo
  - [ ] `Dockerfile`, estágio `dev`: a pasta `/app/web/node_modules` existe na imagem e é gravável por qualquer uid (para o `--user` do `hx` no Linux e na CI)
  - [ ] O `api` e o `db` não mudam; o socket continua só no `docker-proxy`
  - [ ] `pytest tests/web -q` passa e os 4 testes juntos levam menos de 60 s (hoje ~240 s)
  - [ ] O job `verify` do `pr.yml` passa nesta branch (prova do `--user` no Linux)
- **Exemplos:** 1ª execução: `pnpm install` baixa para o volume (~20 s); da 2ª em diante: ~0,1 s. Lockfile mudou: o `pnpm install --frozen-lockfile` dos testes sincroniza.
- **Arquivos:** `docker-compose.yml`, `Dockerfile`
- **Não criar:** `docker-compose.override.yml`; volume anônimo (`run --rm` o apaga a cada execução)
- **Fora do escopo:** o `node_modules` do host (o editor continua usando o dele); `gitpages/`
- **Pronto quando:** `pytest tests/web tests/core/test_ambiente.py -q` verde local e CI verde no push

## [x] T4 · Exceção à regra 3 registrada (humano)
- **Regra (em linguagem simples):** trocar como uma fixture prepara o banco mexe em `tests/`, e o `AGENTS.md` proíbe isso ao implementar. Só com uma lista fechada e escrita, como a T12.
- **Critérios de aceite:**
  - [ ] Entrada nova no `docs/decisoes/DECISIONS.md` (pergunta 1 do plan) com a lista: `tests/conftest.py` (ganha `postgres_server`, a fábrica de modelos, o gancho de número de processos e o grupo do front), `tests/core/conftest.py` (`postgres_server` sai; `migrated_database` clona `head`), `tests/access/conftest.py` (`migrated_database` clona `0002`; reatribuição de `postgres_server` sai), `tests/registry/conftest.py` (reatribuição de `postgres_server` sai), `tests/access/test_login.py::head_database` e `tests/access/test_period_link_schema.py::head_database` (clonam `head`)
  - [ ] A entrada diz: nenhum `def test_` muda, nenhuma asserção sai, cada fixture continua na mesma revisão
  - [ ] Aprovada por caio-nascime (líder)
- **Arquivos:** `docs/decisoes/DECISIONS.md` (o agente pode redigir; o humano aprova)
- **Pronto quando:** a entrada está aprovada e commitada

## [x] T5 · Um PostgreSQL só para a suíte (D4)
- **Regra (em linguagem simples):** hoje três pastas sobem três bancos de teste. Um só basta, porque cada teste já ganha um banco próprio dentro dele.
- **Critérios de aceite:**
  - [ ] `postgres_server` (escopo de sessão) definido só no `tests/conftest.py`, com o mesmo corpo de hoje
  - [ ] `tests/core/conftest.py`, `tests/access/conftest.py` e `tests/registry/conftest.py` não definem nem reatribuem `postgres_server`; o resto fica igual
  - [ ] Durante `pytest -q`, `docker ps` mostra **um** container `postgres:18` de teste (hoje 3)
  - [ ] `tests/core/test_ambiente.py` (c6: versão do PostgreSQL) e `tests/harness/test_session_fixture.py` passam
- **Arquivos:** só os da lista da T4
- **Reaproveitar:** `PostgresServer`, `FreshDatabase`, `connect`, `_set_password` · **Não criar:** plugin novo (só se o A da D4 falhar; registrar)
- **Fora do escopo:** banco-modelo (T6)
- **Pronto quando:** `pytest -q` completo verde, o mesmo número de testes da T1, um container só

## [x] T6 · Banco-modelo por revisão (D3)
- **Regra (em linguagem simples):** em vez de cada teste migrar um banco vazio (~5 s), o banco é migrado uma vez por revisão e cada teste recebe uma cópia em menos de 1 s. Os testes de migração continuam migrando do zero, porque é isso que provam.
- **Critérios de aceite:**
  - [ ] Fábrica de sessão no `tests/conftest.py`: para cada revisão pedida, cria uma vez um banco-modelo (vazio + `alembic upgrade <rev>`), fecha as conexões e guarda o nome
  - [ ] Clone pelo superusuário com `TEMPLATE <modelo> OWNER lastro_owner`; o banco clonado é apagado depois do teste, como o `fresh_database`
  - [ ] As 5 fixtures da T4 usam a fábrica, na mesma revisão de hoje (`head` ou `0002`)
  - [ ] `fresh_database`, `run_alembic_upgrade` e os testes que sobem e descem no corpo não mudam
  - [ ] Falha ao criar o modelo ou ao clonar = erro claro na fixture (nunca `skip`)
  - [ ] Os modelos são apagados no fim da sessão
- **Exemplos:** 19 testes do `test_cadastro_contador.py`: ~5 s de preparo cada → menos de 1 s. `test_db03_migracao_reversivel`: igual a hoje.
- **Arquivos:** só os da lista da T4
- **Reaproveitar:** `run_alembic_upgrade`, `process_output`, `FreshDatabase` · **Não criar:** `pg_dump`; cache entre execuções
- **Fora do escopo:** `database_at_db02`/`database_at_db04` (DB-04, pergunta 5); paralelo
- **Pronto quando:** `pytest -q --durations=25` completo verde com o mesmo número da T1; `git diff developer -- tests/` só nas fixtures da T4, sem `def test_` alterado

## [x] T7 · Testes em paralelo com `pytest-xdist` (D5, D6, D7)
- **Regra (em linguagem simples):** em vez de um teste por vez, a suíte roda em até 4 processos. Um teste rodado sozinho (`feature verify`) continua em série. As regras para escrever teste seguro em paralelo estão no `CODING_STANDARDS.md`, seção 2.
- **Critérios de aceite:**
  - [ ] `pytest-xdist` no grupo `dev` do `pyproject.toml`, `uv.lock` atualizado (`uv lock`); escolha e motivo na D5 (regra 12)
  - [ ] `pyproject.toml` ganha `[tool.pytest.ini_options]` com `addopts = "-n auto --dist loadgroup"`
  - [ ] `tests/conftest.py`: `pytest_xdist_auto_num_workers` devolve até 4 (limitado pelos CPUs) e **0** quando algum argumento tem `::`; os itens de `tests/web/` recebem `xdist_group` (um grupo só)
  - [ ] O `hx` (`tools/harness.py`), o `pr.yml` e o `tests/harness/test_fase_c.py` não mudam
  - [ ] `pytest -q` completo verde **3 vezes seguidas**, com o mesmo número da T1; `pytest -n 0 -q` também verde
  - [ ] `hx feature verify` de uma ficha `passing` qualquer (ex.: DB-03) roda cada critério em série e continua OK
  - [ ] Durante a suíte, no máximo 4 containers `postgres:18` de teste (D7)
- **Exemplos:** `pytest -q` → "created: 4/4 workers"; `pytest tests/x.py::test_y -q` → sem workers.
- **Arquivos:** `pyproject.toml`, `uv.lock`, `tests/conftest.py` (na lista da T4)
- **Não criar:** `pytest.ini`; mudança no `hx`; trava de arquivo (só se a D7 virar B)
- **Fora do escopo:** marcar teste a teste; mudar asserção
- **Pronto quando:** as 3 execuções paralelas verdes, `-n 0` verde e o tempo anotado na #93

## [ ] T8 (falta push, CI e PR) · Medição final, documentação e verificação
- **Critérios de aceite:**
  - [ ] `pytest -q --durations=25` e `hx verify` (host) medidos e comparados com a T1 na #93
  - [ ] `docs/modulos/` ou `ARCHITECTURE.md`: uma nota sobre o banco-modelo, o volume (como limpar: `docker volume rm`) e o paralelo (`pytest -n 0` para investigar)
  - [ ] Se a pergunta 4 for aprovada: corrigir o contorno do `AGENTS.md` (`verify` e `feature verify` rodam no host)
  - [ ] `ruff check .` limpo; `hx check-clean` OK; `hx verify` OK (local e CI)
  - [ ] Não há `hx feature verify` (sem ficha, pergunta 2)
  - [ ] PR para a `developer` com o link da #93, as medições e a revisão de camposs04
- **Pronto quando:** `hx verify` e `hx check-clean` terminam com código 0 e o `pr.yml` está verde
