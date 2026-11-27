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
- **Com a RLS (NUC-03):** a gravação usa o papel da aplicação (`DATABASE_URL`).
  `insert_firm_with_manager` gera o `id` do escritório no app (`uuid4`) e põe a sessão em nome
  dele antes do primeiro insert (plano NUC-03, D5). Sem política aberta.
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
Comente na #68 e avise jvsauma (ACE-02 e NUC-03).

## Armadilhas

- **Cookie `Secure`.** O navegador aceita em `http://localhost`. Em teste, use
  `TestClient(app, base_url="https://testserver")`; com `http://` o cliente não reenvia o cookie.
- **Login em minúsculas.** A entrada compara `lower(identificador_login)`. Grave o login já em
  minúsculas (ACE-02); dois logins que só diferem na caixa travam os dois.
- **Um vínculo ativo por usuário** no MVP (D10, `DECISIONS.md` seção 7). Quem trabalha em dois escritórios usa um usuário em cada; com dois vínculos, a entrada dá o 409 acima.
- **Prazo da sessão (plan, D9):** cai depois de 2 h sem uso (`SESSION_IDLE_TIMEOUT`) e nunca passa de 12 h desde a entrada (`SESSION_MAX_DURATION`). O token não muda: cada pedido aceito só empurra `sessao.expira_em` no banco. Por isso `identify` grava e faz commit, e toda rota protegida custa um `UPDATE` em `sessao`. O cookie vale 12 h no navegador; quem decide se a sessão ainda vale é o servidor.
- **RLS (NUC-03).** A entrada procura o usuário antes de saber o escritório, por
  `buscar_usuario_por_login`. A aplicação não lê `usuario.credencial_hash` direto: um
  `SELECT *` em `usuario` falha para `lastro_app`. Leia só as colunas de que precisa.
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

**Feito na NUC-03:** a RLS destas tabelas e a busca do link pelo `hash_token` sem escritório
(`buscar_link_por_hash`, migração `0006`). Ver a seção abaixo.

## Isolamento no banco (NUC-03)

Migrações `0005` e `0006`; decisões em `planos/NUC-03/plan.md` e em `DECISIONS.md`, seção 10.

**Como funciona:** as 12 tabelas com escritório têm RLS ligada e forçada. Uma linha só aparece, e
só pode ser gravada, numa transação em nome do escritório dela. Sem escritório, a aplicação vê 0
linhas e não grava nada, sem erro.

**Como usar:** com uma sessão de `Database.sessionmaker`, chame `use_firm(db, firm_id)`
(`lastro.core.db`). O escritório vale para todas as transações seguintes da mesma sessão, também
depois de um `commit`. Nas rotas protegidas, `identify` já deixa a sessão em nome do escritório do
membro.

**Buscas antes de se saber o escritório:** só pelas funções abaixo, nunca por consulta direta.
Todas são `SECURITY DEFINER`, pertencem a `lastro_owner`, têm `search_path` fixo e só
`lastro_app` pode executá-las. Depois da busca, chame `use_firm` com o `escritorio_id` devolvido
e siga normalmente.

| Função | Recebe | Devolve | Quem usa |
|---|---|---|---|
| `buscar_usuario_por_login` | login em minúsculas | `usuario_id`, `credencial_hash`, `ativo` | entrada (ACE-01) |
| `buscar_vinculos_do_usuario` | `usuario_id` | `escritorio_id`, `membro_id`, `papel`, um por vínculo ativo | entrada (ACE-01) |
| `buscar_sessao_por_hash` | hash do token | `escritorio_id`, `membro_id`, `expira_em`, `encerrada_em` | `identify`, `sign_out` |
| `buscar_convite_por_hash` | hash do código | `escritorio_id`, `convite_id`, `membro_id`; só convite pendente | aceite do convite (ACE-02) |
| `buscar_link_por_hash` | hash do código | `escritorio_id`, `link_id`, `cliente_id`, `competencia_id`, `expira_em`; link invalidado não volta | abrir o link (ACE-05) |

Nomes e retornos são contrato v0 (regra 11). Mudou? Abra issue `contrato:` e avise o dono da
NUC-03 e quem usa a função.

**Link do cliente (ACE-05):**
- O link **vencido** volta da função. Quem recusa é o app, comparando `expira_em` com o próprio
  relógio, com a mesma recusa do código inexistente (P5 = A). Sem essa comparação, o link vencido
  funciona.
- A RLS isola por **escritório, não por cliente**. Depois de `use_firm`, o banco mostra todos os
  clientes daquele escritório. Filtre sempre pelo `cliente_id` e pelo `competencia_id` que a função
  devolveu, e ignore qualquer identificador vindo da requisição (ACE-05, c8).
