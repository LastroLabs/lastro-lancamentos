# Lastro — Padrões de código (v0.1, proposta)

Regras para escrever código, pastas e arquivos do Lastro. Valem para pessoas e para agentes. Ficam em `docs/CODING-STANDARDS.md` e o `AGENTS.md` aponta para cá (uma linha).

**Princípio:** o código fala inglês; os documentos e a interface falam português. Os padrões abaixo seguem as guias que a indústria usa (PEP 8, Google Python Style Guide, convenções de TypeScript/React e de PostgreSQL). Onde as fontes divergem, a seção 8 diz o que escolhemos e por quê.

Itens marcados `[definir]` são propostas que o time precisa aprovar. Até lá, siga a proposta.

## 1. O que é inglês e o que é português

| Em inglês | Em português |
|---|---|
| Nomes de pastas e arquivos de código, testes, migrações e configs | Documentos: `docs/`, `README`, `AGENTS.md`, `ARCHITECTURE.md`, fichas, planos, `progress/` |
| Variáveis, funções, classes, módulos, constantes, tipos | Texto que o usuário vê (`web/src/copy/`) |
| Tabelas, colunas, índices, constraints, enums | Mensagens de erro da API (RFC 9457, I-14) |
| Rotas e campos da API (`/api/v1/clients`) | Mensagens de commit e de PR (podem ser em português) |
| Comentários e docstrings | Mensagens do `hx` (ERRO / MOTIVO / CORREÇÃO) |
| Nomes de testes (`test_balance_mismatch_blocks_export`) | Nomes dos critérios nas fichas |

Regras de apoio:
- **ASCII apenas** em identificadores, pastas e arquivos: sem acento, sem `ç`, sem espaço. O PEP 8 pede identificadores ASCII e, sempre que possível, palavras em inglês.
- **Comentários e docstrings em inglês.** O PEP 8 só admite outro idioma se o código nunca for lido por quem não o fala. Como o agente e a equipe alternam entre idiomas, ficamos com inglês.
- **Termos do domínio:** use o glossário da seção 7. Sem tradução livre: um conceito, um nome, em todo o código.
- **Nome próprio e sigla ficam como são:** `Dominio` (produto), `CPF`, `CNPJ`, `OFX`. Ex.: `layouts/dominio.yaml`, `validate_cpf()`.
- **Texto para o usuário nunca fica no código.** No front vai em `web/src/copy/`; no back, na mensagem do erro RFC 9457.

## 2. Python

Base: PEP 8, PEP 257 e Google Python Style Guide, conferidos por `ruff` (e por tipo, `[definir]` mypy ou pyright).

**Nomes**

| Elemento | Padrão | Exemplo |
|---|---|---|
| Módulo e arquivo | `snake_case`, curto | `bank_statement.py` |
| Pacote (pasta) | minúsculo, sem `_` se possível | `registry`, `parsing` |
| Classe e exceção | `PascalCase`; erro termina em `Error` | `ParsedStatement`, `BalanceMismatchError` |
| Função, método, variável | `snake_case`, verbo para função | `parse_statement()` |
| Constante de módulo | `UPPER_SNAKE_CASE` | `MAX_UPLOAD_BYTES` |
| Interno ao módulo | um `_` na frente | `_normalize_memo()` |
| Booleano | `is_`, `has_`, `can_` | `is_reviewed` |
| Dinheiro | sufixo `_cents` | `amount_cents` |
| Data e hora | `_at` (instante), `_on` (dia) | `created_at`, `reference_on` |

Evite `l`, `O`, `I` e nomes de uma letra (exceto índice curto em laço). Nome de variável diz o que é, não o tipo (`clients`, não `client_list`).

**Estilo**
- 4 espaços, nunca tab. Linha de até **100** caracteres (o PEP 8 aceita até 99 por acordo da equipe; `[definir]` confira o `line-length` do `pyproject.toml`). Formatação por `ruff format`.
- Imports no topo, em três grupos (biblioteca padrão, terceiros, `lastro`), um por linha, absolutos. Sem `import *`.
- Tipos em toda função pública: `list[str]`, `X | None` (sem `List`/`Optional`). Contratos entre módulos são `@dataclass(frozen=True, slots=True)`.
- Docstring (estilo Google, `"""`) em todo módulo, classe e função **pública**: uma linha de resumo; `Args:`, `Returns:`, `Raises:` quando não for óbvio.
- Exceções: capture a específica; nunca `except:` nu; nada de engolir erro com `pass`.
- Sem estado global mutável. Constante de módulo pode.
- Função pequena e com um propósito; mais de ~40 linhas, reavalie.
- `f-strings` para texto; `logging` (nunca `print`) fora de scripts do `tools/`.
- Dinheiro sempre `int` em centavos (AGENTS.md, regra 4); nunca `float`.

