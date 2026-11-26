# Plan — NUC-03 · Isolar no banco os dados de cada escritório

**Status:** pronto para revisão (sem BLOQUEANTE; aprovar é do humano)
**Branch:** feat/NUC-03-isolar-no-banco-os-dados-de-cada-escrito · **Data:** 26/11/2026 · **Responsável:** jvsauma
**Tasks:** planos/NUC-03/tasks.md

## 1. A decidir (humano)
Todas as perguntas foram respondidas em 26/11 (ver §5). Resta só a ação humana da pergunta 4: abrir a issue para a ACE-05.

Mudanças sugeridas na ficha (o humano aplica em PR): (a) c5 e `depende_de` incluir DB-02, DB-03 e ADM-01 conforme as respostas 2 e 3; (b) c6 passar a "quatro buscas", conforme a resposta 1; (c) c5 trocar "usuario não tem RLS" por "usuario não tem RLS e o app só lê as colunas necessárias", se a resposta 1 for a sugerida; (d) c6 (2a) acrescentar `id` e `criada_em` da sessão ao retorno, se quiser evitar a segunda leitura (ver D4).

## 2. Decisões tomadas pelo agente
### D1 · O escritório vai para o banco por `set_config('app.firm_id', …, true)` (equivale a `SET LOCAL`), reaplicado a cada transação da sessão
- **Alternativas:** A) chamar a função no início de cada rota · B) evento `after_begin` do SQLAlchemy que lê o escritório guardado em `Session.info` e o aplica a cada transação · C) um papel de banco por escritório
- **Escolhida:** B — **motivo:** `access.identify` faz `commit` (renova a sessão) e o valor local morre nesse commit; a rota então abre outra transação sem escritório e veria 0 linhas. B reaplica sozinho, sem depender de cada rota lembrar. C não escala e muda a conexão. A ideia `SET LOCAL` por transação já está aprovada em `banco-de-dados.md` (BD-01..08, 18/11).
- **Fontes:** `gitpages/src/content/docs/decisoes/banco-de-dados.md` (Consequências) · `src/lastro/access/service.py:identify`
- **Impacto:** T4, T5; critérios c1, c2, c4. [x] confirmar

### D2 · Política extra para o dono (`lastro_owner`), porque a RLS forçada também vale para ele
- **Alternativas:** A) `CREATE POLICY … TO lastro_owner USING (true)` · B) `SECURITY DEFINER` com dono de outro papel com `BYPASSRLS` · C) não forçar nas tabelas que as funções leem
- **Escolhida:** A — **motivo:** com `FORCE`, a função `SECURITY DEFINER` (dona: `lastro_owner`, exigido por c6) também seria filtrada e devolveria sempre 0 linhas. B contradiz `create_roles.sql` e `test_migracoes.py` (nenhum papel com `BYPASSRLS`); C contradiz c5 (FORCE). A política de A vale só para o papel que roda migração e funções; a aplicação nunca conecta como ele (`MIGRATIONS_DATABASE_URL` só no Alembic).
- **Fontes:** `migrations/bootstrap/create_roles.sql` · `tests/core/test_migracoes.py:100-112`
- **Impacto:** T2, T3; c5, c6. Precisa de teste que prove que `lastro_app` não ganha nada com essa política. [x] confirmar

### D3 · Política lê o escritório com `NULLIF(current_setting('app.firm_id', true), '')::uuid`
- **Motivo:** depois de um `SET LOCAL`, a mesma conexão devolve texto vazio (não `NULL`) na transação seguinte; o `::uuid` direto daria erro em vez de "0 clientes, sem erro" (c2 e c4). Uma política `FOR ALL` com `USING` e `WITH CHECK` por tabela; `escritorio` compara `id`, as demais `escritorio_id`.
- **Impacto:** T2; c1 a c5. [x] confirmar

### D4 · Nomes e retorno das funções
- **Escolhida:** `buscar_sessao_por_hash(hash)`, `buscar_vinculos_do_usuario(usuario_id)`, `buscar_convite_por_hash(hash)` (e a quarta, `buscar_usuario_por_login`), em português como as tabelas, `search_path = pg_catalog, public`, objetos com nome de esquema, `REVOKE … FROM PUBLIC`, `GRANT EXECUTE` só a `lastro_app`. Retornos exatamente como em c6. A sessão devolve só 4 campos; depois de definir o escritório o app lê `sessao` normalmente sob RLS (id e `criada_em`). Os nomes não vêm da ficha: mudar depois exige mudar `tests/` (regra 3) e issue `contrato:` (regra 11).
- **Impacto:** T1, T3, T5. [x] confirmar

### D5 · `criar-escritorio` (ADM-01) gera o UUID no app e define o escritório antes de gravar
- **Alternativas:** A) app gera `uuid4`, define o contexto com ele e insere `escritorio`, `usuario`, `membro` · B) política permissiva de INSERT em `escritorio` (proibida por `SECURITY.md` §8) · C) função `SECURITY DEFINER` de criação
- **Escolhida:** A — **motivo:** sem política de contorno e sem função nova; `escritorio.id` passa de `server_default` para valor do app só nesse insert. Muda `access/repository.py: insert_firm_with_manager`. [x] confirmar

