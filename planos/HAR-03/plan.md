# Plan — HAR-03 · Gerar fixtures e gabarito sintéticos por semente fixa

**Status:** aprovado (camposs04, 24/11/2026) — perguntas 1–4 respondidas e D1–D7 confirmadas; as duas mudanças na ficha foram aceitas e aplicadas em `aa057a6`
**Branch:** feat/HAR-03-gerar-fixtures-e-gabarito-sinteticos-por · **Data:** 24/11/2026 · **Responsável:** camposs04
**Tasks:** planos/HAR-03/tasks.md

## 1. A decidir (humano)
| # | Pergunta | Gravidade | Resposta | Decide |
|---|---|---|---|---|
| 1 | `fixtures/` está no `.gitignore` e o `hx check-clean` lista arquivos por `git ls-files --exclude-standard`: a pasta **nunca é varrida**, então o c5 ("check-clean sem achado em fixtures/") passaria sem provar nada. O check-clean passa a varrer `fixtures/` de forma explícita (proposta 5 do README)? | BLOQUEANTE | **Respondida 24/11:** sim; `varrer` soma os arquivos de `fixtures/` (percorrendo a árvore) quando a pasta existe. O teste do c5 confirma que um CPF válido plantado numa cópia de `fixtures/` **é** achado, e que a gerada não tem achado. Muda `tools/harness.py` e vale para todo o time (T6) | camposs04 |
| 2 | Arquivo que sobra em `fixtures/` (gerado por versão antiga do gerador): o `build` apaga? O `--check` falha? A ficha só cobre arquivo alterado e ausente | ATENÇÃO | **Respondida 24/11:** `build` apaga o que não gera (exceto `.gitkeep`); `--check` também falha com arquivo a mais, citando o arquivo (T1, T5) | camposs04 |
| 3 | Quem gera `fixtures/` para os testes das consumidoras (CAD-05, IA-02)? A CI roda só `hx verify` e a pasta não é versionada | ATENÇÃO (não bloqueia a HAR-03) | **Respondida 24/11:** uma fixture de pytest de sessão gera em `tmp_path` chamando o gerador; nada depende da pasta da raiz. Fica para a CAD-05 e a IA-02, sem task na HAR-03 | camposs04 |
| 4 | Versão de Python do harness: `tools/hx` diz 3.10+, o cabeçalho de `harness.py` diz 3.11+, o AGENTS.md pede compatibilidade de biblioteca com 3.12 e a stack é 3.14 | ATENÇÃO | **Respondida 24/11:** gerador compatível com Python 3.11+ (o do harness), sem biblioteca nova; a correção dos textos (`tools/hx`, cabeçalho do `harness.py`, AGENTS.md) vai num PR de docs separado, fora desta branch | camposs04 |

Mudanças na ficha, **aceitas por camposs04 em 24/11 e aplicadas no PR #58** (commit `aa057a6`, por decisão de camposs04 após a revisão):
- [x] c4: incluir o caso "(d) arquivo a mais em fixtures/" (pergunta 2) e um teste novo em `verificacao`, sugestão `test_check_com_arquivo_a_mais_falha_sem_apagar`. Aplicada em `aa057a6`.
- [x] c5: trocar "roda hx check-clean" por "roda hx check-clean, que varre fixtures/ mesmo fora do Git" (pergunta 1). Aplicada em `aa057a6`.

## 2. Decisões tomadas pelo agente
### D1 · Gerador em `tools/fixtures_sinteticas.py`, só biblioteca padrão; `hx fixtures build` em `harness.py`
- **Alternativas:** A) módulo novo em `tools/`, importado pelo `harness.py` · B) tudo dentro de `harness.py` (já tem 1399 linhas) · C) em `src/lastro/` com dependências do produto
- **Escolhida:** A — **motivo:** README (tabela de pastas) põe o gerador em `tools/`; o `hx` roda no host sem dependências; C obrigaria o host a ter o ambiente do produto. O gerador importa de `harness` o cálculo de DV (sem duplicar); `harness` importa o gerador só dentro do comando.
- **Impacto:** T2 a T6.
- [x] confirmar (camposs04, 24/11)

