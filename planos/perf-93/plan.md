# Plan — perf-93 · `hx verify` de ~18 min para 3–4 min

**Status:** aprovado (caio-nascime, 27/11/2026, no chat: "pode iniciar a implementação")
**Branch:** perf/93-hx-verify-rapido · **Data:** 27/11/2026 · **Responsável:** caio-nascime
**Tasks:** planos/perf-93/tasks.md · **Issue:** #93 · **Ficha:** nenhuma (pedido do responsável)

## 1. A decidir (humano)
| # | Pergunta | Gravidade | Sugestão de padrão | Decide |
|---|---|---|---|---|
| 1 | Exceção escrita à regra 3 para trocar o **corpo de 5 fixtures** (não de testes) que sobem o banco: `migrated_database` em `tests/core/conftest.py` (`head`) e em `tests/access/conftest.py` (`0002`); `head_database` em `tests/access/test_login.py` e em `tests/access/test_period_link_schema.py`; `postgres_server` nos conftests de `access` e `registry` | BLOQUEANTE (T5, T6) | Entrada nova no `DECISIONS.md`, no formato da T12: lista fechada de arquivos e fixtures, nenhum `def test_` muda, nenhuma asserção sai, a revisão sobe a mesma revisão de antes | caio-nascime (líder) |
| 2 | Sem ficha não há `hx feature verify` nem `estado`. A prova é o `hx verify` (local e CI) e a medição de tempo. Aceito? | ATENÇÃO | Sim. PR com o link da #93, a medição antes/depois e a revisão de camposs04 (CODEOWNERS de `/tools/`, porque o autor não aprova o próprio PR) | caio-nascime |
| 3 | ~~O passo 4 da issue (`pytest-xdist`) entra neste plano?~~ Respondida: sim (seção 5; D5 a D7) | — | — | caio-nascime |
| 4 | Corrigir aqui o contorno do `AGENTS.md` (o `hx` pelo container `dev` não roda `verify` nem `feature verify`)? | ATENÇÃO | Sim, uma linha, na T7. O `AGENTS.md` é regra do time e precisa de aval explícito | caio-nascime |
| 5 | Ordem com o PR #92 (DB-04): depois do merge, a `developer` ganha `database_at_db02` e `database_at_db04`, que também sobem o banco | ATENÇÃO | Rebase depois do #92. As duas fixtures ficam **fora** da exceção (pergunta 1) e continuam rodando o alembic, porque são de testes de migração | caio-nascime |

Mudanças sugeridas na ficha: não se aplica.

## 2. Decisões tomadas pelo agente
### D1 · Pré-compilar o bytecode das dependências na imagem `dev` (passo novo, fora da issue)
- **Achado:** o Dockerfile define `PYTHONDONTWRITEBYTECODE=1` e o `uv sync` roda sem pré-compilar. A imagem tem **0 arquivos `.pyc`**, então cada processo Python recompila o SQLAlchemy, o alembic e o psycopg: medi 2,4–2,6 s só nesses imports, em todo `alembic upgrade`, em todo CLI testado e em todo `pytest` do `feature verify`. Com `compileall` simulado no container, caiu para 1,5 s.
- **Alternativas:** A) `ENV UV_COMPILE_BYTECODE=1` antes do `uv sync` · B) passo `python -m compileall` depois do sync · C) tirar o `PYTHONDONTWRITEBYTECODE` (não resolve: o container é `--rm` e, na CI, `--user` não grava em `/opt/venv`)
- **Escolhida:** A. É a forma documentada pelo uv para imagens Docker ("tends to improve startup time", em troca de build e imagem maiores). Vale para os estágios `dev` e `runtime`.
- **Fontes:** https://docs.astral.sh/uv/guides/integration/docker/ (seção "Compiling bytecode", acesso em 27/11)
- **Impacto:** T2. Nenhum teste muda.
- [x] confirmar (caio-nascime, 27/11)

### D2 · `node_modules` do front num **volume nomeado**, criado gravável para qualquer usuário
- **Alternativas:** A) volume nomeado em `/app/web/node_modules` no serviço `dev` + pasta criada no Dockerfile com permissão para qualquer uid · B) volume anônimo (não serve: `run --rm` apaga o volume anônimo a cada execução) · C) arquivo `docker-compose.override.yml` local, fora do Git (cada dev configura à mão; a CI não usa)
- **Escolhida:** A. Medido no Windows: build 21 s → 4 s, Vitest 28 s → 3 s. A permissão cobre o `--user uid:gid` que o `hx` usa no Linux e na CI (`tools/harness.py`, `montar_comando_docker`). Que o Docker copia a permissão da pasta da imagem para o volume novo é **não verificável aqui**: a T3 prova na CI.
- **Impacto:** T3. O `test_ambiente.py` só proíbe o socket do Docker fora do `docker-proxy`, então o volume não fere o teste.
- [x] confirmar (caio-nascime, 27/11)

