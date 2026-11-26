# Plan — CAD-03 · Cadastrar cliente com nome e CNPJ

**Status:** aprovado (caio-nascime, 25/11/2026)
**Branch:** feat/CAD-03-cadastrar-cliente-com-nome-e-cnpj · **Data:** 25/11/2026 · **Responsável:** caio-nascime
**Tasks:** planos/CAD-03/tasks.md

## 1. A decidir (humano)
| # | Pergunta | Gravidade | Sugestão de padrão | Decide |
|---|---|---|---|---|
| 1 | ~~P-13: 400 ou 422?~~ | RESPONDIDA | **422** (seção 5). | caio-nascime |
| 2 | ~~Nome das rotas (português ou inglês)~~ | RESPONDIDA | Inglês: `POST/GET /api/v1/clients`, `GET /api/v1/clients/{client_id}` (seção 5). | caio-nascime |
| 3 | ~~CNPJ repetido no mesmo escritório~~ | RESPONDIDA | **409**, "Este CNPJ já está cadastrado no seu escritório." (seção 5). | caio-nascime |
| 4 | ~~Contador tenta cadastrar~~ | RESPONDIDA | **403**, "Só o chefe do escritório pode fazer isso." (seção 5). | caio-nascime |
| 5 | ~~Rota de abrir cliente: CAD-03 ou ACE-03?~~ | RESPONDIDA | Ver seção 5 (25/11). | caio-nascime |
| 6 | ~~Tamanho máximo e espaços do nome~~ | RESPONDIDA | `strip()`; "   " conta como vazio; **máximo 255 caracteres** depois do `strip()` (seção 5). Limite do Domínio (D-05) segue `[definir]`. | caio-nascime |
| 7 | ~~Tela do cadastro~~ | RESPONDIDA | Front fora desta ficha (seção 5). | caio-nascime |
| 8 | ~~Quem lê `atribuicao`?~~ | RESPONDIDA | Alternativa A, com função recebida por parâmetro (seção 5 e D3). | caio-nascime |

Mudanças sugeridas na ficha (o humano aplica em PR): c2 trocar `[definir P-13]` pelo status decidido; opcional: c5 (contador recusado, 403) e c6 (CNPJ repetido) se as perguntas 3 e 4 forem aceitas; ACE-02: trocar `/api/v1/clientes/{id}/atribuicao` pelo caminho em inglês (c6 e c7 citam o caminho). **ACE-03 (autorizada em 25/11, a aplicar em PR próprio, avisando arthurlleite):** (a) **feito em 25/11:** c7 agora usa `GET /api/v1/clients/{id}`; (b) no c1, c2, c3, c4, c5, c7 e c8, dizer que a rota e a regra já existem (CAD-03) e que a ACE-03 prova o comportamento por teste; (c) manter o c6 como entrega de código (campo do responsável ativo na lista); (d) dizer como montar as atribuições nos exemplos enquanto a ACE-02 não existir.

