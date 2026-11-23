# Tasks — NUC-01 · Criar o ambiente da API e do banco e responder a saúde da API

**Plan:** planos/NUC-01/plan.md · **Ficha:** features/NUC-01.json
**Ordem:** T1 → revisão humana dos testes → commit só-de-testes (hash `7c567ee`) → T2 em diante (sessão nova, sem editar `tests/`)
**Antes da T1:** pergunta 12 respondida em 23/11 (corpo `{"api": "up", "database": "connected"}`). D1 (Testcontainers pelo proxy, decidida pelo humano em 23/11), D4, D5 e D7 confirmadas em 23/11.
**Antes da T2:** pergunta 11 respondida em 23/11 (opção C: proxy do socket no perfil `dev`). D2, D3 e D6 confirmadas em 23/11. Os itens "a conferir na T2" do plan são critérios de aceite da T2.
**Antes da T7:** o humano aplica na ficha as mudanças sugeridas no plan (rota e corpo da saúde; os nomes de teste ficam os da ficha).

---

## [x] T1 · Escrever os testes dos critérios
- **Critérios da ficha:** c1, c2, c3, c4, c5, c6
- **Regra de negócio (em linguagem simples):** antes de qualquer tela, o time precisa de uma API que sobe com um comando, sabe dizer se o banco está vivo e conecta com um usuário que não pode mexer na estrutura do banco. Os testes provam isso sem depender da máquina de quem roda.
- **Critérios de aceite:**
  - [x] `tests/core/test_ambiente.py`:
    - `test_compose_define_api_e_banco_com_versoes_decididas`: lê `docker-compose.yml` e `Dockerfile`; `api` vem de `python:3.14-*` (estágio `runtime`); `db` usa `postgres:18*`; `DATABASE_URL` só chega por variável, sem senha literal; sem perfil, o `up` sobe exatamente `api` e `db`; `dev` e `docker-proxy` estão no perfil `dev`; só o `docker-proxy` monta `/var/run/docker.sock` e não publica porta; o `dev` recebe `DOCKER_HOST` apontando para o proxy.
    - `test_esqueleto_da_api_tem_pontos_de_extensao_fixos`: importa `lastro.core.config`, `lastro.core.db` e `lastro.api.app` sem abrir conexão; registra uma rota de teste em `/api/v1/<path>` e ela responde.
    - `test_ambiente_de_verificacao_tem_python_e_banco_decididos`: Python 3.14; o container do Testcontainers responde `server_version_num` 18xxxx.
  - [x] `tests/core/test_saude.py`:
    - `test_saude_com_banco_conectado_responde_ok`: 200, corpo exatamente `{"api": "up", "database": "connected"}`, sem login.
    - `test_saude_sem_banco_responde_indisponivel`: 503, `application/problem+json`, `detail` igual à mensagem da ficha; corpo sem host, usuário, senha nem traceback.
  - [x] `tests/core/test_migracoes.py`:
    - `test_migracoes_em_banco_vazio_chegam_a_ultima_versao`
    - `test_migracoes_reaplicadas_nao_mudam_nada`
    - `test_usuario_da_aplicacao_nao_e_superusuario_nem_dono`: sem `rolsuper` e sem `rolbypassrls`; lê e grava em tabela do dono; `CREATE TABLE` e `DROP TABLE` dão erro de permissão.
  - [x] `tests/core/conftest.py`: fixture de sessão com `PostgresContainer("postgres:18", …)`, que roda `migrations/bootstrap/create_roles.sql` e define senhas geradas na hora; cada teste de migração cria um banco novo com nome aleatório e dono `lastro_owner`; no fim da sessão, para e remove o container (o Ryuk fica desligado, D1).
  - [x] Sem proxy, sem Docker ou sem banco, o teste falha com mensagem clara que cita o `docker-proxy`; nenhum `skip`.
  - [x] Todos falham hoje pelo motivo certo (módulos, dependências e migrações ausentes).
