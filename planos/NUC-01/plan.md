# Plan — NUC-01 · Criar o ambiente da API e do banco e responder a saúde da API

**Status:** aprovado — perguntas 1–12 respondidas e D1–D8 confirmadas em 23/11; os itens "a conferir na T2" são critério de aceite da T2
**Branch:** feat/NUC-01-criar-o-ambiente-da-api-e-do-banco-e-res · **Data:** 22/11/2026 (revisões 23/11) · **Responsável:** camposs04
**Tasks:** planos/NUC-01/tasks.md

## 1. A decidir (humano)
| # | Pergunta | Gravidade | Resposta | Decide |
|---|---|---|---|---|
| 1 | Banco de teste: Testcontainers (stack, BD-07) ou serviço do Compose? | BLOQUEANTE | **Respondida 23/11:** Testcontainers; risco de acesso ao Docker do host aceito; c6 continua valendo (D1). Ajustada pela 11: o socket fica só no proxy | camposs04 |
| 2 | "Dois serviços" (c1) contra o `dev` do `hx` | ATENÇÃO | **Respondida 23/11:** serviços de verificação em perfil; o `up` sobe só `api` e `db` (D2) | camposs04 |
| 3 | Quem aplica as migrações ao subir | ATENÇÃO | **Respondida 23/11:** no dev, a `api` roda `alembic upgrade head` com o papel dono e depois sobe; rever na hospedagem | camposs04 |
| 4 | "Sem superusuário" (c5) | ATENÇÃO | **Respondida 23/11:** nenhum dos dois papéis é superusuário; o superusuário só cria os papéis na inicialização | camposs04 |
| 5 | Lugar do script de papéis | ATENÇÃO | **Respondida 23/11:** dentro de `migrations/` (D5) | camposs04 |
| 6 | Python 3.12 na regra 12 do AGENTS.md e na §10 do ARCHITECTURE | ATENÇÃO | **Respondida 23/11:** esta ficha troca a imagem para 3.14; os docs vão num PR separado | camposs04 |
| 7 | Gestão de dependências | ATENÇÃO | **Respondida 23/11:** a opção mais sustentável; ficou uv + lockfile + build em estágios (D6) | camposs04 |
| 8 | Nomes em português da ficha contra o CODING_STANDARDS | ATENÇÃO | **Respondida 23/11:** seguir o CODING_STANDARDS (inglês; `test_<module>_<topic>.py`). **Revista 23/11:** arquivos e nomes de teste ficam os da ficha; a troca para o inglês vai para a ficha de renomeação (CODING_STANDARDS §8) | camposs04 |
| 9 | c1 só verificável de forma estática | ATENÇÃO | **Respondida 23/11:** teste do YAML + conferência manual na T6, no `progress` | camposs04 |
| 10 | Feature grande | ATENÇÃO | **Respondida 23/11:** manter; se passar de 2 sessões, separar a c5 numa `NUC-01b` | camposs04 |
| 11 | Como o `dev` (com `--user uid:gid`) acessa o Docker sem configuração manual e sem mudar `tools/` | BLOQUEANTE | **Respondida 23/11:** opção C: um proxy do socket no perfil `dev`; o `dev` usa `DOCKER_HOST` pela rede interna; só o proxy monta o socket (D1, D2) | camposs04 |
| 12 | Valores do corpo da saúde | BLOQUEANTE | **Respondida 23/11:** `{"api": "up", "database": "connected"}` | camposs04 |

**Mudanças sugeridas na ficha** (o humano aplica em PR; o `hx feature verify` usa os comandos da ficha, então isto precisa entrar antes da T7):
- c1: "o `docker compose up` sobe dois serviços (`api` e `db`); os serviços de verificação (`dev` e o proxy do Docker) ficam no perfil `dev`".
- c2: `create_app()` no lugar de `criar_app()`; na lista de arquivos de ambiente, trocar `requirements-dev.txt` por `pyproject.toml` e `uv.lock` (D6); `migrations/bootstrap/` explícito.
- c3: rota `/api/v1/health`; corpo `{"api": "up", "database": "connected"}`. c4: rota `/api/v1/health`; 503 em `application/problem+json` com a mensagem (em português, igual à ficha) em `detail` (D4).
- c5 e c6: o banco de teste é um PostgreSQL 18 criado pelo Testcontainers (imagem oficial), alcançado por um proxy do Docker.

