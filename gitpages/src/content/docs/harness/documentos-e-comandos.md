---
title: Documentos e comandos
description: Para que serve cada documento do repositório e os comandos reais do hx.
---

O repositório é a memória do time e dos agentes (Claude Code, Codex, antigravity). Se algo não está escrito nele, o agente não sabe e a próxima pessoa também não. Por isso cada documento tem **um único trabalho e um único jeito de ser atualizado**.

O passo a passo de uma feature, com o comando de cada passo, está em [Orquestração](/lastro-lancamentos/fluxo/orquestracao/). Esta página é a referência: o que cada documento faz e o que cada comando aceita.

Tudo o que esta página afirma sobre o `hx` foi conferido no código da branch `developer` (`tools/harness.py`, `tools/hx`, `tools/hx.ps1`).

## Onde cada coisa roda

- **O `hx` roda no host**, com o Python da sua máquina (3.10 ou superior). `tools/hx` (Linux e macOS) e `tools/hx.ps1` (PowerShell) só chamam `python tools/harness.py`.
- **Só o ruff e o pytest rodam no contêiner `dev`**, pelo `docker compose run --rm -T dev`. Quem faz isso são o `hx verify` e o `hx feature verify`, que exigem o Docker ligado.
- `hx state`, `hx check-clean` e `hx feature start` não usam Docker.

Como carregar o atalho:

```text
# Linux e macOS
./tools/hx --help

# PowerShell (o ponto inicial é obrigatório)
. .\tools\hx.ps1
hx --help
```

Antes do primeiro `feature start`, defina quem você é com o seu handle do GitHub, o mesmo do campo `responsavel` da ficha (PROC-02):

```text
export HX_USUARIO=seu-handle          # Linux e macOS
$env:HX_USUARIO = "seu-handle"        # PowerShell
```

Sem `HX_USUARIO`, o `hx` usa o `git config user.name` como reserva.

## Comandos do `hx`

Tirados do parser de `tools/harness.py` (`_criar_parser`). Opção que não está aqui não existe.

| Comando | O que faz | Status |
|---|---|---|
| `hx state` | Lista as fichas de `features/` com estado, responsável, prioridade e título, mais a linha Resumo. Falha com ERRO se alguma ficha for inválida | Implementado |
| `hx state --estado <ESTADO>` | Mostra só as fichas desse estado; pode repetir a opção. A linha Resumo continua contando todas | Implementado |
| `hx state --atencao` | Mostra só as fichas `blocked` e `regressed`, ou "Nada pede atenção." | Implementado |
| `hx check-clean` | Procura CPF e CNPJ com dígito verificador válido, chaves de API, tokens do GitHub, chave privada, atribuições de segredo e, se `LASTRO_NOMES_PROIBIDOS` estiver definida, os nomes da lista. Mostra arquivo, linha e tipo, nunca o valor | Implementado |
| `hx verify` | Roda `ruff check .` e `pytest -q` no contêiner `dev`. Os passos "Arquitetura" e "E2E" aparecem como PULADO | Implementado (parcial) |
| `hx feature start <ID>` | Confere a ficha e abre a feature: cria a branch `feat/<ID>-<slug>` a partir de `origin/developer`, cria `progress/<ID>.md`, marca `in_progress`, faz o commit e o push | Implementado |
| `hx feature start <ID> --sem-branch` | Igual, mas não cria branch nem commita: só muda a ficha e cria o progress no seu disco | Implementado |
| `hx feature verify <ID>` | Roda cada comando da `verificacao` da ficha no contêiner. Tudo verde: grava `passing` e a evidência (data, commit, resultado por critério). Algo falhou numa ficha `passing`: grava `regressed` | Implementado |
| `hx fixtures build [--check]` | Gerar as fixtures sintéticas e o gabarito; `--check` confere se estão em dia | Planejado: ficha HAR-03 (em revisão) |
| `hx verify --e2e` | Rodar as jornadas de ponta a ponta | Planejado, sem ficha |
| Checagem de arquitetura no `hx verify` | Conferir as regras de dependência entre módulos com `import-linter` | Planejado, sem ficha |

Comandos do guia v0.1 que **não existem** no código: `init`, `feature progress` e a opção de dono no `feature start` (a identidade vem de `HX_USUARIO`).

### O que o `hx feature start` confere, nesta ordem

1. A ficha existe e todas as fichas são válidas.
2. `HX_USUARIO` é igual ao `responsavel` da ficha.
3. O estado é `not_started` ou `regressed`.
4. Todas as fichas de `depende_de` estão `passing`.
5. Você não tem outra branch `feat/*` fora da `developer` (WIP = 1).
6. `git fetch origin` funciona e não existe `feat/<ID>-*` no origin.
7. A árvore de trabalho está limpa.

Em terminal interativo, ele pergunta antes de criar a branch (`[s/N]`).

**Regra do slug da branch:** o título da ficha em minúsculas, sem acento, com tudo que não é letra ou número trocado por `-`, cortado em 40 caracteres. Exemplo: a ficha HAR-02 virou `feat/HAR-02-filtrar-hx-state-por-estado-e-resumir-so`.

### O que o `hx feature verify` exige

- O estado é `in_progress`, `regressed` ou `passing`.
- A árvore de trabalho está limpa, porque a evidência guarda o commit.
- O Docker está ligado.
- Cada comando da ficha é `pytest` (com `-q`, `-x` ou `-k`) ou `ruff check <caminho>`; qualquer outro é recusado.