- **Exemplos:** banco no ar → `{"api": "up", "database": "connected"}`; `DATABASE_URL` apontando para porta fechada → 503 com "O banco de dados não está respondendo. Tente de novo em alguns minutos."; rota de teste `/api/v1/test-echo` → 200
- **Arquivos:** `tests/core/test_ambiente.py`, `tests/core/test_saude.py`, `tests/core/test_migracoes.py`, `tests/core/conftest.py`; apagar `tests/core/.gitkeep`
- **Reaproveitar:** leitura de YAML de `tests/ci/test_pr_workflow.py` · **Não criar:** fixture com dado de negócio, senha fixa
- **Fora do escopo:** código de produção, `create_roles.sql` (vem na T2)
- **Decisões relacionadas:** D1, D4, D5, D7
- **Pronto quando:** `docker compose run --rm dev pytest tests/core -q` mostra só falhas esperadas (com a imagem atual: falham por import)

## [ ] T2 · Imagem com uv, Compose com proxy do Docker, `.env.example` e papéis do banco
- **Critérios da ficha:** c1, c6
- **Regra de negócio (em linguagem simples):** qualquer pessoa do time clona, copia o `.env.example` e sobe tudo; as versões das bibliotecas são as mesmas em toda máquina; os testes criam sozinhos um banco limpo a cada rodada.
- **Critérios de aceite:**
  - [ ] `pyproject.toml` com `[project]` (Python 3.14, dependências da D3) e `[dependency-groups]` `dev`; `uv.lock` gerado e versionado; o `[tool.ruff]` existente é mantido
  - [ ] `Dockerfile` em estágios: base `python:3.14-slim` (tag exata), uv de `ghcr.io/astral-sh/uv:<versão fixa>`, `dev` com `uv sync --locked`, `runtime` com `--no-dev`; ambiente virtual fora de `/app`, no `PATH`. Nomes das variáveis do uv conferidos em https://docs.astral.sh/uv/reference/environment/
  - [ ] `docker-compose.yml`: `api` (estágio `runtime`, porta 8000, healthcheck em `/api/v1/health` com Python, sem `curl`); `db` (`postgres:18`, volume em `/var/lib/postgresql`, healthcheck `pg_isready`); `dev` (estágio `dev`, perfil `dev`, mesmo nome e `working_dir`, `depends_on: docker-proxy`, `DOCKER_HOST=tcp://docker-proxy:2375`, `TESTCONTAINERS_RYUK_DISABLED=true`, **sem** socket montado)
  - [ ] `docker-proxy`: `tecnativa/docker-socket-proxy:v0.5.0` com o digest `sha256` anotado, perfil `dev`, `privileged`, **único** serviço que monta `/var/run/docker.sock`, sem `ports`; libera `POST`, `CONTAINERS`, `ALLOW_START`, `ALLOW_STOP`, `IMAGES`, `NETWORKS` e `INFO` (D1), e nada além do que o Testcontainers usar
  - [ ] A conferir (D1), registrado no `progress`, em Linux nativo, Docker Desktop e CI: (a) como o proxy trata `DELETE` e se o Testcontainers precisa de `EXEC`; (b) se o `stop()` remove o container com o Ryuk desligado; se não remove, a fixture remove e apaga as sobras no início da sessão. Religar o Ryuk só com aval do humano; (c) se o host padrão ("gateway IP") alcança a porta do Postgres a partir do `dev`; se não alcança, fixar `TESTCONTAINERS_HOST_OVERRIDE` no Compose com um valor que sirva aos três (ex.: `host.docker.internal` + `extra_hosts` com `host-gateway`, a conferir)
  - [ ] A conferir (D6): a tag exata do uv e o `UV_PROJECT_ENVIRONMENT` em https://docs.astral.sh/uv/reference/environment/; a wheel cp314 do `psycopg-binary` para Linux (se faltar, `libpq5`)
  - [ ] `migrations/bootstrap/create_roles.sql` (idempotente, sem senha) e `create_roles.sh` (initdb do `db`: roda o SQL, aplica `OWNER_DB_PASSWORD` e `APP_DB_PASSWORD`, passa o banco para `lastro_owner`)
  - [ ] `.env.example` com `POSTGRES_*`, `OWNER_DB_PASSWORD`, `APP_DB_PASSWORD`, `DATABASE_URL`, `MIGRATIONS_DATABASE_URL`, valores contendo `exemplo`
  - [ ] `requirements-dev.txt` removido
  - [ ] `docker compose config --services` sem perfil lista só `api` e `db`
  - [ ] `tests/harness` e `tests/ci` continuam verdes no 3.14 com uv
  - [ ] Com o testcontainers instalado, os 4 testes que hoje dão ERROR na fixture passam a falhar pelo motivo da T5 (alembic.ini ausente), não por erro de montagem
