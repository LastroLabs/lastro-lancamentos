# Tasks — ACE-02 · Cadastrar contador por convite e atribuir cliente pelo chefe

**Plan:** planos/ACE-02/plan.md · **Ficha:** features/ACE-02.json
**Ordem:** T1 → revisão humana dos testes → commit só-de-testes (anotar o hash) → T2 em diante (sessão nova, sem editar `tests/`)
**Respondido (plan, seção 5):** rotas e campos em inglês; `{id}` é o id do **membro**. Falta o humano aprovar o plan.

---

## [x] T1 · Escrever os testes dos critérios
- **Critérios da ficha:** c1 a c11
- **Regra de negócio (em linguagem simples):** o chefe cadastra um contador sem senha e recebe, uma vez, um link de convite; o contador usa o link para criar a própria senha; o chefe pode trocar ou cancelar o convite e entregar clientes sem responsável a um membro ativo (ou a si mesmo). Tudo isolado por escritório.
- **Critérios de aceite:**
  - [ ] Existe um teste para cada um dos 14 nomes de `verificacao`, em `tests/access/test_cadastro_contador.py`
  - [ ] Testes extras (nomes próprios): `DELETE` sem convite pendente → 204; `GET` sem responsável → `null`; convite vencido na lista e novo convite sobre ele
  - [ ] Todos falham hoje pelo motivo certo (rota inexistente), sem quebrar a coleta
  - [ ] Só dados inventados; senhas geradas na hora (≥ 8 caracteres); banco em `head`; convite vencido criado direto no banco com `expira_em` no passado; c11 com duas conexões reais; c1 confere por SQL e por `caplog` que o código não foi gravado nem logado
- **Exemplos:** c1: chefe_1 cadastra "CONTADOR TESTE C" / `contador_c` → 201, `status` `convite_pendente`, código com ≥ 43 caracteres; c3 (a–e): mesma recusa 404; c11: dois aceites juntos → um 200 e uma recusa.
- **Arquivos:** `tests/access/test_cadastro_contador.py` (único)
- **Reaproveitar:** `head_database`, `office` e `_assert_problem` de `tests/access/test_login.py`; `tests/registry/test_cliente.py` para cliente · **Não criar:** `conftest.py` novo; fixture escrita à mão com dado real
- **Fora do escopo:** código de produção; editar testes de outras fichas
- **Pronto quando:** `docker compose run --rm dev pytest tests/access/test_cadastro_contador.py -q` mostra só falhas esperadas

## [x] T2 · Base: migração `0007`, configuração e modelo
- **Critérios da ficha:** c10 (e a validade de c1)
- **Regra de negócio (em linguagem simples):** o app precisa saber "esta pessoa já criou a senha? sim ou não" sem nunca ler o hash. Uma função do banco responde só isso, e só para pessoas do escritório da transação. A validade do convite vem de uma variável de ambiente.
- **Critérios de aceite:**
  - [ ] `migrations/versions/0007_…py` cria `usuarios_com_senha(uuid[])` → `usuario_id`, `tem_senha`: `SECURITY DEFINER`, dona `lastro_owner`, `search_path` fixo, `EXECUTE` só para `lastro_app` (padrão de 0005/0006); filtra por membro do escritório de `app.firm_id`; `downgrade` remove a função
  - [ ] Sem escritório na transação → 0 linhas, sem erro; id de outro escritório ou inexistente → ausente
  - [ ] `Settings` ganha a validade do convite (`LASTRO_CONVITE_HORAS`, padrão 48, inteiro ≥ 1); `.env.example` com valor de exemplo
  - [ ] `User.credencial_hash` com `deferred=True, deferred_raiseload=True` (D5); testes de ACE-01, ADM-01 e NUC-03 continuam verdes
- **Exemplos:** chamada em ESC-1 com chefe_1, contador_a (com senha) e contador_c (sem) → 3 linhas (sim, sim, não); contador_x de ESC-2 → ausente; sem escritório → 0 linhas.
- **Arquivos:** `migrations/versions/0007_*.py`, `src/lastro/core/config.py`, `src/lastro/access/models.py`, `.env.example`
- **Reaproveitar:** estrutura de `0006_client_link_lookup.py` · **Não criar:** coluna nova em `usuario`; política RLS permissiva
- **Fora do escopo:** rotas; `credencial_hash` em qualquer SELECT
- **Decisões relacionadas:** D3, D5; DECISIONS ACE-02/F1
- **Pronto quando:** `pytest tests/access/test_cadastro_contador.py::test_senha_criada_por_funcao_restrita -q` passa