### D2 · Planilha .xlsx escrita à mão com `zipfile` (sem biblioteca), entradas sem compressão e data fixa
- **Alternativas:** A) `zipfile` da biblioteca padrão, OOXML mínimo com `sharedStrings`, `ZIP_STORED` e data 1980-01-01 em cada entrada · B) openpyxl (MIT) · C) XlsxWriter (BSD)
- **Escolhida:** A — **motivo:** B e C são dependências que o `hx` do host não tem. Ambas exigem fixar a data de criação e ainda as datas do zip para sair igual byte a byte; o openpyxl sobrescreve `modified` ao salvar. Sem compressão, a saída não depende da versão do zlib (host 3.11+ e container 3.14). `sharedStrings` é o que o Excel grava, o que diminui o risco de o leitor da CAD-05 não abrir a planilha.
- **Fontes (acesso em 24/11/2026):** openpyxl, `writer/excel.py` grava `modified = now()`: https://openpyxl.readthedocs.io/en/stable/_modules/openpyxl/writer/excel.html · resposta do mantenedor do XlsxWriter sobre a data de criação: https://lightrun.com/answers/jmcnamara-xlsxwriter-modification-to-enable-producing-consistent-binary-output · data fixa de zip reprodutível: https://pypi.org/project/repro-zipfile/ e https://reproducible-builds.org/docs/archives/
- **Impacto:** T3 (c1, c3).
- [x] confirmar (camposs04, 24/11)

### D3 · Sorteio só com `random.Random(semente).random()`
- **Alternativas:** A) só `random()` e conversão própria para inteiro e escolha · B) `randint` e `choice` · C) contador com SHA-256
- **Escolhida:** A — **motivo:** a garantia de reprodutibilidade entre versões vale só para o semeador e para `random()`; `randrange` e `choice` podem mudar. Importa porque `build` (host) e `--check`/testes (container) podem rodar em versões diferentes.
- **Fontes (acesso em 24/11/2026):** https://docs.python.org/3.2/library/random.html (notas de reprodutibilidade) · https://bugs.python.org/msg369409. Página atual não aberta: conferir a redação na T2.
- **Impacto:** T2 (c3).
- [x] confirmar (camposs04, 24/11)

### D4 · OFX 1.0.2 (SGML), ASCII, data e período fixos
- **Alternativas:** A) 1.0.2 SGML (cabeçalho `OFXHEADER:100`, tags folha sem fechamento) · B) 2.x XML
- **Escolhida:** A — **motivo:** é o estilo comum em exportação de banco de varejo e o mais exigente para o leitor (PRS-xx); a FDX diz que a maioria dos processadores aceita os dois. **Não verificado** qual versão os bancos dos pilotos exportam: confirmar com quem tem a estrutura em `docs/bancos/` (pasta ainda não existe). Período fixo (out/2026) e `DTSERVER` fixo, para não depender do relógio. Saldo em `LEDGERBAL`; inicial = final − soma. FITID único por conta, no formato `F<conta><seq>`.
- **Fontes (acesso em 24/11/2026):** https://financialdataexchange.org/?p=1187 · exemplo de STMTRS: https://sources.debian.org/src/libofx/1%3A0.9.0-3/doc/ofx_sample_files/ofx_spec201_stmtrs_example.xml · especificação 2.2: https://financialdataexchange.org/wp-content/uploads/2025/12/OFX-2.2.pdf (não lida na íntegra). Sem `ofxtools` (GPL-3, `decisoes/arquitetura.md`).
- **Impacto:** T4 (c2).
- [x] confirmar (camposs04, 24/11)

### D5 · Conteúdo sintético mínimo e fixo
- Semente padrão **1** (a ficha usa 2 como "outra"). Cadastro exatamente o do c1. Por cliente: 1 conta bancária (EMP-1 com 2, para testar "por conta"), 2 sócios `SOCIO TESTE nn`, plano de ~12 contas com `9.9.99 Transitória` (como nos exemplos da CAD-05), 15 a 30 movimentações (IA-02 c3 precisa de ao menos 3 em EMP-1 e 2 em EMP-9).
- A conta correta vem de um modelo de movimentação (ex.: tarifa → despesas bancárias); ao menos 1 linha por cliente vai para a transitória.
- Documentos de teste nas descrições no formato que a IA-01 reconhece (`AG 1234`, `CC 56789-0`, CPF e CNPJ com máscara e DV inválido), para a IA-02 exercitar a anonimização.
- CNPJs válidos: `cnpjs_dos_clientes(semente)` calcula na hora (1 alfanumérico); nunca gravado.
- [x] confirmar (camposs04, 24/11)

