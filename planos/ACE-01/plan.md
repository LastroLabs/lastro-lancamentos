# Plan — ACE-01 · Entrar com login individual e encerrar a sessão

**Status:** pronto para revisão
**Branch:** feat/ACE-01-entrar-com-login-individual-e-encerrar-a · **Data:** 24/11/2026 · **Responsável:** arthurlleite
**Tasks:** planos/ACE-01/tasks.md

## 1. A decidir (humano)
Nenhuma pergunta BLOQUEANTE. As perguntas 1 e 2 foram respondidas em 24/11 (D9 e D10, registradas no `DECISIONS.md`); as ATENÇÕES 3 e 4 seguem o padrão sugerido até alguém dizer o contrário.
| # | Pergunta | Gravidade | Sugestão de padrão | Decide |
|---|---|---|---|---|
| 1 | Prazo da sessão. A modelagem (SESSAO) diz que "o prazo não foi fixado" e a página de segurança pede "expiração por inatividade". A tabela `sessao` só tem `expira_em`. | RESPONDIDA | ~~8 horas corridas a partir da entrada~~ → expira depois de **2 h sem uso**, renovando `expira_em` a cada pedido, com **teto de 12 h** desde a entrada (D9; seção 5) | caio-nascime, 24/11 |
| 2 | O `usuario` é global e pode ter vínculo (`membro`) em mais de um escritório. A ficha não diz em qual escritório a sessão abre nesse caso. | RESPONDIDA | Um vínculo ativo por usuário no MVP; com dois ou mais, erro próprio (409), só depois da senha certa (D10; seção 5) | caio-nascime (dono da ACE-02), 24/11 |
| 3 | Proteção contra CSRF (página de segurança: "proteção CSRF nas rotas que alteram dados"). Esta ficha cria duas rotas que alteram dados: entrar e sair. | ATENÇÃO | Cookie `SameSite=Lax` e entrada só com corpo JSON (navegador não envia JSON de outro site sem pedir permissão antes). Token CSRF próprio fica para uma ficha de segurança, antes do piloto | líder |
| 4 | `usuario.identificador_login` é único com diferença entre maiúsculas e minúsculas (DB-01). | ATENÇÃO | Comparar em minúsculas e sem espaço nas pontas (`lower()` no banco). A ACE-02 grava o login já em minúsculas; dois logins que só diferem na caixa são recusados como senha errada | arthurlleite + caio-nascime |

Mudanças sugeridas na ficha (o humano aplica em PR): nenhuma. O papel volta como `accountant`/`manager` (D3); a ficha fala "papel contador", que é o mesmo conceito no glossário.

## 2. Decisões tomadas pelo agente
Cada uma precisa de confirmação humana.
### D1 · Três rotas sobre um recurso `session`
- **Alternativas:** A) `POST /api/v1/session` (entrar), `GET /api/v1/session` (quem está conectado), `DELETE /api/v1/session` (sair) · B) `/login`, `/logout`, `/me` · C) nomes em português (`/sessao`)
- **Escolhida:** A — **motivo:** rotas e campos da API em inglês (CODING_STANDARDS §1); um recurso só, com os três verbos, deixa claro que a sessão é uma coisa no servidor (ARQ-03, I-5).
- **Corpo de entrar:** `{"username": "...", "password": "..."}`. Resposta 200 com a identificação (igual ao `GET`); `DELETE` responde 204.
- **Impacto:** T1, T4. [ ] confirmar

### D2 · Cookie de sessão no servidor
- **Escolhida:** token aleatório de 32 bytes (`secrets.token_urlsafe`), enviado no cookie `lastro_session` com `HttpOnly`, `Secure`, `SameSite=Lax` e `Path=/api`. No banco só fica o SHA-256 em hexadecimal (`sessao.hash_token`), como o link do cliente (I-6). Cada entrada cria uma sessão nova (rotação no login). Sair grava `encerrada_em` e apaga o cookie.
- **Por que `Secure` sempre:** os navegadores aceitam cookie `Secure` em `http://localhost`, então o dev não precisa de exceção. Os testes usam `https://testserver`.
- **Fontes:** `gitpages/.../arquitetura/stack.md` (linha "Autenticação") e `seguranca.md` (linha "Sessão roubada"); ARQ-03.
- **Impacto:** T3, T4. [ ] confirmar

### D3 · Identificação devolvida: `username`, `name`, `role`, `firm_id`, `firm_name`
- **Escolhida:** `role` com os valores de `lastro.core.contracts.Role` (`manager`, `accountant`), os mesmos da regra de acesso da NUC-02. O banco guarda `chefe`/`contador` (DB-01); a tradução fica no repositório do `access/`. Nenhum hash, token ou senha na resposta.
- **Contrato para as próximas fichas:** `SignedInMember` (frozen) em `access/contracts.py`, com `user_id`, `member_id`, `firm_id`, `username`, `name`, `role` e `firm_name`. A ACE-03 monta o `Membership` da NUC-02 a partir dele.
- **Impacto:** T2, T4. [ ] confirmar