**Estrutura de módulo:** `service.py`, `contracts.py`, `repository.py`, `models.py`, `routes.py` (ver ARCHITECTURE.md, seção 3). Um arquivo novo dentro de um módulo tem nome do que contém (`ofx_reader.py`, `bb_pdf_reader.py`), nunca `utils.py` ou `helpers.py`.

**Testes**
- Pasta `tests/<module>/`, arquivo `test_<module>_<topic>.py`, função `test_<behavior>()`.
- Use **nomes de arquivo únicos** em todo o projeto (o `test_service.py` repetido em duas pastas pode dar "import file mismatch" sem `__init__.py`). `[definir]` ou configure `--import-mode=importlib`.
- Dado de teste é sintético (`fixtures/`), nunca extrato real (AGENTS.md, regra 1).

## 3. TypeScript e React

Base: guia de código do TypeScript (Microsoft), convenções do React, `eslint` + `typescript-eslint` + `prettier`.

**Nomes**

| Elemento | Padrão | Exemplo |
|---|---|---|
| Componente (função e arquivo) | `PascalCase` | `StatementTable.tsx` |
| Props do componente | `<Componente>Props` | `StatementTableProps` |
| Hook | `camelCase` com `use` | `useClientList.ts` |
| Handler de evento | `handle` + evento; prop recebida: `on` + evento | `handleSubmit`, `onSubmit` |
| Tipo, interface, enum | `PascalCase`; **sem prefixo `I`**; membros de enum em `PascalCase` | `Client`, `ReviewStatus.Pending` |
| Variável, função, propriedade | `camelCase` | `fetchClients` |
| Constante | `UPPER_SNAKE_CASE` | `MAX_FILE_SIZE_MB` |
| Pasta | minúscula (`kebab-case` se tiver duas palavras) | `pages/manager` |
| Arquivo que não é componente | `camelCase` | `formatMoney.ts` |
| Teste | `<Arquivo>.test.tsx` ao lado do arquivo | `StatementTable.test.tsx` |

**Boas práticas**
- Só componentes de função, um componente exportado por arquivo, arquivo `.tsx`; lógica sem JSX em `.ts`.
- `strict: true`; `any` proibido (use `unknown` e estreite). Tipos da API vêm do cliente em `web/src/api/`.
- Estado e busca de dados em hooks, não espalhados pelo JSX. O navegador só fala com `/api/v1` (ARCHITECTURE.md, seção 1).
- Texto de interface só de `web/src/copy/`; nunca literal em português dentro do componente.
- Dinheiro: o backend manda centavos (`amountCents`); a formatação em reais acontece em um único lugar (`formatMoney.ts`).
- Acessibilidade básica: `label` em todo campo, `alt` em imagem, foco visível. A página do cliente é mobile primeiro.
- Campos da API: o corpo JSON usa `snake_case` (padrão do FastAPI/Pydantic); a conversão para `camelCase` acontece **só** em `web/src/api/`. `[definir]` alternativa: configurar alias no Pydantic.

## 4. SQL e banco (PostgreSQL)

**Exceções da DB-01, decididas pelo responsável em 23/11/2026:** os nomes físicos de tabelas e colunas permanecem exatamente como na ficha `features/DB-01.json`, em português e no singular (`escritorio`, `usuario`, `membro`, `sessao`, `convite`, `cliente`, `atribuicao`). A exceção não se estende a outros módulos; classes Python e convenção central seguem D2 confirmado no plano DB-01. A DB-01 cria o esquema e suas restrições; as políticas RLS ficam na NUC-03, cuja conclusão é obrigatória antes do uso com dados de piloto. Não criar políticas permissivas para contornar essa divisão. Estas exceções prevalecem sobre as regras gerais de nomes e de RLS na mesma migração abaixo; não dispensam isolamento no produto. Registro: `docs/decisoes/DECISIONS.md`, seção 5.

Base: convenções da comunidade PostgreSQL; os identificadores têm no máximo **63 caracteres** e, sem aspas, o Postgres os grava em minúsculas.