## [x] T3 · Contratos e repositório de contador e convite
- **Critérios da ficha:** c1, c4, c5
- **Regra de negócio (em linguagem simples):** guardar e ler contadores e convites sempre dentro do escritório da sessão. O código do convite nunca é gravado, só o hash. Um contador tem no máximo um convite pendente: gerar outro cancela o anterior, mesmo vencido.
- **Critérios de aceite:**
  - [ ] Contratos imutáveis em `access/contracts.py` (pessoa da lista com situação, convite criado com código e validade) e erros próprios (contador não encontrado, já tem senha, convite inválido)
  - [ ] `repository.py`: inserir usuário sem senha + membro `contador` ativo; listar membros ativos só com colunas (`select(User.nome, …)`, nunca `select(User)`); inserir convite com `expira_em = now() + N horas` no banco e devolver `expira_em`; revogar o pendente; achar membro por id no escritório
  - [ ] Usuário repetido (qualquer caixa, neste ou em outro escritório) → `UsernameTakenError`, por consulta só de colunas, nunca por `buscar_usuario_por_login` (traria o hash)
  - [ ] Nenhuma função faz commit; nenhuma lê `credencial_hash`
- **Exemplos:** cadastrar `Contador_C` → grava `contador_c`; repetir `CONTADOR_C` → recusa; gerar convite sobre um vencido → o antigo fica revogado e o novo é o único pendente.
- **Arquivos:** `src/lastro/access/contracts.py`, `src/lastro/access/repository.py`
- **Reaproveitar:** `_membership_columns` e o padrão de `insert_firm_with_manager` · **Não criar:** segundo repositório; leitura direta de `convite` por `hash_token`
- **Fora do escopo:** serviço, rotas, aceite
- **Decisões relacionadas:** D1, D2, D6
- **Pronto quando:** `ruff check src/lastro/access` limpo e a T4 usa o repositório sem acesso direto a tabela

## [x] T4 · Serviço e rotas do chefe: cadastrar, listar, gerar e cancelar convite
- **Critérios da ficha:** c1, c4, c5, c8 (a–c), c9 (e)
- **Regra de negócio (em linguagem simples):** só o chefe faz isso. Nome ou usuário vazio é 422 e não cria nada. Usuário já usado é 409, sem dizer de qual escritório. O link de convite vale 48 h e aparece uma única vez. Contador que já criou a senha não recebe novo convite.
- **Critérios de aceite:**
  - [ ] `POST /api/v1/accountants` (201), `GET /api/v1/accountants`, `POST` e `DELETE /api/v1/accountants/{id}/invitation` (201 e 204)
  - [ ] Ordem: 401 → 403 'Só o chefe do escritório pode fazer isso.' (contador) → 404 'Contador não encontrado no seu escritório.' / 422 / 409
  - [ ] 422 'Informe o nome do contador.' e 'Informe o usuário de entrada do contador.'; 409 'Este usuário já existe. Escolha outro.'; 409 'Este contador já criou a senha.'
  - [ ] Resposta do cadastro e do novo convite traz o código e `/convite/<código>`; a lista nunca traz código nem hash
  - [ ] Situação via `usuarios_com_senha` e `expira_em <= now()` na consulta (F1 e F3)
  - [ ] Mapas de erro em `EXCEPTION_HANDLERS` (RFC 9457), mensagens em português simples
- **Exemplos:** chefe_1 cadastra → 201 com `convite_pendente`; lista com 3 pessoas; gerar convite para contador_a (com senha) → 409; chefe_2 gera para contador_c de ESC-1 → 404.
- **Arquivos:** `src/lastro/access/service.py`, `src/lastro/api/routes.py`
- **Reaproveitar:** `_problem`, `require_signed_in_member`, `ManagerOnlyError`, `UsernameTakenError`, `hash` SHA-256 de `service._hash_token` · **Não criar:** novo gerador de token; tradução de erro fora de `EXCEPTION_HANDLERS`
- **Fora do escopo:** página `/convite/<código>` do front; aceite
- **Decisões relacionadas:** D1, D2, D6; perguntas 1, 2, 4
- **Pronto quando:** `pytest tests/access/test_cadastro_contador.py -k "cadastra_contador or invalido_ou_duplicado or gera_novo or sem_papel or outro_escritorio" -q` passa nos testes de convite

## [x] T5 · Aceite do convite (sem login)
- **Critérios da ficha:** c2, c3, c11
- **Regra de negócio (em linguagem simples):** quem tem o código confirma o usuário e cria a senha, uma única vez. Convite que não existe, venceu, já foi usado, foi cancelado ou com usuário errado recebe sempre a mesma recusa, sem dizer nada do escritório. Senha curta é recusada **sem gastar** o convite. Dois aceites ao mesmo tempo: só um vale.
- **Critérios de aceite:**
  - [ ] `POST /api/v1/invitations/accept` com código, usuário e senha; 200 com 'Senha criada. Agora é só entrar.'; sem cookie de sessão
  - [ ] Acha o convite só por `buscar_convite_por_hash`; escritório da transação = o que a função devolveu (`use_firm`)
  - [ ] Ordem (D4): convite e usuário → 404 'Este convite não vale mais. Peça um novo ao chefe do escritório.' (corpo idêntico nos 5 casos) → senha < 8 → 422 'A senha precisa ter pelo menos 8 caracteres.' → `UPDATE convite SET usado_em = now() WHERE … usado_em IS NULL AND revogado_em IS NULL AND expira_em > now()` (0 linhas → rollback e 404) → `update(User)…values(credencial_hash=…)`
  - [ ] Hash da senha por `access.service.hash_password`, calculado antes da trava; tudo numa transação
  - [ ] Depois do aceite, o login da ACE-01 funciona e a lista mostra `ativo`; segundo aceite recusado e a senha continua a primeira