- Pendências antes do plano da ACE-05: quem cria a competência e onde se configura a validade
  (`DECISIONS.md`, seção 10, Q1 e Q2).

**Armadilhas:**
- **Tabela nova com `escritorio_id`** precisa, na própria migração, de `ENABLE` e `FORCE ROW LEVEL
  SECURITY`, da política `isolamento_escritorio` para `lastro_app` e da política `acesso_do_dono`
  para `lastro_owner`. Sem isso, a tabela fica sem isolamento.
- **Nunca** dê `BYPASSRLS` a um papel nem crie política aberta para `lastro_app`: os testes
  `test_migracoes.py` e `test_isolamento_banco.py` falham.
- **Testes como `lastro_app`** precisam definir `app.firm_id` na transação. Seeds como
  superusuário ignoram a RLS.
- **Contêiner de teste como root** cria arquivos do root no repositório (`web/dist`, caches) e
  quebra o build do front: rode com o seu usuário.

## Contador por convite e atribuição de cliente (ACE-02)

Só o chefe usa estas rotas, menos o aceite, que não pede sessão. `{id}` de pessoa é o id do
**membro**. O código do convite (`secrets.token_urlsafe(32)`, 43 caracteres) só aparece na
resposta que o cria; o banco guarda o SHA-256. Validade: `LASTRO_CONVITE_HORAS` (padrão 48),
contada pelo relógio do banco, o mesmo do aceite e da lista.

| Rota | O que faz | Resposta |
|---|---|---|
| `POST /api/v1/accountants` | Cadastra `{"name", "username"}` sem senha e gera o convite | 201 com a pessoa, `invitation_code`, `invitation_path` (`/convite/<código>`) e `expires_at` |
| `GET /api/v1/accountants` | Lista as pessoas ativas do escritório, o chefe incluído | 200 com `id`, `name`, `username`, `role`, `status`; nunca código nem hash |
| `POST /api/v1/accountants/{id}/invitation` | Novo convite; revoga o pendente, mesmo vencido | 201 como o cadastro |
| `DELETE /api/v1/accountants/{id}/invitation` | Cancela o convite pendente | 204, também quando não há convite |
| `POST /api/v1/invitations/accept` | Sem sessão: `{"invitation_code", "username", "password"}` cria a senha | 200 "Senha criada. Agora é só entrar." |
| `POST /api/v1/clients/{id}/assignment` | Atribui `{"member_id"}` a um cliente sem responsável (pode ser o próprio chefe) | 201 com `responsible` |
| `GET /api/v1/clients/{id}/assignment` | Diz o responsável ativo | 200 com `responsible` (`null` se não há) |

`status` da pessoa: `ativo` (já criou a senha), `convite_pendente`, `convite_vencido`,
`sem_convite`. "Já criou a senha" vem da função `usuarios_com_senha(uuid[])` (migração `0007`),
que só responde `usuario_id` e `tem_senha`, só para o escritório da transação; nenhuma rota
lê `usuario.credencial_hash`.

| Situação | Status e `detail` |
|---|---|
| Contador tenta cadastrar, convidar, cancelar ou atribuir | 403 "Só o chefe do escritório pode fazer isso." |
| Nome ou usuário vazio | 422 "Informe o nome do contador." / "Informe o usuário de entrada do contador." |
| Usuário já existe (neste ou em outro escritório) | 409 "Este usuário já existe. Escolha outro." |
| Pessoa de outro escritório ou inexistente (convite) | 404 "Contador não encontrado no seu escritório." |
| Contador que já criou a senha recebe convite | 409 "Este contador já criou a senha." |
| Convite inexistente, vencido, usado, cancelado ou usuário que não bate | 404 "Este convite não vale mais. Peça um novo ao chefe do escritório." (corpo igual nos cinco) |
| Senha com menos de 8 caracteres (não gasta o convite) | 422 "A senha precisa ter pelo menos 8 caracteres." |
| Cliente inexistente ou de outro escritório | 404 "Você não tem acesso a este cliente." |
| Responsável inexistente, inativo ou de outro escritório | 404 "Responsável não encontrado no seu escritório." |
| Cliente já tem responsável (a troca é da ACE-04) | 409 "Este cliente já tem um responsável. Use a reatribuição." |

Aceite: ordem convite e usuário → tamanho da senha → `UPDATE convite ... WHERE usado_em IS NULL`
→ gravação da senha, numa transação. Dois aceites juntos: o segundo espera a trava da linha,
não atualiza nada e recebe a recusa do convite. O convite é achado só por
`buscar_convite_por_hash`. Contratos novos (versão 0): `TeamMember`, `IssuedInvitation`,
`Responsible`, `PersonStatus` e os erros em `access/contracts.py`; `registry.service.client_exists`.
