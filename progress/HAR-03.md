# HAR-03 · Gerar fixtures e gabarito sintéticos por semente fixa

- Responsável: camposs04 · Branch: `feat/HAR-03-gerar-fixtures-e-gabarito-sinteticos-por` · Início: 24/11/2026
- Ficha: `features/HAR-03.json` (estado e critérios ficam lá; não repita aqui)

<!--
Como preencher (agente, ao encerrar a sessão):
- REESCREVA as seções do topo: Objetivo, Próxima ação, Bloqueios e perguntas.
- ACRESCENTE, sem apagar o que já existe, em Feito, Rodei, Falhou e Decisões.
  Cada linha começa com a data (DD/MM) e a sessão, ex.: "- 14/11 · S2 · ...".
- Registre só o que realmente rodou. Sem dado real, nome de cliente ou segredo.
- Não escreva estado (passing etc.) aqui: ele fica na ficha, gravado pelo script.
-->

## Objetivo
`hx fixtures build [--semente N] [--check]` gera em `fixtures/` o cadastro sintético, uma planilha de plano por cliente e, por conta bancária, um OFX e um gabarito, sempre iguais para a mesma semente. O `--check` confere a pasta sem regravar, e o check-clean passa a varrer `fixtures/`.

## Próxima ação
Feature concluída (T1 a T7); documentação e ficha (c4, c5, `verificacao`) ajustadas após a revisão do PR #58, com novo `hx feature verify` OK. A fixture de sessão `synthetic_fixtures_dir` (resposta 3 do plan) entrou neste PR em `tests/conftest.py`: testes de qualquer módulo recebem a pasta gerada sem depender de `fixtures/` da raiz. Falta rodar o `hx check-clean` com `LASTRO_NOMES_PROIBIDOS` definida e registrar o resultado (ver Bloqueios). A exceção DB-01 em `docs/SECURITY.md` foi tratada pelo responsável da DB-01 no PR #64 (guin409): a exceção se encerra quando o #58 entrar na developer. Depois, as pendências abaixo, cada uma no seu PR, fora desta branch.

