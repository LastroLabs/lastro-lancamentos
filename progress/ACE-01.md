# ACE-01 · Entrar com login individual e encerrar a sessão

- Responsável: arthurlleite · Branch: `feat/ACE-01-entrar-com-login-individual-e-encerrar-a` · Início: 24/11/2026
- Ficha: `features/ACE-01.json` (estado e critérios ficam lá; não repita aqui)

## Objetivo
Cada pessoa do escritório entra com o próprio usuário e senha, a API sabe quem ela é (usuário, papel, escritório) por uma sessão guardada no servidor, que cai depois de 2 h sem uso (teto de 12 h), e sair encerra essa sessão na hora.

## Próxima ação
Revisão do PR #57. Um humano aprova o plan (`planos/ACE-01/plan.md`, seção 8): confirmar D1 a D10 e as perguntas 3 e 4, que seguem o padrão sugerido.

## Bloqueios e perguntas
- Perguntas 3 e 4 do plan (CSRF, login em minúsculas) seguem o padrão sugerido até alguém decidir. As perguntas 1 e 2 foram respondidas (D9 e D10).
- NUC-03 (guin409): a política RLS de `usuario` precisa permitir a busca pelo login antes de saber o escritório.

## Feito
- 24/11 · S1 · `hx feature start ACE-01`; plan e tasks (D1 a D8, 4 perguntas ATENÇÃO).
- 24/11 · S1 · T1: `tests/access/test_login.py`, 6 testes, banco do Testcontainers migrado até `head`. Commit só de testes: `647b159`.
- 24/11 · S1 · T2 a T4: `access/contracts.py`, `passwords.py` (Argon2), `repository.py`, `service.py`; rotas `POST/GET/DELETE /api/v1/session` e `require_signed_in_member` em `api/routes.py`; handlers de 401 registrados em `create_app()`.
- 24/11 · S1 · T5: `docs/api/openapi.json` e `web/src/api/schema.d.ts` regenerados; `docs/modulos/access.md`; linha do `SignedInMember` na seção 6 do `ARCHITECTURE.md`.
- 24/11 · S2 · Respostas de caio-nascime na revisão do #57: pergunta 1 → sessão cai depois de 2 h sem uso, com teto de 12 h (D9); pergunta 2 → um escritório por usuário no MVP, com erro próprio 409 depois da senha certa (D10). Registro em `DECISIONS.md`, seção 7.
- 24/11 · S2 · T7: `tests/access/test_login_prazo_e_escritorio.py` (5 testes), sem mexer em `test_login.py`. Novo commit só de testes: `47526e6`.
- 24/11 · S2 · T8: `SESSION_IDLE_TIMEOUT`/`SESSION_MAX_DURATION`, `identify` renova `expira_em`; `MultipleFirmsError` → 409; cookie com `max_age` de 12 h; OpenAPI regenerado; `docs/modulos/access.md`.

## Rodei
- 24/11 · S1 · `pytest tests/access/test_login.py -q` antes da implementação → erro de coleta esperado (`No module named 'lastro.access.service'`).
- 24/11 · S1 · `pytest tests/access/test_login.py -q` → 6 passed.
- 24/11 · S1 · Teste temporário de borda (apagado, não versionado): sessão expirada → 401 "Sua sessão terminou"; vínculo inativo → sessão e nova entrada recusadas; login `  CONTADOR_A ` aceito; usuário com dois vínculos ativos → recusa; cookie inventado → 401 "Sua sessão terminou"; sair sem cookie → 401 "Entre para continuar."; recusas de `chefe_1` (senha errada) e `contador_c` (sem senha) em ~0,065 s cada; a primeira recusa de usuário inexistente levou 0,138 s porque o hash de mentira era criado na primeira chamada. Passei a criá-lo no import (`passwords.py`).
- 24/11 · S1 · `pnpm run gerar:api` → openapi.json e schema.d.ts com as rotas de sessão.
- 24/11 · S1 · `git diff 647b159 -- tests/` → vazio.
- 24/11 · S1 · `hx verify` → OK · `hx check-clean` → OK · `hx feature verify ACE-01` → c1 a c6 OK, `passing`.
- 24/11 · S2 · `pytest tests/access/test_login_prazo_e_escritorio.py -q` antes da T8 → falhas esperadas (prazo de 8 h, sem renovação, sem teto; 401 em vez de 409).
- 24/11 · S2 · `pytest tests/access -q` → 81 passed · `git diff 47526e6 -- tests/` → vazio.
- 24/11 · S2 · `hx verify` → OK · `hx check-clean` → OK · `hx feature verify ACE-01` → c1 a c6 OK, `passing`.

## Falhou
- 24/11 · S1 · `hx check-clean` acusou "possível segredo (atribuição)" em nomes de variável (`password = ...`, `token = ...`, `is_password_ok = ...`). Não eram segredos: a regra casa a palavra no nome. Renomeei as variáveis no teste (antes do commit de testes) e no código.
- 24/11 · S1 · `hx verify` falhou no teste da WEB-01 enquanto `openapi.json` não estava commitado (o teste compara com a versão do git). Passou depois do commit.

## Decisões
- 24/11 · S1 · Argon2 com `argon2-cffi` (comparada com `pwdlib` e `passlib`), registrada no plan, D4; dependência em `pyproject.toml` e `uv.lock`.
- 24/11 · S1 · Rotas em inglês sobre um recurso `session` (CODING_STANDARDS §1); `role` com os valores do `Role` da NUC-02 (`manager`/`accountant`).
- 24/11 · S1 · Testes migram até `head` numa fixture própria, sem editar `tests/access/conftest.py` (que fixa `0002` para a DB-01).
- 24/11 · S2 · A escolha do escritório na entrada (lista + `firm_id`) chegou a ser feita localmente e foi descartada antes do push, a pedido de caio-nascime: mudaria a lógica do convite (ACE-02) e não cabe no prazo do MVP.

## Fim de sessão
- [x] `hx verify` verde, ou a falha está descrita em "Falhou"
- [x] Nada quebrado nem pela metade na branch; commit feito
- [x] "Próxima ação" atualizada
- [x] Nenhum dado real nem segredo nas anotações