### D6 · Saída do `--check` e códigos
- Divergência → bloco ERRO/MOTIVO/CORREÇÃO de `mostrar_erro` e **código 1** (falha esperada, convenção do harness). Opção inválida → 2 (argparse). Em dia → código 0 e "fixtures em dia". O `--check` gera em memória e só lê o disco.
- [x] confirmar (camposs04, 24/11)

### D7 · Trava de segurança no gerador
- Antes de gravar, cada linha passa por `harness.tipos_da_linha`; qualquer achado (CPF/CNPJ com DV válido surgido por acaso em FITID, conta ou valor) aborta o build com erro. Reaproveita o detector em vez de criar outro.
- [x] confirmar (camposs04, 24/11)

## 3. Resumo e abordagem
`hx fixtures build [--semente N] [--check]` gera em `fixtures/` o `cadastro.json`, um .xlsx de plano por cliente e, por conta bancária, um OFX e um gabarito JSON, sempre iguais para a mesma semente.
Ordem: T1 testes → T2 modelo em memória (cadastro, plano, movimentações, CNPJs de execução) → T3 escrita de JSON e .xlsx → T4 OFX e gabarito → T5 comando `build` e `--check` → T6 check-clean varrendo `fixtures/` (depende da pergunta 1) → T7 verificação. A geração é uma função pura (semente → mapa caminho→bytes); `build` grava o mapa e `--check` compara o mapa com o disco. Isso dá c3 e c4 de graça e mantém um só caminho de código.

## 4. Contexto encontrado
- **Planos lidos:** `planos/HAR-04/plan.md` (status "pronto para revisão", **não aprovado**: D1–D5 entram como intenção; só a §5 vale como decidida) e `progress/HAR-04.md`.
- **Conferência com o código:** D3 da HAR-04 (CNPJ alfanumérico, `ord(c) − 48`, "resto < 2 → 0") **confere** em `tools/harness.py` (`_CNPJ`, `cnpj_valido`, `_digito_verificador`). D4 (regras só com `equipe.ts`) confere em `validar_regras_do_projeto`; não afeta esta feature. Pendência herdada: a regra "resto < 2" no DV alfanumérico ainda não conferida na rotina do Serpro; a mesma regra está em `src/lastro/ai/anonymization.py` (`_mod11_digit`), então os dois lados concordam.
- **Dependências:** `HAR-04` `passing` (23/11): check-clean detecta CNPJ numérico e alfanumérico.
- **Código relacionado:** `tools/harness.py`: `HarnessErro`, `mostrar_erro`, `main(argv, raiz)` (os testes usam `raiz=tmp_path`), `_criar_parser`, `cnpj_valido`, `cpf_valido`, `_digito_verificador`, `_PESOS_CNPJ_1/2`, `tipos_da_linha`, `varrer`, `_listar_arquivos`, `_percorrer_arvore`, `cmd_check_clean`.
- **Consumidoras:** CAD-05 (lê `plano_planilha`; cabeçalho `código`/`nome`) e IA-02 (lê `descricao` dos gabaritos e `socios`). Formato fixo do c6 é o contrato (regra 11: versão 0).
- **Reaproveitar:** em `tests/harness/test_validacao_lote.py`, o padrão `sys.path.insert(… "tools")` + `import harness` e o CNPJ montado em tempo de execução. Os marcadores e padrões de agência/conta da IA-01.
- **Não criar:** outro cálculo de DV, outro detector de documento, outro formato de erro, dependência nova.
- **Outros planos:** nenhum lido além da dependência (nenhum mexe em `tools/`).
- **Pesquisa externa:** D2, D3 e D4.

## 5. Decisões (já resolvidas)
- 24/11 · Resposta 1: check-clean varre `fixtures/` mesmo fora do Git (T6), por camposs04.
- 24/11 · Resposta 2: `build` apaga o que não gera (exceto `.gitkeep`); `--check` falha com arquivo a mais, por camposs04.
- 24/11 · Resposta 3: CAD-05 e IA-02 geram as fixtures numa fixture de pytest de sessão em `tmp_path`; sem task na HAR-03, por camposs04.
- 24/11 · Resposta 4: gerador para Python 3.11+, sem biblioteca nova; textos de versão em PR de docs separado, por camposs04.
- 24/11 · D1: gerador em `tools/fixtures_sinteticas.py`, só biblioteca padrão, confirmada por camposs04.
- 24/11 · D2: .xlsx com `zipfile`, `ZIP_STORED`, data fixa e `sharedStrings`, confirmada por camposs04.
- 24/11 · D3: sorteio só com `Random(semente).random()`, confirmada por camposs04.
- 24/11 · D4: OFX 1.0.2 SGML, ASCII, período fixo, confirmada por camposs04.
- 24/11 · D5: conteúdo sintético mínimo e semente padrão 1, confirmada por camposs04.
- 24/11 · D6: `--check` com ERRO/MOTIVO/CORREÇÃO e código 1, confirmada por camposs04.
- 24/11 · D7: trava com `harness.tipos_da_linha` antes de gravar, confirmada por camposs04.

