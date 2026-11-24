# Tasks — HAR-03 · Gerar fixtures e gabarito sintéticos por semente fixa

**Plan:** planos/HAR-03/plan.md · **Ficha:** features/HAR-03.json
**Ordem:** T1 → revisão humana dos testes → commit só-de-testes (anotar o hash) → T2 em diante (sessão nova, sem editar `tests/`)
**Respostas do plan (24/11):** pergunta 1 aceita (T6 vale); pergunta 2 aceita (arquivo a mais em T1 e T5). Fora do escopo desta branch: fixture de pytest de sessão para CAD-05/IA-02 (resposta 3) e correção dos textos de versão do Python em PR de docs (resposta 4).

---

## [ ] T1 · Escrever os testes dos critérios
- **Critérios da ficha:** c1 a c6
- **Regra de negócio (em linguagem simples):** todo teste do projeto precisa de extratos e cadastros que pareçam reais sem ser. O gerador cria sempre o mesmo conjunto a partir de um número (a semente), junto com a resposta certa (o gabarito), para provar leitura, conferência de saldo e classificação.
- **Critérios de aceite:**
  - [ ] `tests/harness/test_fixtures.py` tem os 14 testes com os nomes exatos de `verificacao` da ficha
  - [ ] Todo build roda via `harness.main([...], raiz=tmp_path)`; nada escreve em `fixtures/` da raiz
  - [ ] Teste do c5 (pergunta 1): numa cópia temporária, um arquivo de `fixtures/` com CPF válido montado na hora **é** achado pelo `varrer`; a pasta gerada não tem achado
  - [ ] Arquivo a mais (pergunta 2) com teste próprio, `test_check_com_arquivo_a_mais_falha_sem_apagar` (nome sugerido no PR da ficha): `--check` falha citando o arquivo e não o apaga; um novo `build` o apaga e preserva `.gitkeep`. Os 14 testes da ficha não mudam
  - [ ] CNPJ e CPF válidos só montados em tempo de execução (o arquivo de teste passa no `hx check-clean`)
  - [ ] .xlsx lido só com `zipfile` + `xml.etree` (sem dependência nova)
  - [ ] Todos falham hoje porque `fixtures` não existe no parser (`hx`) e o módulo do gerador não existe
- **Exemplos:** `main(["fixtures", "build"], raiz=tmp)` → 0 e `tmp/fixtures/cadastro.json` com ESC-1 e ESC-2; `main(["fixtures", "build", "--semente", "2"], raiz=tmp2)` → algum OFX diferente; altera 1 byte de um OFX e `--check` → código 1, saída com ERRO e o caminho do OFX, byte ainda alterado; cria `fixtures/sobra.txt` e `--check` → código 1 citando `sobra.txt`, que continua lá; `build` → `sobra.txt` apagado, `.gitkeep` mantido.
- **Arquivos:** `tests/harness/test_fixtures.py`
- **Reaproveitar:** padrão de import e de CNPJ em tempo de execução de `tests/harness/test_validacao_lote.py`
- **Fora do escopo:** código de produção
- **Pronto quando:** `docker compose run --rm dev pytest tests/harness/test_fixtures.py -q` mostra 14 falhas esperadas e `sh tools/hx check-clean` segue com 0 achados

## [ ] T2 · Modelo sintético em memória
- **Critérios da ficha:** c1, c2, c5 (parte de dados)
- **Regra de negócio:** um escritório tem chefe e contadores; cada cliente tem um contador responsável, contas bancárias, sócios e um plano de contas com uma conta "transitória" (onde vai o que ninguém soube classificar). Cada movimentação do extrato já nasce com a conta certa, que é o gabarito.
- **Critérios de aceite:**
  - [ ] Função pura `semente → modelo` (escritórios, usuários, clientes, planos, contas bancárias, movimentações), sem ler relógio nem rede
  - [ ] Sorteio só com `Random(semente).random()` e conversões próprias (D3)
  - [ ] Valores em centavos inteiros; saldo inicial + soma = saldo final
  - [ ] Ao menos 1 descrição por cliente com CPF e CNPJ com máscara e DV inválido, `AG nnnn` e `CC nnnnn-n` (D5)
  - [ ] `cnpjs_dos_clientes(semente)` devolve CNPJs válidos, distintos, estáveis e ao menos 1 alfanumérico; usa o DV do `harness`
