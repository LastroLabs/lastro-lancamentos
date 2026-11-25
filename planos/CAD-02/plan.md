# Plan — CAD-02 · Ler a planilha do plano de contas e apontar linha inválida

**Status:** pronto para revisão
**Branch:** `feat/CAD-02-ler-a-planilha-do-plano-de-contas-e-apon` · **Data:** 24/11/2026 · **Responsável:** marrathomaz
**Tasks:** `planos/CAD-02/tasks.md`

## 1. A decidir (humano)
Tudo que bloqueia ou depende de uma pessoa. Resolvida → mova para "5. Decisões".

| # | Pergunta | Gravidade | Sugestão de padrão | Decide |
|---|---|---|---|---|
| 1 | Cabeçalho na linha 1 (P-10): aceitar variações de acento/caixa/espaços (`Código`, `codigo`, `NOME`), colunas em qualquer ordem e colunas extras? E qual mensagem se faltar `código` ou `nome` na linha 1? | ATENÇÃO | Normalizar cabeçalho (strip, minúsculas, sem acento), localizar `codigo` e `nome` em qualquer coluna e ignorar colunas extras. Se faltar um dos dois, recusar a planilha inteira com `"A planilha precisa ter as colunas 'código' e 'nome' na primeira linha."`. | marrathomaz |
| 2 | Linhas totalmente vazias (código e nome vazios/só espaços) no meio ou fim da planilha, e planilha cujas linhas de dados são todas inválidas: como tratar? | ATENÇÃO | Ignorar linhas totalmente vazias mantendo o número real da linha do Excel nas mensagens. Só linhas vazias após cabeçalho → `'A planilha não tem nenhuma conta.'`. Linhas só com erros → 0 contas e os erros de cada linha. | marrathomaz |
| 3 | Células numéricas no código (ex.: Excel grava `101` como inteiro ou `1.1` como float) e espaços nas bordas: converter para texto e aplicar `.strip()`? | ATENÇÃO | Sim: aplicar `.strip()` em textos; para `int`, converter com `str()`; para `float` com parte decimal zero (`101.0`), remover `.0`, preservando o texto exato em células `str` (sem perder zeros à esquerda nem pontos, conforme DB-02 c4). | marrathomaz |
| 4 | A ficha fixa `tests/registry/test_planilha_plano.py` e 5 nomes de teste em português, contra `CODING_STANDARDS.md` §1 (inglês). Manter como na CAD-01? | ATENÇÃO | Sim: manter exatamente os nomes da ficha nos testes (`CODING_STANDARDS.md` §9.4) e escrever todo o código de `src/lastro/registry/` em inglês (§9.1). | marrathomaz |
| 5 | Existem hoje `docs/modulos/registry.md` (CAD-01) e `docs/modules/registry.md` (DB-02). Onde documentar o contrato v0 da CAD-02? | ATENÇÃO | Documentar em `docs/modules/registry.md` (caminho oficial de `ARCHITECTURE.md` §7) e registrar a tabela do contrato em `ARCHITECTURE.md` §6; unificar `docs/modulos/registry.md` em PR separado. | marrathomaz |

Mudanças sugeridas na ficha (o humano aplica em PR): nenhuma obrigatória; opcionalmente explicitar em c4 o comportamento para cabeçalho ausente/inválido e em c2 o tratamento de linhas totalmente em branco.

## 2. Decisões tomadas pelo agente
Cada uma precisa de confirmação humana.

### D1 · Biblioteca `openpyxl` para leitura (e escrita nos testes) de `.xlsx`
- **Alternativas:** A) `openpyxl` (`3.1.5`, licença MIT, Python puro, leitura e escrita `.xlsx`, já prevista em `gitpages/src/content/docs/arquitetura/stack.md` para o Excel do Domínio) · B) `python-calamine` (`0.9.1`, MIT, Rust, wheels Python 3.14, somente leitura — não cria `.xlsx` nos testes nem atende `export/`) · C) `pylightxl` (MIT, stdlib pura, escopo mínimo sem ecossistema consolidado para a exportação do Domínio)
- **Escolhida:** A (`openpyxl>=3.1.5`) — **motivo:** mais comum no ecossistema Python, compatível com Python 3.12 e 3.14, suporta leitura em streaming (`read_only=True`) e escrita nos testes, e evita manter duas bibliotecas de Excel no projeto (reaproveitada por `HAR-03` e `export/`). Sem `defusedxml` adicional porque Python 3.14 já embute Expat ≥ 2.4.0 com mitigação nativa contra XML bombs (Billion Laughs / quadratic blowup).
- **Fontes:** PyPI `openpyxl` (`https://pypi.org/project/openpyxl/`, acesso em 24/11/2026) · Docs `openpyxl` (`https://openpyxl.readthedocs.io/`, acesso em 24/11/2026) · PyPI `python-calamine` (`https://pypi.org/project/python-calamine/`, acesso em 24/11/2026) · PyPI `pylightxl` (`https://pypi.org/project/pylightxl/`, acesso em 24/11/2026) · `gitpages/src/content/docs/arquitetura/stack.md`
- **Impacto:** T1 a T4; `pyproject.toml`, `uv.lock`, rebuild da imagem `dev` (FER-01); futuro reuso em `HAR-03` e `export/`.
- [x] confirmar

