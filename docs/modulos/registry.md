# Módulo `registry`: CNPJ (CAD-01), cliente (CAD-03), esquema (DB-02, DB-04), plano de contas em TXT (CAD-02) e carga do plano (CAD-05)

`src/lastro/registry/` reúne o domínio de cadastro do cliente (cliente, contas bancárias, sócios, plano de contas e configuração). A **CAD-01** entrega a validação e normalização pura de CNPJ numérico e alfanumérico (padrão julho/2026, IN RFB nº 2.229/2024), sem acesso a banco nem HTTP. Decisões em `planos/CAD-01/plan.md`.

## Contrato público (versão 0)

- **Função:** `validate_cnpj(cnpj: str) -> CnpjValidationResult` em `lastro.registry.service`
- **Tipo de retorno:** `CnpjValidationResult` (`@dataclass(frozen=True, slots=True)`) em `lastro.registry.contracts`

```python
from lastro.registry.service import validate_cnpj

result = validate_cnpj(raw_cnpj)
```

| Campo | Tipo | Semântica |
|---|---|---|
| `is_valid` | `bool` | `True` quando o formato e os dois dígitos verificadores passam; `False` caso contrário |
| `normalized` | `str \| None` | 14 caracteres ASCII maiúsculos, sem máscara, quando válido; `None` quando recusado |
| `error_message` | `str \| None` | `None` quando válido; mensagem oficial em português simples quando recusado |

### Mensagens oficiais

| Situação | `error_message` |
|---|---|
| Entrada vazia ou só com espaços | `"Informe o CNPJ do cliente."` |
| Tamanho errado, caractere fora do padrão, máscara mal posicionada, 14 caracteres iguais ou dígito verificador incorreto | `"O CNPJ informado não é válido. Confira os números."` |

> **Versionamento (v0):** qualquer mudança de campo, assinatura ou mensagem oficial deve avisar o responsável pela `CAD-03` (`caio-nascime`), consumidora direta deste contrato.

## Regras de validação e normalização

- Remove espaços nas bordas (`.strip()`) antes de verificar se a entrada está vazia.
- Aceita apenas caracteres ASCII (`re.ASCII`), normalizando letras para maiúsculas:
  - sem máscara: `^[A-Z0-9]{12}[0-9]{2}$`
  - máscara oficial exata: `XX.XXX.XXX/XXXX-XX` (com letras/dígitos nas 12 primeiras posições e apenas dígitos nos 2 verificadores).
- Recusa sequências com todos os 14 caracteres idênticos (ex.: `00.000.000/0000-00`).
- Calcula os dois dígitos verificadores pelo Módulo 11 com `ord(char) - 48` (unificando numérico e alfanumérico), pesos `(5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)` e `(6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)`.

## Consumidores e impactos conhecidos

- **CAD-03 (consumidora direta):** `register_client` usa `result.error_message` direto, sem duplicar a string.
- **DB-01 (`cliente.cnpj_normalizado`):** a persistência precisa aceitar 14 caracteres alfanuméricos em texto (`TEXT`), nunca inteiro nem restrição apenas de dígitos.
- **P-13 (status HTTP de dado inválido):** 422, aprovada em 25/11 (`docs/decisoes/DECISIONS.md`). Este contrato devolve apenas a mensagem de erro; a tradução para status HTTP (RFC 9457) pertence à camada `api/`.
- **`tools/harness.py` (`check-clean`):** a função `cnpj_valido` do harness é propositalmente separada de `src/lastro/` (o código de produção não importa `tools/`). A `HAR-04` trata a parte alfanumérica no harness; manter atenção para que as duas regras não divirjam.
- **Demais contratos de `registry`:** os contratos `registry → classification/export` seguem `[definir]` em `ARCHITECTURE.md` (seção 10).

## Armadilhas

- **Não commitar literais de CNPJ com DV válido:** em testes e exemplos escritos, gere o DV em tempo de execução ou use exemplos com DV inválido (`docs/SECURITY.md` §3).
- **Pontuação fora do lugar não é removida:** o validador não faz `re.sub` genérico de não-alfanuméricos para evitar aceitar caracteres inválidos (como `#`) ou máscaras quebradas.
- **Sem acoplamento com HTTP ou banco:** `src/lastro/registry/cnpj.py` é interno ao módulo; outros módulos devem importar apenas `lastro.registry.service` e `lastro.registry.contracts`.