- **Exemplos:** clone limpo, sem `.env` → `hx verify` funciona (o banco de teste vem do Testcontainers); `.env` copiado → `docker compose up -d --wait` termina com `api` e `db` saudáveis; lock desatualizado → o build falha no `uv sync --locked`
- **Arquivos:** `pyproject.toml`, `uv.lock`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `migrations/bootstrap/create_roles.sql`, `migrations/bootstrap/create_roles.sh`; remove `requirements-dev.txt` (o `pr.yml` não muda)
- **Reaproveitar:** serviço `dev` atual (nome e `working_dir`) · **Não criar:** segundo Dockerfile, `requirements*.txt`, mudança em `tools/`
- **Fora do escopo:** SeaweedFS, worker, imagem de produção final (hospedagem)
- **Decisões relacionadas:** D1, D2, D3, D5, D6, D7
- **Pronto quando:** `pytest tests/core/test_ambiente.py::test_compose_define_api_e_banco_com_versoes_decididas -q` e `pytest tests/core/test_ambiente.py::test_ambiente_de_verificacao_tem_python_e_banco_decididos -q` passam no `dev`

## [ ] T3 · Configuração e sessão do banco em `core/`
- **Critérios da ficha:** c2
- **Regra de negócio (em linguagem simples):** um só lugar lê a configuração do ambiente e abre a conexão; as outras fichas só importam. Importar não pode conectar, senão a API cai ao iniciar sem banco.
- **Critérios de aceite:**
  - [ ] `src/lastro/core/config.py`: classe `Settings` com `database_url` e `migrations_database_url` lidas do ambiente; função `get_settings()` (sem estado global mutável)
  - [ ] `src/lastro/core/db.py`: motor async e `async_sessionmaker` criados sob demanda; dependência que entrega uma sessão por requisição; `is_database_reachable()` com `connect_timeout` curto
  - [ ] Importar os dois módulos sem `DATABASE_URL` não falha nem conecta
  - [ ] A URL nunca aparece em log nem em mensagem de erro
- **Exemplos:** `DATABASE_URL=postgresql+psycopg://lastro_app:…@db/lastro` → sessão abre; host inexistente → `is_database_reachable()` devolve `False` em poucos segundos, sem exceção vazando
- **Arquivos:** `src/lastro/core/config.py`, `src/lastro/core/db.py`
- **Não criar:** contexto de RLS e permissões (NUC-03/ACE)
- **Fora do escopo:** login, sessão de usuário
- **Decisões relacionadas:** D3, D7
- **Pronto quando:** a parte de import de `test_esqueleto_da_api_tem_pontos_de_extensao_fixos` passa

## [ ] T4 · `create_app()` e rota de saúde em `api/`
- **Critérios da ficha:** c2, c3, c4
- **Regra de negócio (em linguagem simples):** a rota de saúde diz a quem opera o sistema se a API e o banco estão vivos, sem login e sem revelar nada interno. Banco fora do ar vira mensagem simples: o que aconteceu + o que fazer.
- **Critérios de aceite:**
  - [ ] `src/lastro/api/app.py` com `create_app(settings=None)` e um roteador `/api/v1` onde as fichas registram rotas
  - [ ] `GET /api/v1/health` em `src/lastro/api/routes.py`, fina, chamando `is_database_reachable()`
  - [ ] 200 com `{"api": "up", "database": "connected"}`; banco fora → 503 `application/problem+json` com `detail` da ficha (em português)
  - [ ] Nenhum traceback em resposta de erro