### D3 · Banco-modelo **por revisão**, clonado com `CREATE DATABASE … TEMPLATE`
- **Alternativas:** A) um modelo só, em `head` · B) uma fábrica de sessão que guarda um modelo por revisão pedida (`head`, `0002`) · C) dump/restore com `pg_dump`
- **Escolhida:** B. O `migrated_database` de `access` fica fixado na `0002` (DB-01), então só `head` mudaria o que esses testes provam. Para A e B, o clone é feito pelo superusuário, com `OWNER lastro_owner`, sem conexão aberta no modelo e com a estratégia padrão `WAL_LOG` (a melhor para banco pequeno). C é mais lento e mais complexo.
- **Conferido:** a cópia não leva privilégio de nível de banco nem `ALTER DATABASE SET`. As migrações não usam nenhum dos dois (só `ALTER DEFAULT PRIVILEGES` e `GRANT`/`REVOKE` dentro do banco, que são copiados). Os papéis valem para o servidor inteiro.
- **Fontes:** https://www.postgresql.org/docs/18/sql-createdatabase.html · https://www.postgresql.org/docs/18/manage-ag-templatedbs.html (acesso em 27/11)
- **Impacto:** T6. Os testes de migração (`fresh_database` + alembic no corpo) **não mudam**.
- [x] confirmar (caio-nascime, 27/11)

### D4 · Um PostgreSQL só: `postgres_server` definido uma vez, no `tests/conftest.py`
- **Alternativas:** A) mover `postgres_server` para o `tests/conftest.py` e apagar as reatribuições em `access` e `registry` · B) módulo de plugin via `pytest_plugins` · C) manter as 3 cópias
- **Escolhida:** A. É o mecanismo padrão do pytest para compartilhar fixture entre pastas e não precisa de configuração nova. A T5 prova pela contagem de containers (1). Se o import duplicado do core atrapalhar, cair para B e registrar.
- **Impacto:** T5. Os nomes das fixtures continuam os mesmos.
- [x] confirmar (caio-nascime, 27/11)

### D5 · Biblioteca do paralelo: `pytest-xdist`
- **Alternativas:** A) `pytest-xdist` 3.8.0 (MIT, 01/07/2025, requer Python ≥3.9) · B) `pytest-parallel` 0.1.1 (MIT, sem versão desde 10/10/2021, só lista o 3.6) · C) `pytest-run-parallel` 0.10.0 (MIT, 08/2026), que roda o mesmo teste em várias **threads** para provar segurança de thread, outro propósito
- **Escolhida:** A. É o padrão do ecossistema e tem marca de grupo (`--dist loadgroup`), gancho para o número de processos e receita para fixture de sessão. Não lista o 3.14 nos classificadores, mas **testei**: instalou e rodou `-n 2` no Python 3.14.10 do container (ambiente descartável em `/tmp`, 27/11). B está abandonada.
- **Fontes:** https://pypi.org/pypi/pytest-xdist/json · https://pypi.org/pypi/pytest-parallel/json · https://pypi.org/pypi/pytest-run-parallel/json · https://pytest-xdist.readthedocs.io/en/stable/distribution.html · https://pytest-xdist.readthedocs.io/en/stable/how-to.html (acesso em 27/11)
- **Impacto:** T7; dependência no grupo `dev` do `pyproject.toml` e no `uv.lock` (regra 12).
- [x] confirmar (caio-nascime, 27/11)

