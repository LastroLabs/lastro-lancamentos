# WEB-01 · Criar o ambiente do front-end: SPA React com rotas dos três papéis, cliente da API gerado e textos centralizados

- Responsável: jvsauma · Branch: `feat/WEB-01-criar-o-ambiente-do-front-end-spa-react` · Início: 23/11/2026
- Ficha: `features/WEB-01.json` (estado e critérios ficam lá; não repita aqui)

<!--
Como preencher (agente, ao encerrar a sessão):
- REESCREVA as seções do topo: Objetivo, Próxima ação, Bloqueios e perguntas.
- ACRESCENTE, sem apagar o que já existe, em Feito, Rodei, Falhou e Decisões.
  Cada linha começa com a data (DD/MM) e a sessão, ex.: "- 14/11 · S2 · ...".
- Registre só o que realmente rodou. Sem dado real, nome de cliente ou segredo.
- Não escreva estado (passing etc.) aqui: ele fica na ficha, gravado pelo script.
-->

## Objetivo
Entregar o projeto `web/` (React 19, TypeScript, Vite, pnpm, Biome, Vitest) com as rotas dos três papéis, o cliente da API gerado do OpenAPI e todos os textos de tela em `web/src/copy/`, conferidos pelo `docs/design/microcopy.md`.

## Próxima ação
1. Abrir o PR da ficha: c3 e c4 com `/api/v1/health` e `up`/`connected`; c5 incluindo `components/` e atributos (ver `planos/WEB-01/plan.md`, seção 1). A ficha ainda diz `/saude`, `no_ar` e `conectado`.
2. Commitar `features/WEB-01.json` (gravado pelo `hx feature verify`) e rodar `hx feature verify WEB-01` de novo, pois o merge de `developer` veio depois do commit da evidência.
3. `hx check-clean` e abrir o PR com o template de `.github/`.

## Bloqueios e perguntas
- A ficha ainda contradiz a NUC-01 em c3 e c4 (resposta já decidida no plan; falta o PR da ficha).
- O `tools/harness.py` trazido de `developer` exige Python 3.11+ (`from datetime import UTC`). Com o `python3` do sistema (3.10), `./tools/hx` falha. Foi preciso chamar o harness com o Python 3.14 de `~/.local/bin`.

## Feito
- 23/11 · S1 · `/planejar WEB-01`: `planos/WEB-01/plan.md` e `tasks.md` (7 tasks); 7 perguntas e D1–D6 respondidas e confirmadas por jvsauma.
- 23/11 · S2 · `git pull origin developer` (merge automático, sem conflito) na branch. No histórico já estão os commits de testes, implementação e testes de componente da WEB-01 (`46fd870`, `765ee4a`, `bb768d8`), feitos fora desta sessão.

## Rodei
- 23/11 · S2 · `git pull origin developer --no-rebase --no-edit` → merge feito, 11 arquivos, sem conflito
- 23/11 · S2 · `sh tools/hx verify` → falhou: `ImportError: cannot import name 'UTC'` (Python 3.10 do sistema)
- 23/11 · S2 · `~/.local/bin/python3.14 tools/harness.py verify` → ruff OK, pytest OK; Arquitetura e E2E pulados (não implementados); RESULTADO: OK

## Falhou
- 23/11 · S2 · `sh tools/hx verify` no Python 3.10 do sistema: o harness atualizado pelo merge precisa de 3.11 ou mais. Causa: `tools/harness.py` (HAR-04). O `tools/hx` ainda aceita "Python 3.10 ou superior" na mensagem.

## Decisões
- 23/11 · S1 · Node 24 com pnpm fixado pelo npm (D1), TanStack Router em código (D2), textos em JSON (D3), OpenAPI exportado por módulo Python em `src/lastro/api/` (D4), `fetch` injetado no lugar de MSW (D5), sem TanStack Query nem biblioteca de UI (D6). Detalhe em `planos/WEB-01/plan.md`.
- 23/11 · S1 · Testes Vitest em `web/tests/`; `/` é a página inicial; 404 sem link; c5 varre `components/` e atributos de texto.

## Fim de sessão
- [x] `hx verify` verde, ou a falha está descrita em "Falhou" (verde com o Python 3.14; falha no Python 3.10 descrita)
- [ ] Nada quebrado nem pela metade na branch; commit feito (falta commitar `features/WEB-01.json`, o merge e este arquivo; sem push)
- [x] "Próxima ação" atualizada
- [x] Nenhum dado real nem segredo nas anotações