### Desvios na implementação (registrados após a revisão do PR #58)
- **D7 no comando, e não no gerador:** a trava com `harness.tipos_da_linha` roda em `_exigir_sem_documentos`, dentro do comando `hx fixtures build` em `tools/harness.py`. **Motivo:** quando o harness roda como script principal (`tools/hx`), o módulo existe em duas cópias (`__main__` e `harness`), e um `HarnessErro` lançado pelo gerador não seria capturado pelo `main`. Um achado aborta o build com **código 2** (convenção do `main` para `HarnessErro`); o teste exige só código ≠ 0. Confirmado por camposs04 em 24/11/2026.
- **Extra: `--semente` negativa sai com código 2.** `Random(-N)` sorteia o mesmo que `Random(N)`, e o cadastro gravaria uma semente que não bate com os dados. Confirmado por camposs04 em 24/11/2026.
- **Extra: o `build` apaga as pastas que ficam vazias** depois de remover os arquivos que o gerador não produz (resposta 2). Confirmado por camposs04 em 24/11/2026.
- **Resposta 3 antecipada:** a fixture de pytest de sessão (`synthetic_fixtures_dir`, em `tests/conftest.py`) entrou neste PR, e não na CAD-05/IA-02. **Motivo:** com o PR #64, os testes novos da DB-01 passam a precisar das fixtures assim que o #58 entrar. Testes em `tests/harness/test_session_fixture.py`. Feito por caio-nascime em 25/11/2026, com autorização de camposs04 para codificar na branch; aguarda confirmação dela na revisão.

## 6. Avaliação da ficha
| # | Achado | Gravidade | Critério |
|---|---|---|---|
| 1 | check-clean não varre `fixtures/` (gitignored): c5 passa sem provar | resolvido em 24/11 (pergunta 1) | c5 |
| 2 | Arquivo a mais em `fixtures/` não coberto | resolvido em 24/11 (pergunta 2) | c3, c4 |
| 3 | "Semente padrão" sem valor na ficha | ATENÇÃO (D5) | c1, c3 |
| 4 | Nome da função que devolve os CNPJs não está na ficha | ATENÇÃO (D5; o T1 fixa) | c5 |
| 5 | 6 critérios (acima de 4), mas um módulo e uma função pura; sem dividir | ATENÇÃO | todos |
| 6 | "Ao menos 1 movimentação por cliente" com agência e conta: o check-clean não detecta agência/conta, só o teste prova | ATENÇÃO | c2 |
| 7 | c1 e c3 pedem `--semente` sem citar a opção | ATENÇÃO (D6) | c3 |

## 7. Riscos
- Número sorteado (FITID, conta, valor) formar CPF/CNPJ válido → D7 aborta o build.
- Saída diferente entre host e container (versão do Python ou do zlib) → D2 (sem compressão) e D3 (só `random()`); o teste do c3 roda o build duas vezes no mesmo processo, então a T5 também compara com um build pelo `tools/hx` do host, se houver.
- CNPJ válido literal no código ou nos testes sujaria o check-clean do repositório → calculado em tempo de execução, como na HAR-04.
- Mudar o formato do c6 quebra CAD-05 e IA-02 → contrato v0, mudança só com issue `contrato:`.
- Leitor da CAD-05 não abrir a planilha mínima → `sharedStrings`; a T3 valida abrindo com `zipfile` + `xml.etree`.

## 8. Aprovação
- [x] Perguntas BLOQUEANTES respondidas (1, em 24/11; 2 a 4 também respondidas)
- [x] Decisões do agente confirmadas (D1 a D7, em 24/11)
- [x] Plan e tasks revisados por camposs04 em 24/11
