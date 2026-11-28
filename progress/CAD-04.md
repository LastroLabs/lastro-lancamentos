# CAD-04 · Informar as contas bancárias do cliente com banco, apelido e meses de uso

- Responsável: jvsauma · Branch: `feat/CAD-04-informar-as-contas-bancarias-do-cliente` · Início: 27/11/2026
- Ficha: `features/CAD-04.json` (estado e critérios ficam lá; não repita aqui)

<!--
Como preencher (agente, ao encerrar a sessão):
- REESCREVA as seções do topo: Objetivo, Próxima ação, Bloqueios e perguntas.
- ACRESCENTE, sem apagar o que já existe, em Feito, Rodei, Falhou e Decisões.
  Cada linha começa com a data (DD/MM) e a sessão, ex.: "- 14/11 · S2 · ...".
- Registre só o que realmente rodou. Sem dado real, nome de cliente ou segredo.
- Não escreva estado (passing etc.) aqui: ele fica na ficha, gravado pelo script.
-->

## Objetivo
O contador (ou o chefe atribuído a si) cadastra, lista e altera contas bancárias do cliente com banco, apelido e meses de uso opcionais; nada é apagado.

## Próxima ação
Revisão do PR da CAD-04 na `developer`. Depois, CAD-06 (identificação protegida e conta contábil da conta bancária) e consumidores das contas.

## Bloqueios e perguntas
- (nenhum)

## Feito
- 27/11 · S3 · merge de `origin/developer` (conflito em `contracts.py` e `service.py`: mantidos os dois lados, CAD-04 e CAD-02/05); correção da corrida no PATCH e teste de dois PATCH concorrentes.
- 27/11 · S2 · T2 a T7: `bancos.csv` (463 bancos do STR/BCB), `banks.py`, `bank_accounts.py`, contratos v0, repositório, serviço, rotas POST/GET/PATCH, docs (`registry.md`, `ARCHITECTURE.md` §6), OpenAPI e `schema.d.ts` regenerados.

## Rodei
- 27/11 · S2 · `docker compose run --rm dev pytest tests/registry/test_contas_bancarias.py -q` → 11 passed
- 27/11 · S2 · `docker compose run --rm dev pytest -q` → 533 passed, 1 failed (teste do OpenAPI, ver Falhou)
- 27/11 · S2 · `docker compose run --rm dev pytest tests/web/test_web_foundation.py -q` com os arquivos gerados no stage → 5 passed
- 27/11 · S2 · `python tools/harness.py check-clean` → 0 achados, OK
- 27/11 · S2 · `docker compose run --rm -T --user uid:gid dev pytest -q tests/web` → 5 passed
- 27/11 · S2 · `pytest -q` completo (como root) → 534 passed; `ruff check .` → All checks passed
- 27/11 · S2 · commits: 706eaff (implementação) e e2724dc (ordem de import no teste)
- 27/11 · S2 · `hx verify` (ruff e pytest, no container, com `--user`) → OK
- 27/11 · S2 · `hx feature verify CAD-04` (rodado pelo responsável) → `passing`, c1 a c8 ok, no commit e2724dc
- 27/11 · S3 · `hx verify` após o merge com `developer` e a correção da corrida → OK (ruff e pytest)
- 27/11 · S3 · `pytest tests/registry/test_contas_bancarias_corrida.py` com a ordem antiga da trava → falha (apelido desfeito); com a correção → passa

## Falhou
- 27/11 · S3 · rubrica do PR #94: o PATCH lia a conta antes da trava do cliente; dois PATCH concorrentes (apelido e último mês) desfaziam um ao outro, contra a P4. Reproduzido por teste com a ordem antiga (apelido desfeito).
- 27/11 · S2 · `test_web01_cliente_da_api_gerado_do_openapi_e_estavel` falhou porque `docs/api/openapi.json` regenerado ainda não estava no git; passou depois de `git add`.
- 27/11 · S2 · `ruff check .`: I001 em `tests/registry/test_contas_bancarias.py` (não editado por mim, regra 3); o responsável corrigiu a mão e entrou no commit e2724dc.
- 27/11 · S2 · `hx verify` falhava no teste do front (`pnpm run build`, EACCES em `web/dist/assets`): a pasta tinha dono root, criada por pytest que rodei no Docker como root; o `hx` roda com `--user uid:gid`. Removi `web/dist` e passou. Não era código.

## Decisões
- 27/11 · S3 · `update_bank_account` trava o cliente (`FOR UPDATE`) antes de ler a conta e valida contra o valor lido sob a trava (READ COMMITTED enxerga o PATCH anterior já commitado). Teste novo em arquivo separado `tests/registry/test_contas_bancarias_corrida.py`, sem editar o `test_contas_bancarias.py`.
- 27/11 · S3 · `features/CAD-04.json` ainda traz `[definir P-13]` em c2, c4, c6 e c7: o plano diz que o humano aplica a troca por 422 em PR; não editei a ficha.
- 27/11 · S2 · id da conta é `uuid7` gerado na aplicação: a tabela não tem coluna de criação e a lista ordena por id.
- 27/11 · S2 · mês em branco (`""`) é tratado como ausente; o plano não definia.
- 27/11 · S2 · `schema.d.ts` também é regenerado pelo teste da web, então entra junto com o OpenAPI.

## Fim de sessão
- [x] `hx verify` verde, ou a falha está descrita em "Falhou"
- [x] Nada quebrado nem pela metade na branch; commit feito
- [x] "Próxima ação" atualizada
- [x] Nenhum dado real nem segredo nas anotações