## 2. Decisões tomadas pelo agente
### D1 · Banco de teste pelo Testcontainers; o `dev` fala com o Docker por um proxy — **decidida pelo humano em 23/11** (respostas 1 e 11)
- **Testcontainers:** `testcontainers[postgres]` no grupo dev (Apache-2.0, Python ≥3.10, classificadores até 3.14, v4.15.0 de 24/07/2026). Uso: `PostgresContainer("postgres:18", username=…, password=…, dbname=…, driver=None)` em fixture de sessão; cada teste de migração cria um banco novo nele. Senhas geradas na hora, sem segredo em arquivo.
- **Proxy:** serviço `docker-proxy` com `tecnativa/docker-socket-proxy:v0.5.0` (Apache-2.0). Só ele monta `/var/run/docker.sock`, sem porta publicada no host. O README exige `privileged` porque o proxy fala com o socket. O `dev` recebe `DOCKER_HOST=tcp://docker-proxy:2375` (porta do exemplo do README). A tag `v0.5.0` está no Docker Hub; a v0.6.0 (GitHub) deixou de publicar tags de versão e recomenda `lts`/`latest`, que são móveis. Por isso: `v0.5.0` e o digest `sha256` anotado na T2.
- **Permissões do proxy** (nomes do README; todas `0` por padrão, salvo `EVENTS`, `PING` e `VERSION`): `POST=1` (sem ele só há `GET`/`HEAD`), `CONTAINERS=1` (criar, inspecionar, logs, listar), `ALLOW_START=1`, `ALLOW_STOP=1`, `IMAGES=1` (baixar imagem), `NETWORKS=1`, `INFO=1`. **A conferir na T2:** como o proxy trata `DELETE` (remover container; o README não cita a variável) e se o Testcontainers usa `EXEC` na espera do Postgres. Liberar só o que a T2 mostrar necessário.
- **Ryuk:** a documentação não diz o que ele faz com `DOCKER_HOST` em TCP. O que ela confirma: o Ryuk é um container que monta o socket do host do daemon (`TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE`, padrão `/var/run/docker.sock`) e ouve numa porta TCP (`RYUK_PORT`, padrão 8080). Ligado, ele montaria o socket fora do proxy, o que contraria a resposta 11. **Escolha:** `TESTCONTAINERS_RYUK_DISABLED=true`, e a fixture para e remove o container no fim da sessão (`with`/`finally`). **A conferir na T2:** se o `stop()` remove o container com o Ryuk desligado. Se não remover, há duas saídas: (a) a fixture remove explicitamente e, no início da sessão, apaga sobras da execução anterior; (b) religar o Ryuk. A (b) põe o socket em outro container e precisa de aval do humano antes.
- **Alcance de rede:** a biblioteca procura o container "via gateway IP" e aceita `TESTCONTAINERS_HOST_OVERRIDE`. A porta do Postgres fica publicada no host do daemon, não no proxy. **A conferir na T2**, nos três ambientes: se o padrão alcança a porta a partir do `dev`. Se não alcançar, fixar no Compose um valor que sirva aos três (ex.: `host.docker.internal`, que no Linux depende de `extra_hosts` com `host-gateway`, também a conferir).
- **Sem configuração manual:** tudo fica no `docker-compose.yml`, sem número de grupo nem `.env`. A expectativa é funcionar em Linux nativo, Docker Desktop e CI; o alcance de rede e o Ryuk ficam **a conferir na T2** nos três.
- **CI (`pr.yml`):** não muda. O runner `ubuntu-latest` tem Docker; o `docker compose run dev` sobe o proxy junto. A CI baixa o proxy e `postgres:18` a cada execução.
- **Desvios encontrados na T2 (23/11, conferidos só em Linux nativo; Docker Desktop e CI ainda a conferir):**
  - **`EXEC=1` no proxy.** O `PostgresContainer` do testcontainers 4.15 espera o banco rodando `psql` *dentro* do container (`POST /containers/{id}/exec` e depois `POST /exec/{id}/start`). Com `EXEC=0`, o proxy devolve 403 em `/exec/{id}/start` e o `start()` estoura o tempo. **Poder a mais:** quem alcança o proxy pode rodar comando em **qualquer** container do host, não só no do teste. Isso inclui os do Compose, como o `db` com as senhas no ambiente. O proxy não restringe por container. Mitigação: a mesma do risco do proxy (sem porta no host, só o `dev` na rede dele, nunca rodar código de terceiros no `dev`).
  - **`DELETE`** não tem variável própria no proxy. O `haproxy.cfg` da imagem barra todo método fora do GET sem `POST=1`, e depois decide pelo caminho. `DELETE /containers/{id}` passa com `POST=1` + `CONTAINERS=1`, sem liberação extra.
  - **`TESTCONTAINERS_HOST_OVERRIDE=host.docker.internal` + `extra_hosts: host.docker.internal:host-gateway` no `dev`.** Com `DOCKER_HOST=tcp://docker-proxy:2375`, o Testcontainers usava o nome do proxy como host do banco, e a conexão foi recusada (a porta não está lá). Com o override, o banco de teste é alcançado pela **porta que o Docker publica no host** (porta alta aleatória, em todas as interfaces do host, durante a sessão de testes).
  - **Ryuk desligado (`TESTCONTAINERS_RYUK_DISABLED=true`), mantido.** O `stop()` remove o container quando o start dá certo (conferido). Quando a subida ou a espera falham, a fixture agora remove o container no `finally` (commit `59452ed`, conferido com um proxy sem `EXEC`). Fica de fora: processo morto à força (kill -9, CI cancelada), que deixa o container de pé.
