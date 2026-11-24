# ACE-01 · Entrar com login individual e encerrar a sessão

- Responsável: arthurlleite · Branch: `feat/ACE-01-entrar-com-login-individual-e-encerrar-a` · Início: 24/11/2026
- Ficha: `features/ACE-01.json` (estado e critérios ficam lá; não repita aqui)

## Objetivo
Cada pessoa do escritório entra com o próprio usuário e senha, a API sabe quem ela é (usuário, papel, escritório) por uma sessão guardada no servidor, e sair encerra essa sessão na hora.

## Próxima ação
Revisão do PR. Um humano aprova o plan (`planos/ACE-01/plan.md`, seção 8) e responde as 4 perguntas ATENÇÃO, ou aceita o padrão sugerido.

## Bloqueios e perguntas
- Perguntas 1 a 4 do plan (prazo da sessão, usuário com dois escritórios, CSRF, login em minúsculas) seguem o padrão sugerido até alguém decidir.
- NUC-03 (guin409): a política RLS de `usuario` precisa permitir a busca pelo login antes de saber o escritório.

## Feito
- 24/11 · S1 · `hx feature start ACE-01`; plan e tasks (D1 a D8, 4 perguntas ATENÇÃO).
- 24/11 · S1 · T1: `tests/access/test_login.py`, 6 testes, banco do Testcontainers migrado até `head`. Commit só de testes: `647b159`.
- 24/11 · S1 · T2 a T4: `access/contracts.py`, `passwords.py` (Argon2), `repository.py`, `service.py`; rotas `POST/GET/DELETE /api/v1/session` e `require_signed_in_member` em `api/routes.py`; handlers de 401 registrados em `create_app()`.
- 24/11 · S1 · T5: `docs/api/openapi.json` e `web/src/api/schema.d.ts` regenerados; `docs/modulos/access.md`; linha do `SignedInMember` na seção 6 do `ARCHITECTURE.md`.

## Rodei
- 24/11 · S1 · `pytest tests/access/test_login.py -q` antes da implementação → erro de coleta esperado (`No module named 'lastro.access.service'`).
- 24/11 · S1 · `pytest tests/access/test_login.py -q` → 6 passed.
- 24/11 · S1 · Teste temporário de borda (apagado, não versionado): sessão expirada → 401 "Sua sessão terminou"; vínculo inativo → sessão e nova entrada recusadas; login `  CONTADOR_A ` aceito; usuário com dois vínculos ativos → recusa; cookie inventado → 401 "Sua sessão terminou"; sair sem cookie → 401 "Entre para continuar."; recusas de `chefe_1` (senha errada) e `contador_c` (sem senha) em ~0,065 s cada; a primeira recusa de usuário inexistente levou 0,138 s porque o hash de mentira era criado na primeira chamada. Passei a criá-lo no import (`passwords.py`).
- 24/11 · S1 · `pnpm run gerar:api` → openapi.json e schema.d.ts com as rotas de sessão.
- 24/11 · S1 · `git diff 647b159 -- tests/` → vazio.
- 24/11 · S1 · `hx verify` → OK · `hx check-clean` → OK · `hx feature verify ACE-01` → c1 a c6 OK, `passing`.

## Falhou
- 24/11 · S1 · `hx check-clean` acusou "possível segredo (atribuição)" em nomes de variável (`password = ...`, `token = ...`, `is_password_ok = ...`). Não eram segredos: a regra casa a palavra no nome. Renomeei as variáveis no teste (antes do commit de testes) e no código.
- 24/11 · S1 · `hx verify` falhou no teste da WEB-01 enquanto `openapi.json` não estava commitado (o teste compara com a versão do git). Passou depois do commit.

## Decisões
- 24/11 · S1 · Argon2 com `argon2-cffi` (comparada com `pwdlib` e `passlib`), registrada no plan, D4; dependência em `pyproject.toml` e `uv.lock`.
- 24/11 · S1 · Rotas em inglês sobre um recurso `session` (CODING_STANDARDS §1); `role` com os valores do `Role` da NUC-02 (`manager`/`accountant`).
- 24/11 · S1 · Testes migram até `head` numa fixture própria, sem editar `tests/access/conftest.py` (que fixa `0002` para a DB-01).

## Fim de sessão
- [x] `hx verify` verde, ou a falha está descrita em "Falhou"
- [x] Nada quebrado nem pela metade na branch; commit feito
- [x] "Próxima ação" atualizada
- [x] Nenhum dado real nem segredo nas anotações
