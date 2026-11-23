# NUC-01 · Criar o ambiente da API e do banco e responder a saúde da API

- Responsável: camposs04 · Branch: `feat/NUC-01-criar-o-ambiente-da-api-e-do-banco-e-res` · Início: 22/11/2026
- Ficha: `features/NUC-01.json` (estado e critérios ficam lá; não repita aqui)

<!--
Como preencher (agente, ao encerrar a sessão):
- REESCREVA as seções do topo: Objetivo, Próxima ação, Bloqueios e perguntas.
- ACRESCENTE, sem apagar o que já existe, em Feito, Rodei, Falhou e Decisões.
  Cada linha começa com a data (DD/MM) e a sessão, ex.: "- 14/11 · S2 · ...".
- Registre só o que realmente rodou. Sem dado real, nome de cliente ou segredo.
- Não escreva estado (passing etc.) aqui: ele fica na ficha, gravado pelo script.
-->

## Objetivo
Um comando sobe a API (Python 3.14) e o PostgreSQL 18; `GET /api/v1/health` diz se o banco está conectado; o Alembic migra com o papel dono e a API conecta com um papel sem poder sobre o esquema.

## Próxima ação
Ficha atualizada (PR `docs/NUC-01-ficha`), emenda no `DECISIONS.md` (PR `docs/NUC-01-decisions`) e T7 feitas em 23/11; a ficha está `passing`. Falta:
1. Aprovar o PR `docs/NUC-01-ficha`; depois, na branch da feature, rodar `git merge origin/main`. Se a ficha mudou na revisão, refazer a T7 (`git diff cacb33a -- tests/`, `ruff check .`, `hx check-clean`, `hx verify`, `hx feature verify NUC-01`).
2. Aprovar o PR `docs/NUC-01-decisions` (BD-07 emenda, FER-01, Consequência e P-12).
3. Tirar o PR da feature do modo rascunho.

## Bloqueios e perguntas
Pendências fora desta ficha (não bloqueiam a NUC-01):
- **Docker Desktop não testado:** itens (a), (b) e (c) da D1. Linux nativo e CI já conferidos (CI: run `45119217554`, job `137508892873`). Importa só se alguém do time usar Mac ou Windows.
- **Varredura de nomes do `check-clean` desligada:** a variável `LASTRO_NOMES_PROIBIDOS` não está definida no local (o `check-clean` de 23/11 avisou "verificação de nomes pulada"). Na CI ela vem do segredo de mesmo nome e falta lá também, conferido no run 45119217554: o job check-clean anotou "Varredura de nomes pulada: o segredo não está disponível (PR de fork?)". Assunto do dono do harness.
- **PR de docs do Python 3.12:** a regra 12 do `AGENTS.md` e a §10 do `ARCHITECTURE.md` ainda citam 3.12 (resposta 6 do plan).
- **`privileged` do proxy:** tirar o `privileged: true` do `docker-proxy` se um teste nos três ambientes mostrar que ele é dispensável. O README do proxy diz que ele é necessário "em alguns contextos de SELinux/AppArmor", sem dizer quais.

Histórico dos bloqueios da implementação:
- 5 · Resolvido pelo commit só-de-testes `cacb33a` (cast `defaclobjtype::text`). Registro original: **SQL do teste de reaplicação inválido no PostgreSQL 18.** Em `test_migracoes_reaplicadas_nao_mudam_nada`, o `SNAPSHOT_SQL` concatena `text || ':' || defaclobjtype`. A coluna `pg_default_acl.defaclobjtype` é do tipo `"char"`, e o PostgreSQL 18.7 recusa com `operator is not unique: text || "char"`. Reproduzi num `postgres:18` vazio, sem nenhuma migração: o erro é da consulta, não da implementação. Com `defaclobjtype::text`, a consulta roda e, numa cópia de `tests/core` fora do repositório, os 3 testes de migração passam. Proposta: trocar só esse trecho para `defaclobjtype::text`, sem mudar valor esperado.
- 1, 2 e 3 (teste do esqueleto, alarmes do `check-clean`, sobra de container): resolvidos pelo commit só-de-testes `59452ed` do humano.
- 4 · Aviso de depreciação: `testcontainers.postgres is deprecated, use testcontainers.community.postgres` (4.15.0). Os testes importam o caminho antigo; hoje só avisa.

