# Tasks — CAD-02 · Ler a planilha do plano de contas e apontar linha inválida

**Plan:** `planos/CAD-02/plan.md` · **Ficha:** `features/CAD-02.json`
**Ordem:** T1 → revisão humana dos testes → commit só-de-testes (e lockfile `openpyxl`, anotar o hash) → T2 em diante (sessão nova, sem editar `tests/`)

---

## [ ] T1 · Escrever os testes dos critérios (e adicionar `openpyxl` ao ambiente)
- **Critérios da ficha:** c1, c2, c3, c4
- **Regra de negócio (em linguagem simples):** provar em testes automatizados que uma planilha `.xlsx` de plano de contas vira lista ordenada de contas válidas, que linhas sem código ou sem nome e códigos repetidos são apontados com o número exato da linha sem descartar as demais contas, e que planilha vazia ou arquivo inválido é recusado por inteiro com mensagem clara em português.
- **Critérios de aceite:**
  - [ ] `openpyxl>=3.1.5` adicionada em `pyproject.toml`, `uv.lock` atualizado e imagem `dev` reconstruída (`FER-01`)
  - [ ] Existe um teste para cada um dos 5 nomes em `verificacao` de `features/CAD-02.json`: `test_planilha_valida_vira_lista_de_contas`, `test_linha_incompleta_rejeitada_com_numero`, `test_codigo_repetido_rejeitado_com_as_duas_linhas`, `test_planilha_sem_contas_recusada` e `test_arquivo_que_nao_e_planilha_recusado`
  - [ ] Os 5 testes falham hoje pelo motivo certo (função `read_chart_of_accounts_spreadsheet` ausente em `lastro.registry.service`), sem quebrar a coleta do pytest
  - [ ] Todos os dados são sintéticos e gerados em `tmp_path` em tempo de execução (nenhum arquivo real nem fixture persistida)
- **Exemplos:**
  - c1: cabeçalho `código`/`nome` + 3 linhas (`1.1.01` `Caixa`, `2.1.05` `Fornecedores`, `9.9.99` `Transitória`) → 3 contas nessa ordem e 0 erros
  - c2: linha 2 válida, linha 3 sem nome, linha 4 sem código, linha 5 válida → 2 contas aceitas (`1.1.01`, `9.9.99`) e 2 erros (`'Linha 3: falta o nome da conta.'`, `'Linha 4: falta o código da conta.'`)
  - c3: linha 2 `1.1.01` `Caixa`, linha 3 `2.1.05` `Fornecedores`, linha 4 `1.1.01` `Caixa geral` → 2 contas aceitas e 1 erro (`'Linha 4: o código 1.1.01 já apareceu na linha 2.'`)
  - c4: (a) só cabeçalho → 0 contas e `'A planilha não tem nenhuma conta.'`; (b) texto salvo como `.xlsx` → 0 contas e `'Este arquivo não é uma planilha. Envie um arquivo .xlsx.'`
- **Arquivos:** `tests/registry/test_planilha_plano.py`, `pyproject.toml`, `uv.lock`
- **Reaproveitar:** padrão de import sob demanda de `tests/registry/test_cnpj.py` · **Não criar:** código de produção em `src/` nem arquivo `.xlsx` commitado em `fixtures/`
- **Fora do escopo:** implementação em `src/lastro/registry/`, rotas HTTP e banco de dados
- **Decisões relacionadas:** D1, D3, D4, D6 (`plan.md`)
- **Pronto quando:** `docker compose build dev && docker compose run --rm dev pytest tests/registry/test_planilha_plano.py -q` executa os 5 testes e mostra apenas as 5 falhas esperadas

## [ ] T2 · Definir contratos v0 e interface pública no módulo `registry`
- **Critérios da ficha:** c1, c4
- **Regra de negócio (em linguagem simples):** criar a estrutura imutável que representa cada conta lida (código e nome) e o resultado da leitura da planilha (contas aceitas e erros encontrados), e expor a função pública que a `CAD-05` e os testes vão chamar.
- **Critérios de aceite:**
  - [ ] `ChartAccountEntry(code: str, name: str)` e `ChartSpreadsheetResult(accounts: tuple[ChartAccountEntry, ...], errors: tuple[str, ...])` definidos como `@dataclass(frozen=True, slots=True)` em `src/lastro/registry/contracts.py`
  - [ ] `read_chart_of_accounts_spreadsheet(source: bytes | Path) -> ChartSpreadsheetResult` exposta em `src/lastro/registry/service.py`, tipada e com docstring Google em inglês
  - [ ] `validate_cnpj` e `CnpjValidationResult` permanecem inalterados e os testes da `CAD-01` continuam verdes