## 3. Resumo e abordagem
Ligar RLS forçada em todas as tabelas com escritório, dar ao app um caminho mínimo para as buscas feitas antes de se saber o escritório e fazer a API usar ambos. Ordem: testes (T1, revisão humana) → migração `0005` com políticas e funções (T2, T3) → contexto de escritório em `core/` (T4) → login e `identify` pelas funções, `criar-escritorio` com o novo insert (T5) → conferir as rotas de cliente (T6) → docs (T7) → `hx verify` (T8). Sem rota nova, sem tela, sem função do link do cliente.

## 4. Contexto encontrado
- **Planos lidos:** `planos/ACE-01/plan.md` e `planos/CAD-03/plan.md` (herdados, `depende_de`) e `planos/DB-01/plan.md` (aprovado); fora de `depende_de`, `planos/DB-03/plan.md` e `planos/ADM-01/plan.md` (mexem nas mesmas tabelas e no insert de escritório). NUC-01 e `progress/DB-01`/`ACE-01`/`CAD-03` só por estado. Conferência com o código: ACE-01 D1–D9 (sessão, `identify` com commit, 12 h) **confere** em `service.py`; CAD-03 "isolamento só aplicativo até a NUC-03" **confere** (`registry/repository.py` filtra por `escritorio_id`); DB-03 B2 "RLS na NUC-03" **confere**; DB-03 "texto de issue preparado" em `progress/DB-03.md` **divergente** (não há texto lá; só a recomendação).
- **Divergências do adendo:** diz NUC-03 `not_started` e dono guin409 — hoje `in_progress` com jvsauma (commit `76cff7e`); cita o c2 da DB-03 pedindo "índice para buscar sem escritório" — o c2 real não diz isso (a unicidade de `hash_token` já cria o índice). Conclusões do adendo (SECURITY DEFINER, sem `BYPASSRLS`, sem política permissiva) **batem** com c6 e `SECURITY.md` §8.
- **Dependências:** NUC-01, DB-01, ACE-01, CAD-03 `passing`. Fora da lista e `passing`: ADM-01, DB-02, DB-03. ACE-02 (`caio-nascime`) depende da NUC-03.
- **Reaproveitar:** `core/db.py` (`Database`, `get_session`), `access/repository.py` (consultas de sessão e vínculo), fixtures Testcontainers de `tests/core/conftest.py`, `tests/access/test_login.py` (seed como superusuário, que ignora a RLS).
- **Não criar:** papel novo, política permissiva, `BYPASSRLS`, função do link do cliente, rota ou tela, `utils.py`.
- **Pesquisa externa:** sem pesquisa externa necessária (decisão BD-01..08 já fixa RLS forçada e contexto por transação).

## 5. Decisões (já resolvidas)
- 26/11 · P1 (BLOQUEANTE): aceita a sugestão. Quarta função `SECURITY DEFINER` (login em minúsculas → `usuario_id`, `credencial_hash`, `ativo`); o app perde `SELECT` em `usuario.credencial_hash`, mantendo `INSERT` e `UPDATE` (resposta de jvsauma). T3 e T5 passam a incluir a função e o privilégio por coluna.
- 26/11 · P2: aceita. RLS também em `plano_contas`, `conta_contabil`, `conta_bancaria`, `socio`, `competencia` e `link_cliente` (jvsauma).
- 26/11 · P3: aceita. A T1 adapta os testes de DB-02, DB-03 e ADM-01, sem mudar o que provam (jvsauma).
- 26/11 · P4: aceita. A função do link do cliente fica na ACE-05; `link_cliente` fica fechada até lá. Issue a abrir por humano (jvsauma).
- 26/11 · D1 a D5 confirmadas por jvsauma ("aceito todas as sugestões").

## 6. Avaliação da ficha
| # | Achado | Gravidade | Critério |
|---|---|---|---|
| A1 | Contradição c5/c6/c7 sobre `credencial_hash` | BLOQUEANTE | c5, c6, c7 |
| A2 | Tabelas da DB-02 e DB-03 ficam sem RLS | ATENÇÃO | c5 |
| A3 | Testes de outras fichas quebram | ATENÇÃO | todos |
| A4 | 7 critérios, 3 módulos (`core`, `access`, `api`) — grande; se passar de 2 sessões, dividir em c1–c5 e c6–c7 | ATENÇÃO | — |
| A5 | c3 "(a) recusado" não diz qual erro; o teste espera erro do banco | ATENÇÃO | c3 |
| A6 | c6 (2f) "tentar alterar ou apagar função" depende de o teste rodar como `lastro_app` | ATENÇÃO | c6 |

## 7. Riscos
- RLS forçada filtra as próprias funções → D2.
- Escritório some após `commit` e a rota vê 0 linhas → D1, teste de c7 pela API.
- Função `SECURITY DEFINER` mal escrita vira brecha → `search_path` fixo, `EXECUTE` só ao app, retorno mínimo, teste de c6.
- Migração `0005` quebra testes e o `api` do Compose → pergunta 3; `alembic upgrade head` também no teste de reversão.
- Dado real: só UUIDs e nomes sintéticos (ESC-1, EMP-1…); nada em `fixtures/`.

## 8. Aprovação
- [x] Perguntas BLOQUEANTES respondidas
- [x] Decisões do agente confirmadas
- [ ] Plan e tasks revisados por <nome> em DD/MM