## Feito
- 23/11 · S2 (T2) · `pyproject.toml` com `[project]` (3.14, D3), grupo `dev` e `[tool.uv] package = false`; `uv.lock` (43 pacotes); `Dockerfile` em estágios `base`/`dev`/`runtime` com uv e o venv em `/opt/venv`; `docker-compose.yml` com `api`, `db`, `dev` e `docker-proxy` (perfis da D2); `.env.example`; `migrations/bootstrap/create_roles.sql` e `create_roles.sh`; `requirements-dev.txt` removido.
- 23/11 · S2 (T3) · `src/lastro/core/config.py` (`Settings`, `get_settings()`, URLs com `repr=False`) e `src/lastro/core/db.py` (`Database` preguiçoso, `is_database_reachable()`, dependências `get_database`/`get_session`).
- 23/11 · S2 (T4, incompleta) · `src/lastro/api/app.py` (`create_app()`, `API_V1_PREFIX`) e `src/lastro/api/routes.py` (`GET /health`, 503 em problem+json). Parou no bloqueio 1.
- 23/11 · S2 · Hash da referência dos testes trocado para `59452ed` em `tasks.md` (linha "Ordem" e critério da T7). Desvios da T2 registrados no `plan.md` (D1 e riscos): `EXEC=1`, `TESTCONTAINERS_HOST_OVERRIDE` + `host-gateway`, Ryuk desligado.
- 23/11 · S2 (T4) · Terminada: os 3 testes da T4 passam (esqueleto, saúde com banco, saúde sem banco).
- 23/11 · S2 (T5) · `alembic.ini` sem URL (`prepend_sys_path = src`); `migrations/env.py` async, que lê só `migrations_database_url` e falha com mensagem clara sem ela; `migrations/script.py.mako`; `migrations/versions/0001_base_privileges.py` (D8, com `downgrade`); comando da `api` no Compose `alembic upgrade head && exec uvicorn ...`; `COPY alembic.ini` no `runtime`; `migrations/.gitkeep` removido. Parou no bloqueio 5 (1 de 3 testes da T5).

## Rodei
- 23/11 · S1 (T1) · `docker compose run --rm -T dev pytest tests/core -q -rA` sobre os testes do commit `5e5c8c6`, imagem atual (Python 3.12, sem testcontainers). Linhas da NUC-01 (os 8 PASSED restantes são da NUC-02), igual em duas execuções seguidas:
  ```
  ERROR  test_migracoes.py::test_migracoes_em_banco_vazio_chegam_a_ultima_versao
  ERROR  test_migracoes.py::test_migracoes_reaplicadas_nao_mudam_nada
  ERROR  test_migracoes.py::test_usuario_da_aplicacao_nao_e_superusuario_nem_dono
  ERROR  test_saude.py::test_saude_com_banco_conectado_responde_ok
  FAILED test_ambiente.py::test_compose_define_api_e_banco_com_versoes_decididas
  FAILED test_ambiente.py::test_esqueleto_da_api_tem_pontos_de_extensao_fixos
  FAILED test_ambiente.py::test_ambiente_de_verificacao_tem_python_e_banco_decididos
  FAILED test_saude.py::test_saude_sem_banco_responde_indisponivel
  4 failed, 8 passed, 4 errors
  ```
  Motivos: os 4 ERROR vêm da montagem da fixture `postgres_server` ("'testcontainers.postgres' is missing from the dev image (plan D1)"), não da coleta; compose → "docker-compose.yml is missing the services ['api', 'db', 'docker-proxy']"; esqueleto → "missing src/lastro/core/config.py"; c6 → "dev container runs Python 3.12.15"; saúde sem banco → `ModuleNotFoundError: lastro.core.config`.
