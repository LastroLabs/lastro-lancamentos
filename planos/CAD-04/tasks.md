# Tasks — CAD-04 · Informar as contas bancárias do cliente com banco, apelido e meses de uso

**Plan:** planos/CAD-04/plan.md · **Ficha:** features/CAD-04.json
**Ordem:** T1 → revisão humana dos testes → commit só-de-testes (anotar o hash) → T2 em diante (sessão nova, sem editar `tests/`)
Rotas e campos seguem a resposta P3 do plan (seção 5).

---

## [ ] T1 · Escrever os testes dos critérios
- **Critérios da ficha:** c1 a c8
- **Regra de negócio:** o contador responsável cadastra contas bancárias do cliente (banco + apelido, meses opcionais), vê a lista e altera apelido e meses; quem não é o responsável é barrado sem pistas.
- **Critérios de aceite:**
  - [ ] `tests/registry/test_contas_bancarias.py` tem os 8 testes com os nomes de `verificacao`
  - [ ] Todos falham hoje por comportamento ausente (rota inexistente), não por erro de import
  - [ ] Só dados inventados: escritórios, pessoas e CNPJ (gerado em execução, sem literal válido commitado)
  - [ ] c3 compara os 5 corpos 404 byte a byte; c7 confere a contagem de linhas no banco e que `DELETE` na conta não existe
  - [ ] c4 escolhe o código ausente lendo `bancos.csv`; confere colunas `codigo,nome,fonte`, os 8 códigos mínimos e 3 dígitos em todos
- **Exemplos:** os da ficha (EMP-1, contador_a, 001 'Conta movimento', 077 'Conta digital'; `' 341 '` → '341').
- **Arquivos:** `tests/registry/test_contas_bancarias.py`
- **Reaproveitar:** padrão de `tests/registry/test_cliente.py` e `migrated_database` · **Não criar:** helper compartilhado editando `test_cliente.py`
- **Fora do escopo:** código de produção
- **Pronto quando:** `docker compose run --rm dev pytest tests/registry/test_contas_bancarias.py -q` mostra só falhas esperadas

## [ ] T2 · Lista de bancos versionada e leitura
- **Critérios da ficha:** c4
- **Regra de negócio:** só aceitamos código de banco que consta na lista do repositório; o nome do banco vem do arquivo, nunca do usuário.
- **Critérios de aceite:**
  - [ ] `src/lastro/registry/data/bancos.csv` com colunas `codigo,nome,fonte` (lista completa do STR baixada do portal do BCB, P1; confira o link antes; inclui no mínimo 001, 033, 077, 104, 237, 260, 341, 748)
  - [ ] Todo `codigo` tem 3 dígitos ASCII, sem repetição; `fonte` traz a URL e a data de acesso
  - [ ] `bank_name(code)` devolve o nome ou `None`; arquivo lido uma vez (cache)
- **Exemplos:** `'001'` → nome do arquivo; `'999'` ausente → `None`.
- **Arquivos:** `src/lastro/registry/data/bancos.csv`, `src/lastro/registry/banks.py`
- **Reaproveitar:** `Path(__file__)` (a imagem usa `PYTHONPATH`) · **Não criar:** lista de bancos no código nem em outro módulo
- **Fora do escopo:** atualização automática da lista
- **Decisões relacionadas:** D2 · **Pronto quando:** `pytest tests/registry/test_contas_bancarias.py::test_codigo_de_banco_validado_pela_lista -q` passa na parte do arquivo (o teste inteiro só passa na T5)

## [ ] T3 · Validações puras e contratos
- **Critérios da ficha:** c2, c4, c5, c6
- **Regra de negócio:** banco e apelido são obrigatórios; o código do banco tem 3 números e existe na lista; apelidos iguais por acento, caixa ou espaços contam como o mesmo; meses vêm como AAAA-MM e viram dia 1.
- **Critérios de aceite:**
  - [ ] Funções puras (sem banco) em `registry/bank_accounts.py`: limpar/validar banco, apelido (+ forma normalizada, D3), mês (D5) e ordem fim ≥ início
  - [ ] Mensagens exatamente as da ficha: 'Informe o banco da conta.', 'Dê um apelido para a conta.', 'O código do banco tem 3 números. Confira e tente de novo.', 'Não encontramos um banco com este código. Confira o número.', 'Informe o mês no formato AAAA-MM, por exemplo 2026-10.', 'O último mês não pode ser antes do primeiro.'
  - [ ] Contratos v0 em `registry/contracts.py`: `BankAccountSummary`, `InvalidBankAccountDataError`, `DuplicateNicknameError`
- **Exemplos:** `' 341 '` → `'341'`; `'12'`/`'ABC'` → mensagem dos 3 números; `'conta  MOVIMENTO'` e `'Conta Movimênto'` → mesma forma normalizada; `'2026-1'`, `'10/2026'`, `'2026-13'` → mensagem do mês.
- **Arquivos:** `src/lastro/registry/bank_accounts.py`, `src/lastro/registry/contracts.py`
- **Reaproveitar:** `registry/cnpj.py` como modelo de módulo puro · **Não criar:** dependência nova
- **Fora do escopo:** banco de dados, HTTP
- **Decisões relacionadas:** D3, D4, D5, D6 · **Pronto quando:** `ruff check src/lastro/registry` limpo e importável; os testes de c2/c6 avançam na T5

