# CAD-02 · Ler o plano de contas em TXT e apontar linha inválida

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
Ler e validar o plano de contas exportado do Domínio em TXT de 78 colunas, no módulo `registry` (sem banco nem HTTP). `read_chart_of_accounts(bytes | Path)` devolve `ChartOfAccountsResult(accounts, errors, warnings, refusal)` (contrato v1, `DECISIONS.md` §11 T5 e T13): as contas com reduzido, classificação, nome, tipo e conta superior, os erros tolerados das analíticas folha, os avisos e uma recusa única quando o erro compromete o plano (RF-CAD-03; regra em `docs/modulos/registry.md`).

## Próxima ação
Revisão humana dos commits da T2 à T7. Depois, com autorização, `git push` da branch e PR para `developer` citando `DECISIONS.md` §11 T12 (o commit só de testes é o `76a2c51`, e `git diff 76a2c51 -- tests/` está vazio) e T13 (contrato v1, sem issue). Rodar o `check-clean` com `LASTRO_NOMES_PROIBIDOS` definida antes do PR.

## Bloqueios e perguntas
- Leitura a confirmar na revisão: uma linha que é consequência (a conta superior não foi aceita) e também tem erro tolerável (E2, E2z, E4) conta como causa, porque o passo 8 do `registry.md` exige "sem problema de hierarquia" para tolerar. Nenhum teste da ficha cobre esse caso.
- O "Pronto quando" da T3 (c2) só passa com a hierarquia da T4, porque o teste confere a conta superior `11`. E o c6(d) da T4 precisa da tolerância da analítica folha, que por isso entrou na T4, e não na T5.

## Feito
- 25/11 · S1 · Feature iniciada (commit `6d72ac2`), plano e tasks revisados e aprovados em `planos/CAD-02/` (commit `53c0542`).
- 25/11 · S1 · Escritos os 5 testes dos critérios c1 a c4 em `tests/registry/test_planilha_plano.py` com planilhas `.xlsx` sintéticas geradas em `tmp_path` em tempo de execução (commit só de testes `6e3e3ab`).
- 25/11 · S1 · Adicionada a dependência `openpyxl` em `pyproject.toml` e `uv.lock`; implementados `ChartAccountEntry` e `ChartSpreadsheetResult` em `src/lastro/registry/contracts.py`, a leitura/validação em `src/lastro/registry/chart_spreadsheet.py` e a fachada `read_chart_of_accounts_spreadsheet` em `src/lastro/registry/service.py`; documentado o contrato v0 em `ARCHITECTURE.md` (§6) e `docs/modules/registry.md` (commit `01bc3bd`), sem editar `tests/`.
- 25/11 · S1 · Evidência de verificação gravada em `features/CAD-02.json` via harness (commit `edd1cdf`, referente ao commit `01bc3bdebeb2`).
- 25/11 · S2 · Atualizado `progress/CAD-02.md` e executadas as verificações finais do harness para fechamento do PR.
- 27/11 · S3 · T2 (`b7722c1`): `ChartAccountEntry` e `ChartOfAccountsResult` (v1) em `contracts.py`, `read_chart_of_accounts` em `service.py` e `src/lastro/registry/chart_txt.py` (recusa de arquivo, decodificação, linhas); apagados `chart_spreadsheet.py`, `read_chart_of_accounts_spreadsheet` e `ChartSpreadsheetResult`. Tipos e funções da CAD-03 intactos.
- 27/11 · S3 · T3 (`c4a7221`): erro próprio de cada linha na ordem da tabela (E1, E8, E3a, E3b, E5a, E5b, E2, E2z, E4).
- 27/11 · S3 · T4 (`f7523b3`): repetições E6/E7 em toda linha, hierarquia pelo maior prefixo próprio e tolerância da analítica folha.
- 27/11 · S3 · T5 (`b9489d7`): toleradas viram causa quando não sobra analítica; avisos de sintética sem filhas.
- 27/11 · S3 · T6 (`f84cc61`): `openpyxl` fora do `pyproject.toml`; `uv.lock` regenerado no contêiner (saíram `openpyxl` e `et-xmlfile`, `revision = 5`); imagem `lastro-dev` reconstruída.
- 27/11 · S3 · T7: ficha em `passing` pelo `hx feature verify` (`72406b9`).