Depois de rodar, faça commit da ficha: o script grava o arquivo, mas não commita.

### Mensagens de erro

Todo erro do `hx` sai no formato ERRO / MOTIVO / CORREÇÃO, com código de saída diferente de 0.

## Os documentos do repositório

Os quatro primeiros você toca todo dia. Os demais, quando o assunto aparecer. A coluna "Existe?" foi conferida na `developer` em 18/11/2026.

| Documento | Para que serve | Quem mexe | Existe? |
|---|---|---|---|
| `AGENTS.md` | Manual curto (até 100 linhas) que todo agente lê ao abrir uma sessão: comandos, regras e onde achar o resto. O `CLAUDE.md` só aponta para ele | Donos do harness, por PR | Sim |
| `features/<ID>.json` | Uma ficha por feature: o que entregar, critérios com exemplo, comandos de verificação, dependências e estado | Escopo e critérios: líder e dono do módulo. Estado e evidência: só o `hx` | Sim |
| `progress/<ID>.md` | Diário da feature: objetivo, próxima ação, bloqueios, feito, rodei, falhou, decisões. Nasce do `hx feature start` a partir de `docs/templates/progress.md` | Quem está com a feature; o agente preenche ao encerrar a sessão | Sim |
| `planos/<ID>/plan.md` e `planos/<ID>/tasks.md` | Avaliação da ficha, decisões a confirmar e as tasks (T1 é sempre escrever os testes). Gerados pelo comando `/planejar <ID>` do Claude Code (`.claude/commands/planejar.md`) | O agente gera; só um humano marca o plan como aprovado | Sim |
| PR template e rubrica | O template (`.github/pull_request_template.md`) pede a tabela critério → teste. A rubrica (`docs/rubrica-revisao.md`) tem 6 itens de 0 a 2 pontos | Template: donos do harness. Rubrica: quem revisa | Sim. Ver [Regras e revisão de PR](/lastro-lancamentos/harness/regras/) |
| `docs/decisoes/DECISIONS.md` | Registro das decisões: ID, data, status, decisão, motivo e fichas afetadas | A líder decide; registro por PR | Vazio na `developer`; o conteúdo de 18/11 está na branch `fichas/onda-s1`, ainda não mesclada |
| `docs/SECURITY.md` | Regras de dados do repositório público, anonimização e checagem automática | Guardião de dados | Sim |
| `docs/templates/` | Modelos de ficha, progress, plan e tasks | Donos do harness | Sim |
| `docs/requisitos/requisitos_lastro.json` | Os 85 RFs como dados, fonte das fichas | Líder | Só na branch `fichas/onda-s1` |
| `tools/harness.py` | O script do processo (não é agente): valida fichas, abre features, roda verificações e grava estados. Mesmo resultado em qualquer máquina | Donos do harness | Sim |
| `.github/workflows/pr.yml` | Roda `hx verify` e `hx check-clean` em todo push e todo PR | Donos do harness | Sim |
| `docs/qualidade.md` | Registro de qualidade da semana | Donos do harness | Arquivo vazio |

:::note[Planejado]
Estes documentos aparecem no guia v0.1, mas **ainda não existem** no repositório:

- `docs/modulos/<modulo>.md`: uma página por módulo, com responsabilidade, contratos e armadilhas. Sem ficha.
- `docs/bancos/<banco>.md`: como cada banco formata o extrato, só estrutura. Nasce com a primeira ficha de leitura (EP-04).
- `layouts/dominio.yaml`: colunas do Excel do Domínio, marcado PROVISORIO (D-05). Nasce com a ficha de exportação (EP-12).
- `.github/workflows/noturno.yml`: rotina das 03:00 que reverificaria as fichas `passing`. Sem ficha. Hoje só o `hx feature verify` grava `regressed`.
:::

## Estados de uma feature

Os cinco estados que o validador aceita (`ESTADOS` em `tools/harness.py`):

| Estado | Significado | Quem grava |
|---|---|---|
| `not_started` | Ficha pronta, ainda sem início | Quem cria a ficha |
| `in_progress` | A dev abriu a feature | `hx feature start` |
| `passing` | Todos os comandos da ficha passaram; a evidência foi gravada | `hx feature verify` |
| `regressed` | Estava `passing` e um novo `hx feature verify` falhou | `hx feature verify` |
| `blocked` | Depende de decisão pendente; exige `bloqueada_por` preenchido | Nenhum comando ainda (ver abaixo) |

O diagrama com os gatilhos de cada transição está em [Orquestração](/lastro-lancamentos/fluxo/orquestracao/#máquina-de-estados).

:::note[Planejado]
Nenhum comando do `hx` grava `blocked` nem tira uma ficha de `blocked`. Hoje isso é um PR na ficha feito pelo dono do harness (AGENTS.md, regra 2). O `hx` recusa iniciar ou verificar uma ficha `blocked`. Sem ficha.
:::

Fontes: `tools/harness.py`, `tools/hx`, `tools/hx.ps1`, `AGENTS.md`, `.claude/commands/planejar.md`, `.github/workflows/pr.yml` e `docs/templates/` (branch `developer`, 18/11/2026); `docs/decisoes/DECISIONS.md` (branch `fichas/onda-s1`).