### D2 · Regra pura em `registry/`, sem banco nem HTTP
- **Alternativas:** A) leitor interno em `src/lastro/registry/chart_spreadsheet.py` exposto por `src/lastro/registry/service.py` · B) leitura direto em `api/` · C) acoplado ao `repository.py`
- **Escolhida:** A — **motivo:** `depende_de` é vazio; respeita `ARCHITECTURE.md` §3, §4 e §7; mantém `P-13` (status HTTP) fora desta ficha e entrega serviço reutilizável diretamente pela `CAD-05`.
- **Fontes:** `ARCHITECTURE.md` §3, §4 e §7; `features/CAD-05.json`.
- **Impacto:** T2 a T4; critérios c1 a c4.
- [x] confirmar

### D3 · Retorno estruturado sem exceção (`ChartSpreadsheetResult` e `ChartAccountEntry`)
- **Alternativas:** A) dataclasses imutáveis `@dataclass(frozen=True, slots=True)` com `accounts: tuple[ChartAccountEntry, ...]` e `errors: tuple[str, ...]` · B) lançar exceção em c4 e retornar tupla em c1–c3 · C) retornar `dict` genérico
- **Escolhida:** A — **motivo:** segue o padrão da `CAD-01` (`CnpjValidationResult`) e `NUC-02`, expressa igualmente sucesso (c1), aceitação parcial com erros por linha (c2, c3, `CAD-05` c2) e recusa inteira com `accounts == ()` (c4), sem exigir `try/except` na `CAD-05`.
- **Fontes:** `src/lastro/registry/contracts.py`; `CODING_STANDARDS.md` §2; ficha c1–c4.
- **Impacto:** T1 a T4; futura `CAD-05`.
- [x] confirmar

### D4 · Nomes da interface pública v0 e tipos de entrada (`bytes | Path`)
- **Alternativas:** A) `read_chart_of_accounts_spreadsheet(source: bytes | Path) -> ChartSpreadsheetResult` · B) aceitar apenas `bytes` · C) aceitar apenas `Path`
- **Escolhida:** A — **motivo:** `Path` atende testes com arquivos temporários e fixtures da `HAR-03`; `bytes` atende uploads HTTP em memória na `CAD-05`. Nomes seguem o glossário (`CODING_STANDARDS.md` §7: `chart_of_accounts`) e `registry/contracts.py` (`ChartAccountEntry`, `ChartSpreadsheetResult`), com implementação privada em `src/lastro/registry/chart_spreadsheet.py`.
- **Fontes:** `CODING_STANDARDS.md` §2 e §7; `features/CAD-05.json`; `features/HAR-03.json`.
- **Impacto:** T1 a T5; futura `CAD-05`.
- [x] confirmar

### D5 · Leitura segura de `.xlsx` (streaming, primeira aba, validação pelo conteúdo e limite de tamanho)
- **Alternativas:** A) `load_workbook(..., read_only=True, data_only=True)` lendo a primeira aba (`worksheets[0]`), fechamento em `finally`, limite configurável (padrão 20 MiB, alinhado a D-06) e recusa por erro de ZIP/XML/formato com a mensagem de c4(b) · B) carregar workbook inteiro em memória (`read_only=False`) e confiar na extensão `.xlsx`
- **Escolhida:** A — **motivo:** c4(b) exige recusar arquivo de texto com extensão `.xlsx`; `read_only=True` reduz uso de RAM; `data_only=True` evita importar fórmulas literais; limite protege contra arquivos abusivos.
- **Fontes:** Docs `openpyxl` (`read_only`, acesso em 24/11/2026); `docs/decisoes/DECISIONS.md` (D-06); ficha c4.
- **Impacto:** T3, T4; critérios c1 a c4.
- [x] confirmar

