# Módulo `ci`: sync das fichas com o Project (HX-11)

`tools/project_sync.py` espelha `features/*.json` no Project da organização: um issue
`<ID>: <título>` por ficha, com coluna (campo `Status`), responsável e bloqueios.
O workflow, o Environment `project-sync` e o agendamento são da **HX-12** (seção Workflow).

## Comando

```
python tools/project_sync.py --origem developer [--dry-run]
python tools/project_sync.py --origem agendada  [--dry-run]
```

- `--origem developer` (push em `developer`): lê `features/` e faz tudo: cria o issue que falta,
  atualiza o título, avança a coluna, reconcilia responsável e bloqueios, fecha e reabre.
  É a **única** origem que cria issue.
- `--origem agendada` (schedule, ~15 min): **não lê `features/`**. Consulta pela API as branches
  `feat/<ID>-*` e seus PRs e só move a coluna de cards em A FAZER, FAZENDO ou EM REVISÃO.
- `--dry-run`: lista as mudanças e não escreve nada. Use no primeiro uso.

Códigos de saída: 0 = ok · 2 = erro de ambiente ou da API (mensagem ERRO/MOTIVO/CORREÇÃO).

## Variáveis

| Variável | Para quê |
|---|---|
| `GH_TOKEN` | token do GitHub App (gerado na HX-12; nunca é impresso) |
| `GITHUB_REPOSITORY` | `dono/repo` dos issues (o Actions já define) |
| `PROJECT_NUMBER` | número do Project (`vars.PROJECT_NUMBER`) |
| `PROJECT_ORG` | organização do Project; padrão `LastroLabs` |

Pré-requisito fora do repositório: um GitHub App instalado na organização com escrita em Issues
e Projects. Ver a seção do workflow abaixo.

## Workflow (HX-12)

`.github/workflows/project-sync.yml` roda o script em dois jobs, ambos no Environment `project-sync`:

| Gatilho | Job | Comando |
|---|---|---|
| push em `developer` | `sync-developer` | `python3 tools/project_sync.py --origem developer` |
| schedule `*/15 * * * *` | `sync-agendada` | `python3 tools/project_sync.py --origem agendada` |

Configuração no GitHub (fora do repositório, conferida por um segundo dono do `.github/`):

| Nome | Tipo | Onde |
|---|---|---|
| `APP_PRIVATE_KEY` | **segredo** | só no Environment `project-sync` (nunca no repositório) |
| `APP_CLIENT_ID` | variável (não é segredo) | repositório |
| `PROJECT_NUMBER` | variável | repositório |
| `PROJECT_SYNC_DRY_RUN` | variável | repositório; `true` acrescenta `--dry-run` |

- O Environment `project-sync` fica restrito às branches `main` e `developer`.
- Só a action `create-github-app-token` lê a chave. O script recebe só o `GH_TOKEN` de curta
  duração (mascarado e revogado no fim do job). Segredo nunca entra em `run:` nem em `env:`.
- Sem gatilho de PR nem `workflow_dispatch`, e nenhum checkout tem `ref:`.
- Primeiro uso: `PROJECT_SYNC_DRY_RUN=true`; depois de ler o log, um humano troca para `false`.

Notas:

- O schedule roda o YAML e o script **da branch padrão**: até o merge developer→main, a execução
  agendada não existe.
- `concurrency` usa o grupo fixo `project-sync` sem cancelar o run em andamento. O GitHub guarda
  um só run pendente por grupo: um run novo substitui o pendente (um push em developer pendente
  pode ser trocado por um agendado). O modo developer é idempotente; o próximo push recupera.
- Em repositório público, o GitHub desativa o agendamento após 60 dias sem atividade.

## Colunas

Campo `Status` com 5 opções: `A FAZER`, `FAZENDO`, `EM REVISÃO`, `FINALIZADA`, `REGREDIU`.

| Estado da ficha | Coluna |
|---|---|
| `not_started` | A FAZER |
| `in_progress` | FAZENDO |
| `passing` | FINALIZADA (fecha o issue) |
| `regressed` | REGREDIU (reabre o issue) |
| `blocked` | não move (o bloqueio nativo do issue já aparece) |

- **developer só avança** (A FAZER < FAZENDO < EM REVISÃO < FINALIZADA). Exceções: `regressed`
  vai para REGREDIU e `passing` vai para FINALIZADA, inclusive vindo de REGREDIU. Com ficha
  `in_progress`, card em REGREDIU ou FINALIZADA fica onde está.
- **agendada**: branch sem PR com card em A FAZER → FAZENDO; PR aberto → EM REVISÃO; PR fechado
  sem merge tira de EM REVISÃO (→ FAZENDO); PR com merge não é tocado. Com mais de um PR vale o
  mais recente. FINALIZADA e REGREDIU só mudam em developer. Branch sem card só gera aviso.

## Regras e armadilhas

- O issue casa com a ficha pelo título exato `^<ID>: ` (`HX-2: ...` não casa com `HX-20`).
- Responsável e bloqueios ficam **exatamente** iguais à ficha: o que sobra no GitHub é removido.
  Login inexistente: issue sem responsável e `AVISO` no log.
- Bloqueio usa o campo numérico `id` do issue, não o `number` (API de issue dependencies).
- Ficha apagada não apaga issue: ele continua como está e o log avisa.
- O script **nunca** escreve em `features/` e nunca roda código de branch de feature com segredo.
- Os testes (`tests/ci/test_project_sync.py`) usam uma API falsa em memória; nenhum chama a rede.
