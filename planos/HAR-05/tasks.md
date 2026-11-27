# Tasks — HAR-05 · Plano de contas sintético em TXT

**Plan:** `planos/HAR-05/plan.md` · **Ficha:** `features/HAR-05.json`
**Ordem:** aprovação humana do plano → T1 → revisão humana dos testes → commit de testes → T2–T4 sem editar `tests/` → T5

## [ ] T1 · Escrever os testes antes do código

- **Critérios:** HAR-05 c1–c3 e a atualização autorizada da HAR-03 c1/c6.
- **Aceite:** criar os três testes com os nomes exatos da ficha em `tests/harness/test_fixtures_plano_txt.py`; c1 fatia cada linha, exige 78 caracteres, UTF-8/CRLF e igualdade com `cadastro.json`; c2 verifica 10 grupos, 13 analíticas, pais sintéticos, reduzidos únicos e `conta_correta` só analítica; c3 gera 50 sementes, exige ao menos 50 planos conferidos e usa o detector do `check-clean` em cada linha.
- **Exceção T12:** em `tests/harness/test_fixtures.py`, remover apenas o teste e os auxiliares XLSX listados; trocar o bloco XLSX de determinismo por TXT; no teste do cadastro, trocar `plano_planilha` por `plano_txt` e acrescentar asserções de classificação, reduzido e tipo. Atualizar somente c1, c6 e `verificacao` de `features/HAR-03.json`.
- **Prova:** os testes novos falham pelo comportamento ainda ausente; os testes antigos fora da T12 permanecem intactos. Revisão humana e commit de testes antes de T2.
- **Arquivos:** `tests/harness/test_fixtures_plano_txt.py`, `tests/harness/test_fixtures.py`, `features/HAR-03.json`.

## [ ] T2 · Ampliar o modelo sintético do plano

- **Critérios:** c1, c2.
- **Aceite:** `PLANO_BASE` contém os 10 grupos `S` e as 13 analíticas `A`, com ancestrais antes das filhas; cada item do cadastro contém `codigo`, `classificacao`, `reduzido`, `nome`, `tipo` e `transitoria`; reduzidos têm 7 dígitos, são únicos por cliente e vêm de sorteio independente; os modelos de movimentação e `conta_correta` não mudam.
- **Arquivos:** `tools/fixtures_sinteticas.py`.
- **Prova:** `pytest tests/harness/test_fixtures_plano_txt.py::test_plano_sintetico_tem_grupos_e_analiticas -q`.

## [ ] T3 · Gerar TXT e proteger as linhas

- **Critérios:** c1, c3.
- **Aceite:** trocar `plano_planilha` por `plano_txt`; gerar um TXT de 78 caracteres por linha em UTF-8/CRLF, sem cabeçalho; conferir cada linha contra `harness.tipos_da_linha`; refazer o reduzido até um limite quando houver CPF/CNPJ válido e deixar a trava D7 abortar se não houver alternativa segura.
- **Arquivos:** `tools/fixtures_sinteticas.py`.
- **Prova:** testes c1 e c3 da HAR-05, mais `test_build_aborta_se_linha_tiver_documento_valido` da HAR-03.

## [ ] T4 · Retirar XLSX do harness

- **Critérios:** c1, c3; HAR-03 c1/c6.
- **Aceite:** remover a geração XLSX, `membros_xlsx` e auxiliares sem uso; `_exigir_sem_documentos` não recebe mais esses membros e continua examinando todos os arquivos antes de gravar; `cmd_fixtures_build` usa a nova assinatura.
- **Arquivos:** `tools/fixtures_sinteticas.py`, `tools/harness.py`.
- **Prova:** `pytest tests/harness/test_fixtures.py tests/harness/test_fixtures_plano_txt.py -q`.

## [ ] T5 · Verificar, documentar e entregar

- **Aceite:** `git diff <hash-do-commit-de-testes> HEAD -- tests/` vazio; HAR-05 e HAR-03 verificadas pelo harness (com commit entre as fichas); `hx verify` e `hx check-clean` OK; TXT da semente padrão lido pela CAD-02 quando disponível; `progress/HAR-05.md` atualizado, PR para `developer` com a exceção T12 e pedido de revisão ao dono do harness.
- **Prova:** `python tools/harness.py feature verify HAR-05`, `python tools/harness.py feature verify HAR-03`, `python tools/harness.py verify` e `python tools/harness.py check-clean` concluídos, com resultados registrados.