### D6 · Inclusão de `openpyxl` em `pyproject.toml` + `uv.lock` já na T1
- **Alternativas:** A) adicionar `openpyxl>=3.1.5` ao `pyproject.toml` e atualizar `uv.lock` (com rebuild da imagem `dev`, FER-01) na T1, permitindo gerar os `.xlsx` de teste com `openpyxl` · B) montar `.xlsx` manualmente com `zipfile`/XML nos testes da T1 e instalar `openpyxl` só na T2
- **Escolhida:** A — **motivo:** c1–c4 exigem planilhas `.xlsx` reais criadas pelos testes; montar OOXML na mão é frágil e redundante com a biblioteca escolhida em D1.
- **Fontes:** `docs/decisoes/DECISIONS.md` (FER-01); `Dockerfile`; ficha c1–c4.
- **Impacto:** T1 (commit inicial de testes + lockfile) e T6.
- [x] confirmar

## 3. Resumo e abordagem
Leitura e validação pura de planilhas `.xlsx` de plano de contas no módulo `registry`, devolvendo a lista ordenada de contas válidas (`code`, `name`) e mensagens em português simples apontando linhas incompletas, códigos duplicados ou recusa do arquivo inteiro.
1. T1: adicionar `openpyxl` em `pyproject.toml`/`uv.lock`, reconstruir a imagem `dev` e criar `tests/registry/test_planilha_plano.py` com os 5 testes da ficha.
2. T2: adicionar `ChartAccountEntry` e `ChartSpreadsheetResult` em `src/lastro/registry/contracts.py` e expor `read_chart_of_accounts_spreadsheet` em `src/lastro/registry/service.py`.
3. T3: implementar abertura segura (`read_only=True`, `data_only=True`, tratamento de arquivo inválido), validação do cabeçalho na linha 1, leitura das contas válidas na ordem e recusa de planilha sem contas em `src/lastro/registry/chart_spreadsheet.py`.
4. T4: implementar validação de linhas sem código/sem nome e detecção de código repetido citando as duas linhas em `src/lastro/registry/chart_spreadsheet.py`.
5. T5: documentar o contrato v0 em `ARCHITECTURE.md` §6 e `docs/modules/registry.md`.
6. T6: rodar `ruff`, `hx check-clean`, `hx verify` e `hx feature verify CAD-02`.

## 4. Contexto encontrado
- **Código relacionado:** `src/lastro/registry/service.py` (`validate_cnpj`), `src/lastro/registry/contracts.py` (`CnpjValidationResult`), `src/lastro/registry/cnpj.py` (módulo privado), `src/lastro/registry/models.py` (`ChartOfAccounts`, `LedgerAccount` com `codigo` e `nome` em `Text` e `UNIQUE(escritorio_id, cliente_id, plano_id, codigo)`), `tests/registry/test_cnpj.py`.
- **Dependências:** nenhuma (`depende_de` vazio). Consome esta ficha: `CAD-05` (`not_started`, `marrathomaz`). `HAR-03` (`not_started`) gerará planilhas `.xlsx` com cabeçalho `'código'` e `'nome'` na linha 1.
- **Planos fora de `depende_de` lidos (mesmo módulo `registry`):**
  - `planos/CAD-01/plan.md` (**aprovado**, 23/11) — motivo: CAD-02 edita `registry/service.py` e `registry/contracts.py`. Conferência: `service.py`, `contracts.py`, `cnpj.py` e `test_cnpj.py` **conferem**; doc criado em `docs/modulos/registry.md` **diverge** de `ARCHITECTURE.md` §7 (`docs/modules/`), virando pergunta 5.
  - `planos/DB-02/plan.md` (**aprovado** em `DECISIONS.md` §6 e ficha `passing`, embora o cabeçalho do plan ainda diga "pronto para revisão" — **divergente** no cabeçalho, sem impacto aqui) — motivo: modelos `plano_contas`/`conta_contabil` em `registry/models.py`. Conferência: `models.py` e `docs/modules/registry.md` **conferem**.
- **Reaproveitar:** padrão de contrato imutável e serviço fino de `src/lastro/registry/contracts.py` e `service.py`; padrão de import interno nos testes de `tests/registry/test_cnpj.py` para não quebrar coleta na T1.
- **Não criar:** persistência em banco, rota HTTP, status HTTP (`P-13`), `utils.py`, nem nova dependência além de `openpyxl`.
- **Pesquisa externa:** comparadas `openpyxl` (3.1.5, MIT, leitura+escrita, já na stack), `python-calamine` (0.9.1, MIT, Rust, só leitura) e `pylightxl` (MIT, stdlib, mínimo), mais segurança XML em Python 3.14 (Expat ≥ 2.4.0 nativo); fontes e datas em D1 (acesso em 24/11/2026).

