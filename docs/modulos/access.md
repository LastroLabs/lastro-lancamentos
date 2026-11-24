# Módulo `access`: entrar, identificar a sessão e sair (ACE-01)

`src/lastro/access/` guarda quem é quem no escritório: usuário, vínculo (`membro`), papel e sessão.
As tabelas são da DB-01. Decisões em `planos/ACE-01/plan.md`.

## Rotas

| Rota | O que faz | Resposta |
|---|---|---|
| `POST /api/v1/session` | Entra com `{"username", "password"}` | 200 com a identificação e o cookie `lastro_session` |
| `GET /api/v1/session` | Diz quem está conectado | 200 com a identificação |
| `DELETE /api/v1/session` | Sai: a mesma sessão não vale mais | 204 e o cookie apagado |

Identificação: `username`, `name`, `role` (`manager` ou `accountant`), `firm_id`, `firm_name`.
Nunca traz senha, hash ou token.

## Recusas (401, `application/problem+json`)

| Situação | `detail` |
|---|---|
| Usuário inexistente, senha errada, usuário sem senha (convite pendente), usuário, vínculo ou escritório inativo, mais de um vínculo ativo | "Usuário ou senha incorretos." |
| Pedido sem o cookie | "Entre para continuar." |
| Cookie de sessão encerrada, expirada, inexistente ou de vínculo inativo | "Sua sessão terminou. Entre de novo." |

A primeira linha tem sempre o mesmo corpo e o mesmo custo: sem hash para conferir, a senha é
conferida contra um hash de mentira.

## Rota protegida (próximas fichas)

```python
from lastro.access.contracts import SignedInMember
from lastro.api.routes import require_signed_in_member

@router.get("/clients")
async def list_clients(member: Annotated[SignedInMember, Depends(require_signed_in_member)]):
    ...
```

`SignedInMember` traz `member_id`, `firm_id` e `role` (o `Role` da NUC-02): é o que a regra de
acesso (`lastro.core.service.decide_access`) precisa para montar o `Membership`.

## Senha

`lastro.access.service.hash_password(senha)` devolve o hash Argon2 (`argon2-cffi`, parâmetros
padrão) para `usuario.credencial_hash`. A ACE-02 usa ao aceitar o convite.

## Armadilhas

- **Cookie `Secure`.** O navegador aceita em `http://localhost`. Em teste, use
  `TestClient(app, base_url="https://testserver")`; com `http://` o cliente não reenvia o cookie.
- **Login em minúsculas.** A entrada compara `lower(identificador_login)`. Grave o login já em
  minúsculas (ACE-02); dois logins que só diferem na caixa travam os dois.
- **Um vínculo ativo por usuário.** Com dois escritórios, a entrada é recusada (plan, pergunta 2).
- **Prazo de 8 horas** a partir da entrada (`SESSION_DURATION`), sem renovar por uso.
- **RLS (NUC-03).** A entrada procura o usuário antes de saber o escritório; a política de
  `usuario` precisa deixar essa consulta passar.
- **Sem log de credencial.** Nada deste módulo registra senha, hash ou token.