## [ ] T4 · Informar e listar contas (repositório e serviço)
- **Critérios da ficha:** c1, c2, c3, c4, c5, c6, c8
- **Regra de negócio:** só o responsável ativo do cliente (contador, ou chefe atribuído a si) informa e lê contas; as recusas de acesso vêm antes de qualquer validação; recusa não grava nada.
- **Critérios de aceite:**
  - [ ] `add_bank_account` e `list_bank_accounts` em `registry/service.py`: acesso via `get_client` → validações na ordem do plan (pergunta 5) → trava `FOR UPDATE` no cliente → duplicado (409) → grava e `commit`
  - [ ] Apelido gravado como digitado (sem espaços nas pontas); `moeda` 'BRL'; meses gravados no dia 1; resposta traz `bank_name` do arquivo e meses `AAAA-MM` ou nulos
  - [ ] Lista ordenada de forma estável (por criação, depois id); só SQL em `repository.py`, sempre com `escritorio_id` e `cliente_id` da sessão
  - [ ] Falha na gravação faz `rollback`
- **Exemplos:** EMP-1 sem contas + (001,'Conta movimento') + (077,'Conta digital') → lista com 2; chefe_1 em EMP-1 sem banco → 403 (não 422); EMP-2 aceita 'Conta movimento' de novo.
- **Arquivos:** `src/lastro/registry/repository.py`, `src/lastro/registry/service.py`
- **Reaproveitar:** `get_client`, `ClientNotFoundError`, `ClientNotAssignedError` · **Não criar:** outra regra de acesso, UNIQUE novo
- **Fora do escopo:** rotas, PATCH, `identificacao_protegida`, `conta_contabil_id`
- **Decisões relacionadas:** D1, plan perguntas 2 e 5 · **Pronto quando:** testes de serviço via API da T5

## [ ] T5 · Rotas POST e GET e respostas de erro
- **Critérios da ficha:** c1, c2, c3, c4, c5, c6, c8
- **Regra de negócio:** a API devolve o status certo com a mensagem do que corrigir: 422 dado inválido, 409 apelido repetido, 403 chefe não atribuído, 404 sem acesso.
- **Critérios de aceite:**
  - [ ] `POST` (201) e `GET` em `/api/v1/clients/{client_id}/bank-accounts`; escritório vem da sessão, nunca do corpo; resposta sem `escritorio_id`
  - [ ] `InvalidBankAccountDataError` → 422 `application/problem+json`; `DuplicateNicknameError` → 409 'Já existe uma conta com este apelido neste cliente. Use outro apelido.'
  - [ ] Os 5 casos do c3 devolvem o mesmo corpo 404; o c8 devolve o mesmo corpo 403 nos 3 casos
  - [ ] Corpo sem campo (`bank` ou `nickname` ausentes) cai na mensagem da ficha, não no texto padrão do FastAPI (campos opcionais no modelo, como em `ClientRequest`)
- **Exemplos:** os de c1, c2, c3, c4, c5, c6 e c8 da ficha.
- **Arquivos:** `src/lastro/api/routes.py`
- **Reaproveitar:** `_membership`, `_problem`, `UNAUTHORIZED_RESPONSES`, handlers de 403/404 · **Não criar:** rota de apagar
- **Fora do escopo:** PATCH, tela
- **Pronto quando:** `pytest` dos testes de c1, c2, c3, c4, c5, c6 e c8 da ficha passam

## [ ] T6 · PATCH: alterar apelido e meses, encerrar a conta
- **Critérios da ficha:** c7
- **Regra de negócio:** o contador pode renomear a conta e ajustar ou encerrar o uso por mês; o banco não muda e nada é apagado.
- **Critérios de aceite:**
  - [ ] `PATCH …/bank-accounts/{account_id}` e `update_bank_account`; semântica da pergunta 4; valida contra os meses já gravados (fim antes do início → mensagem do c6)
  - [ ] Banco diferente → 422 'O banco de uma conta não pode ser trocado. Cadastre uma nova conta.'; apelido repetido (ignorando a própria conta) → 409
  - [ ] Conta de outro cliente ou de outra carteira → 404 idêntico ao do c3; recusa não muda nada
  - [ ] Nenhuma rota `DELETE`; contagem de linhas de `conta_bancaria` nunca diminui
- **Exemplos:** 'Conta movimento' → 'Conta principal'; último mês '2026-11' gravado como 2026-11-01; `bank` '237' → 422; apelido 'Conta digital' → 409.
- **Arquivos:** `src/lastro/registry/service.py`, `src/lastro/registry/repository.py`, `src/lastro/api/routes.py`
- **Reaproveitar:** funções da T3 e da T4 · **Não criar:** exclusão lógica ou coluna `ativo`
- **Fora do escopo:** troca de banco, `conta_contabil_id`
- **Pronto quando:** `pytest tests/registry/test_contas_bancarias.py::test_contador_altera_e_encerra_conta_sem_apagar -q` passa

## [ ] T7 · Documentar contratos v0 e regenerar o contrato da API
- **Critérios da ficha:** apoio (regra 11 do AGENTS.md)
- **Regra de negócio:** quem for consumir as contas (CAD-06, classificação) precisa achar o contrato e saber que está em versão 0.
- **Critérios de aceite:**
  - [ ] `docs/modulos/registry.md` e `ARCHITECTURE.md` §6 listam contratos, funções, rotas, mensagens e a ordem das checagens
  - [ ] `docs/api/openapi.json` regenerado se a CI o conferir (`src/lastro/api/export_openapi.py`)
- **Arquivos:** `docs/modulos/registry.md`, `ARCHITECTURE.md`, `docs/api/openapi.json`
- **Fora do escopo:** código; dado real
- **Pronto quando:** `hx verify` não acusa divergência de docs ou do OpenAPI

## [ ] T8 · Verificação final
- **Critérios de aceite:**
  - [ ] `git diff <hash-dos-testes> -- tests/` vazio
  - [ ] `ruff check .` limpo
  - [ ] `hx check-clean` e `hx verify` em OK
  - [ ] `hx feature verify CAD-04` grava `passing`
- **Pronto quando:** os três comandos do `hx` terminam com código 0
