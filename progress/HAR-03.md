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
Em sessão nova, sem editar `tests/`: T2 de `planos/HAR-03/tasks.md` (modelo em memória em `tools/fixtures_sinteticas.py`), depois T3 a T7. Primeiro alvo: `docker compose run --rm dev pytest tests/harness/test_fixtures.py::test_cnpj_em_tempo_de_execucao_valido_e_estavel -q`. Âncora dos testes: commit `49751a5` (`git diff 49751a5 -- tests/` deve continuar vazio).

## Bloqueios e perguntas
- CONTRATO A CONFIRMAR (marcado nos testes): tipo do retorno de `cnpjs_dos_clientes` (o teste aceita dict cliente → CNPJ ou lista).
- CONTRATO A CONFIRMAR: `plano_planilha` relativo a `fixtures/`, como `ofx` e `gabarito` (o c6 não diz a quê).
- CONTRATO A CONFIRMAR: na D7, o gerador chama `harness.tipos_da_linha` (o teste troca a função no `harness` e, se importada pelo nome, também no gerador); o código de saída do aborto não está fixado (o teste exige só ≠ 0).
- Mudanças aceitas na ficha (c4 com arquivo a mais, c5 com check-clean varrendo `fixtures/`) ainda aguardam o PR de camposs04.

## Feito
- 24/11 · S1 · Feature iniciada (commit da790af); plan e tasks aprovados por camposs04 (commit 3a5b017).
- 24/11 · S2 · T1: `tests/harness/test_fixtures.py` com 23 testes (os 14 da ficha, com os nomes exatos de `verificacao`, e 9 das decisões do plan: pergunta 2, D1 a D7). Todo build roda em `tmp_path`; CPF/CNPJ válidos só calculados em tempo de execução. Commit só de testes: `49751a5` (âncora).

## Rodei
- 24/11 · S2 · `pytest tests/harness/test_fixtures.py --collect-only -q` (host) → 23 coletados
- 24/11 · S2 · `docker compose run --rm dev pytest tests/harness/test_fixtures.py -q` → 23 falharam, todos pelo motivo esperado (19 × build com código 2 porque o subcomando `fixtures` não existe; 2 × `ModuleNotFoundError: fixtures_sinteticas`; 2 × código 2 no lugar de 1/0)
- 24/11 · S2 · `docker compose run --rm dev pytest tests/harness -q --ignore=tests/harness/test_fixtures.py` → 167 passaram
- 24/11 · S2 · `docker compose run --rm dev ruff check tests/harness/test_fixtures.py` → All checks passed
- 24/11 · S2 · `sh tools/hx check-clean` (sem `LASTRO_NOMES_PROIBIDOS`: nomes pulados) → 0 achados
- 24/11 · S2 · `hx check-clean` com `LASTRO_NOMES_PROIBIDOS` definida → 0 achados (rodado e informado por camposs04)

## Falhou
- 24/11 · S2 · Os 23 testes de `tests/harness/test_fixtures.py` falham de propósito (T1, testes antes do código): o subcomando `fixtures` e `tools/fixtures_sinteticas.py` ainda não existem. Por isso `hx verify` não foi rodado: ficaria vermelho até a T5/T6.

## Decisões
- 24/11 · S1 · Respostas 1 a 4 e D1 a D7 do plan confirmadas por camposs04 (ver `planos/HAR-03/plan.md` §5).
- 24/11 · S2 · Testes extras com nomes próprios, sem colidir com os 14 da ficha: `test_check_com_arquivo_a_mais_falha_sem_apagar` (nome sugerido no plan), `test_check_em_pasta_vazia_falha_sem_gravar`, `test_semente_invalida_sai_com_codigo_2`, `test_harness_importa_gerador_so_no_comando`, `test_planilha_sem_compressao_e_data_fixa`, `test_sorteio_usa_so_random`, `test_ofx_versao_102_sgml_ascii`, `test_conteudo_minimo_do_modelo`, `test_build_aborta_se_linha_tiver_documento_valido`.
- 24/11 · S2 · O gerador é importado dentro de cada teste (não no topo), para que cada um falhe pelo próprio motivo enquanto o módulo não existe.
- 24/11 · S2 · No teste do c5, o git é simulado (responde sem `fixtures/`), para provar que o check-clean varre a pasta mesmo fora do Git, sem depender de git real no container.

## Fim de sessão
- [x] `hx verify` verde, ou a falha está descrita em "Falhou"
- [x] Nada quebrado nem pela metade na branch; commit feito
- [x] "Próxima ação" atualizada
- [x] Nenhum dado real nem segredo nas anotações