## 2. Decisões tomadas pelo agente
Cada uma precisa de confirmação humana.
### D1 · Regra de cadastro em `registry/service.py`, SQL só em `registry/repository.py`
- **Alternativas:** A) `service.py` (regras) + `repository.py` novo (tabela `cliente`) + rotas finas em `api/routes.py` · B) SQL dentro da rota · C) módulo novo `clients/`
- **Escolhida:** A — **motivo:** `ARCHITECTURE.md` §3, §7 e I-7; `registry` já é o dono de `cliente` (`registry/models.py`). C é proibido (§7).
- **Impacto:** T2 a T4. [x] confirmar
### D2 · Reaproveitar a regra da NUC-02 sem mudar o contrato do `core`
- **Alternativas:** A) listar e abrir com `filter_visible_clients` e `decide_access`; "só o chefe cadastra" checado no `registry` pelo papel · B) criar `Action.REGISTER` no `core` (mudança de contrato v0, exige issue `contrato:`)
- **Escolhida:** A — **motivo:** `Action` hoje é `LIST`, `ACCESS` e `MANAGE_ASSIGNMENT`; cadastrar não envolve cliente existente. Menos impacto em NUC-03 e ACE-0x.
- **Fontes:** `src/lastro/core/service.py`, `src/lastro/core/contracts.py`. **Impacto:** T3. [x] confirmar
### D3 · `Membership` montado a partir de `SignedInMember`
- `Membership(member_id, firm_id, role, is_active=True)`; a sessão só chega aqui depois de `identify`, que já recusou vínculo inativo. **Responsável (pergunta 8, alternativa A):** `access.service.responsible_member_ids(db, firm_id, client_ids)` devolve o responsável ativo de cada cliente (`atribuicao` com `fim IS NULL`). O `registry` **não importa o `access`** (evita ciclo com a ACE-02): `api/routes.py` passa essa função a `registry.service.list_clients` e `get_client` como argumento. **Impacto:** T2, T3, T4. [x] confirmar
### D4 · Erros em RFC 9457 pelos handlers já existentes, mais três novos
- **Reaproveitar:** `_problem`, `PROBLEM_JSON`, `require_signed_in_member` e `EXCEPTION_HANDLERS` de `src/lastro/api/routes.py` (401 de c4 já sai de lá).
- **Novos:** `InvalidClientDataError` (carrega a mensagem do `CnpjValidationResult` ou "Informe o nome do cliente."; status da pergunta 1), `ClientNotFoundError` (404, **uma só** mensagem/título/corpo para inexistente e outro escritório, c3) e, se aceitas, `ClientAccessDeniedError` (403) e `DuplicateCnpjError` (409). A mensagem do CNPJ vem de `result.error_message`, sem duplicar o texto (`docs/modulos/registry.md`).
- **Impacto:** T3, T4. [x] confirmar
### D5 · Resposta mínima
- `POST` → 201 com `id`, `name`, `cnpj` (sem máscara, 14 caracteres maiúsculos); lista e detalhe com os mesmos três campos. **Sem** responsável na lista: é a c6 da ACE-03. Sem `escritorio_id` na resposta. Nomes de campo em `snake_case` (§3). **Impacto:** T4. [x] confirmar
### D6 · Fixture de banco copiada do padrão da ACE-01, local ao novo teste
- **Alternativas:** A) fixtures `head_database` e `office` próprias em `tests/registry/test_cliente.py`, copiando o padrão de `tests/access/test_login.py` · B) mover para um `conftest.py` compartilhado (mexe em teste de outra ficha)
- **Escolhida:** A — **motivo:** não toca testes passing; consolidar fica como chore futuro. Usuários inseridos por SQL com senha gerada na hora e `hash_password`; CNPJ válido gerado em tempo de execução (nunca literal, `SECURITY.md` §3). Dados: ESC-1, ESC-2, chefe_1, chefe_2, EMP-1, "EMPRESA TESTE 1".
- **Impacto:** T1. [x] confirmar
### D7 · Sem biblioteca nova, sem migração
- Tabela `cliente` existe (DB-01/DB-02, revisão `0003`); CNPJ validado por `validate_cnpj` (CAD-01); FastAPI/SQLAlchemy já no `pyproject.toml`. Sem pesquisa externa. [x] confirmar

## 3. Resumo e abordagem
O chefe cadastra cliente (nome + CNPJ) pela API; a lista do escritório e o endereço direto respeitam a regra de acesso da NUC-02; sem sessão nada é gravado.
1. T1: testes da ficha (5 nomes) e os adicionais, em `tests/registry/test_cliente.py`.
2. T2: contratos, repositório e consultas (`cliente` + `atribuicao` aberta).
3. T3: `register_client`, `list_clients`, `get_client` no `service.py`.
4. T4: rotas, handlers e status.
5. T5: OpenAPI, cliente do front, docs e `ARCHITECTURE.md` §6.
6. T6: verificação final.

## 4. Contexto encontrado
- **Planos lidos:** `planos/CAD-01` (aprovado), `planos/NUC-02` (aprovado), `planos/ACE-01` (**pronto para revisão**: decisões D1 a D10 valem como "intenção" e foram conferidas no código). Fora de `depende_de`: nenhum.
- **Conferência com o código (tudo confere):** `validate_cnpj`/`CnpjValidationResult` em `registry/service.py` e `contracts.py`; `decide_access`, `filter_visible_clients`, `Membership`, `ClientScope` em `core/`; `SignedInMember`, `require_signed_in_member`, 401 de c4 em `api/routes.py`; `Client` (`cliente`, `UNIQUE(escritorio_id, cnpj_normalizado)`) em `registry/models.py`; `Assignment` com `fim IS NULL` único por cliente. **Divergência menor:** o plan da CAD-01 e `docs/modulos/registry.md` citam a CAD-03 como `not_started`/`RaissaOliveira19`; hoje é `in_progress`/`caio-nascime`. Sugestão: ajustar o nome em `registry.md` e `ARCHITECTURE.md` §6 na T5.
- **Dependências:** CAD-01, ACE-01, NUC-02 `passing`.
- **Não existe ainda:** `registry/repository.py`, rota de cliente, `tests/api/` vazio. **RLS** (NUC-03, depende desta ficha) ainda não existe: o filtro por `escritorio_id` no repositório é a única camada até lá; não criar política de contorno (`SECURITY.md` §8).
- **Reaproveitar:** `lastro.access.service.hash_password`, padrão de `tests/access/test_login.py` (`head_database`, `office`, `_client`), geração de CNPJ de `tests/registry/test_cnpj.py`, `lastro.api.export_openapi`.
- **Não criar:** módulo novo, `utils.py`, migração, `Action` nova no `core`, tela, atribuição de cliente (ACE-02), campo de responsável na lista (ACE-03).
- **Pesquisa externa:** sem pesquisa externa necessária.