## Cadastro de cliente (CAD-03, versão 0)

Decisões em `planos/CAD-03/plan.md`. O isolamento tem duas camadas: toda consulta de `repository.py` filtra pelo `escritorio_id` da sessão, nunca do corpo, e o banco também esconde os clientes de outro escritório (RLS da NUC-03; ver `docs/modulos/access.md`, "Isolamento no banco"). Mantenha o filtro: a RLS é a segunda barreira, não a única.

### Serviço (`lastro.registry.service`)

| Função | O que faz | Erros |
|---|---|---|
| `register_client(db, membership, name, cnpj) -> ClientSummary` | Só o chefe cadastra. Ordem fixa: papel, nome (`strip()`, vazio, depois mais de 255 caracteres), CNPJ (`validate_cnpj`). Commit só no sucesso | `ManagerOnlyError`, `InvalidClientDataError(message)`, `DuplicateCnpjError` (pelo `UNIQUE (escritorio_id, cnpj_normalizado)`, também em corrida) |
| `list_clients(db, membership, find_responsibles) -> list[ClientSummary]` | Clientes do escritório filtrados por `core.service.filter_visible_clients`, por nome | — |
| `get_client(db, membership, client_id, find_responsibles) -> ClientSummary` | Abre um cliente por `core.service.decide_access(..., Action.ACCESS, ...)` | `ClientNotFoundError` (inexistente, id malformado ou de outro escritório: o mesmo erro), `ClientNotAssignedError` (chefe sem atribuição) |

`membership` é o `Membership` de `lastro.core.contracts`, montado pela `api/` a partir do `SignedInMember` (`is_active=True`: o `identify` já recusou vínculo inativo). `find_responsibles(db, firm_id, client_ids) -> dict[str, str | None]` é passada pela `api/` (`lastro.access.service.responsible_member_ids`). O `registry` não importa nada do `access` (nem `access.contracts`) e não lê `atribuicao` (plano D3), para não formar ciclo com a ACE-02.

`ClientSummary` (`lastro.registry.contracts`): `client_id`, `name`, `cnpj` (14 caracteres, sem máscara). Sem id do escritório.

### Rotas (`lastro.api.routes`, sob `/api/v1`)

| Rota | Sucesso | Recusas |
|---|---|---|
| `POST /clients` (`{"name", "cnpj"}`) | 201, `{"id", "name", "cnpj"}` | 401 "Entre para continuar."; 403 "Só o chefe do escritório pode fazer isso."; 422 "Informe o nome do cliente.", "O nome do cliente deve ter no máximo 255 caracteres." ou a mensagem do CNPJ; 409 "Este CNPJ já está cadastrado no seu escritório." |
| `GET /clients` | 200, lista de `{"id", "name", "cnpj"}` | 401 |
| `GET /clients/{client_id}` | 200, `{"id", "name", "cnpj"}` | 401; 403 "Atribua este cliente a você para fazer isso."; 404 "Você não tem acesso a este cliente." (corpo idêntico para inexistente e outro escritório) |

O campo do responsável na lista fica para a ACE-03 (c6).

## Esquema do cadastro e do plano de contas (DB-02, DB-04)

Texto da DB-02 trazido de `docs/modules/registry.md`, que deixa de existir (a pasta oficial é `docs/modulos/`).

A revisão Alembic `0003` acrescenta `plano_contas`, `conta_contabil`, `conta_bancaria` e `socio`. Cada tabela usa a chave primária `(escritorio_id, cliente_id, id)` e uma FK composta para `cliente`. A coluna `id` recebe UUID gerado pelo banco.

`plano_contas` pertence a um cliente, tem versão positiva e única por cliente, e registra o membro do mesmo escritório que importou o plano (`situacao`: `importado`, `publicado` ou `substituido`). `conta_contabil` pertence a uma versão do plano do mesmo cliente; a conta pai precisa estar na mesma versão. O código contábil é texto e único apenas dentro daquela versão. `conta_bancaria` guarda o código do banco como texto e só referencia uma conta contábil do próprio cliente. `socio` guarda nome e nome normalizado.