### D6 · Ligar o paralelo pela configuração do pytest, sem mudar o `hx`
- **Achado:** `tests/harness/test_fase_c.py` (linhas 102–166) fixa que o passo do `verify` é exatamente `pytest -q`. Mudar `_PASSOS_DE_VERIFICACAO` quebra testes da HX.
- **Alternativas:** A) `addopts = "-n auto --dist loadgroup"` no `pyproject.toml` + gancho `pytest_xdist_auto_num_workers` no `tests/conftest.py`: até 4 processos na suíte e **0 (série)** quando o comando aponta um teste por `::` (é o caso do `feature verify`) · B) mudar o `hx` e o `test_fase_c.py` (exceção na HX, revisão do dono do harness) · C) `PYTEST_ADDOPTS` no compose (sem como deixar o `feature verify` em série)
- **Escolhida:** A. O `hx`, a CI e o `test_fase_c.py` não mudam. O gancho devolvendo 0 não é documentado, mas **testei** (27/11): suíte → "created: 3/3 workers"; `arquivo::teste` → em série; `-n 0` → em série. O grupo do front é posto pelo `tests/conftest.py` (`xdist_group` nos itens de `tests/web/`), sem editar o arquivo de teste.
- **Impacto:** T7; o `tests/conftest.py` entra na exceção da pergunta 1.
- [x] confirmar (caio-nascime, 27/11, junto com o "pode iniciar"; o hx e o feature verify seguem como hoje)

### D7 · Um PostgreSQL por processo (até 4), sem trava compartilhada
- **Alternativas:** A) cada processo sobe o seu (a fixture de sessão já faz isso sob o xdist) · B) um só, compartilhado por trava de arquivo (receita do xdist; exige a dependência `filelock`) · C) o processo principal sobe e repassa aos outros por gancho do xdist
- **Escolhida:** A. Não precisa de código nem dependência a mais. O total é fixo (o número de processos) e não cresce com o número de testes. Cada processo cria os próprios bancos-modelo (D3). Se a memória ou o tempo de subida pesarem na medição, passar para B e registrar.
- **Impacto:** T7.
- [x] confirmar (caio-nascime, 27/11)

## 3. Resumo e abordagem
Baixar o `hx verify` para 3–4 min sem tirar teste e sem mudar asserção. Ordem pelo risco, medindo depois de cada passo:
(1) medição de base; (2) bytecode pré-compilado (Dockerfile); (3) `node_modules` em volume (compose e Dockerfile); (4) exceção à regra 3 registrada; (5) um PostgreSQL só; (6) banco-modelo por revisão; (7) paralelo com `pytest-xdist`; (8) medição final, CI verde e PR.
**Estimativa honesta** (a partir de `--durations`, ainda não medida): passos 2 e 3 tiram ~4–5 min; os passos 5 e 6, ~6–7 min (≈80 testes × ~5 s de preparo), e sobram **6–8 min**. Com 4 processos (passo 7), a meta de **3–4 min** fica ao alcance. A regra de teste em paralelo já está no `CODING_STANDARDS.md` (seção 2, "Testes em paralelo").

## 4. Contexto encontrado
- **Fichas e planos lidos (contexto, não dependência):** NUC-01 (`docker-compose.yml`, fixtures de banco, `test_ambiente.py`), HX-10 (`pr.yml`), WEB-01 (testes do front). Todas `passing`. As regras que valem estão no código lido abaixo.
- **`DECISIONS.md`:** T12 (formato de exceção à regra 3, modelo para a pergunta 1); PROC-01 (base `developer`). Nenhuma entrada sobre tempo de teste.
- **Código (confere):**
  - `pr.yml`: job `verify` com **`timeout-minutes: 15`**; as últimas execuções levam ~10 min (9 a 10 min no `verify` da DB-04, em 27/11). A suíte já está perto do limite da CI.
  - `tools/harness.py`: `_PASSOS_DE_VERIFICACAO` e `montar_comando_docker` (`--user` só em POSIX) não mudam. `tests/harness/test_fase_c.py` fixa o comando exato, e o plano não toca nele.
  - `tests/core/test_ambiente.py` lê o compose e o Dockerfile: exige `dev` no perfil `dev`, o estágio `dev` em `python:3.14` e o socket só no `docker-proxy`. As T2 e T3 respeitam.
  - Quem sobe banco até `head`/`0002` sem fazer mais nada: as 5 fixtures da pergunta 1 (≈80 testes). Quem sobe e desce no corpo do teste: `test_identity_schema.py` (c reversível), `test_period_link_schema.py` c4, `test_registry_schema.py` c4, `test_migracoes.py`. Estes ficam iguais.
  - `access` e `registry` recarregam o `tests/core/conftest.py` com outro nome de módulo, o que dá 3 fixtures `postgres_server` de sessão e 3 containers.
