# HAR-04 · Alinhar validação de fichas e check-clean às decisões de 18/11

- Responsável: caio-nascime · Branch: `feat/HAR-04-alinhar-validacao-de-fichas-e-check-clea` · Início: 23/11/2026
- Ficha: `features/HAR-04.json` (estado e critérios ficam lá; não repita aqui)

<!--
Como preencher (agente, ao encerrar a sessão):
- REESCREVA as seções do topo: Objetivo, Próxima ação e Bloqueios e perguntas.
- ACRESCENTE, sem apagar o que já existe, em Feito, Rodei, Falhou e Decisões.
  Cada linha começa com a data (DD/MM) e a sessão, ex.: "- 14/11 · S2 · ...".
- Registre só o que realmente rodou. Sem dado real, nome de cliente ou segredo.
- Não escreva estado (passing etc.) aqui: ele fica na ficha, gravado pelo script.
-->

## Objetivo
O `hx state` (e `feature verify`/`start`) recusa ficha fora das regras de 18/11: campos exatos, ID, módulo, prioridade, onda, campos fixos, responsável da equipe e nome de teste único. O `hx check-clean` passa a achar CNPJ alfanumérico com dígito verificador válido.

## Próxima ação
Aguardar a revisão do PR #50 (base `developer`). Um humano marca D1 a D5 e a aprovação de plan e tasks em `planos/HAR-04/plan.md`; se pedirem ajuste, rodar `hx verify` e `hx feature verify HAR-04` de novo. Opcional: rodar `hx check-clean` com `LASTRO_NOMES_PROIBIDOS` definida e marcar o item no PR.

## Bloqueios e perguntas
- Conferir a regra "resto < 2 → 0" do DV alfanumérico na rotina oficial do Serpro (plan, D3); hoje vale a mesma regra do CNPJ numérico, que os testes usam.

## Feito
- 23/11 · S1 · Plan, tasks e recorte da ficha; testes em `tests/harness/test_validacao_lote.py` (commit 143faed).
- 23/11 · S2 · `tools/harness.py`: `validar_regras_do_projeto` (ligada em `_carregar_fichas_validas` só se existir `equipe.ts`), `ler_handles_da_equipe`, dicas na CORREÇÃO; `_CNPJ` e `cnpj_valido` aceitam letras (commit 21c342c).
- 23/11 · S2 · Imagem `lastro-dev` reconstruída (estava de 17/11, sem as dependências da NUC-01).
- 23/11 · S2 · `hx feature verify HAR-04` gravou `passing` (commit 4708dbc).
- 23/11 · S3 · Docs `decisoes/processo.md` e `fluxo/orquestracao.mdx`: nota "Planejado" trocada por "Implementado (HAR-04)" (commit 54c374f).
- 23/11 · S3 · Push da branch e PR #50 aberto para a `developer`, com o template preenchido.
- 23/11 · S3 · HX-11 e HX-12 marcadas `passing` à mão, com evidência real (ver Rodei e Decisões); registrado no PR #50.

## Rodei
- 23/11 · S2 · `pytest tests/harness -q` (venv local) → 167 passaram
- 23/11 · S2 · `ruff check .` → OK
- 23/11 · S2 · `hx state` na raiz real → código 0; `hx check-clean` → 0 achados
- 23/11 · S2 · `hx verify` (container, após rebuild) → ruff e pytest OK
- 23/11 · S2 · `hx feature verify HAR-04` → c1 a c7 e c9 OK, código 0
- 23/11 · S3 · `hx check-clean` → 0 achados (sem `LASTRO_NOMES_PROIBIDOS`: nomes pulados)
- 23/11 · S3 · 13 comandos da ficha HX-11 e 11 da HX-12 (pytest e ruff, venv local) → todos ok; evidência gravada com o commit 69cef1f3394f

## Falhou
- 23/11 · S2 · `hx verify` falhou com `No module named 'pydantic'`: imagem `lastro-dev` desatualizada. Resolvido com `docker compose --profile dev build dev`.
- 23/11 · S2 · `pytest -q` no venv local (Python 3.13, sem pydantic e testcontainers) falha em `tests/core`; não tem relação com a HAR-04.

## Decisões
- 23/11 · S1 · Regras de 18/11 só valem se `gitpages/src/data/equipe.ts` existir na raiz (opção A), para não mudar testes antigos (caio-nascime).
- 23/11 · S2 · Handle da equipe comparado sem diferenciar maiúsculas de minúsculas, como no GitHub.
- 23/11 · S3 · PR aberto contra a `developer` (base indicada nos docs do fluxo), não contra a `main`.
- 23/11 · S2 · `ruff format` não foi aplicado em `tools/harness.py`: o projeto não usa o formatador e o diff ficaria enorme.
- 23/11 · S3 · EXCEÇÃO à regra 2 do AGENTS.md: `estado` e `evidencia` de HX-11 e HX-12 editados à mão, autorizado por caio-nascime nesta sessão (features dele, concluídas e não encerradas; `hx feature verify` não serve porque exige `in_progress` e o WIP=1 impede o `start`). Vale só para essas duas fichas.

## Fim de sessão
- [x] `hx verify` verde, ou a falha está descrita em "Falhou"
- [x] Nada quebrado nem pela metade na branch; commit feito
- [x] "Próxima ação" atualizada
- [x] Nenhum dado real nem segredo nas anotações