- **Exemplos:** K + `contador_c` + senha válida → 200; mesmo K de novo → 404; K + `contador_x` → 404 e K continua pendente; K + senha 'curta' → 422 e K aceita depois uma senha válida.
- **Arquivos:** `src/lastro/access/service.py`, `src/lastro/access/repository.py`, `src/lastro/api/routes.py`
- **Reaproveitar:** `use_firm`, `buscar_convite_por_hash`, `MIN_PASSWORD_LENGTH` de `access/admin.py` · **Não criar:** consulta direta a `convite` por hash; `select(User)`; leitura de `credencial_hash`
- **Fora do escopo:** abrir sessão no aceite (o contador entra pelo login); página do front
- **Decisões relacionadas:** D4; DECISIONS ACE-02/F2 a F4
- **Pronto quando:** `pytest tests/access/test_cadastro_contador.py -k "aceita_convite or convite_invalido or senha_curta or aceites_simultaneos" -q` passa

## [x] T6 · Atribuição de cliente pelo chefe
- **Critérios da ficha:** c6, c7, c8 (e), c9 (a–d)
- **Regra de negócio (em linguagem simples):** o chefe entrega um cliente sem responsável a um membro ativo do escritório, inclusive a si mesmo. Cliente que já tem responsável não é atribuído de novo aqui (a troca é da ACE-04). Cliente ou responsável de outro escritório recebe a mesma recusa de "não existe".
- **Critérios de aceite:**
  - [ ] `POST /api/v1/clients/{id}/assignment` (201) e `GET /api/v1/clients/{id}/assignment`
  - [ ] 1 linha em `atribuicao` com `fim` nulo e `atribuido_por` = membro do chefe; `inicio` do banco
  - [ ] Ordem (P-09): 401 → 404 'Você não tem acesso a este cliente.' → 403 'Só o chefe do escritório pode fazer isso.' (`decide_access` com `MANAGE_ASSIGNMENT`) → 404 'Responsável não encontrado no seu escritório.' → 409 'Este cliente já tem um responsável. Use a reatribuição.'
  - [ ] Contador com convite pendente pode receber cliente; corrida entre duas atribuições termina em 409
  - [ ] A existência do cliente vem da função combinada na pergunta 3 do plan; o `access` não lê `cliente` nem importa modelos do `registry`
- **Exemplos:** EMP-1 → contador_c: 201; EMP-2 → chefe_1: 201; EMP-1 → contador_c de novo: 409; chefe_2 com EMP-1: 404.
- **Arquivos:** `src/lastro/access/service.py`, `src/lastro/access/repository.py`, `src/lastro/api/routes.py` (e `registry/service.py` só se a pergunta 3 = A)
- **Reaproveitar:** `core.service.decide_access`, `ClientNotFoundError`, `ManagerOnlyError`, `responsible_member_ids` · **Não criar:** segunda regra de acesso; reatribuição
- **Fora do escopo:** trocar responsável (ACE-04); lista do contador (ACE-03)
- **Decisões relacionadas:** D6; perguntas 2, 3, 5
- **Pronto quando:** `pytest tests/access/test_cadastro_contador.py -k "atribui or atribuido or atribuir" -q` passa

## [x] T7 · Documentação e OpenAPI
- **Critérios da ficha:** apoio a todos
- **Regra de negócio (em linguagem simples):** quem vem depois precisa achar as rotas, os erros e o contrato novo sem ler o código.
- **Critérios de aceite:**
  - [ ] `docs/modulos/access.md` com rotas, recusas, situação do contador e a função `usuarios_com_senha`
  - [ ] `docs/api/openapi.json` regenerado por `lastro.api.export_openapi`; teste de `tests/web` continua verde
  - [ ] `ARCHITECTURE.md` (seção 6) cita os contratos novos do `access`, versão 0
  - [ ] Humano avisado para abrir a issue `contrato:` (pergunta 8)
- **Exemplos:** a tabela de rotas lista as 9 rotas novas e seus códigos de status.
- **Arquivos:** `docs/modulos/access.md`, `docs/api/openapi.json`, `ARCHITECTURE.md`, `progress/ACE-02.md`
- **Reaproveitar:** formato de `docs/modulos/access.md` · **Não criar:** doc novo fora de `docs/modulos/`
- **Fora do escopo:** editar `features/ACE-02.json` (vai por PR do humano)
- **Pronto quando:** `pytest tests/web -q` passa e a tabela do módulo cobre todas as rotas

## [ ] T8 · Verificação final
- **Critérios de aceite:**
  - [ ] `git diff <hash-dos-testes> -- tests/` vazio
  - [ ] `ruff check .` limpo
  - [ ] `hx check-clean` e `hx verify` em OK (sem senha nem usuário real nos testes)
  - [ ] `hx feature verify ACE-02` grava `passing`
- **Pronto quando:** os três comandos do `hx` terminam com código 0
