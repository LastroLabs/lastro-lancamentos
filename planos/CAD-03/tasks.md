# Tasks — CAD-03 · Cadastrar cliente com nome e CNPJ

**Plan:** planos/CAD-03/plan.md · **Ficha:** features/CAD-03.json
**Ordem:** T1 → revisão humana dos testes → commit só-de-testes (anotar o hash) → T2 em diante (sessão nova, sem editar `tests/`)
**Decisões fechadas:** P-13 = 422; rotas em `/api/v1/clients`; 409 para CNPJ repetido; 403 para contador. Falta o humano aprovar o plan e registrar a P-13 em `DECISIONS.md`.

---

## [ ] T1 · Escrever os testes dos critérios
- **Critérios da ficha:** c1, c2, c3, c4
- **Regra de negócio (em linguagem simples):** só o chefe cadastra cliente. O cliente aparece na lista do escritório dele e de mais ninguém; quem não está conectado não grava nada; nome em branco ou CNPJ errado são recusados com a mensagem que diz o que corrigir.
- **Critérios de aceite:**
  - [ ] Existem os 5 testes citados em `verificacao`: `test_chefe_cadastra_cliente_que_aparece_na_lista`, `test_cliente_sem_nome_recusado`, `test_cliente_com_cnpj_invalido_recusado`, `test_cliente_invisivel_para_outro_escritorio`, `test_cadastro_sem_sessao_recusado`
  - [ ] Testes adicionais (perguntas 3 a 6 aceitas), com nomes próprios fora da `verificacao`: contador recusado com 403; nome com 255 caracteres aceito e com 256 recusado; CNPJ repetido no mesmo escritório; chefe do mesmo escritório abre cliente sem responsável (403, P-09)
  - [ ] Todos falham hoje pelo motivo certo (rota ainda inexistente), sem quebrar a coleta
  - [ ] Só dados inventados; CNPJ válido gerado em tempo de execução (nunca literal); senhas geradas na hora; "a lista continua com 0 clientes" conferida também por SQL na tabela `cliente`
- **Exemplos:**
  - c1: chefe_1 em ESC-1 cadastra "EMPRESA TESTE 1" com CNPJ gerado e com máscara → 201 com `id`, nome e CNPJ sem máscara; a lista traz 1 cliente.
  - c2 (a): nome "" → recusa com 'Informe o nome do cliente.'; (b) DV errado → 'O CNPJ informado não é válido. Confira os números.'; 0 linhas em `cliente`.
  - c3: chefe_2 pede a lista (vazia), `GET` de EMP-1 e de um UUID inexistente → 404, 'Você não tem acesso a este cliente.', corpo igual nos dois, sem dado de EMP-1.
  - c4: sem cookie → 401 'Entre para continuar.'; 0 linhas em `cliente`.
- **Arquivos:** `tests/registry/test_cliente.py` (único)
- **Reaproveitar:** padrão de `tests/access/test_login.py` (`head_database`, `office`, `_client`, `_assert_problem`) e o gerador de CNPJ de `tests/registry/test_cnpj.py` · **Não criar:** teste que importe módulo interno de outro módulo; CNPJ literal
- **Fora do escopo:** código de produção; editar testes de outras fichas
- **Decisões relacionadas:** D6; perguntas 1 a 5
- **Pronto quando:** `docker compose run --rm dev pytest tests/registry/test_cliente.py -q` mostra só falhas esperadas

## [ ] T2 · Contrato e repositório de cliente
- **Critérios da ficha:** c1, c3
- **Regra de negócio (em linguagem simples):** gravar e ler clientes sempre dentro de um escritório. O repositório nunca recebe o escritório do corpo do pedido, só o da sessão. Para a regra de acesso, cada cliente vem com o responsável ativo (ou nenhum).
- **Critérios de aceite:**
  - [ ] `ClientSummary` (imutável: `client_id`, `name`, `cnpj`) em `registry/contracts.py`
  - [ ] `registry/repository.py` com: inserir cliente do escritório; listar clientes do escritório; buscar um cliente por `(firm_id, client_id)`
  - [ ] O `registry` não lê `atribuicao` nem importa o `access`; o responsável chega por uma função recebida (pergunta 8, D3)
  - [ ] `access/service.py` + `access/repository.py`: `responsible_member_ids(db, firm_id, client_ids)` devolve, por cliente, o membro com `atribuicao.fim IS NULL` (ou nenhum), filtrando por escritório
  - [ ] Toda consulta filtra por `escritorio_id`; cliente de outro escritório não é devolvido
  - [ ] Repositório não faz commit (padrão de `access/repository.py`)
