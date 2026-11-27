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
Humano: conferir o resultado do `hx verify`, decidir sobre o erro de ordem de imports em `tests/registry/test_contas_bancarias.py` (I001; `ruff check --fix` nesse arquivo), commitar e rodar `hx feature verify CAD-04`.

## Bloqueios e perguntas
- `ruff check .` acusa I001 (ordem dos imports) em `tests/registry/test_contas_bancarias.py`; a regra 3 proíbe editar `tests/`, então fica para o humano.

## Feito
- 27/11 · S2 · T2 a T7: `bancos.csv` (463 bancos do STR/BCB), `banks.py`, `bank_accounts.py`, contratos v0, repositório, serviço, rotas POST/GET/PATCH, docs (`registry.md`, `ARCHITECTURE.md` §6), OpenAPI e `schema.d.ts` regenerados.

## Rodei
- 27/11 · S2 · `docker compose run --rm dev pytest tests/registry/test_contas_bancarias.py -q` → 11 passed
- 27/11 · S2 · `docker compose run --rm dev pytest -q` → 533 passed, 1 failed (teste do OpenAPI, ver Falhou)
- 27/11 · S2 · `docker compose run --rm dev pytest tests/web/test_web_foundation.py -q` com os arquivos gerados no stage → 5 passed
- 27/11 · S2 · `python tools/harness.py check-clean` → 0 achados, OK

## Falhou
- 27/11 · S2 · `test_web01_cliente_da_api_gerado_do_openapi_e_estavel` falhou porque `docs/api/openapi.json` regenerado ainda não estava no git; passou depois de `git add`.
- 27/11 · S2 · `ruff check .`: I001 em `tests/registry/test_contas_bancarias.py` (não editado, regra 3).

## Decisões
- 27/11 · S2 · id da conta é `uuid7` gerado na aplicação: a tabela não tem coluna de criação e a lista ordena por id.
- 27/11 · S2 · mês em branco (`""`) é tratado como ausente; o plano não definia.
- 27/11 · S2 · `schema.d.ts` também é regenerado pelo teste da web, então entra junto com o OpenAPI.

## Fim de sessão
- [ ] `hx verify` verde, ou a falha está descrita em "Falhou"
- [ ] Nada quebrado nem pela metade na branch; commit feito
- [ ] "Próxima ação" atualizada
- [ ] Nenhum dado real nem segredo nas anotações