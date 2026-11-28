# Plan — CAD-04 · Informar as contas bancárias do cliente com banco, apelido e meses de uso

**Status:** aprovado (jvsauma, 27/11/2026)
**Branch:** feat/CAD-04-informar-as-contas-bancarias-do-cliente · **Data:** 27/11/2026 · **Responsável:** jvsauma
**Tasks:** planos/CAD-04/tasks.md

## 1. A decidir (humano)
Nenhuma pergunta aberta: as 5 foram respondidas em 27/11 por jvsauma, que autorizou o padrão sugerido (seção 5).

Mudanças sugeridas na ficha (o humano aplica em PR): trocar `[definir P-13]` por 422 em c2, c4, c6 e c7 (P-13 aprovada em 25/11); c4: citar a fonte e a lista completa do `bancos.csv` (P1); c7: dizer o que o PATCH faz com campo omitido ou `null` (P4); nomes de rota (P3).

## 2. Decisões tomadas pelo agente
### D1 · Regra em `registry`, sem módulo novo; acesso reaproveita `registry.service.get_client`
- **Alternativas:** A) `service.py` chama `get_client` (404/403 da P-09) e depois grava · B) reescrever a decisão de acesso · C) módulo `accounts/` (proibido, ARCHITECTURE §7)
- **Escolhida:** A — **motivo:** c3 e c8 pedem exatamente a ordem 401→404→403 da P-09 e o mesmo corpo; `get_client` já a entrega. Conta de outro cliente no caminho vira `ClientNotFoundError` (corpo idêntico, c7 d/e).
- **Impacto:** T4, T6. [x] confirmar
### D2 · Arquivos novos: `registry/banks.py` (lê o CSV) e `registry/bank_accounts.py` (validação pura)
- **Alternativas:** A) dois arquivos como `cnpj.py` · B) tudo em `service.py` (já 208 linhas)
- **Escolhida:** A — **motivo:** padrão de `cnpj.py`; testável sem banco. `service.py` continua a única interface pública. **Impacto:** T2, T3. [x] confirmar
### D3 · Normalização do apelido em Python (`unicodedata` NFKD sem marcas, minúsculas, espaços reduzidos)
- **Alternativas:** A) biblioteca padrão · B) extensão `unaccent` do PostgreSQL (exige migração) · C) biblioteca nova (regra 12)
- **Escolhida:** A — **motivo:** zero dependência, comportamento igual ao da c5. **Impacto:** T3. [x] confirmar
### D4 · Código do banco: só dígitos ASCII (`isascii()` e `isdigit()`), 3 posições
- **Motivo:** `str.isdigit()` aceita dígitos de outros alfabetos; a lista usa ASCII. **Impacto:** T3. [x] confirmar
### D5 · Mês `AAAA-MM` por regex estrita e gravado como dia 1
- **Alternativas:** A) regex `^\d{4}-(0[1-9]|1[0-2])$` + `date(ano, mes, 1)` · B) `datetime.strptime` (aceita `2026-1`)
- **Escolhida:** A — **motivo:** "2026-1" e "10/2026" têm de ser recusados (c6). Ano `0000` cai na mesma mensagem. **Impacto:** T3. [x] confirmar
### D6 · Contratos v0 novos no `registry` (regra 11)
- `BankAccountSummary(account_id, bank, bank_name, nickname, currency, first_month, last_month)` e `InvalidBankAccountDataError(message)` e `DuplicateNicknameError` em `registry/contracts.py`; funções `add_bank_account`, `list_bank_accounts`, `update_bank_account` em `registry/service.py`. Registrar em `ARCHITECTURE.md` §6 e `docs/modulos/registry.md`. Sem consumidor existente: não precisa de issue `contrato:`. **Impacto:** T7. [x] confirmar

## 3. Resumo e abordagem
O contador (ou o chefe atribuído a si) cadastra, lista e altera contas bancárias do cliente com banco, apelido e meses opcionais; nada é apagado.
Ordem: testes (T1) → lista de bancos e leitura (T2) → validações puras (T3) → repositório e serviço de informar/listar (T4) → rotas e erros HTTP (T5) → PATCH (T6) → documentação e contratos (T7) → verificação (T8). A tabela `conta_bancaria` já existe (DB-02, migração 0003) com a restrição de cobertura (fim ≥ início) e RLS forçada (NUC-03): não há migração. `moeda` fica no padrão `BRL`; `identificacao_protegida` e `conta_contabil_id` ficam fora (CAD-06/futuro).

