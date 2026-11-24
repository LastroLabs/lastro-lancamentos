# Tasks — ACE-01 · Entrar com login individual e encerrar a sessão

**Plan:** planos/ACE-01/plan.md · **Ficha:** features/ACE-01.json
**Ordem:** T1 → revisão humana dos testes → commit só-de-testes (anotar o hash) → T2 em diante (sessão nova, sem editar `tests/`)

Dados de referência (inventados, iguais aos da ficha): escritório `ESC-1`; `chefe_1` (chefe), `contador_a`, `contador_b` e `contador_c` (contador; `contador_c` com convite pendente e sem senha). Senhas geradas na hora pelo teste.

---

## [x] T1 · Escrever os testes dos critérios
- **Critérios da ficha:** c1 a c6
- **Regra de negócio (em linguagem simples):** cada pessoa do escritório entra com o próprio usuário e a própria senha. O sistema sabe quem é, de que escritório e com que papel, até a pessoa sair. Quem erra não descobre se o erro foi no usuário ou na senha.
- **Critérios de aceite:**
  - [x] `tests/access/test_login.py` com as 6 funções citadas em `verificacao`
  - [x] Banco do Testcontainers migrado até `head` numa fixture do próprio arquivo (plan, D8); usuários gravados direto no banco com hash de `hash_password`
  - [x] c2 e c6 comparam o corpo inteiro das recusas e contam as linhas de `sessao`
  - [x] Nenhuma resposta traz a senha, o hash ou o token no corpo
  - [x] Todos falham hoje pelo motivo certo (falta `lastro.access.service` ou a rota), não por erro no teste
- **Exemplos:** `contador_a` + senha certa → 200 e `{"username": "contador_a", "role": "accountant", "firm_name": "ESC-1", ...}`; senha errada → 401 "Usuário ou senha incorretos."
- **Arquivos:** `tests/access/test_login.py`
- **Fora do escopo:** código de produção; `tests/access/conftest.py`
- **Pronto quando:** `docker compose run --rm dev pytest tests/access/test_login.py -q` mostra só falhas esperadas

## [x] T2 · Contratos, senha e regra de entrada
- **Critérios da ficha:** c1, c2, c6
- **Regra de negócio (em linguagem simples):** a senha nunca é guardada; guarda-se um resumo (Argon2) que só confere. Usuário que ainda não criou a senha, inativo ou sem escritório recebe a mesma recusa de senha errada.
- **Critérios de aceite:**
  - [x] `SignedInMember`, `InvalidCredentialsError` e `SessionEndedError` em `access/contracts.py`
  - [x] `hash_password` e conferência com hash de mentira quando não há hash (plan, D5)
  - [x] Login comparado em minúsculas, sem espaço nas pontas (pergunta 4)
  - [x] Exatamente um vínculo ativo em escritório ativo; senão, recusa (pergunta 2)
- **Exemplos:** `contador_c` com `credencial_hash` nulo e senha vazia → `InvalidCredentialsError`
- **Arquivos:** `src/lastro/access/contracts.py`, `src/lastro/access/passwords.py`, `src/lastro/access/service.py`, `src/lastro/access/repository.py`, `pyproject.toml`, `uv.lock`
- **Reaproveitar:** `Role` de `core/contracts.py`; modelos da DB-01 · **Não criar:** migração; cadastro de usuário
- **Fora do escopo:** aceite de convite (ACE-02)
- **Decisões relacionadas:** D3, D4, D5, D7
- **Pronto quando:** `pytest tests/access/test_login.py -q -k "mesma_recusa"` passa depois da T4 (a prova é por HTTP)

## [x] T3 · Sessão no servidor
- **Critérios da ficha:** c1, c3, c4
- **Regra de negócio (em linguagem simples):** cada entrada gera uma chave nova e secreta. O banco guarda só o resumo dela, com data de criação, validade e de encerramento. Sair encerra na hora.
- **Critérios de aceite:**
  - [x] Token de 32 bytes; `sessao.hash_token` = SHA-256 em hexadecimal
  - [x] `expira_em` = entrada + 8 h (pergunta 1)
  - [x] `identify` recusa sessão encerrada, expirada, inexistente ou de vínculo, usuário ou escritório inativo
  - [x] `sign_out` grava `encerrada_em`
- **Exemplos:** duas entradas de `contador_a` → duas linhas em `sessao` com hashes diferentes
- **Arquivos:** `src/lastro/access/service.py`, `src/lastro/access/repository.py`
- **Fora do escopo:** expiração por inatividade; limpar sessões antigas
- **Decisões relacionadas:** D2, D6
- **Pronto quando:** `pytest tests/access/test_login.py -q -k "sessoes_simultaneas or sair"` passa depois da T4