`cliente.plano_atual_id` aponta para um plano do próprio cliente. As contas transitória, de entrada de sócio e de saída de sócio só podem apontar para contas desse plano (FK composta com `plano_atual_id`). A troca do plano exige limpar ou trocar, **no mesmo `UPDATE`**, uma conta configurada que não exista no plano novo. Uma conta configurada não pode permanecer quando o plano atual é nulo.

O downgrade da `0003` remove as quatro colunas de configuração e as quatro tabelas, preservando as tabelas e os registros da DB-01. Ele elimina os dados próprios da DB-02; deve ser executado apenas conforme o procedimento de migração do ambiente. As políticas de RLS vêm da NUC-03 (`0005`).

**DB-04 (revisão `0007`, depois da `0005` e da `0006` da NUC-03):** `conta_contabil` ganha:

| Coluna | Tipo | Regra |
|---|---|---|
| `codigo_reduzido` | `text`, nulo permitido | 7 dígitos atribuídos pelo programa contábil; é o código que a exportação usa (D-05). `UNIQUE (escritorio_id, cliente_id, plano_id, codigo_reduzido)` (`uq_conta_contabil_plano_reduzido`); nulos não conflitam |
| `tipo` | `text NOT NULL DEFAULT 'A'` | `CHECK (tipo IN ('S', 'A'))` (`ck_conta_contabil_tipo`). `S` = grupo (sintética), `A` = recebe lançamento (analítica). Linhas anteriores ficam `A` |

`codigo` **não muda de nome**: guarda a classificação em dígitos, sem pontos (`1101`, `9999`). Renomear quebraria os testes da DB-02 e da DB-03.

**Testes de esquema fixados na revisão da própria ficha.** Teste que compara a lista exata de colunas, ou o conteúdo inteiro das tabelas, sobe só até a revisão da sua ficha (DB-02 c1 na `0003`, DB-03 c4 na `0004`). Assim, uma migração posterior que acrescenta colunas não quebra a ficha antiga. Ficha nova que muda tabela de outra ficha prova as colunas de `head` nos próprios testes.

## Leitura do plano de contas em TXT (CAD-02, contrato v1)

O contador exporta o plano do programa contábil (Domínio) como texto de largura fixa. A CAD-02 lê e valida esse arquivo, sem banco nem HTTP. Implementação interna em `src/lastro/registry/chart_txt.py`, exposta só por `service.py` e `contracts.py`. Substitui o leitor `.xlsx`, que nunca chegou à `developer`; o `openpyxl` sai das dependências.

```python
from lastro.registry.service import read_chart_of_accounts

result = read_chart_of_accounts(data)  # bytes ou Path; nunca levanta exceção por arquivo ruim
```

### Formato da linha (78 caracteres, sem cabeçalho)

| Fatia | Campo | Observação |
|---|---|---|
| `[0:7]` | código reduzido | 7 dígitos; atribuído pelo programa contábil a cada cliente; não tem relação com a hierarquia |
| `[7:27]` | classificação | só dígitos, alinhada à esquerda, sem pontos; a hierarquia vem dela |
| `[27:67]` | nome | até 40 caracteres, truncado pelo programa; o tipo pode ficar colado ao nome (`...LTDAA`) |
| `[67]` | tipo | `S` (grupo) ou `A` (analítica) |
| `[68:78]` | espaços | |

A conta superior é o **maior prefixo próprio** da classificação que existe no arquivo (`110101` → `1101` → `11` → `1`). Não depende da máscara (`1.1.2.3.3` ou `1.1.1.2.5`) nem da ordem das linhas.

### Contrato (`lastro.registry.contracts`)

