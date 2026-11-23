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
(1 a 2 linhas: o comportamento que esta feature entrega)

## Próxima ação
(a primeira coisa a fazer ao retomar; de preferência um comando ou um arquivo)

## Bloqueios e perguntas
- (nenhum)

## Feito
- DD/MM · S1 ·

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

## Falhou
- DD/MM · S1 · o que falhou e a causa, se souber

## Decisões
- 23/11 · S1 (T1) · O `5e5c8c6` foi o commit original dos testes; o `7c567ee` passa a ser a referência da T7 (`git diff 7c567ee -- tests/`) porque mudou só as mensagens de erro de subprocesso (stdout e stderr no lugar de só stderr), com autorização do humano, sem mudar assert, condição nem valor esperado.

## Fim de sessão
- [ ] `hx verify` verde, ou a falha está descrita em "Falhou"
- [ ] Nada quebrado nem pela metade na branch; commit feito
- [ ] "Próxima ação" atualizada
- [ ] Nenhum dado real nem segredo nas anotações