- **Exemplos:** semente 1 → EMP-1 (responsável contador_a) com 2 contas bancárias; uma linha "TARIFA PACOTE" → conta de despesas bancárias; uma linha "PIX RECEBIDO CONTRAPARTE_007" → transitória. CPF gerado `111.222.333-00` → `cpf_valido` False.
- **Arquivos:** `tools/fixtures_sinteticas.py`
- **Reaproveitar:** `harness._digito_verificador`, `_PESOS_CNPJ_1/2`, `cnpj_valido`, `cpf_valido` · **Não criar:** outro cálculo de DV
- **Fora do escopo:** escrever arquivos; PDF (BB/Inter); nomes reais ou parecidos com reais
- **Decisões relacionadas:** D1, D3, D5
- **Pronto quando:** `pytest tests/harness/test_fixtures.py::test_cnpj_em_tempo_de_execucao_valido_e_estavel -q` passa

## [ ] T3 · Escrever cadastro.json e planilhas .xlsx
- **Critérios da ficha:** c1, c6 (cadastro)
- **Regra de negócio:** o contador carrega o plano de contas do cliente por planilha (CAD-05); por isso cada plano também sai em .xlsx com `código` e `nome` na linha 1.
- **Critérios de aceite:**
  - [ ] `cadastro.json` em UTF-8, chaves e tipos exatamente como no c6, sem campo de CNPJ, chaves e listas em ordem fixa
  - [ ] .xlsx por cliente com `zipfile`, `ZIP_STORED`, data 1980-01-01 em todas as entradas, ordem fixa e `sharedStrings` (D2)
  - [ ] Duas chamadas com a mesma semente produzem os mesmos bytes
- **Exemplos:** EMP-1 → `planos/EMP-1.xlsx` com A1 `código`, B1 `nome`, uma linha `9.9.99 | Transitória`.
- **Arquivos:** `tools/fixtures_sinteticas.py`
- **Reaproveitar:** `json` da biblioteca padrão (UTF-8, `ensure_ascii=False`, indentação fixa) · **Não criar:** dependência openpyxl/XlsxWriter
- **Fora do escopo:** ler a planilha no produto (CAD-05)
- **Decisões relacionadas:** D2
- **Pronto quando:** `pytest tests/harness/test_fixtures.py -q -k "cadastro_dos_dois or planilha_do_plano"` passa

## [ ] T4 · Escrever OFX e gabarito por conta bancária
- **Critérios da ficha:** c2, c6 (gabarito)
- **Regra de negócio:** o extrato é conferido por cálculo: o saldo inicial mais todas as entradas e saídas tem de dar o saldo final. O gabarito diz, linha a linha, o que está no OFX e qual é a conta certa.
- **Critérios de aceite:**
  - [ ] OFX 1.0.2 SGML, ASCII, `DTSERVER` e período fixos, `FITID` único `F<conta><seq>`, `LEDGERBAL` com o saldo final (D4)
  - [ ] Gabarito JSON com `cliente`, `banco`, `apelido`, saldos em centavos e `movimentacoes` (`data` AAAA-MM-DD, `valor_centavos`, `descricao`, `id_transacao` = FITID, `conta_correta` do plano)
  - [ ] Nº de movimentações igual nos dois; caminhos citados no cadastro existem
- **Exemplos:** −1.590 centavos no gabarito → `<TRNAMT>-15.90` no OFX; inicial 100000 + soma −12345 → `<BALAMT>876.55`.
- **Arquivos:** `tools/fixtures_sinteticas.py`
- **Reaproveitar:** modelo da T2 · **Não criar:** leitor de OFX (é do módulo `parsing`); `ofxtools` (GPL-3)
- **Fora do escopo:** PDF; variações por banco
- **Decisões relacionadas:** D4
- **Pronto quando:** `pytest tests/harness/test_fixtures.py -q -k "ofx_e_gabarito or saldo_do_ofx or conta_correta or documentos_de_teste or formato_do_cadastro"` passa