| Tipo | Campo | Tipo Python | Semântica |
|---|---|---|---|
| `ChartAccountEntry` | `line_number` | `int` | Posição da linha no arquivo (linhas em branco contam) |
| | `reduced_code` | `str` | 7 dígitos |
| | `classification` | `str` | Só dígitos |
| | `name` | `str` | Sem espaços nas pontas |
| | `kind` | `Literal["S", "A"]` | |
| | `parent_classification` | `str \| None` | `None` nas contas de topo |
| `ChartOfAccountsResult` | `accounts` | `tuple[ChartAccountEntry, ...]` | Aceitas, na ordem do arquivo; `()` na recusa |
| | `errors` | `tuple[str, ...]` | Linhas toleradas (deixadas de fora); `()` na recusa |
| | `warnings` | `tuple[str, ...]` | Não impedem a carga; `()` na recusa |
| | `refusal` | `str \| None` | Mensagem única de recusa; `None` quando aceito |

A `api/` decide pelo `refusal`: preenchido → 422 (P-13) com a mensagem; `None` → sucesso, com `errors` e `warnings` na resposta.

### Regra de leitura, nesta ordem

1. Bytes vazios → `refusal = "O arquivo não tem nenhuma conta."`
2. Acima de 20 MiB, começando com `PK\x03\x04` (`.xlsx`/ZIP) ou `%PDF-`, ou com byte `\x00` → `"Este arquivo não é um plano de contas em texto. Envie o plano de contas em arquivo .txt."`
3. Decodifica UTF-8 (com ou sem BOM); se falhar, Windows-1252 com `errors="replace"` (o cp1252 puro levanta em `0x81`, `0x8D`, `0x8F`, `0x90`, `0x9D`).
4. Separa com `split("\n")` e `rstrip("\r")` em cada linha (não `splitlines`, que quebra em outros caracteres). Linhas em branco são ignoradas; o número da linha é a posição real. Nenhuma linha com conteúdo → `"O arquivo não tem nenhuma conta."`
5. **Erro próprio** de cada linha: o primeiro da tabela abaixo. As causas vêm antes dos toleráveis, para a mensagem apontar o que de fato impede a carga.
6. **Repetições**, conferidas em toda linha, mesmo com erro próprio, e com prioridade sobre ele (é o que torna o resultado independente da ordem): reduzido válido que já apareceu (E6) e classificação legível que já apareceu (E7). A primeira ocorrência fica; a de baixo é a causa.
7. **Hierarquia**, sobre todas as linhas com classificação legível (primeira ocorrência), em ordem crescente de comprimento. `mínimo` é o menor comprimento do arquivo.
   - sem conta superior e mais longa que o mínimo → causa: `a conta {cla} não tem conta superior no arquivo.`
   - conta superior analítica → causa: `a conta {cla} está abaixo da conta analítica {pai} (linha {m}).`
   - conta superior não aceita → consequência: `a conta {cla} está abaixo da conta {pai} (linha {m}), que tem erro.`
8. Uma linha com erro próprio **tolerável** (E2, E2z, E4) fica de fora e vai para `errors` só se for a primeira com aquela classificação, for `A`, não tiver nenhuma linha abaixo dela e não tiver problema de hierarquia. Senão, o mesmo erro vira causa.
9. Mensagem de cada linha (uma só): repetição, depois causa de hierarquia, depois erro próprio. A consequência não é mostrada nem contada: a causa está na linha de cima.
10. Havendo causa → recusa com a **primeira causa** (menor número de linha) e a contagem das outras causas:
    - 1 causa: `{mensagem} Corrija essa linha e envie o arquivo de novo.`
    - mais de 1: `{mensagem} Há mais {n} {linha|linhas} com problema. Corrija e envie o arquivo de novo.` (`1 linha`, `3 linhas`)
11. Nenhuma analítica aceita: se houve linha tolerada, ela vira causa (passo 10); senão `"O arquivo não tem nenhuma conta analítica. Confira se é o plano de contas do cliente."`
12. Aceito: as contas na ordem do arquivo, os erros tolerados e um aviso para cada sintética aceita sem nenhuma linha abaixo dela: `Linha {n}: a conta sintética {cla} não tem contas abaixo dela.` Sintética cuja única filha foi tolerada não gera aviso (o erro da filha já aparece).

### Erros de linha (sempre com o prefixo `Linha {n}: `)