- **Exemplos:** chamar `read_chart_of_accounts_spreadsheet(path)` devolve uma instância imutável de `ChartSpreadsheetResult` com tuplas `accounts` e `errors`
- **Arquivos:** `src/lastro/registry/contracts.py`, `src/lastro/registry/service.py`
- **Reaproveitar:** estrutura de `CnpjValidationResult` e `validate_cnpj` · **Não criar:** `utils.py`, rota em `api/` ou exceção pública para erros de negócio
- **Fora do escopo:** lógica interna de leitura de `.xlsx` (T3 e T4) e persistência em banco
- **Decisões relacionadas:** D2, D3, D4 (`plan.md`)
- **Pronto quando:** `docker compose run --rm dev pytest tests/registry/test_cnpj.py -q` passa e `ruff check src/lastro/registry/` sai limpo

## [ ] T3 · Implementar abertura segura do `.xlsx`, cabeçalho e leitura de contas válidas
- **Critérios da ficha:** c1, c4
- **Regra de negócio (em linguagem simples):** abrir o arquivo de forma segura conferindo seu conteúdo real (não a extensão), validar que a primeira linha traz as colunas de código e nome, ler as contas mantendo a ordem das linhas e recusar a planilha inteira se o arquivo não for `.xlsx` ou não trouxer nenhuma conta.
- **Critérios de aceite:**
  - [ ] Arquivo não-`.xlsx`, texto renomeado para `.xlsx`, ZIP corrompido ou acima do limite (20 MiB) devolve 0 contas e `'Este arquivo não é uma planilha. Envie um arquivo .xlsx.'`
  - [ ] Leitura usa `openpyxl.load_workbook(..., read_only=True, data_only=True)` na primeira aba e fecha o workbook em `finally`
  - [ ] Cabeçalho da linha 1 aceita `código` e `nome` (normalizando caixa, acento e espaços, em qualquer ordem de coluna, ignorando extras); ausência de coluna obrigatória recusa a planilha com mensagem clara (conforme pergunta 1)
  - [ ] Planilha válida devolve todas as contas com `code` e `name` em texto preservando a ordem das linhas e 0 erros; planilha só com cabeçalho (ou só linhas vazias) devolve 0 contas e `'A planilha não tem nenhuma conta.'`
- **Exemplos:**
  - `.xlsx` com 3 contas válidas → 3 itens na ordem, `errors == ()`
  - `.xlsx` só com linha 1 `código`/`nome` → `accounts == ()`, `errors == ('A planilha não tem nenhuma conta.',)`
  - arquivo texto com extensão `.xlsx` → `accounts == ()`, `errors == ('Este arquivo não é uma planilha. Envie um arquivo .xlsx.',)`
- **Arquivos:** `src/lastro/registry/chart_spreadsheet.py`, `src/lastro/registry/service.py`
- **Reaproveitar:** `ChartAccountEntry` e `ChartSpreadsheetResult` de `src/lastro/registry/contracts.py` · **Não criar:** leitura de banco, HTTP ou escrita em disco
- **Fora do escopo:** validação detalhada de linhas incompletas e códigos repetidos (T4)
- **Decisões relacionadas:** D1, D2, D5 (`plan.md`) e perguntas 1, 2, 3
- **Pronto quando:** `docker compose run --rm dev pytest tests/registry/test_planilha_plano.py::test_planilha_valida_vira_lista_de_contas tests/registry/test_planilha_plano.py::test_planilha_sem_contas_recusada tests/registry/test_planilha_plano.py::test_arquivo_que_nao_e_planilha_recusado -q` passa