- **Exemplos:** banco no ar → 200; porta fechada → 503; rota de teste `/api/v1/test-echo` → 200
- **Arquivos:** `src/lastro/api/app.py`, `src/lastro/api/routes.py`
- **Não criar:** autenticação, CORS, middleware de sessão
- **Fora do escopo:** tratador global RFC 9457 para todas as rotas (só o da saúde)
- **Decisões relacionadas:** D4
- **Pronto quando:** `pytest tests/core/test_ambiente.py::test_esqueleto_da_api_tem_pontos_de_extensao_fixos -q` e `pytest tests/core/test_saude.py -q` passam

## [ ] T5 · Alembic e migração base de permissões
- **Critérios da ficha:** c5
- **Regra de negócio (em linguagem simples):** o esquema do banco evolui por migrações versionadas, rodadas pelo dono. A aplicação só lê e grava: se for invadida, não consegue apagar tabelas nem fugir do isolamento por escritório (RLS, que vem depois).
- **Critérios de aceite:**
  - [ ] `alembic.ini` sem URL; `migrations/env.py` (async) lê `migrations_database_url` de `core/config.py`
  - [ ] `migrations/versions/0001_base_privileges.py` com as permissões da D8 e `downgrade` que as desfaz
  - [ ] Duas execuções seguidas de `alembic upgrade head`: a segunda não aplica nada e a versão não muda
  - [ ] O comando da `api` no Compose roda `alembic upgrade head` antes do Uvicorn (resposta 3)
- **Exemplos:** banco novo → versão `0001`; de novo → `0001`, nada aplicado; `lastro_app` faz `CREATE TABLE x` → permissão negada
- **Arquivos:** `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`, `migrations/versions/0001_base_privileges.py`, `docker-compose.yml` (comando da `api`); apagar `migrations/.gitkeep`
- **Não criar:** tabela de negócio, extensão `pg_trgm`
- **Decisões relacionadas:** D5, D7, D8
- **Pronto quando:** `pytest tests/core/test_migracoes.py -q` passa

## [ ] T6 · Conferência manual da c1 e documentação
- **Critérios da ficha:** c1 (parte que o teste não prova)
- **Regra de negócio (em linguagem simples):** o teste lê o arquivo; só subir de verdade prova que sobe.
- **Critérios de aceite:**
  - [ ] Num clone limpo: `cp .env.example .env` e `docker compose up -d --wait` → `api` e `db` saudáveis; `curl localhost:8000/api/v1/health` → 200; resultado em "Rodei" do `progress/NUC-01.md`
  - [ ] README: seção curta "Subir o ambiente" e a tabela de arquivos atualizada (`pyproject.toml`/`uv.lock` no lugar de `requirements-dev.txt`)
  - [ ] Texto da emenda para `DECISIONS.md` (uv, perfil `dev`, proxy do Docker como único a montar o socket) entregue ao humano, que aplica
- **Arquivos:** `README.md`, `progress/NUC-01.md`
- **Fora do escopo:** editar ficha, AGENTS.md, ARCHITECTURE.md ou DECISIONS.md (resposta 6; sugestões no plan)
- **Decisões relacionadas:** D6
- **Pronto quando:** os comandos acima rodaram e o resultado está no `progress`

## [ ] T7 · Verificação final
- **Critérios de aceite:**
  - [ ] A ficha já traz a rota e o corpo da saúde do plan (PR do humano); os nomes de teste ficam os da ficha
  - [ ] `git diff 7c567ee -- tests/` vazio
  - [ ] `ruff check .` limpo
  - [ ] `hx check-clean` e `hx verify` em OK; tempo do `hx verify` anotado no `progress` (risco de CI lenta)
  - [ ] `hx feature verify NUC-01` grava `passing`
- **Pronto quando:** os três comandos do `hx` terminam com código 0