## [ ] T5 · Comando `hx fixtures build [--semente N] [--check]`
- **Critérios da ficha:** c1, c3, c4
- **Regra de negócio:** quem roda o comando sempre obtém a mesma pasta; o `--check` só confere, para a CI e o dev saberem se a pasta está velha sem que nada seja sobrescrito.
- **Critérios de aceite:**
  - [ ] Gerador devolve mapa `caminho → bytes`; `build` grava em `<raiz>/fixtures/` e apaga o que não gera, exceto `.gitkeep` (pergunta 2)
  - [ ] Antes de gravar, cada linha passa por `harness.tipos_da_linha`; achado aborta com ERRO/MOTIVO/CORREÇÃO (D7)
  - [ ] `--check`: em dia → código 0 e "fixtures em dia"; alterado, ausente ou a mais → código 1 com ERRO, MOTIVO e CORREÇÃO citando o arquivo e mandando rodar `hx fixtures build`; nada gravado (D6)
  - [ ] Subcomando no `_criar_parser`; `harness` importa o gerador só dentro do comando
  - [ ] `--help` em português
- **Exemplos:** apaga `gabaritos/EMP-9-*.json` e roda `--check` → código 1, cita o arquivo, arquivo continua ausente; `--semente abc` → código 2 (argparse).
- **Arquivos:** `tools/harness.py`, `tools/fixtures_sinteticas.py`
- **Reaproveitar:** `HarnessErro`, `mostrar_erro`, `main(argv, raiz)` · **Não criar:** outro formato de erro
- **Fora do escopo:** passo de fixtures na CI e fixture de pytest de sessão das consumidoras (resposta 3: fica para CAD-05 e IA-02)
- **Decisões relacionadas:** D1, D6, D7
- **Pronto quando:** `pytest tests/harness/test_fixtures.py -q -k "mesma_semente or outra_semente or check_"` passa

## [ ] T6 · check-clean varre `fixtures/` (pergunta 1, aceita em 24/11)
- **Critérios da ficha:** c5
- **Regra de negócio:** a pasta gerada fica fora do Git, mas é ela que mais corre risco de ter documento parecido com real; o check-clean precisa olhar para ela mesmo assim.
- **Critérios de aceite:**
  - [ ] `varrer` acrescenta os arquivos de `fixtures/` (por `_percorrer_arvore`) quando a pasta existe, sem duplicar os que o git já lista
  - [ ] Saída continua sem mostrar valores
  - [ ] Testes antigos de check-clean (`test_fase_b.py`, `test_validacao_lote.py`) seguem verdes
- **Exemplos:** `fixtures/x.txt` com CPF válido montado no teste → 1 achado `fixtures/x.txt:1`; `fixtures/` gerada → 0 achados.
- **Arquivos:** `tools/harness.py`
- **Reaproveitar:** `_percorrer_arvore`, `_ler_texto` · **Não criar:** outro varredor
- **Fora do escopo:** mudar o `.gitignore`; varrer outras pastas ignoradas
- **Pronto quando:** `pytest tests/harness/test_fixtures.py::test_fixtures_passam_no_check_clean tests/harness/test_fase_b.py -q` passa

## [ ] T7 · Verificação final
- **Critérios de aceite:**
  - [ ] `git diff <hash-dos-testes> -- tests/` vazio
  - [ ] `ruff check .` limpo
  - [ ] `sh tools/hx fixtures build` no host e `--check` no container dão código 0 (mesmos bytes entre versões de Python)
  - [ ] `hx check-clean` e `hx verify` em OK
  - [ ] `hx feature verify HAR-03` grava `passing`
  - [ ] README (proposta 5) e `docs/SECURITY.md` §3 apontam para o comando real, em PR de docs se o dono pedir
- **Fora do escopo:** correção dos textos de versão do Python (`tools/hx`, cabeçalho do `harness.py`, AGENTS.md): PR de docs separado (resposta 4)
- **Pronto quando:** `hx check-clean`, `hx verify` e `hx feature verify HAR-03` terminam com código 0