| Elemento | Padrão | Exemplo |
|---|---|---|
| Tabela | `snake_case`, **plural** | `bank_accounts`, `statement_lines` |
| Coluna | `snake_case`, singular | `closing_balance_cents` |
| Chave primária | `id` | `id` |
| Chave estrangeira | `<tabela_no_singular>_id` | `client_id` |
| Booleano | `is_`, `has_` | `is_reviewed` |
| Data e hora | `_at` (`timestamptz`), `_on` (`date`) | `uploaded_at`, `reference_on` |
| Dinheiro | `bigint` em centavos, sufixo `_cents` | `amount_cents` |
| Tabela de ligação | as duas entidades | `user_clients` |
| Constraints e índices | prefixo + tabela + coluna | `pk_`, `fk_`, `uq_`, `ck_`, `ix_` |

- Nada de aspas nem maiúsculas em nome; sem prefixos como `tbl_`; sem palavras reservadas (`user`, `order`, `group`) como nome de tabela ou coluna. É um dos motivos de usar plural (`users`, `orders`).
- Nomeie constraints e índices por convenção central (em SQLAlchemy/Alembic, um `naming_convention` no `MetaData`), para que as migrações sejam reproduzíveis. `[definir]` confirme o formato na documentação do Alembic.
- Use `timestamptz` para instantes, `text` para texto, `bigint` em centavos para dinheiro. Colunas `NOT NULL` por padrão; `NULL` só com motivo.
- Toda tabela com dado de escritório tem a coluna do escritório e a política de RLS na mesma migração (ARCHITECTURE.md, I-4).
- **Migrações:** uma por PR, em `migrations/versions/`, arquivo `<revision>_<verb>_<object>.py` (ex.: `add_statement_lines`). Nunca edite migração já aplicada.
- **Consultas escritas à mão:** palavras-chave em MAIÚSCULAS, nomes em minúsculas, um item por linha em `SELECT` longo, sempre com parâmetros (nunca concatenar texto). `[definir]` `sqlfluff` no `hx verify`.
- Segredos, dados reais e extratos nunca entram em migração, seed ou fixture.

## 5. Pastas e arquivos

- **Pastas e arquivos de código:** inglês, ASCII, sem espaços. Python em `snake_case`; front conforme a seção 3.
- **Documentos:** conteúdo em português, mas o **nome** do arquivo segue o padrão do repositório (`AGENTS.md`, `ARCHITECTURE.md`, `SECURITY.md`, `CODING-STANDARDS.md`): maiúsculas e inglês na raiz; em `docs/`, nomes curtos em inglês e `kebab-case`.
- **Fichas, planos e progress:** `features/<ID>.json`, `planos/<ID>/plan.md`, `planos/<ID>/tasks.md`, `progress/<ID>.md`. O ID é o do harness (`NUC-01`, `HX-09`).
- **Configs:** `pyproject.toml`, `package.json`, `docker-compose.yml`, `.env.example`; nunca commite `.env`.
- Sem arquivos genéricos (`utils`, `helpers`, `misc`, `common`, `new`, `final`, `v2`): o nome diz o conteúdo.
- Pasta nova de primeiro nível ou módulo novo: não crie (ARCHITECTURE.md, seção 7).
- Codificação UTF-8, final de linha `LF`, uma linha em branco no fim do arquivo. `[definir]` `.editorconfig` e `.gitattributes`.

## 6. Conferência automática

| O que | Ferramenta | Situação |
|---|---|---|
| Python: formato, imports, nomes, docstrings | `ruff` (`format`, e regras `E`, `F`, `I`, `N`, `UP`, `B`, `D`) | `[definir]` ver o que o `pyproject.toml` já ativa |
| Python: tipos | mypy ou pyright | `[definir]` |
| Front: lint, nomes, formato | `eslint`, `typescript-eslint` (`naming-convention`), `prettier` | `[definir]` |
| SQL e migrações | `sqlfluff`; revisão de migração no PR | `[definir]` |
| Arquivos e finais de linha | `.editorconfig` | `[definir]` |

Regra de ouro: **o que uma ferramenta confere deve entrar no `hx verify`**. O que ninguém confere, a revisão do PR cobra (rubrica; `[definir]` em qual item). Sem ferramenta, a regra é só um desejo.

## 7. Glossário do domínio (português → inglês) — proposta

Um conceito, um nome. Use sempre o da coluna inglesa em código, banco, rotas e testes. Confirme com o time antes de renomear.

