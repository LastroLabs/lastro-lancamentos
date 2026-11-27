# Plan — ACE-02 · Cadastrar contador por convite e atribuir cliente pelo chefe

**Status:** pronto para revisão
**Branch:** feat/ACE-02-cadastrar-contador-por-convite-e-atribui · **Data:** 26/11/2026 · **Responsável:** jvsauma
**Tasks:** planos/ACE-02/tasks.md

## 1. A decidir (humano)
Nenhuma pergunta aberta: as 9 foram respondidas em 26/11 por jvsauma, que aceitou a sugestão de padrão em todas (seção 5).

Mudanças sugeridas na ficha (o humano aplica em PR): nomes de rotas e campos em inglês (pergunta 1); 422 no lugar de `[definir P-13]` (6); incluir 204 de `DELETE` sem convite e `responsible: null` (4 e 5).

## 2. Decisões tomadas pelo agente
### D1 · Código do convite com `secrets.token_urlsafe(32)` (43 caracteres), guardado como SHA-256 em hex
- **Alternativas:** A) `token_urlsafe(32)` · B) `token_hex(32)` (64 caracteres) · C) `uuid4` (só 122 bits, e 36 caracteres não cumprem "pelo menos 43")
- **Escolhida:** A — **motivo:** mesmo padrão da sessão (`SESSION_TOKEN_BYTES`) e do link do cliente (I-6); o CHECK de `convite.hash_token` exige 64 hex minúsculos. **Fonte:** [docs.python.org/3/library/secrets.html](https://docs.python.org/3/library/secrets.html) (acesso em 26/11)
- **Impacto:** T3; c1. - [x] confirmar
### D2 · Validade e "vencido" pelo relógio do banco
- **Alternativas:** A) `expira_em = now() + N horas` no próprio INSERT, devolvendo `expira_em` · B) calcular no app
- **Escolhida:** A — **motivo:** a ACE-02/F3 manda a lista e o aceite concordarem; B quebraria a restrição `expira_em > criado_em` se o relógio do app atrasasse (NUC-03, nota ACE-05/N1).
- **Impacto:** T3; c1, c3 (b), c5. - [x] confirmar
### D3 · `LASTRO_CONVITE_HORAS` em `core/config.py` (padrão 48, inteiro ≥ 1), documentada no `.env.example`
- **Alternativas:** A) variável de ambiente (a ficha já a cita) · B) por escritório (exige coluna nova, fora da DB-01)
- **Escolhida:** A — valor inválido impede a API de subir, como `NAME_PROTECTION_LEVEL`. **Impacto:** T2; c1. - [x] confirmar
### D4 · Ordem do aceite: convite e usuário (404) → tamanho da senha (422) → `UPDATE convite` → `UPDATE usuario`
- **Alternativas:** A) a ordem acima · B) senha curta primeiro. **Escolhida:** A — quem não tem um código válido sempre recebe a mesma recusa; o hash Argon2 é calculado **antes** do `UPDATE convite`, para segurar a trava da linha o mínimo. Uma única transação; qualquer recusa faz rollback (F4). **Impacto:** T5; c2, c3, c11. - [x] confirmar
### D5 · Marcar `User.credencial_hash` com `deferred=True, deferred_raiseload=True` (NUC-03/R4, "recomendado")
- **Escolhida:** aplicar em `access/models.py`; um `select(User)` sem querer vira erro de Python apontando o campo. Não afeta o INSERT do ADM-01. **Impacto:** T2; c2, c10. - [x] confirmar
### D6 · Detalhes de dados
- Gerar convite revoga antes (`revogado_em = now()`) o pendente **mesmo vencido**, na mesma transação: o índice único parcial só olha `usado_em`/`revogado_em`, e o vencido ainda conta como pendente.
- `atribuicao.inicio` não tem padrão no banco: gravar `now()` do banco. Duas atribuições ao mesmo tempo: o índice único parcial recusa a segunda e o app responde o 409 de c7.
- Situação na lista: tem senha → `ativo`; senão, convite sem `usado_em`/`revogado_em` com `expira_em > now()` → `convite_pendente`, com `<= now()` → `convite_vencido`; senão `sem_convite`. Lista só membros ativos do escritório, chefe incluído (P-09 (7)).
- Reaproveitar `MIN_PASSWORD_LENGTH` (8) de `access/admin.py` e `UsernameTakenError` (contrato v0, #68). Rotas novas ficam em `api/routes.py` (ficará grande; riscos). - [x] confirmar

## 3. Resumo e abordagem
O chefe cadastra o contador (usuário sem senha, vínculo `contador`, convite com código aleatório guardado só como hash); o contador abre o link, cria a senha e passa a entrar pelo login da ACE-01. O chefe também gera ou cancela o convite e atribui um cliente sem responsável a qualquer membro ativo, inclusive a si mesmo.
Ordem: (1) testes; (2) migração `0007` com `usuarios_com_senha`, configuração e modelo; (3) repositório e contratos; (4) serviço e rotas do chefe (cadastro, lista, convite); (5) aceite sem login; (6) atribuição; (7) docs e OpenAPI; (8) verificação. Chefe e escritório vêm sempre da sessão, nunca do corpo; o aceite define o escritório pelo que `buscar_convite_por_hash` devolve.

## 4. Contexto encontrado
- **Planos lidos:** `ACE-01` (pronto para revisão, **não aprovado**: vale como intenção; as respostas E1/E2 estão no `DECISIONS.md` e valem), `CAD-03` (aprovado), `DB-01` (aprovado), `NUC-03` (aguarda aprovação da §8, mas o código está na main, #76; R1–R4 do `DECISIONS.md` valem). Fora de `depende_de`: nenhum lido.
- **`DECISIONS.md` lido:** ACE-02/F1–F4 (função `usuarios_com_senha`, R4, relógio do banco, aceite em duas etapas), NUC-03/R1–R4, ACE-01/E1–E2 (um escritório por usuário; o chefe cria um usuário por escritório), P-02 (só o chefe cadastra), P-09 (atribuição só do chefe; lista inclui o chefe), P-13 (422), D-09. A parte "decidida em 26/11 por caio-nascime" segue válida, mesmo com o responsável agora sendo jvsauma.
- **Conferência com o código:** **confere** — `buscar_convite_por_hash` (0005: devolve escritório, convite e membro, filtra `expira_em > now()`); `use_firm` (`core/db.py`); `hash_password`; `responsible_member_ids`; `ManagerOnlyError`, `ClientNotFoundError` e seus handlers; 422 da P-13; índice único de convite pendente e de atribuição aberta; `lastro_app` com UPDATE em `convite`, `usuario(credencial_hash)` e INSERT em `atribuicao`; `head` = 0006. **Divergente:** ficha em português × rotas em inglês (pergunta 1); R4 recomenda `deferred` e `models.py:46` ainda não tem (D5). **Não verificável:** a ficha prevê o front `/convite/<código>`, que não existe.
- **Reaproveitar:** `access/service.py` (`hash_password`, `_hash_token`, `_ROLES`), `access/repository.py` (padrão "só colunas"), `core/service.decide_access` (`MANAGE_ASSIGNMENT`), `api/routes.py` (`_problem`, `require_signed_in_member`, `_membership`), `UsernameTakenError`, testes `tests/access/test_login.py` (banco em `head`) e `tests/registry/test_cliente.py`.
- **Não criar:** segundo gerador de hash; leitura de `credencial_hash`; consulta a `convite` por `hash_token`; módulo, `utils.py` ou dependência nova.
- **Pesquisa externa:** só a fonte de D1; sem outra pesquisa necessária.

## 5. Decisões (já resolvidas)
- 26/11 · Todas as sugestões de padrão aceitas por jvsauma. Pendências humanas que seguem: aplicar a mudança da ficha em PR e abrir a issue `contrato:` (8), e conferir com o dono do `registry` a função da pergunta 3.
- 1 · Rotas e campos em inglês: `/api/v1/accountants`, `/accountants/{id}/invitation`, `/invitations/accept`, `/clients/{id}/assignment`; campos `id`, `name`, `username`, `role`, `status`, `invitation_code`, `invitation_path`, `expires_at`; valores de situação como na ficha.
- 2 · `id` = id do membro. · 3 · Opção A: função pública nova no `registry` (ex.: `client_exists`), passada pela `api/`. · 4 · `DELETE` sem convite: 204; 404 só se o contador não existe.
- 5 · `GET` sem responsável: 200 com `responsible: null`; com responsável, `{id, name, username}`. · 6 · 422 no lugar de `[definir P-13]`. · 7 · Uma ficha só, 2 a 3 sessões. · 8 · O humano abre a issue `contrato:`. · 9 · Front `/convite/<código>` fora do escopo.

## 6. Avaliação da ficha
| # | Achado | Gravidade | Critério |
|---|---|---|---|
| 1 | Rotas e campos em português × padrão do código (resolvido: inglês) | RESOLVIDO | todos |
| 2 | `id` da pessoa não definido; resposta de `DELETE` sem convite e de `GET` sem responsável não definidas | ATENÇÃO | c5, c6 |
| 3 | `[definir P-13]` já decidido (422) | ATENÇÃO | c3, c4 |
| 4 | c1, c2 e c5 têm muitas verificações num teste só (SQL, log, lista); ficam em `verificacao` única | ATENÇÃO | c1, c2, c5 |
| 5 | "O código não está nos logs": prova por `caplog`, que só cobre logs do app | ATENÇÃO | c1 |
| 6 | Senha literal `'senha-teste-123'` pode acionar o `check-clean`; gerar na hora (como a CAD-03) | ATENÇÃO | c2, c11 |
| 7 | Dependências `ACE-01`, `CAD-03`, `DB-01`, `NUC-03` estão `passing` | OK | — |
| 8 | Feature grande (pergunta 7) | ATENÇÃO | todos |

## 7. Riscos
- Dois aceites simultâneos → `UPDATE … WHERE usado_em IS NULL` e rollback (F4); teste c11 com duas conexões reais.
- Recusa do aceite deixa rastro (gasta convite ou grava senha) → tudo numa transação, 422 e 404 antes de gravar.
- `UPDATE usuario … WHERE credencial_hash IS NULL` seria leitura da coluna e o banco recusa → não usar; a proteção é o convite só existir para quem não tem senha (c5).
- Vazar o código: nunca em coluna, log nem resposta da lista; a resposta de c1/c5 é a única vez em que aparece.
- `api/routes.py` já tem 373 linhas e ganhará cerca de 10 rotas → se passar de ~700, dividir em PR próprio (pergunta ao dono da `api/`).
- Teste que cria convite vencido deve gravar `expira_em` no passado direto no banco (F3).

## 8. Aprovação
- [x] Perguntas BLOQUEANTES respondidas (jvsauma, 26/11)
- [x] Decisões do agente confirmadas
- [x] Plan e tasks revisados por <João> em 26/11
