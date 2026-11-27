# HAR-05 · Gerar o plano de contas sintético em TXT, com grupos e analíticas, no lugar da planilha

- Responsável: RaissaOliveira19 · Branch: `feat/HAR-05-gerar-o-plano-de-contas-sintetico-em-txt` · Início: 27/11/2026
- Ficha: `features/HAR-05.json` (estado e critérios ficam lá; não repita aqui)

<!--
Como preencher (agente, ao encerrar a sessão):
- REESCREVA as seções do topo: Objetivo, Próxima ação, Bloqueios e perguntas.
- ACRESCENTE, sem apagar o que já existe, em Feito, Rodei, Falhou e Decisões.
  Cada linha começa com a data (DD/MM) e a sessão, ex.: "- 14/11 · S2 · ...".
- Registre só o que realmente rodou. Sem dado real, nome de cliente ou segredo.
- Não escreva estado (passing etc.) aqui: ele fica na ficha, gravado pelo script.
-->

## Objetivo
Substituir a planilha sintética do plano de contas por TXT de 78 colunas, com grupos e analíticas, preservando os gabaritos e a proteção contra documentos válidos.

## Próxima ação
Solicitar revisão do PR ao dono do harness; conferir a leitura dos TXT pela CAD-02 quando o PR dessa ficha estiver integrado à `developer`.

## Bloqueios e perguntas
- A responsável aprovou o plano, as tarefas e os testes em 27/11; a marcação das caixas do plano continua reservada a ela.
- A integração com a CAD-02 aguarda o PR #74, ainda aberto com mudanças solicitadas. `LASTRO_NOMES_PROIBIDOS` não está definida neste ambiente; o `check-clean` pulou apenas essa checagem.

## Feito
- 27/11 · S1 · A HAR-05 foi iniciada pelo harness; a branch foi criada manualmente a partir de `origin/developer` após a opção interativa ficar sem resposta.
- 27/11 · S1 · Plano e tarefas da HAR-05 preparados para revisão, sem escrever testes ou código de implementação.
- 27/11 · S1 · Raissa aprovou o plano e as tarefas, incluindo D1–D4, antes da escrita de testes.
- 27/11 · S1 · Raissa aprovou os testes e a exceção T12; testes e ajuste autorizado da HAR-03 registrados no commit `15d2468` antes do código.
- 27/11 · S1 · Gerador passou a emitir três planos TXT por semente, com 10 grupos e 13 analíticas por cliente, reduzidos independentes e trava de documentos preservada. Código e documentação no commit `06b5a85`.
- 27/11 · S1 · OFX e gabaritos da semente padrão preservados byte a byte em relação a `origin/developer` (8 arquivos); `git diff 15d2468 HEAD -- tests/` vazio.

## Rodei
- 27/11 · S1 · `python tools/harness.py feature start HAR-05` → ficha e progress iniciados, sem branch automática; `git switch -c feat/HAR-05-gerar-o-plano-de-contas-sintetico-em-txt` → branch criada.
- 27/11 · S1 · `python -m pytest tests/harness/test_fixtures_plano_txt.py -q` → 3 falhas esperadas antes da implementação; `python -m pytest tests/harness/test_fixtures_plano_txt.py tests/harness/test_fixtures.py -q` → 24 passaram depois.
- 27/11 · S1 · `python tools/harness.py feature verify HAR-03` → regressão esperada em c3/c6 antes do código; depois → 14 verificações OK. `python tools/harness.py feature verify HAR-05` → 3 falhas antes do código; depois → c1–c3 OK.
- 27/11 · S1 · `python tools/harness.py verify` → ruff e pytest OK; `python tools/harness.py fixtures build` → 12 arquivos; `python tools/harness.py fixtures build --check` → 12 iguais; `python tools/harness.py check-clean` → 0 achados, nomes pulados por variável ausente.

## Falhou
- 27/11 · S1 · A criação automática da branch não ocorreu porque o prompt interativo do harness recebeu resposta vazia; a branch foi criada manualmente.
- 27/11 · S1 · As falhas das fichas antes da implementação eram esperadas pelo roteiro HAR-05 e foram resolvidas sem editar `tests/` depois do commit `15d2468`.

## Decisões
- 27/11 · S1 · Usar a ficha HAR-05 e o roteiro `docs/refatoracoes/HAR-05.md` como escopo; nenhuma decisão técnica nova foi aprovada nesta sessão.
- 27/11 · S1 · Raissa aprovou as escolhas técnicas D1–D4 do plano via resposta nesta conversa.
- 27/11 · S1 · O sorteio de reduzidos usa `_Sorteio` separado e até 20 tentativas por conta; ao esgotar tentativas por documento, a trava D7 recusa o build antes da gravação.

## Fim de sessão
- [x] `hx verify` verde, ou a falha está descrita em "Falhou"
- [x] Nada quebrado nem pela metade na branch; commit feito
- [x] "Próxima ação" atualizada
- [x] Nenhum dado real nem segredo nas anotações
