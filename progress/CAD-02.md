# CAD-02 · Ler a planilha do plano de contas e apontar linha inválida

- Responsável: marrathomaz · Branch: `feat/CAD-02-ler-a-planilha-do-plano-de-contas-e-apon` · Início: 25/11/2026
- Ficha: `features/CAD-02.json` (estado e critérios ficam lá; não repita aqui)

<!--
Como preencher (agente, ao encerrar a sessão):
- REESCREVA as seções do topo: Objetivo, Próxima ação, Bloqueios e perguntas.
- ACRESCENTE, sem apagar o que já existe, em Feito, Rodei, Falhou e Decisões.
  Cada linha começa com a data (DD/MM) e a sessão, ex.: "- 14/11 · S2 · ...".
- Registre só o que realmente rodou. Sem dado real, nome de cliente ou segredo.
- Não escreva estado (passing etc.) aqui: ele fica na ficha, gravado pelo script.
-->

## Objetivo
Leitura e validação pura de planilhas `.xlsx` de plano de contas no módulo `registry` (sem banco nem HTTP), devolvendo a lista ordenada de contas válidas (`code`, `name`) e mensagens em português simples para linhas incompletas, códigos repetidos, planilhas sem contas/cabeçalho inválido ou arquivos que não são `.xlsx` (RF-CAD-03).

## Próxima ação
Rodar `sh tools/hx check-clean` com `LASTRO_NOMES_PROIBIDOS` definida localmente, fazer `git push` da branch `feat/CAD-02-ler-a-planilha-do-plano-de-contas-e-apon` e abrir o PR para `developer` com a descrição preenchida.

## Bloqueios e perguntas
- (nenhum)

## Feito
- 25/11 · S1 · Feature iniciada (commit `6d72ac2`), plano e tasks revisados e aprovados em `planos/CAD-02/` (commit `53c0542`).
- 25/11 · S1 · Escritos os 5 testes dos critérios c1 a c4 em `tests/registry/test_planilha_plano.py` com planilhas `.xlsx` sintéticas geradas em `tmp_path` em tempo de execução (commit só de testes `6e3e3ab`).
- 25/11 · S1 · Adicionada a dependência `openpyxl` em `pyproject.toml` e `uv.lock`; implementados `ChartAccountEntry` e `ChartSpreadsheetResult` em `src/lastro/registry/contracts.py`, a leitura/validação em `src/lastro/registry/chart_spreadsheet.py` e a fachada `read_chart_of_accounts_spreadsheet` em `src/lastro/registry/service.py`; documentado o contrato v0 em `ARCHITECTURE.md` (§6) e `docs/modules/registry.md` (commit `01bc3bd`), sem editar `tests/`.
- 25/11 · S1 · Evidência de verificação gravada em `features/CAD-02.json` via harness (commit `edd1cdf`, referente ao commit `01bc3bdebeb2`).
- 25/11 · S2 · Atualizado `progress/CAD-02.md` e executadas as verificações finais do harness para fechamento do PR.

## Rodei
- 25/11 · S1 · `hx feature verify CAD-02` → c1, c2, c3 e c4 (2 comandos) ok; evidência registrada em `features/CAD-02.json` no commit `edd1cdf` (sobre `01bc3bdebeb2`).
- 25/11 · S2 · `git diff 6e3e3ab -- tests/` → vazio (testes intactos desde o commit só de testes).
- 25/11 · S2 · `sh tools/hx verify` → `[1/2] ruff check . OK`, `[2/2] pytest -q OK`, Arquitetura e E2E pulados; `RESULTADO: OK`.
- 25/11 · S2 · `sh tools/hx check-clean` → `0 achado(s)`, `RESULTADO: OK` (aviso: `LASTRO_NOMES_PROIBIDOS` não definida neste ambiente).

## Falhou
- 25/11 · S2 · Nenhuma falha de código, lint ou teste; apenas o aviso esperado de `LASTRO_NOMES_PROIBIDOS` não definida ao rodar `sh tools/hx check-clean` sem a variável no ambiente.

## Decisões
- 25/11 · S1 · Escolhida `openpyxl>=3.1.5` (D1/D6) para leitura em streaming (`read_only=True`, `data_only=True`, limite de 20 MiB alinhado à D-06, D5) e geração dos `.xlsx` sintéticos nos testes; regra pura em `registry/` sem banco/HTTP (D2); retorno estruturado imutável `ChartSpreadsheetResult` / `ChartAccountEntry` sem exceção de negócio (D3); assinatura `read_chart_of_accounts_spreadsheet(source: bytes | Path)` (D4); cabeçalho na linha 1 normalizado ignorando colunas extras (P-10, pergunta 1), linhas totalmente vazias ignoradas preservando numeração real do Excel (pergunta 2), normalização de células numéricas/strings preservando zeros à esquerda e pontos (pergunta 3), nomes de testes da ficha mantidos com código em inglês (pergunta 4) e contrato v0 documentado em `docs/modules/registry.md` + `ARCHITECTURE.md` §6 (pergunta 5). Detalhes em `planos/CAD-02/plan.md`.

## Fim de sessão
- [x] `hx verify` verde, ou a falha está descrita em "Falhou"
- [x] Nada quebrado nem pela metade na branch; commit feito
- [x] "Próxima ação" atualizada
- [x] Nenhum dado real nem segredo nas anotações