- **Fontes:** https://github.com/Tecnativa/docker-socket-proxy (README, LICENSE.txt, releases) · https://hub.docker.com/r/tecnativa/docker-socket-proxy/tags · https://github.com/testcontainers/moby-ryuk · https://testcontainers-python.readthedocs.io/en/latest/ · https://testcontainers-python.readthedocs.io/en/latest/modules/postgres/README.html · https://pypi.org/project/testcontainers/ (acesso em 23/11)
- **Impacto:** T1, T2, T5 · c3, c5, c6
- [x] decidida pelo humano em 23/11

### D2 · Perfis do Compose: `api` e `db` sem perfil; `dev` e `docker-proxy` no perfil `dev`
- **Alternativas:** A) perfil · B) dois arquivos de Compose · C) quatro serviços no `up`
- **Escolhida:** A. Citar o `dev` no `docker compose run` ativa o perfil dele. O `dev` depende do `docker-proxy`, que está no mesmo perfil: dependência em perfil diferente invalida o modelo. O `dev` não depende de `db`. O `tools/` não muda. O `--rm` do `hx` remove só o `dev`; o proxy fica de pé até `docker compose --profile dev down`.
- **Fontes:** https://docs.docker.com/compose/how-tos/profiles/ · https://docs.docker.com/reference/compose-file/services/ (acesso em 22 e 23/11)
- **Impacto:** T2 · c1, c6
- [x] confirmada em 23/11

### D3 · Bibliotecas: FastAPI, Pydantic 2 + `pydantic-settings`, SQLAlchemy 2 async + `psycopg[binary]` 3, Alembic, Uvicorn; no grupo dev: `httpx` (TestClient), `testcontainers[postgres]`, `pytest`, `ruff`, `pyyaml`
- **Alternativas (configuração):** A) `pydantic-settings` · B) `os.environ` + dataclass · C) `environs`. **(ASGI):** A) Uvicorn · B) Hypercorn · C) Granian
- **Escolhida:** A e A: validação com o Pydantic 2 já decidido; Uvicorn é o padrão do FastAPI. Testes síncronos, sem `pytest-asyncio`. O `testcontainers` não traz driver, então o `psycopg` entra explícito.
- **Fontes:** https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/ · https://fastapi.tiangolo.com/deployment/manually/ · https://pypi.org/project/psycopg-binary · `stack.md` (acesso em 22 e 23/11)
- **Impacto:** T2–T5 · c2–c6
- [x] confirmada em 23/11

### D4 · Erro 503 em RFC 9457 (`application/problem+json`), mensagem da ficha em `detail`
- **Alternativas:** A) problem+json (`type`, `title`, `status`, `detail`) · B) `{"message": …}`
- **Escolhida:** A (I-14). As chaves seguem a RFC; o `detail` leva o texto em português, igual ao da ficha.
- **Impacto:** T1, T4 · c4
- [x] confirmada em 23/11

### D5 · Papéis `lastro_owner` e `lastro_app` num SQL único, `migrations/bootstrap/create_roles.sql`
- **Como fica:** SQL puro e idempotente, sem senha e sem `SUPERUSER`, `CREATEDB`, `CREATEROLE` nem `BYPASSRLS`. No `db`, o `migrations/bootstrap/create_roles.sh` (em `/docker-entrypoint-initdb.d`) roda o SQL, define as senhas com `OWNER_DB_PASSWORD` e `APP_DB_PASSWORD` do `.env` e passa o banco para `lastro_owner`. No teste, a fixture roda o **mesmo** SQL como superusuário do container, define senhas aleatórias e cria cada banco com `OWNER lastro_owner`.
- **Alternativas:** A) SQL compartilhado + script fino · B) a primeira migração cria o papel (o dono precisaria de `CREATEROLE`) · C) montar o script no container do Testcontainers (o caminho precisaria existir no host do daemon)
- **Impacto:** T1, T2, T5 · c5
- [x] confirmada em 23/11