## [x] T4 · Rotas, cookie e erros
- **Critérios da ficha:** c1 a c6
- **Regra de negócio (em linguagem simples):** a API entrega a chave num cookie que o JavaScript não lê, e responde "Entre para continuar." para quem chega sem sessão.
- **Critérios de aceite:**
  - [x] `POST`, `GET` e `DELETE /api/v1/session` (plan, D1)
  - [x] Cookie `lastro_session` com `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/api`; apagado ao sair
  - [x] Dependência `require_signed_in_member` para as próximas fichas
  - [x] 401 em `application/problem+json`, mensagem em `detail`, sem dado de usuário ou de escritório
- **Exemplos:** `GET /api/v1/session` sem cookie → 401 "Entre para continuar."
- **Arquivos:** `src/lastro/api/routes.py`
- **Reaproveitar:** `Problem` e `PROBLEM_JSON` de `api/routes.py`; `get_session` de `core/db.py`
- **Fora do escopo:** token CSRF (pergunta 3); tela de login
- **Decisões relacionadas:** D1, D2, D6
- **Pronto quando:** `pytest tests/access/test_login.py -q` passa

## [x] T5 · OpenAPI, cliente do front e doc do módulo
- **Critérios de aceite:**
  - [x] `docs/api/openapi.json` e `web/src/api/schema.d.ts` regenerados com `pnpm run gerar:api`
  - [x] `docs/modulos/access.md` com as rotas, o cookie, a dependência e as armadilhas
- **Arquivos:** `docs/api/openapi.json`, `web/src/api/schema.d.ts`, `docs/modulos/access.md`
- **Pronto quando:** `pytest tests/web/test_web_foundation.py -q -k gerado` passa

## [x] T6 · Verificação final
- **Critérios de aceite:**
  - [x] `git diff <hash-dos-testes> -- tests/` vazio
  - [x] `ruff check .` limpo
  - [x] `hx check-clean` e `hx verify` em OK
  - [x] `hx feature verify ACE-01` grava `passing`
- **Pronto quando:** os três comandos do `hx` terminam com código 0

---

Respostas às perguntas 1 e 2 (caio-nascime, 24/11, na revisão do #57). A T3 trocou de prazo: as 8 h corridas viram D9.

## [ ] T7 · Testes de inatividade e de quem tem dois escritórios
- **Decisões relacionadas:** D9, D10
- **Regra de negócio (em linguagem simples):** a sessão cai depois de 2 h sem uso e nunca passa de 12 h. Quem tem vínculo em dois escritórios não entra no MVP; com a senha certa recebe um aviso próprio, com a errada a recusa de sempre.
- **Critérios de aceite:**
  - [ ] Novo arquivo `tests/access/test_login_prazo_e_escritorio.py`; `tests/access/test_login.py` não muda
  - [ ] Pedido aceito renova `expira_em` para agora + 2 h, sem passar de `criada_em` + 12 h
  - [ ] Sessão parada além de `expira_em` ou com mais de 12 h → 401 "Sua sessão terminou. Entre de novo."
  - [ ] Dois vínculos ativos: senha errada → 401 de sempre; senha certa → 409 "Este usuário está em mais de um escritório. Peça ao chefe um usuário para cada escritório."; sem nome de escritório, sem cookie, sem sessão
  - [ ] Falham hoje pelo motivo certo
- **Arquivos:** `tests/access/test_login_prazo_e_escritorio.py`
- **Pronto quando:** `pytest tests/access/test_login_prazo_e_escritorio.py -q` mostra só falhas esperadas

## [ ] T8 · Implementar D9 e D10
- **Critérios de aceite:**
  - [ ] `SESSION_IDLE_TIMEOUT` (2 h) e `SESSION_MAX_DURATION` (12 h) em `access/service.py`; `identify` renova o prazo
  - [ ] `MultipleFirmsError` em `access/contracts.py`; 409 na API, só depois da senha certa
  - [ ] OpenAPI e `schema.d.ts` regenerados; `docs/modulos/access.md` e `docs/decisoes/DECISIONS.md` (seção 7) atualizados
  - [ ] `git diff <novo-hash-dos-testes> -- tests/` vazio; `hx verify`, `hx check-clean` e `hx feature verify ACE-01` em OK
- **Arquivos:** `src/lastro/access/`, `src/lastro/api/routes.py`, `docs/api/openapi.json`, `web/src/api/schema.d.ts`, `docs/modulos/access.md`
- **Pronto quando:** `pytest tests/access -q` passa
