---
title: O ritmo da semana
description: Sete momentos e uma única reunião.
---

A semana tem **sete momentos e uma única reunião**. O planejamento é na segunda (45 min) e o resto é assíncrono. Sexta não tem reunião.

| Momento | Quem | Quando | Duração | Saída |
|---|---|---|---|---|
| A · Preparar | Donos do harness | Domingo à noite ou segunda cedo | 30 a 45 min | Features da semana prontas e decisões fechadas |
| B · Planejar | Time todo | Segunda | 45 min | Cada pessoa com uma feature e um responsável gravado na ficha |
| C · Começar | Quem pegou a feature | Logo após o planejamento | 5 min de setup | Branch criada, progress aberto, testes escritos e falhando |
| D · Desenvolver | Quem pegou a feature | Durante a semana | 1 a 2 sessões | Implementação passando e progress atualizado |
| E · Entregar | Quem pegou a feature | Quando os testes passam | 15 a 20 min | PR aberto com todas as evidências |
| F · Revisar | Outra pessoa e a CI | Em até 24 h | 15 a 25 min | Feature `passing` na main |
| G · Fechar | Donos do harness | Domingo | 30 min | Painel da semana e lições viradas em regra |

## A · Preparar

- Rodar `hx state` e olhar as issues do noturno. Feature `regressed` entra primeiro.
- Escolher as features pela meta de `passing` e pela ordem de dependência.
- Revisar os `features/*.json`: critérios verificáveis e `depende_de` preenchido.
- Atualizar o `DECISIONS.md`. Uma decisão aberta que trava uma feature a deixa `blocked` e fora da sprint.
- Contratos novos congelados pelo dono B antes da segunda.
- Tudo em um PR de preparação, mesclado antes da reunião.

## B · Planejar

- 0 a 5 min: painel do `hx state` projetado.
- 5 a 15 min: só as decisões abertas que travam alguém hoje.
- 15 a 35 min: cada pessoa escolhe uma feature e lê a ficha em voz alta. Critério errado? Fala agora.
- 35 a 45 min: riscos e dependências cruzadas.
- WIP=1: ninguém com duas features em andamento.
- O líder faz um commit preenchendo `responsavel`. Sem isso, não dá para iniciar.

## C · Começar

- `hx feature start LEI-02 --owner voce` cria a branch, marca `in_progress` e cria o progress.
- Ler a ficha, a página do módulo e as decisões citadas (10 min).
- Escrever os testes primeiro, a partir dos critérios. Eles devem falhar.
- Commitar os testes sozinhos, para provar que vieram antes do código.
- Abrir uma sessão nova do agente para implementar, sem editar os testes.

## D · Desenvolver

- Commits pequenos, só na pasta do seu módulo. `hx verify` com frequência.
- Ao parar o dia, escrever a próxima ação no progress.
- Precisa de contrato novo? Issue `contrato:`. Precisa de decisão? Issue `decisao:` e feature `blocked`.
- Falhou duas vezes pelo mesmo motivo? Pare, registre a causa e peça ajuda.
- Passou de 2 sessões? Avise: feature grande vira duas fichas.

## E · Entregar

- `hx verify --e2e`, `hx feature verify LEI-02` e `hx check-clean`.
- Fechar o progress: feito, rodei, falhou, decisão, próxima ação.
- Abrir o PR com o template, incluindo a tabela critério → teste.
- Pedir revisão. Você não mescla o próprio PR.
- Só depois de abrir o PR, iniciar a próxima feature.

## F · Revisar

- Ler a ficha e conferir a tabela critério → teste.
- Rodar `hx feature verify` na branch, sem confiar só na CI.
- Preencher a rubrica: aceitar, pedir ajustes ou bloquear.
- Comentário que se repete em dois PRs vira check automático.
- Merge por squash, com CI verde e aprovação.

## G · Fechar

- `hx state` comparado com a meta acumulada.
- Abaixo da meta: aplicar o rebaixamento combinado. As 4 funcionalidades essenciais não saem.
- Limpeza: branches mortas, progress concluídos, `qualidade.md`.
- Erro repetido da semana vira check, teste ou regra no `AGENTS.md`.
- Registrar decisões em `DECISIONS.md` e alimentar o próximo momento A.

`hx` é o atalho para `docker compose run --rm dev python tools/harness.py`.

Fonte: Fluxo de desenvolvimento do Lastro, seção 04.