- 23/11 · S1 (T1) · Prova em container descartável, sobre uma cópia de `tests/core` numa pasta temporária fora do repositório, com um `create_roles.sql` provisório (cria `lastro_owner` e `lastro_app` com LOGIN) só nessa cópia:
  `docker run --rm --network host -v /var/run/docker.sock:/var/run/docker.sock -v <cópia>:/app -w /app -e TESTCONTAINERS_RYUK_DISABLED=true python:3.14-slim sh -c "pip install pytest pyyaml 'testcontainers[postgres]' 'psycopg[binary]' alembic fastapi httpx && pytest tests/core/test_ambiente.py tests/core/test_saude.py tests/core/test_migracoes.py -q -rA"`
  Bibliotecas instaladas: Python 3.14.10, pytest 9.2.0, PyYAML 6.0.4, testcontainers 4.15.0, psycopg 3.3.9 (+ psycopg-binary 3.3.9), alembic 1.20.1, fastapi 0.165.0, httpx 0.28.1. Resultado: 5 failed, 1 passed, 2 errors:
  - `test_compose_define_api_e_banco_com_versoes_decididas`: FAILED, serviços `api`, `db` e `docker-proxy` ausentes (T2)
  - `test_esqueleto_da_api_tem_pontos_de_extensao_fixos`: FAILED, "missing src/lastro/core/config.py" (T3)
  - `test_ambiente_de_verificacao_tem_python_e_banco_decididos`: PASSED (Python 3.14 e PostgreSQL 18 do Testcontainers)
  - `test_saude_com_banco_conectado_responde_ok`: ERROR na fixture `migrated_database`, `alembic upgrade head` saiu com 255 ("No 'script_location' key found in configuration", sem `alembic.ini`, T5)
  - `test_saude_sem_banco_responde_indisponivel`: FAILED, `ModuleNotFoundError: lastro` (sem `PYTHONPATH=/app/src` nesse container; na imagem `dev` o motivo é `lastro.core.config` ausente)
  - `test_migracoes_em_banco_vazio_chegam_a_ultima_versao` e `test_migracoes_reaplicadas_nao_mudam_nada`: FAILED, "missing alembic.ini (T5)"
  - `test_usuario_da_aplicacao_nao_e_superusuario_nem_dono`: ERROR na fixture `migrated_database`, mesmo motivo do alembic (T5)
  - A fixture subiu o `postgres:18`, rodou o SQL de papéis, definiu as senhas e criou e apagou os bancos; depois da sessão, `docker ps -a --filter ancestor=postgres:18` não listou nada (o `stop()` removeu o container com o Ryuk desligado).
  - Não cobriu: o caminho pelo `docker-proxy`. O container falou direto com o socket do Docker (`-v /var/run/docker.sock`) e com rede `host`; proxy, permissões dele e alcance da porta a partir do `dev` ficam para a T2 (itens "a conferir" da D1).
- 23/11 · S2 (T2) · Itens "a conferir", só em **Linux nativo** (Ubuntu 24.04, Docker 29.1.2, Compose 2.40.3):
  - Versões: `python:3.14-slim` = Python 3.14.10 trixie → `FROM python:3.14.10-slim-trixie`. uv: `ghcr.io/astral-sh/uv:0.13.9` (`uv --version` na imagem; é a versão dos exemplos fixados do guia Docker do uv), fixado com o digest `sha256:d3b601f0c7b118bc1753febf7c41cc80981df678445e0254284eecf84db79a7d`. Proxy `tecnativa/docker-socket-proxy:v0.5.0`, digest `sha256:1f5038b54f06c3e18422902cf00ba21803d1c97805aae032e5e6673d532d3459` (`docker image inspect`).
  - `UV_PROJECT_ENVIRONMENT`: a referência do uv diz "Specifies the path to the directory to use for a project virtual environment". Conferido no build: o venv ficou em `/opt/venv` e não existe `/app/.venv`; `which python pytest ruff` → `/opt/venv/bin/*`. O `runtime` importa fastapi, sqlalchemy, psycopg, alembic, uvicorn e pydantic_settings, não tem pytest e roda como `uid=10001(lastro)`.
  - `psycopg-binary` 3.3.9 tem wheel `cp314-cp314-manylinux2014_x86_64` no `uv.lock` (e o `greenlet` 3.5.6 também): não precisa de `libpq5`.
  - (a) `DELETE`: o proxy não tem variável própria. No `haproxy.cfg.template` da imagem, `http-request deny unless METH_GET || { env(POST) -m bool }`, depois a regra por caminho, então `DELETE /containers/{id}` passa com `POST=1` + `CONTAINERS=1`. `EXEC`: **precisa**. Com `EXEC=0`, o `start()` falhou em 120 s com `403 ... /exec/<id>/start: Forbidden`: o `PostgresContainer` 4.15 espera o banco rodando `psql` dentro do container. Liberei `EXEC: 1`.
  - (b) Com o Ryuk desligado, o `stop()` remove o container: depois de cada sessão bem-sucedida, `docker ps -aq --filter ancestor=postgres:18` → 0. Quando o `start()` falhou, sobrou um container (bloqueio 3), que removi à mão.
  - (c) Host padrão: **não alcança**. Com `DOCKER_HOST=tcp://docker-proxy:2375`, o Testcontainers está no modo `docker_host` e usa o nome do proxy: `connection to server at "172.19.0.2", port 32772 failed: Connection refused`. Com `TESTCONTAINERS_HOST_OVERRIDE: host.docker.internal` + `extra_hosts: host.docker.internal:host-gateway`, alcança (nome da variável conferido em `testcontainers/core/config.py`: `TC_HOST` ou `TESTCONTAINERS_HOST_OVERRIDE`).
  - **Não conferido:** Docker Desktop e CI (`ubuntu-latest`). Espero que funcione (o `host-gateway` vale nos dois), mas não rodei.