- **Exemplos:** inserir EMP-1 em ESC-1 → volta o id gerado; buscar EMP-1 com o id de ESC-2 → `None`; lista de ESC-1 → só clientes de ESC-1.
- **Arquivos:** `src/lastro/registry/repository.py`, `src/lastro/registry/contracts.py`, `src/lastro/access/service.py`, `src/lastro/access/repository.py`
- **Reaproveitar:** `registry/models.py` (`Client`) · **Não criar:** migração, módulo novo, `utils.py`, import de `access/models.py` no `registry` (I-7)
- **Fora do escopo:** regra de papel e de CNPJ (T3); HTTP (T4); responsável na resposta da API (ACE-03)
- **Decisões relacionadas:** D1, D3, D5
- **Pronto quando:** `pytest tests/registry/test_cliente.py::test_chefe_cadastra_cliente_que_aparece_na_lista -q` avança além do erro de rota inexistente (fecha junto com T3 e T4), e `ruff check src/lastro/registry` está limpo

## [ ] T3 · Regras de cadastro, lista e abertura no `service.py`
- **Critérios da ficha:** c1, c2, c3
- **Regra de negócio (em linguagem simples):** (1) só chefe cadastra; (2) o nome sem espaços nas pontas não pode ficar vazio; (3) o CNPJ passa por `validate_cnpj` e grava a forma normalizada; (4) a lista mostra só o que a regra de acesso deixa o usuário ver; (5) abrir um cliente de outro escritório ou inexistente dá exatamente a mesma resposta.
- **Critérios de aceite:**
  - [ ] `register_client`, `list_clients` e `get_client` em `registry/service.py`, recebendo a sessão do banco, o `Membership` do `core` (montado pela `api/` a partir do `SignedInMember`, D3) e, na lista e no abrir, a função que acha o responsável (sem importar o `access`, nem o `access.contracts`; corrigido em 25/11 após a revisão do PR #71)
  - [ ] Nome vazio → `InvalidClientDataError` com 'Informe o nome do cliente.'; CNPJ inválido → o mesmo erro com `result.error_message` (texto não duplicado)
  - [ ] Nome com mais de 255 caracteres (depois do `strip()`) → `InvalidClientDataError` com 'O nome do cliente deve ter no máximo 255 caracteres.'
  - [ ] Ordem fixa: papel, nome (vazio, depois tamanho), CNPJ; a recusa traz só a primeira falha (c2 testa um defeito por vez)
  - [ ] Contador (ou papel desconhecido) → recusa de papel (pergunta 4); CNPJ repetido → erro da pergunta 3
  - [ ] `get_client` usa `decide_access(..., Action.ACCESS, ...)`; `NOT_FOUND` e cliente inexistente → o mesmo `ClientNotFoundError`; `NOT_ASSIGNED` → recusa da pergunta 5
  - [ ] `list_clients` usa `filter_visible_clients`; nada gravado em caso de recusa; commit só no sucesso, rollback no erro
- **Exemplos:** chefe_1, "EMPRESA TESTE 1" + CNPJ com máscara → cliente com CNPJ sem máscara; "   " → 'Informe o nome do cliente.'; chefe_2 com o id de EMP-1 → `ClientNotFoundError`.
- **Arquivos:** `src/lastro/registry/service.py` (e `contracts.py` para os erros)
- **Reaproveitar:** `validate_cnpj`, `decide_access`, `filter_visible_clients`, `Membership`, `ClientScope`, `Role` · **Não criar:** `Action` nova no `core`; regra de acesso paralela; mensagem de CNPJ duplicada
- **Fora do escopo:** status HTTP (T4); atribuir responsável
- **Decisões relacionadas:** D1 a D4
- **Pronto quando:** `pytest tests/registry/test_cliente.py::test_cliente_sem_nome_recusado tests/registry/test_cliente.py::test_cliente_com_cnpj_invalido_recusado -q` passa (com T4)

## [ ] T4 · Rotas, handlers e status
- **Critérios da ficha:** c1, c2, c3, c4
- **Regra de negócio (em linguagem simples):** a API só traduz: sem cookie → 401; dado inválido → status da P-13; cliente que não é seu ou não existe → 404 com o mesmo corpo; erros no formato `application/problem+json` com português simples (o que aconteceu + o que fazer).
- **Critérios de aceite:**
  - [ ] As rotas de lista e de abrir passam `access.responsible_member_ids` ao `registry.service`
  - [ ] `POST`, `GET` (lista) e `GET /{client_id}` de clientes (`/api/v1/clients` e `/api/v1/clients/{client_id}`), sob `/api/v1`, todos com `Depends(require_signed_in_member)`
  - [ ] `POST` → 201 e corpo `id`, `name`, `cnpj` (14 caracteres, sem máscara); nenhum campo de escritório ou hash
  - [ ] Handlers novos registrados em `EXCEPTION_HANDLERS`: dado inválido (P-13), 404 único ('Você não tem acesso a este cliente.'), e, se aceitos, 403 e 409
  - [ ] Erros de validação do próprio FastAPI não substituem a mensagem da ficha (nome vazio chega ao `service`, não é barrado por Pydantic com texto em inglês)
  - [ ] Rota recusada por papel/404 não valida o corpo antes (P-09, item 5)
- **Exemplos:** sem cookie → 401 'Entre para continuar.'; `GET` de id que não é UUID → 404 igual ao inexistente (não 422).
- **Arquivos:** `src/lastro/api/routes.py`
- **Reaproveitar:** `_problem`, `PROBLEM_JSON`, `UNAUTHORIZED_RESPONSES`, `Problem`, `require_signed_in_member` · **Não criar:** arquivo de rotas novo fora da regra de `ARCHITECTURE.md` §3; SQL na rota
- **Fora do escopo:** tela; campo do responsável; rotas de atribuição
- **Decisões relacionadas:** D4, D5; perguntas 1 a 5
- **Pronto quando:** `pytest tests/registry/test_cliente.py -q` passa inteiro

## [ ] T5 · OpenAPI, cliente do front e documentação
- **Critérios da ficha:** — (exigido por `test_web01_cliente_da_api_gerado_do_openapi_e_estavel`)
- **Regra de negócio (em linguagem simples):** o desenho da API é publicado em arquivo e o front usa tipos gerados dele; se a API mudou e o arquivo não, o teste do WEB-01 quebra.
- **Critérios de aceite:**
  - [ ] `pnpm run gerar:api` (em `web/`) regenera `docs/api/openapi.json` e `web/src/api/schema.d.ts`; segunda execução não muda nada
  - [ ] `docs/modulos/registry.md` descreve rotas, recusas e o contrato `ClientSummary` (v0); corrige o nome da responsável da CAD-03
  - [ ] `ARCHITECTURE.md` §6: linha do contrato `registry → api` atualizada (mesmo PR, §9); avisar os donos da ACE-02/ACE-03 no PR (sem issue `contrato:`, decisão de caio-nascime); `docs/modulos/access.md` documenta `responsible_member_ids`
  - [ ] Decisões 1 a 5 e 8 do plan registradas em `docs/decisoes/DECISIONS.md` pelo humano (P-13)
- **Arquivos:** `docs/api/openapi.json`, `web/src/api/schema.d.ts`, `docs/modulos/registry.md`, `docs/modulos/access.md`, `ARCHITECTURE.md`
- **Reaproveitar:** `lastro.api.export_openapi`, script `gerar:api` · **Não criar:** doc novo
- **Fora do escopo:** telas e `web/src/copy/`
- **Pronto quando:** `pytest tests/web/test_web_foundation.py::test_web01_cliente_da_api_gerado_do_openapi_e_estavel -q` passa

## [ ] T6 · Verificação final
- **Critérios de aceite:**
  - [ ] `git diff <hash-dos-testes> -- tests/` vazio
  - [ ] `ruff check .` limpo
  - [ ] `hx check-clean` (com `LASTRO_NOMES_PROIBIDOS`) e `hx verify` em OK
  - [ ] `hx feature verify CAD-03` grava `passing`
  - [ ] `progress/CAD-03.md` atualizado; PR avisa que o isolamento é só aplicativo até a NUC-03
- **Pronto quando:** `hx check-clean`, `hx verify` e `hx feature verify CAD-03` terminam com código 0