### D6 · Dependências com `uv`: `pyproject.toml` + `uv.lock` + grupo `dev`, e Dockerfile em estágios (`dev` e `runtime`)
- **Alternativas:**
  - A) `pip` + `requirements*.txt` com `==`: as dependências transitivas só ficam travadas com `pip freeze` ou pip-tools, e o hash é tudo ou nada.
  - B) `uv` + `uv.lock` com grupos (PEP 735): `uv sync --locked` falha com o lock desatualizado e `--no-dev` tira o grupo dev; é a ferramenta da stack.
  - C) build em estágios (complementa A ou B).
- **Escolhida:** B + C: trava tudo sem ferramenta extra e separa dev de produção no mesmo arquivo.
- **O que muda:**
  - **Dockerfile:** `python:3.14-slim`; uv de `ghcr.io/astral-sh/uv:<versão fixa>`; estágio `dev` com `uv sync --locked` e estágio `runtime` com `--no-dev`; ambiente virtual fora de `/app` (o `dev` monta `.:/app`), via `UV_PROJECT_ENVIRONMENT`, com o `bin` no `PATH`; `--no-install-project` + `PYTHONPATH=/app/src`.
  - **Compose:** a `api` usa o `runtime` e o `dev` usa o `dev`.
  - **`hx verify`:** o comando não muda; a imagem precisa de rebuild quando o lock muda.
  - **c2:** sai `requirements-dev.txt`, entram `pyproject.toml` e `uv.lock`.
  - **README:** muda na T6.
- **A conferir na T2:** a tag exata do uv e o `UV_PROJECT_ENVIRONMENT` em https://docs.astral.sh/uv/reference/environment/.
- **Fontes:** https://docs.astral.sh/uv/guides/integration/docker/ · https://docs.astral.sh/uv/concepts/projects/dependencies/ · https://docs.astral.sh/uv/concepts/projects/sync/ · https://pip.pypa.io/en/stable/topics/repeatable-installs/ · https://pip.pypa.io/en/stable/topics/secure-installs/ (acesso em 23/11)
- **Impacto:** T2, T6 · c1, c2
- [x] confirmada em 23/11

### D7 · Duas URLs: `DATABASE_URL` (aplicação) e `MIGRATIONS_DATABASE_URL` (dono, só para o Alembic); campos `database_url` e `migrations_database_url`
- **Alternativas:** A) duas variáveis · B) uma só (quebra a c5)
- **Impacto:** T2, T3, T5 · c1, c5
- [x] confirmada em 23/11

### D8 · Migração base `0001_base_privileges` só com permissões
- **Conteúdo:** `ALTER DEFAULT PRIVILEGES FOR ROLE lastro_owner` com SELECT, INSERT, UPDATE, DELETE em tabelas e USAGE em sequências para `lastro_app`, e `USAGE` no schema. Nenhuma tabela de negócio. Reaplicar não muda nada.
- **Alternativas:** A) permissões · B) migração vazia (não prova a c5) · C) `pg_trgm` já (fica para a ficha que usar)
- **Impacto:** T5 · c5
- [x] confirmada em 23/11

## 3. Resumo e abordagem
Esqueleto de ponta a ponta: Compose com `api` (Python 3.14) e `db` (PostgreSQL 18); `dev` e `docker-proxy` em perfil; o Testcontainers cria o banco de teste pelo proxy. Configuração e sessão em `core/`, `create_app()` com `/api/v1/health` em `api/`, Alembic com dois papéis e dependências travadas pelo `uv.lock`.
Ordem: T1 testes → T2 imagem, uv, Compose, proxy, `.env.example` e papéis → T3 `core/` → T4 `api/` e saúde → T5 Alembic → T6 conferência manual da c1 e docs → T7 verificação.