- 23/11 · S2 (T2) · `docker compose config --services` (sem perfil) → `db`, `api`. Sem `.env`, o Compose avisa 5 vezes "variable is not set. Defaulting to a blank string" e não falha. Testei `${VAR:?msg}` num Compose de teste: o `docker compose run` de **outro** serviço falha ("required variable ... is missing a value"), porque a interpolação vale para o arquivo inteiro. Por isso ficou `${VAR}` puro: o `hx verify` funciona sem `.env`, com esses avisos.
- 23/11 · S2 (T2) · Pronto quando: `docker compose run --rm -T --user uid:gid dev pytest tests/core/test_ambiente.py::test_compose_define_api_e_banco_com_versoes_decididas tests/core/test_ambiente.py::test_ambiente_de_verificacao_tem_python_e_banco_decididos -q` → `2 passed, 1 warning in 3.94s`. `pytest tests/harness tests/ci -q` no `dev` 3.14 → `289 passed`. Em `tests/core`, os ERROR da fixture passaram a ser `alembic upgrade head` com 255 ("No 'script_location' key found", T5), não montagem.
- 23/11 · S2 (T3) · No `dev`, sem nenhuma `*DATABASE_URL` no ambiente: `python -c "import lastro.core.config, lastro.core.db"` → ok. `is_database_reachable()` em porta fechada → `False` em 0,26 s; em host `.invalid` → `False` em 0,01 s; o log mostra só `database is not reachable (OperationalError)`. `repr(Settings(...))` → `Settings()`.
- 23/11 · S2 (T4) · `pytest tests/core/test_ambiente.py::test_esqueleto_da_api_tem_pontos_de_extensao_fixos tests/core/test_saude.py -q` → `test_saude_sem_banco_responde_indisponivel` PASSED; esqueleto FAILED no bloqueio 1 (as asserções antes dele passaram); `test_saude_com_banco_conectado_responde_ok` ERROR na fixture (alembic, T5).
- 23/11 · S2 · `sh tools/hx verify` → ruff `All checks passed!` (depois de corrigir um I001 em `db.py`); pytest `3 failed, 300 passed, 2 warnings, 2 errors` em ~13 s (15,8 s no total). Falham: esqueleto (bloqueio 1), as 2 migrações sem `alembic.ini` (T5) e 2 ERROR do alembic (T5).
- 23/11 · S2 · `sh tools/hx check-clean` → `RESULTADO: FALHOU`, com 6 achados, todos em `tests/core` (bloqueio 2). Os 2 achados de `create_roles.sh` (nome de variável do psql `owner_password=` + `$OWNER_DB_PASSWORD`) foram corrigidos trocando o nome para `owner_pw`/`app_pw`.
- 23/11 · S2 · `git diff 7c567ee -- tests/` → vazio (0 bytes).
- 23/11 · S2 (correções autorizadas em `tests/`, antes do `59452ed`) · `type(route)` em `app.routes` no FastAPI 0.165.0: 4 `starlette.routing.Route` e 2 `fastapi.routing._IncludedRouter` sem `.path`. `pytest tests/core -q -rA` → 12 passed, 2 failed, 2 errors (todos da T5). `hx check-clean` → 0 achados, OK. Prova do `finally`: proxy temporário sem `EXEC` + `TC_MAX_TRIES=3` → a fixture falhou com a mensagem do `docker-proxy` e sobraram 0 `postgres:18`.
- 23/11 · S2 (T5) · `pytest tests/core/test_migracoes.py -q -rA` → banco vazio PASSED, usuário da aplicação PASSED, reaplicação FAILED (`AmbiguousFunction: operator is not unique: text || "char"` no `SNAPSHOT_SQL`, bloqueio 5).
- 23/11 · S2 (T5) · `postgres:18` (18.7) vazio e descartável, via `psql`: a consulta do teste → mesmo erro; com `defaclobjtype::text` → roda (0 linhas).
- 23/11 · S2 (T5) · Cópia de `tests/core` fora do repositório, numa pasta temporária, só com o cast `::text`, montada no `dev` com `alembic.ini`, `migrations/` e `src/` em modo só leitura → `3 passed` em `test_migracoes.py`. Nenhum arquivo de `tests/` mudou.
- 23/11 · S2 (T5) · `docker compose build api` → Built; a imagem tem `alembic.ini`, `migrations` e `src`, e `alembic 1.20.1`.
- 23/11 · S2 · Fim: `sh tools/hx verify` → ruff `All checks passed!`; pytest `1 failed, 304 passed, 2 warnings` em 20,25 s (23,0 s no total), e a falha é só a do bloqueio 5. `sh tools/hx check-clean` → 0 achados, `RESULTADO: OK`. `git diff 59452ed -- tests/` → vazio (0 bytes). Sobraram 0 `postgres:18` depois das execuções.
- 23/11 · S2 (T6, rodado pelo humano e relatado ao agente) · Clone limpo do commit `1325dee`, projeto `lastro-t6`: `cp .env.example .env` → `docker compose up -d --wait` → `curl localhost:8000/api/v1/health`.
  - **1ª tentativa: falhou.** A porta 8000 estava ocupada por outro projeto (`django-api`). O Docker criou o `lastro-t6-api-1`, mas falhou ao ligá-lo à rede (`failed to set up container networking ... port is already allocated`). O `up` seguinte reaproveitou esse container sem rede (`Networks: {}`, `resolv.conf` do host).
  - **2ª tentativa: passou.** Depois de liberar a porta, `docker compose down -v` e `docker compose up -d --wait`: `db` e `api` healthy; a saúde respondeu `{"api":"up","database":"connected"}`. Isso confirma, de forma indireta, o `create_roles.sh` e o comando da `api`: a `api` conectou como `lastro_app` com a senha do `.env` e as migrações rodaram como `lastro_owner` antes do Uvicorn.
  - Consulta dos papéis: registrada na nova subida, com o healthcheck novo (entrada "pós-T6, rodado pelo humano" abaixo).