### D4 · Senha com Argon2 (`argon2-cffi`)
- **Alternativas (regra 12):**
  - A) `argon2-cffi` (MIT, mantida, roda em 3.12 e 3.14, padrão RFC 9106)
  - B) `pwdlib` (MIT, mais nova; por baixo usa a própria `argon2-cffi`)
  - C) `passlib` (sem lançamento desde outubro de 2020: projeto parado)
- **Escolhida:** A — **motivo:** a stack já fixou "senha com Argon2"; é a biblioteca mais simples e a que as outras usam por baixo. Parâmetros padrão da biblioteca (perfil de baixa memória da RFC 9106).
- **Interface:** `hash_password(password) -> str` em `access/service.py`. A ACE-02 usa ao aceitar o convite; os testes usam para montar os usuários.
- **Impacto:** T2, `pyproject.toml`, `uv.lock`. [ ] confirmar

### D5 · Recusa igual e com o mesmo custo
- Usuário inexistente, senha errada, usuário sem senha (`credencial_hash` nulo, c6), usuário, vínculo ou escritório inativo e caso da pergunta 2: todos dão 401 com o mesmo corpo ("Usuário ou senha incorretos."). Quando não há hash para conferir, o código confere a senha contra um hash fixo de mentira, para a resposta levar o mesmo tempo e não revelar quem existe.
- **Impacto:** T2, T3. [ ] confirmar

### D6 · Mensagens de 401
- Sem cookie: "Entre para continuar." (c5).
- Cookie presente, mas a sessão está encerrada, expirada, não existe ou o vínculo ficou inativo: "Sua sessão terminou. Entre de novo." (c4). Assim um token inventado não se distingue de um antigo.
- Sair sem sessão válida segue a mesma regra (401), como qualquer rota protegida (P-01).
- Erro em RFC 9457 (`application/problem+json`, I-14), com a mensagem em `detail` e o título "Sem acesso".
- **Impacto:** T4. [ ] confirmar

### D7 · Onde fica cada parte
- `access/repository.py`: as consultas a `usuario`, `membro`, `escritorio` e `sessao` (I-7).
- `access/passwords.py`: Argon2 (arquivo interno do módulo).
- `access/service.py`: `hash_password`, `sign_in`, `identify`, `sign_out`; quem chama passa a `AsyncSession`.
- `api/routes.py`: as três rotas e a dependência `require_signed_in_member`, que a ACE-03 em diante reaproveita.
- **Impacto:** T2 a T4. [ ] confirmar

### D8 · Testes com banco de verdade
- Os testes sobem a API com `create_app()` contra o PostgreSQL do Testcontainers (fixtures da NUC-01) migrado até `head`. Os usuários são gravados direto no banco pelo teste, com a senha gerada na hora e o hash de `hash_password`. Cada contador usa o próprio `TestClient`, com o próprio cookie.
- O `conftest.py` de `tests/access/` fixa a revisão `0002` para os testes da DB-01; o teste desta ficha migra até `head` numa fixture própria, sem mexer no `conftest.py`.
- **Impacto:** T1. [ ] confirmar

### D9 · Expiração por inatividade com teto (resposta à pergunta 1)
- **Escolhida:** a entrada grava `expira_em` = agora + 2 h. Cada pedido aceito renova `expira_em` para o menor entre agora + 2 h e `criada_em` + 12 h. Passou de `expira_em` ou de 12 h desde a entrada: "Sua sessão terminou. Entre de novo." O token não muda; só o prazo no banco anda. O cookie vale até o teto de 12 h, porque quem decide é o servidor.
- **Custo:** um `UPDATE` em `sessao` por pedido autenticado. Aceitável no MVP; dá para espaçar a renovação depois, se pesar.
- **Impacto:** T7, T8. [ ] confirmar

### D10 · Um escritório por usuário, com erro próprio (resposta à pergunta 2)
- **Escolhida:** entrar exige um vínculo ativo, em escritório ativo. Quem tem dois ou mais recebe **409** `application/problem+json`, título "Mais de um escritório", `detail` "Este usuário está em mais de um escritório. Peça ao chefe um usuário para cada escritório.", sem cookie e sem linha em `sessao`. O caso não deve acontecer no MVP (a ACE-02 convida para um escritório); o erro próprio dá contexto a quem for dar suporte.
- **Só depois da senha certa:** com senha errada, a resposta continua a 401 de sempre (D5), então o 409 não revela a um estranho que a conta existe. O corpo não cita os escritórios.
- **Alternativas:** A) a 401 de senha errada (confunde quem acertou a senha) · B) escolher o escritório na entrada (proposto e descartado em 24/11: muda a lógica do convite e não cabe no prazo do MVP).
- **Registro:** `docs/decisoes/DECISIONS.md`, seção 7 (ACE-01/E2).
- **Impacto:** T7, T8. [ ] confirmar