## 4. Contexto encontrado
- **Código relacionado:** `src/lastro/core/__init__.py`, `src/lastro/api/__init__.py` (vazios); `migrations/.gitkeep`; `tests/core/.gitkeep`.
- **Harness:** `montar_comando_docker` roda `docker compose run --rm -T --user uid:gid dev <cmd>`; `hx verify` roda `ruff check .` e `pytest -q` em todos os testes. Não mexer em `tools/`.
- **CI:** `.github/workflows/pr.yml` roda `sh tools/hx verify` e `sh tools/hx check-clean` em `ubuntu-latest`, `contents: read`.
- **check-clean:** `_SEGREDO` acusa `password|senha|secret…=` com 16+ caracteres, salvo valores com `exemplo`, `changeme` ou `xxx`.
- **Reaproveitar:** leitura de YAML de `tests/ci/test_pr_workflow.py`; `[tool.ruff]` do `pyproject.toml` (mantido).
- **Não criar:** módulo novo, `utils.py`, rota fora de `/api/v1`, tabela de negócio, login, `requirements*.txt`.
- **Pesquisa externa:** D1, D2, D3, D6; volume do PostgreSQL 18 em `/var/lib/postgresql` (https://hub.docker.com/_/postgres, https://github.com/docker-library/postgres/pull/1259, acesso em 22/11).

## 5. Decisões (já resolvidas)
- 18/11 · Python 3.14, PostgreSQL 18, FastAPI, SQLAlchemy 2 + Alembic (ARQ-01..08, BD-01..08).
- 23/11 · Respostas 1–12 (tabela da seção 1), por camposs04.

## 6. Avaliação da ficha
| # | Achado | Gravidade | Critério |
|---|---|---|---|
| 1 | Nomes, rota, corpo e arquivos de teste da ficha divergem do plano (respostas 8 e 12): a ficha precisa mudar antes da T7 | ATENÇÃO | c2–c6, `verificacao` |
| 2 | Lista de arquivos da c2 muda com a D6 | ATENÇÃO | c2 |
| 3 | c1 só estática no container; conferência manual na T6 | ATENÇÃO | c1 |
| 4 | "Banco recém-criado": banco novo por teste no container do Testcontainers | ATENÇÃO | c5 |
| 5 | "Sem pular teste" (c6): sem Docker, proxy ou banco, o teste **falha**; nunca `skip` | ATENÇÃO | c6 |
| 6 | Nenhum risco de dado real: só configuração e senhas de exemplo ou geradas | — | — |

## 7. Riscos
- O proxy libera criar e iniciar containers. Quem cria container com bind mount do host ainda tem muito poder sobre a máquina: o risco diminui, não some. Mitigação: liberar só as seções necessárias, sem porta no host, só imagens fixadas, nunca rodar `dev` com código de terceiros (risco aceito, respostas 1 e 11).
- `EXEC=1` no proxy (desvio da T2, D1): quem fala com o proxy roda comando em qualquer container do host, inclusive no `db` do Compose. Mitigação: a do item acima; rever se uma versão futura do Testcontainers esperar o Postgres sem `exec`.
- Banco de teste por porta publicada no host (desvio da T2, D1): durante a sessão de testes, o `postgres:18` descartável fica numa porta alta do host, em todas as interfaces, com senha aleatória gerada na hora e sem dado nenhum. Numa rede não confiável, outra máquina pode tentar conectar nesse intervalo. Mitigação: senha gerada por execução, container removido no fim; rever se a CI ou um dev rodar em rede aberta.
- Ryuk desligado (D1): um processo morto à força (kill -9, CI cancelada) deixa o `postgres:18` de pé. Limpeza manual: `docker ps -aq --filter ancestor=postgres:18 | xargs -r docker rm -f`. Na CI, o runner é descartado.
- Proxy fora do ar ou sem permissão (HTTP 403) → o teste falha com mensagem clara que cita o `docker-proxy`; nunca `skip`.
- Alcance de rede e Ryuk sem confirmação na documentação → a conferir na T2 nos três ambientes; saídas descritas na D1.
- Tags de versão do proxy descontinuadas a partir da v0.6.0 → `v0.5.0` + digest; rever na troca de versão.
- CI mais lenta: download do proxy e de `postgres:18` a cada `hx verify` → fixture de sessão (um container por execução); medir na T7.
- Wheel do `psycopg-binary` cp314 em Linux não confirmada → a T2 confere; se faltar, `libpq5` na imagem.
- Troca do `dev` para 3.14 e para uv pode quebrar `tests/harness` e `tests/ci` → critério de aceite da T2.

## 8. Aprovação
- [x] Perguntas BLOQUEANTES respondidas (1, 11 e 12, em 23/11)
- [x] Decisões do agente confirmadas (D1 decidida pelo humano; D2–D8 confirmadas em 23/11)
- [x] Plan e tasks revisados por camposs04 em 23/11
