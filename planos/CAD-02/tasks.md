# Tasks — CAD-02 · Ler o plano de contas em TXT e apontar linha inválida

**Plan:** planos/CAD-02/plan.md · **Ficha:** features/CAD-02.json · **Regra:** docs/modulos/registry.md ("Leitura do plano de contas em TXT")
**Ordem:** T1 → revisão humana dos testes → commit só de testes (anotar o hash) → `hx feature verify CAD-02` (grava `regressed`; commit da ficha) → T2 em diante numa sessão nova, sem editar `tests/`

---

## [ ] T1 · Escrever os testes dos critérios e apagar os do `.xlsx`
- **Critérios da ficha:** c1 a c10
- **Regra de negócio:** o contador envia o plano exportado do Domínio (TXT, 78 colunas). O sistema aceita as contas, deixa de fora com aviso só a analítica folha com erro simples, e recusa o arquivo inteiro com uma mensagem única quando o erro compromete o plano.
- **Critérios de aceite:**
  - [ ] `tests/registry/test_plano_txt.py` tem as 10 funções citadas na `verificacao`, com os mesmos nomes
  - [ ] `tests/registry/test_planilha_plano.py` foi apagado (T12)
  - [ ] o serviço é importado dentro de um auxiliar (D1), e cada teste falha sozinho por `AttributeError`
  - [ ] as linhas são montadas no teste por um auxiliar que confere 78 caracteres; os nomes são inventados (regra 1)
  - [ ] cada caso de c4(c) e de c6 tem mensagem no `assert` dizendo qual caso falhou
- **Exemplos:** os da ficha, com o plano `VALIDO` de 6 linhas (1, 11, 1101, 1102, 2, 201)
- **Arquivos:** `tests/registry/test_plano_txt.py` (novo) e `tests/registry/test_planilha_plano.py` (apagar)
- **Fora do escopo:** código de produção
- **Pronto quando:** `docker compose run --rm dev pytest tests/registry -q` mostra só as 10 falhas esperadas, e o resto da pasta passa

## [ ] T2 · Contrato, fachada e leitura do arquivo
- **Critérios da ficha:** c9 e a parte de arquivo de c1 e c8
- **Regra de negócio:** antes de olhar as linhas, recusar o que não é o plano em texto (ZIP ou `.xlsx`, PDF, byte nulo, mais de 20 MiB). Arquivo vazio ou só com linhas em branco "não tem nenhuma conta". O texto vem em UTF-8 (com ou sem BOM) ou em Windows-1252.
- **Critérios de aceite:**
  - [ ] `ChartAccountEntry` e `ChartOfAccountsResult` exatamente como a tabela "Contrato" do `registry.md`, `frozen=True, slots=True`
  - [ ] `read_chart_of_accounts(source: bytes | Path)` em `service.py`, chamando `_read_chart_of_accounts` de `chart_txt.py`
  - [ ] `Path`: `stat()` antes de ler; um `OSError` sobe ao chamador (D2)
  - [ ] recusa de arquivo nesta ordem: vazio → `EMPTY`; mais de 20 MiB, `PK\x03\x04`, `%PDF-` ou `\x00` → `NOT_TEXT`
  - [ ] decodifica e só depois fatia; `split("\n")` + `rstrip("\r")`; ignora linhas em branco e guarda o número real de cada linha
  - [ ] `chart_spreadsheet.py`, `read_chart_of_accounts_spreadsheet` e `ChartSpreadsheetResult` apagados; os tipos e funções da CAD-03 intactos
- **Exemplos:** `b""` → `EMPTY`; `b"%PDF-1.7\n..."` → `NOT_TEXT`; arquivo com BOM e CRLF → mesmo resultado que em UTF-8 com LF
- **Arquivos:** `src/lastro/registry/chart_txt.py` (novo), `contracts.py`, `service.py`; apagar `chart_spreadsheet.py`
- **Reaproveitar:** o padrão de fachada da CAD-01 · **Não criar:** um segundo ponto de entrada
- **Fora do escopo:** regras das linhas (T3 a T5) e `pyproject.toml` (T6)
- **Decisões relacionadas:** D2, D5
- **Pronto quando:** `docker compose run --rm dev pytest tests/registry/test_plano_txt.py::test_arquivo_que_nao_e_o_plano_recusado_sem_excecao -q` passa

## [ ] T3 · Erro próprio de cada linha
- **Critérios da ficha:** c2, a parte de linha de c4(c) e o E2 de c3
- **Regra de negócio:** cada linha tem no máximo um erro próprio: o primeiro da tabela "Erros de linha". As causas (linha curta, texto depois da posição 78, classificação, tipo) vêm antes dos toleráveis (reduzido, nome), para a mensagem apontar o que de fato impede a carga.
- **Critérios de aceite:**
  - [ ] ordem: E1, E8, E3a, E3b, E5a, E5b, E2 vazio, E2, E2z, E4, com o texto exato da tabela
  - [ ] o nome de 40 caracteres colado ao tipo é lido inteiro (`[27:67]`, tipo em `[67]`)
  - [ ] aspas só no valor recusado, como foi lido