## 3. Resumo e abordagem
O contador entra com usuário e senha, recebe um cookie de sessão guardada no servidor, pergunta "quem sou eu" e sai. Erros não dizem qual campo errou nem se o usuário existe.
1. T1: testes da ficha em `tests/access/test_login.py`.
2. T2: contratos, Argon2 e a regra de entrada no `access/`.
3. T3: sessão no banco: criar, identificar, encerrar.
4. T4: rotas, cookie e erros RFC 9457 na API.
5. T5: OpenAPI e cliente do front regenerados; doc do módulo.
6. T6: verificação final.
7. T7: testes das respostas às perguntas 1 e 2 (D9 e D10), em commit só de testes.
8. T8: implementação de D9 e D10; OpenAPI, doc e `DECISIONS.md` atualizados; verificação de novo.

## 4. Contexto encontrado
- **Código relacionado:** modelos `User`, `Member`, `Firm` e `Session` em `src/lastro/access/models.py` (DB-01); `Role` e `Membership` em `src/lastro/core/contracts.py` (NUC-02); `get_session` em `src/lastro/core/db.py` e `create_app` em `src/lastro/api/app.py` (NUC-01).
- **Dependências:** NUC-01 e DB-01 `passing`. Consomem esta ficha: ACE-02 (aceite do convite usa `hash_password`), ACE-03 a ACE-05 e CAD-* (rota protegida usa `require_signed_in_member`).
- **Planos lidos:** NUC-01, NUC-02 e DB-01 (aprovados). Do meu comentário na #16: login em minúsculas (pergunta 4) e `sessao.hash_token` sem CHECK de formato (o código sempre grava 64 hex).
- **Front:** a rota `/entrar` já existe (WEB-01). `docs/api/openapi.json` e `web/src/api/schema.d.ts` são gerados e conferidos pelo teste da WEB-01: precisam ser regenerados (T5).
- **Não criar:** migração (as tabelas existem), cadastro de usuário, aceite de convite, tela de login, RLS (NUC-03), `utils.py`.
- **Pesquisa externa:** licença e manutenção de `argon2-cffi`, `pwdlib` e `passlib` (D4). Nenhuma busca levou dado do projeto.

## 5. Decisões (já resolvidas)
- 18/11 · ARQ-03: sessão no servidor, não JWT.
- 18/11 · P-01: 401 sem sessão ou com sessão encerrada.
- 18/11 · Stack: cookie `HttpOnly`, `Secure`, `SameSite=Lax` e senha com Argon2.
- 24/11 · Pergunta 1 (D9): sessão expira por inatividade de 2 h, com teto de 12 h desde a entrada (caio-nascime, na revisão do #57).
- 24/11 · Pergunta 2: um vínculo ativo por usuário no MVP, com erro próprio (409) para quem tem dois (D10). Quem precisar de dois escritórios usa um usuário em cada. Escolher o escritório na entrada chegou a ser proposto, mas mudaria a lógica do convite (ACE-02) e não cabe no prazo (caio-nascime, dono da ACE-02, na revisão do #57).

## 6. Avaliação da ficha
| # | Achado | Gravidade | Critério |
|---|---|---|---|
| 1 | 6 critérios (> 4), mas todos sobre o mesmo fluxo de sessão. Cabe em uma sessão de testes e uma de implementação. Não sugiro dividir. | ATENÇÃO | todos |
| 2 | Prazo da sessão e vários escritórios por usuário não estão na ficha (perguntas 1 e 2, respondidas). Os testes de D9 e D10 ficam em `tests/access/test_login_prazo_e_escritorio.py`, fora da `verificacao` da ficha; rodam no `hx verify`. Sugestão (o humano aplica em PR): acrescentar c7 (inatividade) e c8 (dois escritórios, 409) à ficha. | ATENÇÃO | c1 |
| 3 | "Mesma recusa" vira regra checável: status, corpo inteiro igual e nenhuma linha nova em `sessao`. | — | c2, c6 |
| 4 | Exemplos claros, com usuários inventados e senhas geradas na hora. | — | c1–c6 |

## 7. Riscos
- RLS da NUC-03: a entrada procura o usuário antes de saber o escritório. As políticas precisam deixar essa consulta passar sem abrir o resto → avisar o dono da NUC-03 (guin409) no PR.
- Sessão parada cai em 2 h (D9); um computador esquecido em uso contínuo fica logado até o teto de 12 h.
- Quem trabalha em dois escritórios precisa de um usuário em cada (D10); revisar se um piloto precisar.
- Sem token CSRF (pergunta 3): depende do `SameSite=Lax` até a ficha de segurança.
- Mudar `SignedInMember` ou a dependência depois exige issue `contrato:` (regra 11).

## 8. Aprovação
- [ ] Perguntas ATENÇÃO respondidas ou padrão aceito
- [ ] Decisões do agente confirmadas
- [ ] Plan e tasks revisados por ________ em __/__