## Rodei
- 25/11 · S1 · `hx feature verify CAD-02` → c1, c2, c3 e c4 (2 comandos) ok; evidência registrada em `features/CAD-02.json` no commit `edd1cdf` (sobre `01bc3bdebeb2`).
- 25/11 · S2 · `git diff 6e3e3ab -- tests/` → vazio (testes intactos desde o commit só de testes).
- 25/11 · S2 · `sh tools/hx verify` → `[1/2] ruff check . OK`, `[2/2] pytest -q OK`, Arquitetura e E2E pulados; `RESULTADO: OK`.
- 25/11 · S2 · `sh tools/hx check-clean` → `0 achado(s)`, `RESULTADO: OK` (aviso: `LASTRO_NOMES_PROIBIDOS` não definida neste ambiente).
- 27/11 · S3 · `docker compose run --rm -T dev pytest tests/registry/test_plano_txt.py -q`: 10 passed (depois da T5).
- 27/11 · S3 · `docker compose run --rm -T dev uv lock` (uv 0.13.9): "Removed et-xmlfile v2.0.0", "Removed openpyxl v3.1.5". `git grep -n openpyxl -- src tests pyproject.toml uv.lock` sem resultado.
- 27/11 · S3 · `docker compose build dev`: imagem reconstruída; `openpyxl` ausente na imagem.
- 27/11 · S3 · Conferência manual em script fora do repositório, com dados sintéticos: duas analíticas folha com `0000000` dão 2 erros tolerados, sem recusa (D3); `Path` inexistente levanta `FileNotFoundError` (D2); `Path` acima de 20 MiB é recusado pelo `stat()`; 1.200 embaralhamentos com até 3 erros injetados, sem nenhuma troca entre aceitar e recusar.
- 27/11 · S3 · `git diff 76a2c51 -- tests/`: vazio.
- 27/11 · S3 · `python tools/harness.py check-clean`: 0 achado(s), `RESULTADO: OK` (aviso: `LASTRO_NOMES_PROIBIDOS` não definida).
- 27/11 · S3 · `python tools/harness.py verify` com a imagem reconstruída: ruff OK, pytest OK, Arquitetura e E2E pulados; `RESULTADO: OK`.
- 27/11 · S3 · `python tools/harness.py feature verify CAD-02`: c1 a c10 OK; `RESULTADO: OK`.

## Falhou
- 25/11 · S2 · Nenhuma falha de código, lint ou teste; apenas o aviso esperado de `LASTRO_NOMES_PROIBIDOS` não definida ao rodar `sh tools/hx check-clean` sem a variável no ambiente.
- 27/11 · S3 · Na T3, o teste do c2 falhou só na conta superior (`None` em vez de `'11'`), que entrou na T4. Depois da T4 ele passou.

## Decisões
- 25/11 · S1 · Escolhida `openpyxl>=3.1.5` (D1/D6) para leitura em streaming (`read_only=True`, `data_only=True`, limite de 20 MiB alinhado à D-06, D5) e geração dos `.xlsx` sintéticos nos testes; regra pura em `registry/` sem banco/HTTP (D2); retorno estruturado imutável `ChartSpreadsheetResult` / `ChartAccountEntry` sem exceção de negócio (D3); assinatura `read_chart_of_accounts_spreadsheet(source: bytes | Path)` (D4); cabeçalho na linha 1 normalizado ignorando colunas extras (P-10, pergunta 1), linhas totalmente vazias ignoradas preservando numeração real do Excel (pergunta 2), normalização de células numéricas/strings preservando zeros à esquerda e pontos (pergunta 3), nomes de testes da ficha mantidos com código em inglês (pergunta 4) e contrato v0 documentado em `docs/modules/registry.md` + `ARCHITECTURE.md` §6 (pergunta 5). Detalhes em `planos/CAD-02/plan.md`.
- 27/11 · S3 · Leitor do TXT conforme `planos/CAD-02/plan.md` (D2 a D5, confirmadas): `stat()` antes de ler e `OSError` sobe ao chamador; `0000000` não é repetição; `uv lock` no contêiner; funções pequenas por etapa da regra em `chart_txt.py`. As decisões S1 do `.xlsx` acima ficam substituídas (`DECISIONS.md` §11 T1).
- 27/11 · S3 · E8 considera só o caractere espaço depois da posição 78, conforme o texto da tabela ("texto que não é espaço"). E3b e E2 citam o valor sem os espaços das pontas.

## Fim de sessão
- [x] `hx verify` verde, ou a falha está descrita em "Falhou"
- [x] Nada quebrado nem pela metade na branch; commit feito
- [x] "Próxima ação" atualizada
- [x] Nenhum dado real nem segredo nas anotações