## 5. Decisões (já resolvidas)
- 18/11 · `ARQ-08` (Python 3.14) e `P-10` (assumida: cabeçalho `código` e `nome` na linha 1, a confirmar com os pilotos) — `docs/decisoes/DECISIONS.md`.
- 23/11 · `FER-01` (assumida: dependências gerenciadas com `uv` em `pyproject.toml` + `uv.lock`, com rebuild da imagem `dev` quando o lock muda) — `docs/decisoes/DECISIONS.md`.
- 25/11 . Normalizar cabeçalho, localizar `codigo` e `nome` em qualquer coluna e ignorar colunas extras. Se faltar um dos dois, recusar a planilha inteira com `"A planilha precisa ter as colunas 'código' e 'nome' na primeira linha."`, conforme o padrão sugerido (pergunta 1, Thomaz).
- 25/11 . Ignorar linhas totalmente vazias mantendo o número real da linha do Excel nas mensagens. Só linhas vazias após cabeçalho → `'A planilha não tem nenhuma conta.'`. Linhas só com erros → 0 contas e os erros de cada linha, conforme o padrão sugerido (pergunta 2, Thomaz).
- 25/11 . Sim: aplicar `.strip()` em textos; para `int`, converter com `str()`; para `float` com parte decimal zero (`101.0`), remover `.0`, preservando o texto exato em células `str` (sem perder zeros à esquerda nem pontos, conforme DB-02 c4) (pergunta 3, Thomaz).
- 25/11 . Sim: manter exatamente os nomes da ficha nos testes (`CODING_STANDARDS.md` §9.4) e escrever todo o código de `src/lastro/registry/` em inglês (§9.1). (pergunta 4, Thomaz).
- 25/11 . Documentar em `docs/modules/registry.md` (caminho oficial de `ARCHITECTURE.md` §7) e registrar a tabela do contrato em `ARCHITECTURE.md` §6; unificar `docs/modulos/registry.md` em PR separado. (pergunta 5, Thomaz).

## 6. Avaliação da ficha
| # | Achado | Gravidade | Critério |
|---|---|---|---|
| 1 | Variações de cabeçalho (acento/caixa/ordem/colunas extras) e mensagem para cabeçalho ausente não estão exemplificadas (pergunta 1). | ATENÇÃO | c1, c4 |
| 2 | Linhas totalmente vazias e planilha onde todas as linhas têm erro não estão exemplificadas (pergunta 2). | ATENÇÃO | c2, c4 |
| 3 | Células numéricas no código (Excel convertendo `101` em `int`/`float`) e espaços nas bordas não estão exemplificados (pergunta 3). | ATENÇÃO | c1, c2 |
| 4 | Nomes de arquivo e testes em português na ficha divergem de `CODING_STANDARDS.md` §1 (pergunta 4). | ATENÇÃO | todos |
| 5 | Dois arquivos de doc do módulo (`docs/modulos/registry.md` e `docs/modules/registry.md`) coexistem no repositório (pergunta 5). | ATENÇÃO | — |
| 6 | P-10 é suposição a confirmar com os pilotos; contrato v0 pode precisar evoluir após contato com planilhas reais. | ATENÇÃO | c1 |
| 7 | Escopo enxuto (4 critérios, 1 módulo, 5 comandos em `verificacao` cobrindo 100% dos critérios); não precisa dividir. | — | todos |

## 7. Riscos
- Arquivo `.xlsx` malformado, renomeado ou corrompido lançar exceções distintas (`BadZipFile`, `InvalidFileException`, `ET.ParseError`, `KeyError`) → encapsular todas na abertura/leitura e devolver a mensagem exata de c4(b).
- Vazamento de descritor de arquivo em `openpyxl` com `read_only=True` → sempre chamar `wb.close()` em bloco `finally`.
- Planilha real dos pilotos ter cabeçalho diferente de `código`/`nome` na linha 1 (P-10) → isolar a detecção de cabeçalho em função dedicada e registrar no contrato v0.
- Esquecer de atualizar `uv.lock` ou reconstruir a imagem `dev` após adicionar `openpyxl` (FER-01) → previsto explicitamente na T1 e verificado no `hx verify`.

## 8. Aprovação
- [x] Perguntas ATENÇÃO respondidas ou padrão aceito (1 a 5)
- [x] Decisões do agente confirmadas (D1 a D6)
- [x] Plan e tasks revisados por marrathomaz em 25/11