- **Exemplos:** reduzido `12A4567` → `o código reduzido "12A4567" precisa ter 7 dígitos.`; classificação `11.03` → `a classificação "11.03" precisa ter só números.`; tipo em branco → `falta o tipo da conta (S ou A).`
- **Arquivos:** `src/lastro/registry/chart_txt.py`
- **Fora do escopo:** decidir se o erro é tolerado (T5)
- **Pronto quando:** `pytest tests/registry/test_plano_txt.py::test_nome_de_40_caracteres_colado_no_tipo -q` passa

## [ ] T4 · Repetições e hierarquia
- **Critérios da ficha:** c1, c5 e c6
- **Regra de negócio:** o Domínio não repete reduzido nem classificação, então repetição indica arquivo corrompido ou misturado, e o resultado não pode depender da ordem das linhas. A conta superior é o maior prefixo da classificação que existe no arquivo. Conta sem superior, ou abaixo de uma analítica, recusa o arquivo.
- **Critérios de aceite:**
  - [ ] E6 e E7 conferidos em toda linha, mesmo com erro próprio, e com prioridade sobre ele; a primeira ocorrência fica e a de baixo é a causa
  - [ ] `0000000` não gera E6 (D3). A ficha não cita esse caso, então ele é conferido à mão no T7
  - [ ] hierarquia sobre todas as linhas com classificação legível (primeira ocorrência), das mais curtas para as mais longas, com `mínimo` = menor comprimento
  - [ ] `parent_classification` preenchido; `None` nas contas de topo
  - [ ] causas: sem superior e mais longa que o mínimo; abaixo de analítica. Consequência: superior não aceita (não é mostrada nem contada)
- **Exemplos:** `1102` repetida na linha 7 → `Linha 7: a classificação 1102 já aparece na linha 4.`; `3101` sem `3` nem `31` → `a conta 3101 não tem conta superior no arquivo.`; `110101` abaixo da analítica `1101` → `... está abaixo da conta analítica 1101 (linha 3).`
- **Arquivos:** `src/lastro/registry/chart_txt.py`
- **Decisões relacionadas:** D3, D5
- **Pronto quando:** os testes de c1, c5 e c6 passam (`pytest tests/registry/test_plano_txt.py -q -k "hierarquia or repeticao or txt_valido"`)

## [ ] T5 · Tolerância, recusa única e avisos
- **Critérios da ficha:** c3, c4, c7, c8 e c10
- **Regra de negócio:** só a analítica folha, sem problema de hierarquia e primeira com aquela classificação, pode ficar de fora com erro simples (E2, E2z, E4). Qualquer outra causa recusa tudo com uma mensagem: a primeira causa mais quantas outras há. Se nenhuma analítica foi aceita, as toleradas viram causa. Sintética aceita sem nada abaixo dela vira aviso.
- **Critérios de aceite:**
  - [ ] uma mensagem por linha: repetição → causa de hierarquia → erro próprio
  - [ ] 1 causa: `{msg} Corrija essa linha e envie o arquivo de novo.`; N causas: `{msg} Há mais {N-1} {linha|linhas} com problema. Corrija e envie o arquivo de novo.`
  - [ ] na recusa, `accounts`, `errors` e `warnings` vazios; quando aceito, `refusal is None`
  - [ ] sem analítica aceita: toleradas viram causa; sem toleradas, a mensagem `NO_ANALYTIC`
  - [ ] a sintética cuja única filha foi tolerada não gera aviso
- **Exemplos:** grupo 11 sem nome → `Linha 2: falta o nome da conta. Corrija essa linha e envie o arquivo de novo.`; grupo 12 vazio → aviso `Linha 7: a conta sintética 12 não tem contas abaixo dela.`
- **Arquivos:** `src/lastro/registry/chart_txt.py`
- **Pronto quando:** `docker compose run --rm dev pytest tests/registry/test_plano_txt.py -q` passa nos 10

## [ ] T6 · Tirar o `openpyxl`
- **Critérios da ficha:** nenhum direto (T1 do §11; "Pronto quando" do roteiro)
- **Regra de negócio:** o `.xlsx` não é mais aceito, então a biblioteca e o comentário dela saem das dependências.
- **Critérios de aceite:**
  - [ ] `openpyxl` fora do `pyproject.toml` (com o comentário `# CAD-02, plan D1/D6`)
  - [ ] `uv.lock` regenerado no contêiner (D4), sem `openpyxl` nem `et-xmlfile`, com `revision = 5`
  - [ ] `docker compose build dev` reconstruído antes do T7
- **Arquivos:** `pyproject.toml`, `uv.lock`
- **Pronto quando:** `git grep -n openpyxl -- src tests pyproject.toml uv.lock` sem resultado

## [ ] T7 · Verificação final
- **Critérios de aceite:**
  - [ ] `git diff <hash-dos-testes> -- tests/` vazio
  - [ ] `hx check-clean` em OK (com `LASTRO_NOMES_PROIBIDOS` definida, se possível)
  - [ ] `hx verify` em OK com a imagem reconstruída
  - [ ] `hx feature verify CAD-02` grava `passing`; commit da ficha
  - [ ] conferência manual da D3: duas analíticas folha com `0000000` → 2 erros tolerados, sem recusa
  - [ ] `progress/CAD-02.md` reescrito para o TXT (Objetivo, Próxima ação), com o que rodou
  - [ ] PR cita `DECISIONS.md` §11 T12 (testes) e T13 (contrato v1, sem issue)
- **Pronto quando:** os três comandos do `hx` terminam com código 0