## 4. Contexto encontrado
- **Planos lidos:** NUC-02 e CAD-03 (aprovados); ACE-02 e DB-02 (rascunho: "intenção, não decidida"). Li o cabeçalho e o status deles, não o texto inteiro; o que usei como fato veio do código e do `DECISIONS.md`.
- **DECISIONS lidas:** P-09 (chefe: lista sim, acesso só do responsável; ordem 401→404→403; 403/404 antes de validar), P-13 (422), P-01 (404 igual), D-07, P-03, ACE-02/F5 (rotas em inglês), DB-02/B1–B3, NUC-03/R1 (RLS forçada; `use_firm` por transação). NUC-03/R4 não se aplica (não lê `usuario`).
- **Conferência com o código:** **confere** — `registry.service.get_client` (404/403 da P-09), `filter_visible_clients`/`decide_access` em `core/service.py`, `access.service.responsible_member_ids` passada por parâmetro, `BankAccount` (`registry/models.py:203`) e migração `0003` (colunas e `ck_conta_bancaria_cobertura`), papel `lastro_app` com SELECT/INSERT/UPDATE/DELETE (`0001`) e política RLS `FOR ALL` (`0005`). **Não verificável** — as decisões de ACE-02 e DB-02 além dessas.
- **Reaproveitar:** `registry/repository.py` (`find_client`; padrão de `ClientRow`), `registry/contracts.py` (`ClientNotFoundError`, `ClientNotAssignedError`), handlers `_client_not_found`, `_client_not_assigned`, `_invalid_client_data` em `api/routes.py`, `_membership`, `require_signed_in_member`. Testes: padrão de `tests/registry/test_cliente.py` e `migrated_database` de `tests/registry/conftest.py`.
- **Não criar:** outra decisão de acesso; coluna ou migração; rota DELETE; módulo `accounts/`; helper de CNPJ novo (use o do teste da CAD-03 copiado para o arquivo novo, sem editar `test_cliente.py`).
- **Não existe ainda:** `src/lastro/registry/data/bancos.csv`; nenhum código lê a pasta `data/`. A imagem usa `PYTHONPATH=/app/src`, então o arquivo é lido por `Path(__file__)`.
- **Pesquisa externa:** só a fonte da lista de bancos. [Lista de Participantes do STR, dados abertos do BCB](https://dadosabertos.bcb.gov.br/dataset/lista-de-participantes-do-str) (acesso em 27/11/2026): atualizada diariamente, CSV/HTML, licença ODbL; o "número-código" substitui o antigo código COMPE e é "n/a" para quem não tem código. Um endereço direto de CSV apareceu só numa página espelho; **não confirmado**, confirme no portal oficial.

## 5. Decisões (já resolvidas)
- 27/11 · P1 (BLOQUEANTE): `bancos.csv` com a **lista completa** de participantes do STR com número-código, do portal do BCB (ODbL); `fonte` traz a URL e a data de acesso. Quem implementa a T2 baixa o arquivo e confere o link (o agente do plano não baixou). Resposta de jvsauma.
- 27/11 · P2: sem migração; trava `SELECT … FOR UPDATE` na linha do cliente e comparação do apelido normalizado em Python. Resposta de jvsauma.
- 27/11 · P3: `POST/GET /api/v1/clients/{client_id}/bank-accounts`, `PATCH …/bank-accounts/{account_id}`; campos `id`, `bank`, `bank_name`, `nickname`, `currency`, `first_month`, `last_month`. Resposta de jvsauma.
- 27/11 · P4: PATCH com campo omitido = não muda; `first_month`/`last_month` `null` = limpa; `nickname` `null` ou vazio = "Dê um apelido para a conta."; `bank` igual ao atual aceita, diferente = 422 da c7(a). Resposta de jvsauma.
- 27/11 · P5: apelido até 255 caracteres após `strip` ("O apelido deve ter no máximo 255 caracteres."); ordem: acesso (401/404/403) → banco vazio → apelido vazio → banco formato → banco existe → apelido longo → meses → duplicado (409); todo 422 antes do 409. Resposta de jvsauma.
- 28/11 · P6 (revisão do PR #94): mês `first_month`/`last_month` em branco (`""`) conta como ausente, igual a `null`; no PATCH, `""` limpa o mês. Resposta de jvsauma.
- 28/11 · P7 (revisão do PR #94): o `bancos.csv` é atualizado à mão, por PR, quando o BCB mudar a lista; sem rotina automática no MVP. Resposta de jvsauma.
- 28/11 · P8 (revisão do PR #94): o teste de corrida `tests/registry/test_contas_bancarias_corrida.py` (criado depois do código, em resposta à rubrica) e o ajuste de ordem de import em `test_contas_bancarias.py` (ruff I001, feito à mão) estão aprovados como exceção à regra 3. Resposta de jvsauma.
- 22/11 · P-09 e 25/11 · P-13: valem como estão (DECISIONS.md).

## 6. Avaliação da ficha
| # | Achado | Gravidade | Critério |
|---|---|---|---|
| 1 | Lista de bancos: só 8 códigos exigidos; risco de recusar banco real | RESOLVIDO (P1, lista completa) | c4 |
| 2 | `[definir P-13]` já decidido (422) | ATENÇÃO | c2, c4, c6, c7 |
| 3 | Unicidade do apelido sem apoio do esquema (P2, resolvida) | ATENÇÃO | c5 |
| 4 | PATCH com campo omitido/`null` indefinido (P4, resolvida) | ATENÇÃO | c7 |
| 5 | Tamanho do apelido e ordem das checagens não definidos (P5, resolvida) | ATENÇÃO | c2, c4, c5, c6 |
| 6 | Feature grande: 8 critérios, 1 módulo; pode passar de 2 sessões | ATENÇÃO | todos |
| 7 | "Nunca diminui a contagem de linhas" só se prova pela ausência de rota; o app tem permissão de DELETE no banco | ATENÇÃO | c7 |
| 8 | Dependências ACE-02, NUC-02, DB-02 estão `passing` | — | — |
| 9 | Verificações são um teste por critério, nos nomes da ficha; provam os critérios | — | c1–c8 |

## 7. Riscos
- Corrida entre dois cadastros do mesmo apelido → trava `FOR UPDATE` na linha do cliente, com teste de concorrência opcional.
- Dado real no `bancos.csv` → só nomes de instituições e códigos públicos; nenhum dado de pessoa. Testes usam clientes e CNPJ sintéticos gerados em execução.
- Vazamento entre escritórios → RLS forçada + `get_client`; teste do c3 compara os corpos 404.
- Se estourar 2 sessões: dividir em CAD-04 (c1–c5, c8) e nova ficha para c6–c7 (o humano abre a ficha).

## 8. Aprovação
- [x] Perguntas BLOQUEANTES respondidas
- [x] Decisões do agente confirmadas (27/11, jvsauma)
- [x] Plan e tasks revisados por jvsauma em 27/11