- 23/11 · S2 (pós-T6) · Healthcheck do `db` trocado para `pg_isready -h 127.0.0.1 -U ... -d ...`. Não rodei de novo o `up` com essa mudança; o teste estático do Compose roda no `hx verify` abaixo.
- 23/11 · S2 (pós-T6, rodado pelo humano e relatado ao agente) · Nova subida com o healthcheck `pg_isready -h 127.0.0.1`, a partir de uma cópia limpa da pasta de trabalho, sem o `.env` local: `db` Healthy (6,6 s), `api` Healthy (11,9 s); `GET /api/v1/health` → `{"api":"up","database":"connected"}`. Consulta dos papéis no `db` do Compose:
  ```
     rolname    | rolsuper | rolcreatedb | rolcreaterole | rolbypassrls
  --------------+----------+-------------+---------------+--------------
   lastro_owner | f        | f           | f             | f
   lastro_app   | f        | f           | f             | f
  ```
  Dono do banco: `lastro_owner`. Confirma o `create_roles.sh` rodando de verdade: os dois papéis criados, nenhum é superusuário nem tem `CREATEDB`, `CREATEROLE` ou `BYPASSRLS`, e o banco foi passado para `lastro_owner`.
- 23/11 · S2 (pós-T6) · `sh tools/hx verify` → `[1/2] ruff check . OK`, `[2/2] pytest -q OK`, `RESULTADO: OK` (exit 0, cerca de 26 s). `sh tools/hx check-clean` → 0 achados, `RESULTADO: OK`. `git diff cacb33a -- tests/` → vazio (0 bytes). Sobraram 0 `postgres:18`.
- 23/11 · S2 (CI, relatado pelo humano) · Run `45119217554`, job verify `137508892873` (`hx verify` do `pr.yml`, runner do GitHub): `[2/2] pytest -q OK` e `RESULTADO: OK`. O caminho Testcontainers + `docker-proxy` + `host-gateway` funcionou na CI. O trecho de log mostrado não traz linhas do Compose nem do proxy; a prova é o `tests/core` verde sem `skip`. A remoção do container não aparece no log.
- 23/11 · S3 (T7) · Ficha trazida por merge de `origin/docs/NUC-01-ficha` (commit de merge `859ac78`); **o PR dessa ficha ainda não foi aprovado**. Se o PR mudar antes de aprovar, a T7 precisa rodar de novo. Sobre o `859ac78`, sem mudança local fora da ficha:
  - `git diff cacb33a -- tests/` → vazio (0 bytes).
  - `ruff check .` (no container `dev`; o host não tem `ruff`) → `All checks passed!`, exit 0.
  - `sh tools/hx check-clean` → `AVISO: verificação de nomes pulada (variável não definida)`, 0 achados, `RESULTADO: OK`, exit 0.
  - `sh tools/hx verify` → `[1/2] ruff check . OK`, `[2/2] pytest -q OK`, Arquitetura e E2E `PULADO (ainda não implementado)`, `RESULTADO: OK`, exit 0, **29,5 s** no total.
  - `sh tools/hx feature verify NUC-01` → os 8 comandos da `verificacao` (c1 a c6) `OK`, `RESULTADO: OK`, exit 0, 57,8 s; o script gravou `estado: passing` e a `evidencia` (commit `859ac781e01a`, `2026-11-23T06:06:25Z`) em `features/NUC-01.json`.
  - Depois: 0 containers `postgres:18` sobrando.