## 5. Decisões (já resolvidas)
- 18/11 · P-01 (401/403/404, corpo idêntico), P-02 e P-02a (só o chefe cadastra; cliente aparece no escritório), P-09 (chefe vê a lista, só o responsável acessa).
- 22/11 · NUC-02: regra de acesso pura em `core/`.
- 25/11 · Pergunta 2: rotas em inglês (`/api/v1/clients`), pelo CODING_STANDARDS §1 e pelo precedente `/session` (caio-nascime). ACE-03 c7 já ajustada; a ACE-02 (`/clientes/{id}/atribuicao`) segue com ajuste sugerido, sem autorização de edição.
- 25/11 · Pergunta 6: nome com `strip()` e máximo de **255 caracteres** (valor escolhido por caio-nascime). Acima disso: mesmo status da P-13, mensagem sugerida "O nome do cliente deve ter no máximo 255 caracteres." (texto a confirmar). Se o layout do Domínio (D-05) impuser limite menor, rever.
- 25/11 · Pergunta 8: alternativa A. O `access` oferece `responsible_member_ids`; o `registry` recebe a função por parâmetro, passada pela `api/`, sem importar o `access` (caio-nascime). Sem issue `contrato:`, por decisão dele; a função é de uso interno do `api/` e do `registry` e fica documentada em `docs/modulos/access.md`.
- 25/11 · Pergunta 1 (P-13): recusa por dado inválido é **422** (caio-nascime). Falta só registrar a P-13 como aprovada em `DECISIONS.md` (o humano, fora do `/planejar`); vale também para CAD-04, 06 e 07.
- 25/11 · Pergunta 3: CNPJ repetido no mesmo escritório → **409**, "Este CNPJ já está cadastrado no seu escritório.", sem expor o outro cliente; o mesmo CNPJ em outro escritório é aceito (caio-nascime).
- 25/11 · Pergunta 4: contador que tenta cadastrar → **403**, "Só o chefe do escritório pode fazer isso." (texto da ACE-02 c8), com teste adicional (caio-nascime).
- 25/11 · Pergunta 7: tela do cadastro fora desta ficha; sugerir ficha de front se faltar (caio-nascime).
- 25/11 · Pergunta 5: a CAD-03 cria a rota mínima de lista e de abrir cliente (id, nome, CNPJ) com a regra completa da P-09, inclusive o 403 do chefe sem atribuição, coberto por teste adicional. A ACE-03 cobre o resto: campo do responsável (c6) e seus testes. caio-nascime autorizou atualizar a ficha da ACE-03 para isso (caio-nascime). **A edição da ficha não foi feita pelo `/planejar`**; ver "Mudanças sugeridas".

## 6. Avaliação da ficha
| # | Achado | Gravidade | Critério |
|---|---|---|---|
| 1 | Status de dado inválido `[definir P-13]` (pergunta 1, respondida: 422) | ATENÇÃO | c2 |
| 2 | Caminhos das rotas não estão na ficha e divergiam entre fichas (pergunta 2, respondida) | ATENÇÃO | c1, c3, c4 |
| 3 | CNPJ repetido, contador cadastrando e chefe sem atribuição não têm critério (perguntas 3 a 5) | ATENÇÃO | — |
| 4 | c3 usa "endereço direto" e c1 "lista": rotas que se sobrepõem à ACE-03 (pergunta 5) | ATENÇÃO | c1, c3 |
| 5 | c2 junta nome vazio e CNPJ inválido; cada um tem teste próprio, o que prova (a) e (b) | — | c2 |
| 6 | c3 pede corpo 404 "idêntico" ao de inexistente; teste compara corpo inteiro (status, `title`, `detail`) | ATENÇÃO | c3 |
| 7 | "a lista de ESC-1 continua com 0 clientes" exige olhar o banco ou a lista após a recusa; usar a API e conferir `cliente` por SQL | ATENÇÃO | c2, c4 |
| 8 | 4 critérios, 1 módulo, 5 comandos; cabe em 2 sessões (testes e implementação). Não dividir. Risco de dado real baixo: CNPJs gerados na hora; `hx check-clean` cobre | — | todos |

## 7. Riscos
- CNPJ válido literal em teste, docstring ou doc quebra o `hx check-clean` → gerar só em execução; exemplos escritos com DV inválido.
- Vazar existência de cliente de outro escritório (c3, I-4) → um só caminho de código para `NOT_FOUND`; teste compara corpos byte a byte; toda consulta filtra por `escritorio_id` da sessão (nunca do corpo).
- Sem RLS até a NUC-03 → registrar no PR que o isolamento desta ficha é só aplicativo.
- Sobreposição com ACE-02/ACE-03 (rotas, campos) → avisar os donos no PR; `ClientSummary` e `responsible_member_ids` são v0 (regra 11); sem issue por decisão de caio-nascime, então mudar um deles depois exige avisar os donos no PR.
- Corrida entre dois cadastros do mesmo CNPJ → depender do `UNIQUE` e capturar `IntegrityError` (pergunta 3).

## 8. Aprovação
- [x] Perguntas BLOQUEANTES respondidas (1 e 2, em 25/11)
- [x] Decisões do agente confirmadas (D1 a D7, caio-nascime, 25/11)
- [x] Plan e tasks revisados por caio-nascime em 25/11