| Português | Inglês (código) | Observação |
|---|---|---|
| escritório | `firm` | escritório de contabilidade |
| contador | `accountant` | |
| chefe | `manager` | |
| cliente | `client` | empresa atendida |
| sócio | `partner` | |
| carteira | `portfolio` | clientes atribuídos a um contador |
| conta bancária | `bank_account` | |
| extrato | `statement` | |
| movimentação | `transaction` | linha do extrato; evite `movement` |
| plano de contas | `chart_of_accounts` | |
| conta contábil | `ledger_account` | |
| lançamento | `journal_entry` | |
| contraparte | `counterparty` | |
| sugestão | `suggestion` | |
| pergunta, resposta do cliente | `question`, `client_answer` | |
| revisão, pendente | `review`, `pending` | |
| quarentena | `quarantine` | arquivo recém-enviado, ainda não validado |
| conferência (saldo e continuidade) | `validation` | módulo `validation/` |
| conciliação | `reconciliation` | só quando for conciliação mesmo |
| exportação | `export` | |
| fotografia imutável da exportação | `export_snapshot` | |
| Domínio (sistema contábil) | `dominio` | nome próprio, sem acento |
| histórico (de classificações) | `history` | |
| parecidas | `similar` | busca por similaridade (`pg_trgm`) |

**Contratos v0 (ARCHITECTURE.md, seção 6), nomes propostos:**

| Hoje | Proposto |
|---|---|
| `ExtratoLido` | `ParsedStatement` |
| `MovimentacaoLida` | `ParsedTransaction` |
| `ResultadoConferencia` | `ValidationResult` |
| `Sugestao` | `Suggestion` |
| `RespostaCliente` | `ClientAnswer` |
| `ItemRevisado` | `ReviewedItem` |

## 8. Onde as fontes divergem e o que escolhemos

| Tema | As fontes dizem | Escolha | Motivo (inferência) |
|---|---|---|---|
| Tabela no singular ou plural | Guias do Supabase e do postgres.ai preferem plural; outras guias da comunidade preferem singular | **Plural** | Evita palavras reservadas (`user`, `order`) e é o mais comum no ecossistema SQLAlchemy |
| Nome de arquivo de componente React | Airbnb e guias derivadas usam `PascalCase.tsx`; outras guias usam `kebab-case` | **`PascalCase.tsx`** para componentes, `camelCase` para o resto | O nome do arquivo bate com o nome exportado e facilita busca |
| Prefixo `I` em interface | A guia do TypeScript da Microsoft desaconselha; a comunidade não é unânime | **Sem prefixo** | Segue a guia oficial |
| Largura de linha | PEP 8: 79 (até 99 por acordo); Google: 80 | **100** `[definir]` | Cabe nomes em inglês e anotações de tipo; confira com o `ruff` |
| Idioma de comentários | PEP 8: inglês | **Inglês** | Agentes e ferramentas leem melhor; o público do projeto pode ser global |

## 9. Código existente em português

Hoje há código, tabelas e testes com nomes em português (inclusive em `tools/` e `tests/harness`, e em fichas que citam testes pelo nome). Regras para a transição:

1. **Código novo** já nasce em inglês. Em código antigo, não misture: se a função está em português, não crie vizinha em inglês na mesma mudança sem avisar.
2. **Renomear é uma ficha própria por módulo**, sem funcionalidade nova junto, com a lista do que muda (arquivos, tabelas, contratos, nomes de teste citados em fichas).
3. **Banco:** renomear tabela exige migração; só faça antes de existir dado em produção `[definir]`.
4. **Fichas que citam teste pelo nome** (ex.: `test_filtro_um_estado`) precisam ser atualizadas junto com o teste. O `hx` não deixa o agente editar ficha ou teste sozinho: peça autorização.
5. **Docs afetados** ao aprovar este padrão: `ARCHITECTURE.md` (seção 6, 7 e 10, a rota pública `/api/v1/publico/` da I-6 e a frase sobre "identificadores em português"), `AGENTS.md` (uma linha apontando para este arquivo), `feature_template.md` (lista de módulos), `planejar.md` e `tasks-template.md` (checar nomes contra o glossário).

## 10. Fontes

- PEP 8: https://peps.python.org/pep-0008/
- Google Python Style Guide: https://google.github.io/styleguide/pyguide.html
- Guia de código do TypeScript (Microsoft): https://github.com/Microsoft/TypeScript/wiki/Coding-guidelines
- Guia de estilo do React (Airbnb, via Dynatrace): https://developer.dynatrace.com/develop/reference/react-style-guide/
- Guia de design de esquema, postgres.ai: https://postgres.ai/rules/development-db-schema-design-guide
- Guia de estilo SQL, Supabase: https://hub.continue.dev/supabase/postgres-sql-style-guide
- Convenções do PostgreSQL (Vonng): https://blog.vonng.com/en/pg/pg-convention-2018/
- Alembic, convenção de nomes de constraints: https://alembic.sqlalchemy.org/en/latest/naming.html (não conferido nesta sessão)
