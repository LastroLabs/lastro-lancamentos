# CAD-03 · Cadastrar cliente com nome e CNPJ

- Responsável: caio-nascime · Branch: `feat/CAD-03-cadastrar-cliente-com-nome-e-cnpj` · Início: 25/11/2026
- Ficha: `features/CAD-03.json` (estado e critérios ficam lá; não repita aqui)

<!--
Como preencher (agente, ao encerrar a sessão):
- REESCREVA as seções do topo: Objetivo, Próxima ação, Bloqueios e perguntas.
- ACRESCENTE, sem apagar o que já existe, em Feito, Rodei, Falhou e Decisões.
  Cada linha começa com a data (DD/MM) e a sessão, ex.: "- 14/11 · S2 · ...".
- Registre só o que realmente rodou. Sem dado real, nome de cliente ou segredo.
- Não escreva estado (passing etc.) aqui: ele fica na ficha, gravado pelo script.
-->

## Objetivo
O chefe cadastra um cliente com nome e CNPJ pela API (`POST /api/v1/clients`). A lista (`GET /api/v1/clients`) e a abertura (`GET /api/v1/clients/{client_id}`) seguem a regra de acesso da NUC-02 (P-09); outro escritório recebe o mesmo 404 de um cliente inexistente.

## Próxima ação
Rodar `hx verify` completo na branch e registrar o resultado no PR #71; aguardar a resposta do João à correção do D3.

## Bloqueios e perguntas
- `hx verify` completo ainda não terminou verde depois dos commits (ver "Falhou").
- `hx check-clean` só rodou sem `LASTRO_NOMES_PROIBIDOS`; a parte de nomes fica para a CI.
- Donos da ACE-02 e da ACE-03 ainda não foram marcados no PR #71 (contratos v0 `ClientSummary` e `responsible_member_ids`; sem issue `contrato:`, por decisão de caio-nascime).
- O isolamento é só aplicativo até a NUC-03 (RLS).

## Feito
- 25/11 · S2 · T2: `registry/repository.py` (insere, lista e busca cliente sempre filtrando pelo `escritorio_id` da sessão); `ClientSummary` e erros de cliente em `registry/contracts.py`; `access.service.responsible_member_ids` com `access.repository.find_open_assignments` (`atribuicao.fim IS NULL`).
- 25/11 · S2 · T3: `register_client`, `list_clients` e `get_client` em `registry/service.py`. Ordem de checagem: papel, nome (`strip()`, vazio, mais de 255 caracteres), CNPJ por `validate_cnpj`. CNPJ repetido sai pelo `UNIQUE` do banco; abertura por `decide_access`.
- 25/11 · S2 · T4: rotas `POST`/`GET /api/v1/clients` e `GET /api/v1/clients/{client_id}` em `api/routes.py`, e handlers RFC 9457 (422, 403 de papel, 403 sem atribuição, 404 único, 409).
- 25/11 · S2 · T5: `docs/api/openapi.json` e `web/src/api/schema.d.ts` regenerados; `docs/modulos/registry.md`, `docs/modulos/access.md` e `ARCHITECTURE.md` §6 atualizados.
- 25/11 · S2 · P-13 registrada como aprovada (422) em `docs/decisoes/DECISIONS.md` e c2 da ficha trocado de `[definir P-13]` para 422, os dois com autorização de caio-nascime.
- 25/11 · S2 · `tools/harness.py`: o `check-clean` deixa de acusar expressão de código sem aspas (chamada ou índice) como segredo, com autorização de caio-nascime.
- 25/11 · S2 · Commits `0422ef2`, `b0fea1d`, `99b2fe8` e `8b8fa76` (evidência do `hx feature verify`); PR #71 aberto para `developer`, com uma seção que lista as autorizações dadas.
- 25/11 · S2 · Revisão do PR #71 (João): o `registry` importava `access.contracts.SignedInMember`, contra o D3. Correção: o `registry` recebe `Membership` do `core`, e a `api/` o monta a partir do `SignedInMember`. Linha da T3 e `registry.md` ajustados. Commitado e enviado ao PR #71.

## Rodei
- 25/11 · S2 · `pytest tests/registry/test_cliente.py -q` → 9 passed
- 25/11 · S2 · `pnpm run gerar:api` (duas vezes) → a segunda execução não mudou nada
- 25/11 · S2 · `ruff check .` + `pytest -q` (suíte completa, antes dos commits) → ruff limpo; 484 passed, 1 failed (WEB-01)
- 25/11 · S2 · `ruff check .` + `ruff format --check` nos arquivos alterados + `pytest tests/registry tests/access tests/api` → limpo; 109 passed
- 25/11 · S2 · `hx check-clean` (sem `LASTRO_NOMES_PROIBIDOS`) → antes do ajuste: 2 achados em `tests/registry/test_cliente.py` (alarme falso); depois: 0 achados, OK
- 25/11 · S2 · `pytest tests/harness tests/ci` + `ruff check tools/harness.py` → 326 passed; limpo
- 25/11 · S2 · `hx feature verify CAD-03` (rodado pelo dev, no commit `99b2fe8`) → 5/5 ok, evidência gravada pelo script
- 25/11 · S2 · `git diff bd18a00 -- tests/` → vazio
- 25/11 · S2 · Após a correção do D3: `ruff check .` + `pytest tests/registry/test_cliente.py tests/access tests/api tests/core` → limpo; 116 passed. `pnpm run gerar:api` → OpenAPI sem mudança. Depois, `ruff format` só em `registry/service.py` (mudança só de quebra de linha) → `ruff format --check` nos arquivos da ficha limpo, import do app ok

## Falhou
- 25/11 · S2 · `test_web01_cliente_da_api_gerado_do_openapi_e_estavel` na suíte completa: o teste compara `openapi.json` e `schema.d.ts` com a versão commitada, e os dois ainda não estavam commitados. Já foram commitados em `0422ef2`; o teste não foi rodado de novo.
- 25/11 · S2 · `hx check-clean`: alarme falso de segredo em `password = secrets.token_urlsafe(12)` e `"password": ...[login]`. Corrigido no harness (`99b2fe8`).
- 25/11 · S2 · `hx verify` completo: interrompido a pedido do dev, sem resultado.
- 25/11 · S2 · `ruff format --check .` acusa 28 arquivos; na `developer`, sem a branch, eram 27. O arquivo a mais era desta ficha e foi corrigido; os outros 27 não são da CAD-03.

## Decisões
- 25/11 · S2 · P-13 = 422 aprovada por caio-nascime e registrada em `DECISIONS.md`.
- 25/11 · S2 · Regra de segredo do `check-clean`: valor sem aspas que começa com um nome e segue com `(` ou `[` é código, não segredo. Risco aceito: um segredo literal sem aspas nesse formato deixa de ser acusado.
- 25/11 · S2 · D3 reforçado após a revisão do PR #71: o `registry` não importa nada do `access`, nem `access.contracts`, para não formar ciclo de pacotes com a ACE-02.

## Fim de sessão
- [ ] `hx verify` verde, ou a falha está descrita em "Falhou"
- [ ] Nada quebrado nem pela metade na branch; commit feito
- [x] "Próxima ação" atualizada
- [x] Nenhum dado real nem segredo nas anotações