- **Medido no container `dev` (27/11):** `python -c pass` 0,14 s; import de sqlalchemy, alembic e psycopg 2,4–2,6 s (0 `.pyc`); `pnpm install` 2–4 s, sem download; build 21 s e Vitest 28 s com o `node_modules` no disco do Windows.
- **Reaproveitar:** `FreshDatabase`, `connect`, `run_alembic_upgrade` e `process_output` (`tests/core/conftest.py`).
- **Não criar:** helper novo de alembic; `pytest.ini` (a config vai em `[tool.pytest.ini_options]`, que hoje não existe); dependência além do `pytest-xdist` (D5).
- **Pesquisa externa:** PostgreSQL 18 (`CREATE DATABASE`, bancos-modelo) e o guia Docker do uv, acima. O `pytest-xdist` não foi pesquisado (pergunta 3).

## 5. Decisões (já resolvidas)
- 27/11 · Sem ficha, só a issue #93 (caio-nascime).
- 27/11 · O front continua no `hx verify`; descartado marcar como `slow` (caio-nascime).
- 27/11 · Branch `perf/93-hx-verify-rapido` a partir da `developer` (caio-nascime).
- 27/11 · Pergunta 1: exceção à regra 3 aceita, na forma sugerida; a T4 registra no `DECISIONS.md` (caio-nascime).
- 27/11 · Pergunta 2: sem ficha; prova pelo `hx verify` (local e CI) e pela medição; revisão de camposs04 (caio-nascime).
- 27/11 · Pergunta 4: corrigir o contorno do `AGENTS.md` nesta branch, na T7 (caio-nascime).
- 27/11 · Pergunta 5: rebase depois do #92; `database_at_db02`/`database_at_db04` fora da exceção (caio-nascime).
- 27/11 · D1 a D4 confirmadas (caio-nascime).
- 27/11 · Pergunta 3: o paralelo (`pytest-xdist`) entra neste plano (T7). Sobre o custo: 1 container por processo, total fixo e independente do número de testes (caio-nascime).
- 27/11 · A regra "Testes em paralelo" foi acrescentada ao `CODING_STANDARDS.md`, seção 2 (pedido de caio-nascime).

## 6. Avaliação (sem ficha: avaliado contra a issue)
| # | Achado | Gravidade | Onde |
|---|---|---|---|
| 1 | Trocar fixtures em `tests/` exige exceção à regra 3 | BLOQUEANTE | T5, T6 |
| 2 | Meta de 3–4 min provavelmente não sai sem o paralelo | ATENÇÃO | issue |
| 3 | Sem `verificacao` de ficha, o "pronto" depende de medição, não de teste | ATENÇÃO | T1, T7 |
| 4 | Volume com `--user` no Linux só se prova na CI | ATENÇÃO | T3 |
| 5 | Causa nova não listada na issue: falta de bytecode (D1) | ATENÇÃO | issue |
| 6 | O `AGENTS.md` indica um contorno que não funciona para `verify`/`feature verify` | ATENÇÃO | T7 |

## 7. Riscos
- **Banco-modelo muda o que um teste prova** → só fixtures que hoje fazem "banco vazio + upgrade até X, nada mais"; mesma revisão; nenhum `def test_` muda; `git diff` revisado pela lista da pergunta 1.
- **Clone falha com conexão aberta no modelo** → a fábrica fecha tudo antes de clonar; a falha aparece como erro claro na fixture, não como teste pulado.
- **Volume com permissão errada na CI** → a T3 só fecha com o `pr.yml` verde nesta branch.
- **`node_modules` velho no volume depois de mudar o lockfile** → os testes do WEB-01 já rodam `pnpm install --frozen-lockfile`, que sincroniza.
- **Imagem maior e build mais lento (D1)** → aceito; a imagem é reconstruída pouco e o ganho vale em cada execução.
- **Teste que falha "às vezes" em paralelo** (arquivo, nome ou ordem compartilhados) → auditoria feita: os testes do harness e da CI usam `tmp_path`; o front vai num grupo só; a T7 roda a suíte paralela 3 vezes seguidas antes de fechar; `pytest -n 0` para investigar.
- **Timeout de 15 min da CI** → hoje a CI leva ~10 min. O plano reduz esse tempo e não mexe no limite.

## 8. Aprovação
- [x] Pergunta 1 respondida (exceção registrada no `DECISIONS.md` §12, V1)
- [x] Decisões D1 a D4 confirmadas
- [x] Decisões D5 a D7 (paralelo) confirmadas
- [x] Plan e tasks revisados por caio-nascime em 27/11
