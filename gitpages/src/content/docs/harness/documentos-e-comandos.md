---
title: Documentos e comandos
description: Para que serve cada documento do repositório e como usar o harness no dia a dia.
---

O repositório é a memória do time e dos agentes (Claude Code, Codex, antigravity). Se algo não está escrito nele, o agente não sabe e a próxima pessoa também não. Por isso cada documento tem **um único trabalho e um único jeito de ser atualizado**.

## O fluxo de uma feature, em 7 passos

| Passo | O que você faz | Documento ou comando |
|---|---|---|
| 1 | Na reunião de segunda, assume uma feature (ex.: LEI-02) | `features/LEI-02.json` |
| 2 | Cria a branch e o registro de trabalho | `harness.py feature start LEI-02 --owner você` |
| 3 | Lê o contexto e escreve os testes primeiro (eles devem falhar) | `docs/modulos/`, `progress/`, `AGENTS.md` |
| 4 | Em sessão nova, o agente implementa sem editar os testes | `AGENTS.md` |
| 5 | Roda a verificação; só o script marca `passing` | `harness.py feature verify LEI-02` |
| 6 | Abre o PR com o template; outra pessoa revisa pela rubrica; a CI refaz a verificação | PR template, `rubrica-revisao.md` |
| 7 | Merge. O progress fica atualizado para quem pegar o próximo passo | `progress/LEI-02.md` |

Todo comando roda dentro do Docker, com o prefixo `docker compose run --rm dev`. O atalho `hx` equivale a `docker compose run --rm dev python tools/harness.py`.

## Os documentos do repositório

Os quatro primeiros você toca todo dia. Os demais, quando o assunto aparecer.

| Documento | Para que serve | Quem mexe | Como usar |
|---|---|---|---|
| `AGENTS.md` | Manual curto (até 100 linhas) que todo agente lê ao abrir uma sessão: comandos, regras e onde achar o resto. O `CLAUDE.md` só aponta para ele | Donos do harness, por PR | Você não precisa decorar. Se o agente errou por falta de regra, abra issue `harness:`; não escreva regra solta no chat |
| `features/<ID>.json` | Uma ficha por feature: o que entregar, critérios de aceite, comando de verificação, dependências e estado | Escopo e critérios: líder de produto e dono do módulo. Estado: só o script | Leia antes de começar. Critério errado ou ambíguo? PR corrigindo a ficha antes de codar |
| `progress/<ID>.md` | Diário da feature: objetivo, o que foi feito, o que rodou, o que falhou, decisões e próxima ação | Quem está com a feature; o agente preenche, você confere | Antes de parar o dia, deixe a próxima ação clara |
| PR template e rubrica | O template (`.github/pull_request_template.md`) pede a tabela critério → teste. A rubrica (`docs/rubrica-revisao.md`) tem 6 itens de 0 a 2 pontos | Template: donos do harness. Rubrica: quem revisa preenche | Ver [Regras e revisão de PR](/lastro-lancamentos/harness/regras/) |
| `docs/decisoes/DECISIONS.md` | Registro das decisões (D-01, D-02…) com contexto, opção escolhida e quem decidiu. Decisão em aberto aparece como aberta | Quem tem autoridade sobre o tema, por PR | Depende de decisão aberta? Marque `blocked` e abra issue `decisao:` |
| `docs/modulos/<modulo>.md` | Uma página por módulo (leitura, validação, classificação, perguntas, revisão, exportação): responsabilidade, contratos, armadilhas | Dono do módulo | Leia antes de mexer. Achou uma armadilha? Duas linhas no mesmo PR |
| `docs/bancos/<banco>.md` | Como cada banco formata o extrato (colunas, datas, sinais, casos estranhos). Só estrutura, nunca dados reais | Quem trabalha na leitura | Formato novo? Documente o padrão e gere uma fixture sintética equivalente |
| `docs/SECURITY.md` | Regras de dados do repositório público e descrição da anonimização e da checagem automática | Guardião de dados | Só fixtures sintéticas; LLM só por `src/lastro/ia/`, depois de `anonimizar()` |
| `layouts/dominio.yaml` | Colunas e regras do Excel de importação do Domínio. Marcado PROVISORIO até o layout oficial (D-05) | Módulo de exportação; a troca pelo oficial é decisão do líder de produto | Gere o Excel lendo este arquivo, nunca com colunas fixas no código |
| `tools/harness.py` | A mão do processo: um script comum (não é agente) que cria fichas, roda verificações e atualiza estados. Mesmo resultado em qualquer máquina | Donos do harness | Faltou comando ou deu erro confuso? Issue `harness:` |
| `.github/workflows/noturno.yml` | Rotina das 03:00 (Brasília): roda todos os E2E e reverifica as features `passing`. Se algo quebrou, abre issue | Donos do harness | De manhã, olhe as issues. Feature que voltou a falhar vira `regressed` e tem prioridade. Pode ser disparada à mão (`workflow_dispatch`) |

## Comandos do `tools/harness.py`

| Comando | O que faz |
|---|---|
| `init` | Prepara o ambiente e confere se tudo sobe (rode uma vez e depois de trocar de máquina) |
| `verify [--e2e]` | Roda lint, testes e regras de arquitetura; com `--e2e`, também as jornadas completas |
| `state` | Mostra o painel: quantas features em cada estado e quem está com o quê |
| `feature start <ID> --owner <você>` | Cria a branch, marca `in_progress` e cria o progress |
| `feature verify <ID>` | Roda os comandos da ficha; se tudo passar, marca `passing` |
| `feature progress <ID>` | Cria o progress de uma feature que não tem (uso excepcional) |
| `fixtures build [--check]` | Gera os extratos sintéticos e o gabarito; `--check` só confere se estão atualizados |
| `check-clean` | Procura dado real, nomes proibidos e segredos antes do PR |

O `feature start` é um script, não uma chamada ao agente: ele só cria arquivos e a branch. Depois você abre o agente, que lê esses arquivos.

### Sua primeira feature, em quatro comandos

No PowerShell, com o Docker ligado:

```text
git checkout main; git pull
hx init
hx feature start LEI-02 --owner seunome
hx feature verify LEI-02
```

## Estados de uma feature

| Estado | Significado |
|---|---|
| `not_started` | Ficha pronta, ainda sem início |
| `in_progress` | Alguém começou com `feature start` |
| `blocked` | Depende de decisão aberta (`bloqueada_por: D-xx`) |
| `passing` | O script rodou os comandos da ficha e todos passaram |
| `regressed` | Estava `passing` e o noturno detectou falha |

## Ainda a confirmar

O guia está na versão 0.1, sujeita a ajuste na primeira semana. Itens a confirmar na prática:

- a leitura do `AGENTS.md` por todos os agentes;
- o comando de instalação do uv;
- a proteção de branch no plano gratuito do GitHub.

Fontes: Lastro: guia do harness v0.1 (08/11/2026); Fluxo de desenvolvimento do Lastro.