## [ ] T4 · Implementar validação de linhas incompletas e códigos repetidos
- **Critérios da ficha:** c2, c3
- **Regra de negócio (em linguagem simples):** ao percorrer cada linha a partir da linha 2, ignorar linhas totalmente vazias, rejeitar com o número real da linha qualquer linha sem código ou sem nome, e rejeitar qualquer código repetido informando tanto a linha repetida quanto a primeira linha onde o código apareceu — sempre aceitando as demais linhas válidas.
- **Critérios de aceite:**
  - [ ] Linha com código preenchido e nome vazio (ou só espaços) gera `'Linha {n}: falta o nome da conta.'` e não entra em `accounts`
  - [ ] Linha com nome preenchido e código vazio (ou só espaços) gera `'Linha {n}: falta o código da conta.'` e não entra em `accounts`
  - [ ] Segunda (ou posterior) ocorrência do mesmo código normalizado gera `'Linha {n}: o código {codigo} já apareceu na linha {primeira}.'`, mantendo a primeira ocorrência em `accounts`
  - [ ] Linhas válidas antes e depois das linhas inválidas continuam aceitas na ordem original
- **Exemplos:**
  - linha 3 sem nome e linha 4 sem código → 2 erros exatos e linhas 2 e 5 aceitas
  - `1.1.01` na linha 2 e `1.1.01` na linha 4 → linha 2 aceita e erro `'Linha 4: o código 1.1.01 já apareceu na linha 2.'`
- **Arquivos:** `src/lastro/registry/chart_spreadsheet.py`
- **Reaproveitar:** normalização de células de T3 · **Não criar:** consulta ao banco de dados ou alteração em `tests/`
- **Fora do escopo:** substituição de plano anterior no banco (P-11, escopo da `CAD-05`)
- **Decisões relacionadas:** D2, D3 (`plan.md`) e perguntas 2, 3
- **Pronto quando:** `docker compose run --rm dev pytest tests/registry/test_planilha_plano.py -q` passa com os 5 testes verdes

## [ ] T5 · Documentar o contrato v0 do leitor de plano de contas
- **Critérios da ficha:** todos (manutenção de arquitetura exigida por `ARCHITECTURE.md` §9)
- **Regra de negócio (em linguagem simples):** registrar o contrato público v0 (`read_chart_of_accounts_spreadsheet`, `ChartAccountEntry`, `ChartSpreadsheetResult`), as mensagens oficiais e a suposição P-10 para que a `CAD-05` consuma a interface sem ambiguidade.
- **Critérios de aceite:**
  - [ ] Tabela de contratos em `ARCHITECTURE.md` §6 inclui o contrato `registry → registry (CAD-05), api` da CAD-02
  - [ ] `docs/modules/registry.md` (ou caminho confirmado na pergunta 5) documenta assinatura, campos, mensagens oficiais, limites e impacto para `CAD-05`
- **Exemplos:** a tabela em `ARCHITECTURE.md` §6 lista `ChartSpreadsheetResult`, `ChartAccountEntry` e `read_chart_of_accounts_spreadsheet`
- **Arquivos:** `ARCHITECTURE.md`, `docs/modules/registry.md`
- **Reaproveitar:** formato do contrato da `CAD-01` em `ARCHITECTURE.md` §6 · **Não criar:** novo diretório em `docs/`
- **Fora do escopo:** unificação de `docs/modulos/registry.md` (PR separado) e edição de `features/CAD-02.json`
- **Decisões relacionadas:** D4 (`plan.md`) e pergunta 5
- **Pronto quando:** `git diff ARCHITECTURE.md docs/modules/registry.md` mostra o contrato v0 completo e coerente com `src/lastro/registry/service.py` e `contracts.py`

## [ ] T6 · Verificação final
- **Critérios de aceite:**
  - [ ] `git diff <hash-dos-testes> -- tests/` vazio (nenhuma edição em testes durante a implementação)
  - [ ] `docker compose run --rm dev ruff check .` limpo
  - [ ] `hx check-clean` e `hx verify` em OK
  - [ ] `hx feature verify CAD-02` grava `passing` na ficha
  - [ ] `progress/CAD-02.md` atualizado ao encerrar a sessão
- **Pronto quando:** `hx check-clean`, `hx verify` e `hx feature verify CAD-02` terminam com código 0