## Bloqueios e perguntas
- `hx check-clean` com a lista real de `LASTRO_NOMES_PROIBIDOS`: a execução de 24/11 (S4, ver Rodei) mostrou "verificação de nomes pulada (variável não definida)", então a lista não foi aplicada. camposs04 define a variável no mesmo shell, roda de novo e registra.
- Pendências fora do escopo da HAR-03:
  - PR de docs com a versão do Python (`tools/hx`, cabeçalho do `harness.py`, AGENTS.md), resposta 4 do plan, incluindo a mensagem "requer Python 3.11+".
  - Traceback quando `fixtures/` existe como arquivo, e não como pasta: o `build` deveria sair com ERRO/MOTIVO/CORREÇÃO (apontado na revisão do PR #58).
  - `docs/modules/harness.md` com o contrato v0 do `hx fixtures build` (formato do c6, caminhos relativos a `fixtures/`, `cnpjs_dos_clientes`).
  - O texto "(padrão: 1)" na ajuda do `--semente` repete `SEMENTE_PADRAO` do gerador; se a semente padrão mudar, o texto precisa mudar junto.

## Feito
- 24/11 · S1 · Feature iniciada (commit da790af); plan e tasks aprovados por camposs04 (commit 3a5b017).
- 24/11 · S2 · T1: `tests/harness/test_fixtures.py` com 23 testes (os 14 da ficha, com os nomes exatos de `verificacao`, e 9 das decisões do plan: pergunta 2, D1 a D7). Todo build roda em `tmp_path`; CPF/CNPJ válidos só calculados em tempo de execução. Commit só de testes: `49751a5` (âncora).
- 24/11 · S3 · T2 a T6: `tools/fixtures_sinteticas.py` (modelo em memória, `cadastro.json`, .xlsx com `zipfile`, OFX 1.0.2 e gabarito; função pura semente → {caminho: bytes}) e, em `tools/harness.py`, `hx fixtures build [--semente N] [--check]` e o `varrer` incluindo `fixtures/`. Commit da implementação: `b2a8443`.
- 24/11 · S3 · T7: verificação final (ver Rodei). `hx feature verify HAR-03` gravou o estado na ficha, commit `bec9f04`. `git diff 49751a5 -- tests/` vazio.
- 24/11 · S4 · Ajustes de documentação pedidos pelas duas revisões do PR #58 (ACEITAR): desvio da D7 e extras registrados no plan; T1 a T7 marcadas em `tasks.md`; ARCHITECTURE.md lista `tools/fixtures_sinteticas.py`; README corrigido (`.gitkeep` versionado); ajuda do `hx fixtures build` avisa que apaga o que o gerador não produz. Sem mudança de comportamento nem em `tests/`.
- 24/11 · S4 · Ficha ajustada no PR #58, por decisão de camposs04: c4 com o caso (d), arquivo a mais; c5 com o check-clean varrendo `fixtures/` mesmo fora do Git; `test_check_com_arquivo_a_mais_falha_sem_apagar` em `verificacao` (commit `aa057a6`). Novo `hx feature verify HAR-03` gravou a evidência (commit `4ca2bdc`).
- 25/11 · S5 · Fixture de pytest de sessão `synthetic_fixtures_dir` em `tests/conftest.py` (resposta 3 do plan): chama `gerar_arquivos()` da semente padrão uma vez por sessão e grava em `<tmp>/fixtures/`. Testes primeiro, em `tests/harness/test_session_fixture.py` (3 testes: mesmos bytes do gerador, passa no `hx fixtures build --check`, fica fora do repositório), commit só de testes `e02bf20`. Feito por caio-nascime, com autorização de camposs04 para codificar na branch.

## Rodei
- 24/11 · S2 · `pytest tests/harness/test_fixtures.py --collect-only -q` (host) → 23 coletados
- 24/11 · S2 · `docker compose run --rm dev pytest tests/harness/test_fixtures.py -q` → 23 falharam, todos pelo motivo esperado (19 × build com código 2 porque o subcomando `fixtures` não existe; 2 × `ModuleNotFoundError: fixtures_sinteticas`; 2 × código 2 no lugar de 1/0)
- 24/11 · S2 · `docker compose run --rm dev pytest tests/harness -q --ignore=tests/harness/test_fixtures.py` → 167 passaram
- 24/11 · S2 · `docker compose run --rm dev ruff check tests/harness/test_fixtures.py` → All checks passed
- 24/11 · S2 · `sh tools/hx check-clean` (sem `LASTRO_NOMES_PROIBIDOS`: nomes pulados) → 0 achados
- 24/11 · S2 · `hx check-clean` com `LASTRO_NOMES_PROIBIDOS` definida → 0 achados (rodado e informado por camposs04)
- 24/11 · S3 · `pytest tests/harness -q` → 190 passaram, no host (Python 3.12) e no container (3.14)
- 24/11 · S3 · `docker compose run --rm dev ruff check tools/ tests/harness/` → All checks passed
- 24/11 · S3 · `sh tools/hx fixtures build` no host (3.12) → 12 arquivos; `python tools/harness.py fixtures build --check` no container (3.14) → código 0, "fixtures em dia" (mesmos bytes entre as versões)
- 24/11 · S3 · `sh tools/hx check-clean` sem `LASTRO_NOMES_PROIBIDOS` → 0 achados, já varrendo `fixtures/`
- 24/11 · S3 · `hx verify` local → OK depois de `docker compose build dev` (informado por camposs04)
- 24/11 · S3 · CI do PR #58 → verde em verify e check-clean (informado por camposs04)
- 24/11 · S3 · `hx feature verify HAR-03` → OK, c1 a c6 (14 testes), estado gravado no commit `bec9f04` (informado por camposs04)
- 24/11 · S3 · `git diff 49751a5 -- tests/` → vazio
- 24/11 · S4 · `python3 tools/harness.py check-clean` (rodado e informado por camposs04, que pretendia usar a lista real) → saída exata: "AVISO: verificação de nomes pulada (variável não definida)" / "check-clean: 0 achado(s)" / "RESULTADO: OK". A variável não chegou ao processo: os nomes **não** foram conferidos.
- 24/11 · S4 · `sh tools/hx feature verify HAR-03` depois do commit `aa057a6` → RESULTADO: OK, 15 testes (c1: 2, c2: 4, c3: 2, c4: 4, c5: 2, c6: 1); evidência gravada no commit `4ca2bdc`
- 25/11 · S5 · `docker compose run --rm -T dev pytest tests/harness/test_session_fixture.py -q` antes do conftest → 3 erros, todos "fixture 'synthetic_fixtures_dir' not found" (esperado)
- 25/11 · S5 · `docker compose run --rm -T dev pytest tests/harness/test_session_fixture.py tests/harness/test_fixtures.py -q` com o conftest → 26 passaram; `ruff check` nos dois arquivos novos → All checks passed
- 25/11 · S5 · `python tools/harness.py verify` (host Windows; `sh tools/hx` falhou porque `python3` é o atalho da Microsoft Store) → ruff OK, pytest OK, Arquitetura e E2E pulados, RESULTADO: OK
- 25/11 · S5 · `python tools/harness.py check-clean` sem `LASTRO_NOMES_PROIBIDOS` (nomes pulados) → 0 achados

## Falhou
- 24/11 · S2 · Os 23 testes de `tests/harness/test_fixtures.py` falham de propósito (T1, testes antes do código): o subcomando `fixtures` e `tools/fixtures_sinteticas.py` ainda não existem. Por isso `hx verify` não foi rodado: ficaria vermelho até a T5/T6.
- 24/11 · S3 · Primeiro `hx verify` local: 4 falhas em `tests/web/test_web_foundation.py` (WEB-01), "Program not found: 'node'". A imagem dev local estava desatualizada, sem `node`; sem relação com a HAR-03. Resolvido com `docker compose build dev`.
- 24/11 · S3 · Primeiro `hx feature verify HAR-03`: recusado por árvore de trabalho com alterações não commitadas. Rodou depois do commit `b2a8443`.

## Decisões
- 24/11 · S1 · Respostas 1 a 4 e D1 a D7 do plan confirmadas por camposs04 (ver `planos/HAR-03/plan.md` §5).
- 24/11 · S2 · Testes extras com nomes próprios, sem colidir com os 14 da ficha: `test_check_com_arquivo_a_mais_falha_sem_apagar` (nome sugerido no plan), `test_check_em_pasta_vazia_falha_sem_gravar`, `test_semente_invalida_sai_com_codigo_2`, `test_harness_importa_gerador_so_no_comando`, `test_planilha_sem_compressao_e_data_fixa`, `test_sorteio_usa_so_random`, `test_ofx_versao_102_sgml_ascii`, `test_conteudo_minimo_do_modelo`, `test_build_aborta_se_linha_tiver_documento_valido`.
- 24/11 · S2 · O gerador é importado dentro de cada teste (não no topo), para que cada um falhe pelo próprio motivo enquanto o módulo não existe.
- 24/11 · S2 · No teste do c5, o git é simulado (responde sem `fixtures/`), para provar que o check-clean varre a pasta mesmo fora do Git, sem depender de git real no container.
- 24/11 · S3 · Contratos confirmados: `cnpjs_dos_clientes(semente)` devolve `{"EMP-1": cnpj sem máscara, ...}`, com o primeiro alfanumérico; `plano_planilha`, `ofx` e `gabarito` são relativos a `fixtures/`.
- 24/11 · S3 · Desvio do plan (D7): a trava fica no comando do `harness.py`, e não no gerador. Quando o harness roda como script principal (`tools/hx`), existem duas cópias do módulo, e um `HarnessErro` lançado pelo gerador não seria capturado pelo `main`.
- 24/11 · S3 · O aborto da D7 sai com código 2 (convenção do `main` para `HarnessErro`); o teste exige só ≠ 0.
- 24/11 · S3 · `--semente` negativa é recusada com código 2: `Random(-N)` sorteia o mesmo que `Random(N)`, e o cadastro gravaria uma semente que não bate com os dados.
- 24/11 · S3 · O `build` também apaga as pastas que ficam vazias depois de remover as sobras.
- 24/11 · S3 · OFX com CRLF e todas as datas em `AAAAMMDD` (8 dígitos, inclusive `DTSERVER`): um carimbo de 14 dígitos seria candidato ao detector de CNPJ. FITID = `F` + 5 dígitos da conta + 4 da sequência (nunca 11 nem 14 caracteres).
- 24/11 · S4 · Desvio da D7 (trava no comando, aborto com código 2) e os extras (`--semente` negativa → código 2; `build` apaga pastas vazias) confirmados por camposs04 e registrados em `planos/HAR-03/plan.md` §5, sem alterar D1 a D7.
- 24/11 · S4 · Ficam fora do PR #58: traceback com `fixtures/` como arquivo, mensagem "requer Python 3.11+", ficha c4(d)/c5 e o teste extra em `verificacao` (PR de humano), `docs/modules/harness.md`.
- 24/11 · S4 · camposs04 mudou a decisão acima sobre a ficha: c4(d), c5 e o teste extra em `verificacao` entram no próprio PR #58 (commit `aa057a6`), como o plan propunha. Os demais itens seguem fora.
- 24/11 · S4 · Resolvida a pendência da exceção DB-01 em `docs/SECURITY.md` §3 ("enquanto `hx fixtures build` estiver indisponível"): tratada pelo responsável da DB-01 no PR #64 (guin409); a exceção se encerra quando o #58 entrar na developer. Sem edição em `docs/SECURITY.md` neste PR.
- 25/11 · S5 · A fixture de sessão entra no próprio PR #58, e não na CAD-05/IA-02 como dizia a resposta 3: com o #64, os testes novos da DB-01 passam a precisar dela assim que o #58 entrar. Fica em `tests/conftest.py` (raiz dos testes) para valer em todo módulo; é a única mudança fora de `tests/harness/` e `tools/`.
- 25/11 · S5 · Nomes em inglês (`synthetic_fixtures_dir`, `test_session_fixture.py`), como pede o CODING_STANDARDS §9 para código novo. A pasta é compartilhada pela sessão: é só leitura, e quem precisar alterar copia para o próprio `tmp_path` (docstring do conftest). Os testes da ficha não usam a fixture: `git diff 49751a5 -- tests/` deixa de ser vazio só pelos dois arquivos novos.
- 25/11 · S5 · Contrato v0 da fixture: nome `synthetic_fixtures_dir`, escopo de sessão, devolve `Path` de uma pasta chamada `fixtures` com os arquivos da semente padrão. Mudança segue a regra 11 (issue `contrato:`).

## Fim de sessão
- [x] `hx verify` verde, ou a falha está descrita em "Falhou"
- [x] Nada quebrado nem pela metade na branch; commit feito
- [x] "Próxima ação" atualizada
- [x] Nenhum dado real nem segredo nas anotações