## Falhou
- 23/11 · S2 (T2) · Primeiro teste c6 pelo proxy: 403 em `/exec/<id>/start` (EXEC desligado); depois, conexão recusada em `docker-proxy:<porta>` (host padrão). As duas causas foram corrigidas no Compose; ver Rodei.
- 23/11 · S2 (T4) · `test_esqueleto_da_api_tem_pontos_de_extensao_fixos`: `AttributeError: '_IncludedRouter' object has no attribute 'path'` (bloqueio 1). `_IncludedRouter` aparece em `fastapi/routing.py` a partir da 0.137.0 (contei a palavra no wheel de 0.136.0 → 0 e de 0.137.0 → 14).

- 23/11 · S2 (T5) · `test_migracoes_reaplicadas_nao_mudam_nada`: SQL do teste inválido no PostgreSQL 18 (bloqueio 5).
- 23/11 · S2 (T6) · Primeiro `up` no clone limpo: a porta 8000 estava ocupada, e o container da `api` ficou sem rede e foi reaproveitado no `up` seguinte. Resolvido com `docker compose down -v` e um novo `up` (ver Rodei).

## Decisões
- 23/11 · S1 (T1) · O `5e5c8c6` foi o commit original dos testes; o `7c567ee` passa a ser a referência da T7 (`git diff 7c567ee -- tests/`) porque mudou só as mensagens de erro de subprocesso (stdout e stderr no lugar de só stderr), com autorização do humano, sem mudar assert, condição nem valor esperado.
- 23/11 · S2 (T2) · Proxy com `EXEC: 1` além do que está na D1 (a T2 mostrou que é necessário). Risco: `exec` vale para qualquer container do host via proxy; mesma mitigação da seção 7 do plan.
- 23/11 · S2 (T2) · `TESTCONTAINERS_HOST_OVERRIDE: host.docker.internal` + `extra_hosts` com `host-gateway` no `dev` (saída prevista na D1, porque o padrão não alcançou).
- 23/11 · S2 (T2) · Variáveis no Compose como `${VAR}`, sem `:?`, para não quebrar o `hx verify` sem `.env`.
- 23/11 · S2 (T2) · No `db`, cada arquivo de `migrations/bootstrap/` é montado sozinho: o `.sh` em `/docker-entrypoint-initdb.d/` e o `.sql` em `/lastro-bootstrap/`. Montar a pasta inteira faria o entrypoint rodar os dois.
- 23/11 · S2 (T3) · `get_settings()` devolve um `Settings` novo a cada chamada, sem cache (sem estado global). `migrations_database_url` é opcional para a API; o `env.py` (T5) deve exigi-la.
- 23/11 · S2 (T4) · Parei a implementação no bloqueio 1, conforme a instrução da sessão. A T5 não foi começada.
- 23/11 · S2 · O humano escolheu a opção (b) do bloqueio 1 e autorizou 3 correções em `tests/` (rotas pelo `app.openapi()["paths"]`, 6 alarmes do `check-clean`, `try/finally` envolvendo o `start()`), sem mudar valor esperado nem usar `skip`. O humano fez o commit só-de-testes `59452ed`, que passa a ser a referência da T7 (`git diff 59452ed -- tests/`) no lugar do `7c567ee`.
- 23/11 · S2 (T5) · `env.py` usa `get_settings()`, que exige `DATABASE_URL` mesmo para migrar. O conftest e o Compose passam as duas variáveis; separar fica para quando a hospedagem pedir.
- 23/11 · S2 (T5) · Sequências: só `USAGE` para `lastro_app`, como na D8 (basta para `nextval` em inserts).
- 23/11 · S2 (T5) · Parei no bloqueio 5, conforme a regra 3, sem editar `tests/`.
- 23/11 · S2 · O humano autorizou só casts no SQL de `tests/core/test_migracoes.py`. A busca por colunas `"char"` (tipos conferidos em `pg_attribute` num `postgres:18`) achou só `pg_default_acl.defaclobjtype`. O humano fez o commit só-de-testes `cacb33a`, que passa a ser a referência da T7 (`git diff cacb33a -- tests/`) no lugar do `59452ed`. Depois dele, `pytest tests/core -q -rA` → 16 passed (8 da NUC-01, 8 da NUC-02).
- 23/11 · S2 · `tasks.md`: T2, T3, T4 e T5 marcadas como feitas. Ficaram desmarcados, com nota: os "a conferir" da D1 (faltam Docker Desktop e CI), o `create_roles.sh` e o comando da `api` com `alembic upgrade head` (só a T6 confirma). O `downgrade` da `0001` está escrito, mas não foi executado.
- 23/11 · S2 (T6) · Healthcheck do `db` com `-h 127.0.0.1`, para só passar com o servidor definitivo, e não com o temporário do initdb (decidido pelo humano; registrado nos riscos do plan). O README ganhou "Subir o ambiente" (com o aviso da porta 8000) e a tabela de arquivos da raiz atualizada, com `alembic.ini` na raiz, como manda a c2 da ficha. A seção "Testar o ambiente" passou a usar `docker compose --profile dev build`. `tasks.md`: a T6 foi marcada, e também o `create_roles.sh` e o comando da `api`, com nota de que a consulta dos papéis ainda falta.
- 23/11 · S2 (pós-T6) · Pendência da consulta dos papéis resolvida: a saída veio da nova subida com o healthcheck `-h 127.0.0.1` (Rodei). Saíram as notas de pendente do `tasks.md` (T2, T5 e T6) e do topo deste arquivo. No `hx verify` seguinte: `RESULTADO: OK`, e `git diff cacb33a -- tests/` vazio.

## Fim de sessão
- [ ] `hx verify` verde, ou a falha está descrita em "Falhou"
- [ ] Nada quebrado nem pela metade na branch; commit feito
- [ ] "Próxima ação" atualizada
- [ ] Nenhum dado real nem segredo nas anotações