| Cód. | Condição | Mensagem | Classe |
|---|---|---|---|
| E1 | menos de 68 caracteres | `a linha está incompleta.` | causa |
| E8 | texto que não é espaço em branco depois da posição 78 (espaço e tab não contam) | `a linha tem texto depois da posição 78.` | causa |
| E3a | classificação vazia | `falta a classificação da conta.` | causa |
| E3b | classificação com algo além de dígitos | `a classificação "{valor}" precisa ter só números.` | causa |
| E5a | tipo em branco | `falta o tipo da conta (S ou A).` | causa |
| E5b | tipo diferente de S e A | `o tipo "{valor}" não é válido. Use S ou A.` | causa |
| E2 | reduzido vazio | `falta o código reduzido da conta.` | tolerável |
| E2 | reduzido que não tem 7 dígitos ASCII | `o código reduzido "{valor}" precisa ter 7 dígitos.` | tolerável |
| E2z | reduzido `0000000` | `o código reduzido não pode ser 0000000.` | tolerável |
| E4 | nome vazio | `falta o nome da conta.` | tolerável |
| E6 | reduzido já usado numa linha anterior | `o código reduzido {r} já aparece na linha {m}.` | causa |
| E7 | classificação já usada numa linha anterior | `a classificação {c} já aparece na linha {m}.` | causa |

Aspas só no valor recusado, como foi lido; códigos válidos aparecem sem aspas.

### Por que erro em grupo recusa o arquivo inteiro

Medido nos dois planos reais (294 contas, 77 S e 217 A): um erro na raiz `1` derrubaria 72 contas (24%), na `3`, 121 contas, na `32`, 101 contas. Aceitar o resto em silêncio entregaria um plano mutilado. Por isso só a analítica folha com erro simples é tolerada, e todo o resto recusa com uma mensagem só.

### Armadilhas

- **Fatiar depois de decodificar.** Em UTF-8, um acento ocupa 2 bytes; fatiar bytes desloca o tipo. Um arquivo quase todo UTF-8 com 1 byte inválido cai inteiro no Windows-1252 e é recusado por E5a (comportamento fixado em teste).
- **O reduzido mais a classificação formam uma sequência de 8 a 27 dígitos** (`00071921101`). Com 11 ou 14 dígitos, o `check-clean` a trata como candidata a CPF ou CNPJ. Fixture e exemplo escritos precisam passar no `check-clean`.
- **Limitações registradas (fora do MVP):** não confere se a conta superior tem o comprimento do nível anterior da máscara; o formato foi confirmado com uma contadora e dois planos.

## Carga do plano (CAD-05)

A rota recebe o arquivo, chama `read_chart_of_accounts` e grava numa transação só. Regras que a ficha não diz, mas o banco exige (conferidas na simulação de 26/11 com RLS, como `lastro_app`):

1. **Recusa não grava nada.** Com `refusal` preenchido, 422 antes de abrir a transação; o plano atual e a configuração não mudam.
2. **Versão nova.** `plano_contas` com `versao = max + 1` e `situacao = 'publicado'`; o anterior passa a `'substituido'` e **continua no banco** (P-11 substitui o plano atual, não apaga o histórico).
3. **Contas.** `codigo` = classificação, `codigo_reduzido`, `nome`, `tipo` e `pai_id` resolvido por `parent_classification`. Gerar os ids na aplicação e **inserir em ordem crescente de comprimento da classificação**: com `executemany`, uma filha antes da conta pai dá `ForeignKeyViolation` (`fk_conta_contabil_pai`, não adiável).
4. **Troca do plano atual e remapeamento no mesmo `UPDATE`.** `plano_atual_id` passa ao plano novo e cada conta de configuração (`conta_transitoria_id`, `conta_entrada_socio_id`, `conta_saida_socio_id`) passa à conta do plano novo com a mesma classificação, ou fica nula se ela não existir. Em `UPDATE`s separados, a FK com `plano_atual_id` recusa.
5. **Conta bancária.** `conta_bancaria.conta_contabil_id`, se preenchido, também é remapeado pela classificação (a FK não exige o plano atual, mas apontar para o plano substituído é erro silencioso).
6. **Resposta.** Contagem antes e agora, `errors` e `warnings`.
