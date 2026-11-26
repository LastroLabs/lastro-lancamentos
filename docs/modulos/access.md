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

## Recusas (`application/problem+json`)

| Situação | `detail` |
|---|---|
| Usuário inexistente, senha errada, usuário sem senha (convite pendente), usuário, vínculo ou escritório inativo | "Usuário ou senha incorretos." |
| Pedido sem o cookie | "Entre para continuar." |
| Cookie de sessão encerrada, expirada, inexistente ou de vínculo inativo | "Sua sessão terminou. Entre de novo." |

Mais de um vínculo ativo, **com a senha certa**: 409 "Este usuário está em mais de um
escritório. Peça ao chefe um usuário para cada escritório." (D10). Com a senha errada, vale a 401
de sempre, então o 409 não revela a conta a quem não sabe a senha.

A primeira linha da tabela (401) tem sempre o mesmo corpo e o mesmo custo: sem hash para conferir, a senha é
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

## Responsável ativo do cliente (CAD-03)

`lastro.access.service.responsible_member_ids(db, firm_id, client_ids) -> dict[str, str | None]`
devolve, para cada id pedido, o `member_id` da atribuição aberta (`atribuicao.fim IS NULL`) no
escritório, ou `None`. Não grava nada. A `api/` passa essa função a
`lastro.registry.service.list_clients` e `get_client` (plano CAD-03, D3), para o `registry` não
importar o `access`. Versão 0, sem issue `contrato:` (decisão de caio-nascime); mudança avisa os
donos da ACE-02 e da ACE-03 no PR.

## Senha

`lastro.access.service.hash_password(senha)` devolve o hash Argon2 (`argon2-cffi`, parâmetros
padrão) para `usuario.credencial_hash`. A ACE-02 usa ao aceitar o convite.

## Primeiro acesso (ADM-01)

Antes de existir convite (ACE-02), quem instala o sistema cria o primeiro escritório e o seu chefe
por comando. Escritório, usuário e vínculo `chefe` ativo entram numa transação só: ou criam os
três, ou nenhum. O comando não cria contador, cliente nem convite.

```bash
LASTRO_SENHA_CHEFE='<senha do chefe>' \
python -m lastro.access.admin criar-escritorio \
  --escritorio '<nome do escritório>' --usuario '<login do chefe>' --nome '<nome do chefe>'
```

- **Senha só pela variável `LASTRO_SENHA_CHEFE`.** `--senha` é recusado, porque a senha vazaria no
  histórico do shell e em `ps`. Sem a variável e com terminal, o comando pede a senha duas vezes,
  sem eco. Sem terminal, recusa. A senha tem no mínimo 8 caracteres e nunca aparece na saída.
- **Códigos de saída:** `0` criado (saída padrão); `1` usuário já existe ou banco inacessível; `2`
  dado faltando ou senha na linha de comando (os dois últimos na saída de erro).
- **Mensagens:** "Informe o nome do escritório.", "Informe o usuário do chefe.", "Informe o nome do
  chefe.", "Defina a senha do chefe na variável LASTRO_SENHA_CHEFE.", "Não escreva a senha no
  comando. Use a variável LASTRO_SENHA_CHEFE.", "A senha do chefe deve ter pelo menos 8
  caracteres.", "O usuário `<login>` já existe. Nada foi alterado."
- **Usuário que já existe** (em qualquer caixa, ativo ou não) é recusado sem alterar nada, nem a
  senha, e sem criar escritório. O login é gravado em minúsculas.
- **Nome de escritório repetido é permitido.** O que identifica é o login do chefe.
- **Aviso NUC-03:** a gravação usa o papel da aplicação (`DATABASE_URL`). Quando entrar a RLS, a
  política precisa deixar o comando inserir `escritorio`, `usuario` e `membro`.
- **Papel na identificação:** o banco guarda `chefe`; a rota `GET /api/v1/session` devolve
  `manager` (ver "Rotas").

Lógica em `service.create_firm_with_manager`; `admin.py` só lê argumentos e escreve a saída.

**Contrato novo (versão 0, issue `contrato:` [#68](https://github.com/LastroLabs/lastro-lancamentos/issues/68)),
aprovado em 25/11/2026:**

| Item | Onde | Para que serve |
|---|---|---|
| `CreatedFirm(firm_name, username)` | `contracts.py` | Resultado da criação; `username` é o login gravado, em minúsculas |
| `UsernameTakenError` | `contracts.py` | Login já existe; nada foi gravado nem alterado |
| `create_firm_with_manager(db, firm_name, username, name, password)` | `service.py` | Grava escritório, usuário e vínculo `chefe` numa transação, com um só `commit` |

A ACE-02 deve reaproveitar `hash_password` e gravar o login em minúsculas. Mudou o contrato?
Comente na #68 e avise caio-nascime (ACE-02) e jvsauma (NUC-03).

## Armadilhas

- **Cookie `Secure`.** O navegador aceita em `http://localhost`. Em teste, use
  `TestClient(app, base_url="https://testserver")`; com `http://` o cliente não reenvia o cookie.
- **Login em minúsculas.** A entrada compara `lower(identificador_login)`. Grave o login já em
  minúsculas (ACE-02); dois logins que só diferem na caixa travam os dois.
- **Um vínculo ativo por usuário** no MVP (D10, `DECISIONS.md` seção 7). Quem trabalha em dois escritórios usa um usuário em cada; com dois vínculos, a entrada dá o 409 acima.
- **Prazo da sessão (plan, D9):** cai depois de 2 h sem uso (`SESSION_IDLE_TIMEOUT`) e nunca passa de 12 h desde a entrada (`SESSION_MAX_DURATION`). O token não muda: cada pedido aceito só empurra `sessao.expira_em` no banco. Por isso `identify` grava e faz commit, e toda rota protegida custa um `UPDATE` em `sessao`. O cookie vale 12 h no navegador; quem decide se a sessão ainda vale é o servidor.
- **RLS (NUC-03).** A entrada procura o usuário antes de saber o escritório; a política de
  `usuario` precisa deixar essa consulta passar.
- **Sem log de credencial.** Nada deste módulo registra senha, hash ou token.

## Tabelas da DB-03: competência e link do cliente

Migração `0004` (filha de `0003`); modelos `Period` (`competencia`) e `ClientLink` (`link_cliente`).
Decisões em `planos/DB-03/plan.md`.

**O banco já garante:**
- Uma competência por cliente e mês, e o mês sempre no dia 1, em qualquer fuso da sessão.
- O link guarda só `hash_token` (64 hexadecimais minúsculos, único em todo o banco), nunca o código.
- O link aponta para uma competência do mesmo cliente e é criado por um membro do mesmo escritório.
- `expira_em` depois de `criado_em`; `revogado_em` vazio ou não anterior a `criado_em`.

**Fica para a ACE-05:** conferir que quem cria o link é o responsável ativo (P-09) e calcular
`expira_em` (prazo da D-06; sem valor padrão no banco).

**Fica para a NUC-03:** a RLS destas tabelas e a busca do link pelo `hash_token` sem escritório
no contexto (recomendação em `progress/DB-03.md`, a decisão é do dono da NUC-03).
