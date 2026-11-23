---
title: "Decisão: processo e fichas"
description: Branch da verdade, identidade da dev, ondas, verificação completa e as regras das fichas, decididas em 18/11.
---

| Status | Data | Fonte |
|---|---|---|
| Aprovada (PROC-01 a 04, P-03); assumida (P-07, P-08) | 18/11/2026 | `docs/decisoes/DECISIONS.md`, seções 3 e 4 |

## Contexto

O harness (`tools/harness.py`) já cria branch, grava estado e evidência e confere a ficha. Faltava fechar de onde a branch sai, como o script sabe quem é a dev e como contar fichas por onda. O primeiro lote de fichas, a onda S1, expôs essas perguntas na revisão.

## Decisão

### Branch da verdade (PROC-01)

- A `developer` é a branch da verdade: as branches `feat/*` saem dela e os PRs de feature voltam para ela.
- A `main` fica para release e para este site.
- O código já faz isso: `BASE_REMOTA = "origin/developer"` em `tools/harness.py`, usada por `hx feature start`.

### Identidade da dev (PROC-02)

- A identidade é a variável de ambiente `HX_USUARIO`, com o handle do GitHub. É o mesmo valor do campo `responsavel` da ficha.
- O `hx feature start` recusa a ficha se `HX_USUARIO` não bater com `responsavel`.
- Sem `HX_USUARIO`, o código usa `git config user.name` como reserva (`tools/harness.py`, `_identidade_do_dev`).
- Não há opção de linha de comando para dizer quem é a dev: o parser do `hx` só aceita `<ID>` e `--sem-branch` no `feature start`.

### Onda e meta (PROC-03, P-07)

- Onda = semana do cronograma, de 1 a 4.
- A meta acumulada de fichas `passing` é 6, 18, 32 e 39 (ver [Cronograma](/lastro-lancamentos/visao/cronograma/)).
- Na contagem da onda 1, só entram as fichas novas: HAR-02 e HX-10, que já estavam `passing`, não contam (P-07, assumida).

### Verificação completa (PROC-04)

`verificacao` lista 100% dos testes da ficha. A evidência que o `hx feature verify` grava cobre a ficha inteira, critério a critério.

### Fichas encadeadas e WIP (P-03)

- Uma pessoa tem no máximo uma feature em andamento (WIP = 1). O `hx feature start` recusa se a dev tiver outra branch `feat/*` ainda fora da `developer`.
- Na distribuição, ninguém recebe na mesma onda duas fichas encadeadas por `depende_de`. Conta só a dependência **direta**.

### IDs e módulos (P-08 e HAR-04)

- ID da ficha: 2 a 4 letras maiúsculas, hífen e 2 dígitos (`^[A-Z]{2,4}-\d{2}$`). Por convenção, a sigla lembra o módulo (`ACE-01`, `CAD-03`, `NUC-01`; `HAR-nn` para o harness e `CI-nn` para a CI), mas o validador **não** confere a sigla: fichas como `DB-01`, `HX-11` e `ADM-01` são válidas.
- HX-10, HX-11 e HX-12 mantêm o ID, que é anterior à convenção (P-08, assumida).
- `modulo` é um dos 14 módulos de `src/lastro/` (ver [Arquitetura](/lastro-lancamentos/arquitetura/visao-geral/#módulos)), mais `harness`, `ci` e `web`, sempre com o nome da pasta, em inglês.

:::note[Implementado (HAR-04)]
O validador de `tools/harness.py` recusa, em `hx state`, `hx feature verify` e `hx feature start`: campo a mais na ficha, ID fora do padrão, módulo fora da lista de 17, `prioridade` fora de `must`/`should`/`could`, `onda` fora de 1 a 4, `essencial` diferente de `false`, `tipo_verificacao` diferente de `comando`, `bloqueada_por` preenchido fora de `blocked`, `responsavel` fora de `gitpages/src/data/equipe.ts` e nome de teste (depois de `::`) repetido entre fichas. Cada problema aparece como `<ID> (<campo>): ...`, com o código de saída 2. Essas regras só valem quando o `equipe.ts` existe na raiz. A regra das fichas encadeadas (P-03) fica com quem distribui as fichas: o validador não a confere.
:::

## Motivos registrados

| ID | Motivo, como no `DECISIONS.md` |
|---|---|
| PROC-01 | Alinha com o `hx feature start` |
| PROC-02 | Um só identificador entre ficha, harness e GitHub |
| PROC-03 | Planejamento até 07/12 |
| PROC-04 | A evidência do `hx feature verify` cobre a ficha inteira |
| P-03 | ACE-03 é a tela de listagem; as outras fichas só precisam da regra de acesso e da atribuição |
| P-08 | Renomear mexe em evidência e branch |

## Consequências

- O `AGENTS.md` da `developer` ainda mostra o `hx feature start` com uma opção de dono que não existe, e uma mensagem de erro do `harness.py` também. Os dois ficam desatualizados até a próxima PR do harness.
- Ficha com ID fora do padrão ou módulo desconhecido agora é recusada pelo `hx state` (HAR-04).

Fontes: `docs/decisoes/DECISIONS.md` (18/11/2026), seções 3 e 4; `tools/harness.py` (branch `developer`).
