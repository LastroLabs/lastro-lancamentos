# Harness — contrato v0 do `hx`

O `hx` roda no host e só usa a biblioteca padrão do Python. Este documento registra o que outros módulos e fichas consomem dele: os comandos, o formato da ficha, a lista de nomes proibidos, as fixtures sintéticas e os códigos de saída. O contrato está em versão 0 (AGENTS.md, regra 11): mudou, abra issue `contrato:` e avise o dono do harness. Cada item cita o arquivo e a linha de onde foi tirado.

## Entrada

`tools/hx` procura `python3` e, se não achar, `python`; sem nenhum dos dois, sai com 1 e uma mensagem (`tools/hx:3-10`). Depois só repassa os argumentos para `tools/harness.py` (`tools/hx:11`). No PowerShell, o equivalente é `tools/hx.ps1`.

**Windows:** rode o `hx` pelo PowerShell (`. .\tools\hx.ps1`). No Git Bash, `python3` costuma ser o atalho da Microsoft Store: o `tools/hx` o encontra, mas ele não executa ("Python não foi encontrado"). Não rode `hx verify` nem `hx feature verify` de dentro do container `dev`: os dois chamam `docker compose run` e o container não tem a CLI do Docker ("Docker indisponível"). Só `hx check-clean` funciona lá dentro.

## Velocidade do `hx verify` (issue #93)

A suíte completa caiu de ~22 min para poucos minutos sem tirar teste (`planos/perf-93/plan.md`, `DECISIONS.md` §12):
- **Paralelo:** `pytest` roda em até 4 processos (`pytest-xdist`, `addopts` no `pyproject.toml`). Um arquivo ou um teste (`::`, como em cada critério do `hx feature verify`) roda em série. Para investigar uma falha em série: `pytest -n 0`. Regras para escrever teste seguro em paralelo: `CODING_STANDARDS.md`, seção 2.
- **Banco migrado:** as fixtures `migrated_database` e `head_database` copiam um banco-modelo já migrado (`CREATE DATABASE ... TEMPLATE`), criado uma vez por revisão e por processo (`tests/conftest.py`). Testes que sobem e descem migrações continuam usando `fresh_database`.
- **Um PostgreSQL por processo**, definido só em `tests/conftest.py` (`postgres_server`).
- **Front:** `web/node_modules` e a store do pnpm ficam no volume Docker `web-node-modules` (`docker-compose.yml`), não na pasta compartilhada. Para recomeçar do zero: `docker compose --profile dev down` e `docker volume rm <projeto>_web-node-modules` (o prefixo é o nome da pasta do repositório; ex.: `lastro_web-node-modules`). A pasta antiga `.pnpm-store/` na raiz do repositório (ignorada pelo Git) deixa de ser usada e pode ser apagada.
- **Imagem:** dependências Python com bytecode pré-compilado (`UV_COMPILE_BYTECODE=1` no `Dockerfile`). Mudou `pyproject.toml`, `uv.lock` ou `Dockerfile`? `docker compose --profile dev build dev`.

## Comandos

| Comando | O que faz | Origem |
|---|---|---|
| `hx state [--estado E]... [--atencao]` | Painel das fichas. `--estado` filtra e pode repetir; `--atencao` mostra só `blocked` e `regressed`. | `tools/harness.py:1474`, `:1477`, `:1483`, `:539`, `:563` |
| `hx check-clean` | Procura dado real e segredo; relata arquivo, linha e tipo, nunca o valor. | `tools/harness.py:1489`, `:800` |
| `hx verify` | Roda `ruff check .` e `pytest -q` no container Docker; os dois rodam mesmo que o primeiro falhe. Pytest sem teste coletado (código 5) conta como falha. | `tools/harness.py:1492`, `:820-821`, `:869` |
| `hx feature verify <ID>` | Roda os comandos de `verificacao` da ficha e grava estado e evidência. Só verifica fichas `in_progress`, `regressed` ou `passing`. | `tools/harness.py:1497`, `:909`, `:991` |
| `hx feature start <ID> [--sem-branch]` | Abre a feature: valida, pergunta se cria a branch a partir de `origin/developer`, cria o progress e passa a ficha a `in_progress`. Só inicia fichas `not_started` ou `regressed`, com todas as dependências `passing`. A identidade vem de `HX_USUARIO` ou de `git config user.name`. | `tools/harness.py:1502`, `:1507`, `:1062-1063`, `:1087-1088`, `:1118`, `:1142`, `:1265`, `:1329` |
| `hx fixtures build [--semente N] [--check]` | Gera `fixtures/` a partir da semente. Sem `--check`, apaga de `fixtures/` o que o gerador não produz, menos `.gitkeep`. Com `--check`, só compara com o disco e não grava nada. | `tools/harness.py:1517`, `:1529`, `:1533`, `:1369`, `:1439`, `:1448` |

## Ficha (`features/<ID>.json`)

Campos obrigatórios: `id`, `titulo`, `modulo`, `requisitos`, `prioridade`, `onda`, `essencial`, `estado`, `responsavel`, `depende_de`, `bloqueada_por`, `tipo_verificacao`, `criterios`, `verificacao` e `evidencia` (`tools/harness.py:164-180`).

- `id` segue o padrão `AAA-00`: 2 a 4 letras maiúsculas, hífen e 2 dígitos (`tools/harness.py:399`).
- `modulo` é um destes: `core`, `access`, `registry`, `uploads`, `parsing`, `validation`, `classification`, `questions`, `review`, `export`, `ai`, `observability`, `api`, `worker`, `harness`, `ci` ou `web` (`tools/harness.py:400-418`).
- `prioridade` é `must`, `should` ou `could`, e `onda` vai de 1 a 4 (`tools/harness.py:419-420`).
- `criterios` é uma lista com ao menos um critério, de `id` único (`tools/harness.py:277-287`).

O `estado` é um de `not_started`, `in_progress`, `passing`, `blocked` ou `regressed` (`tools/harness.py:163`). Regras por estado:

- `blocked` exige `bloqueada_por`; nos outros estados, `bloqueada_por` fica vazio (`tools/harness.py:331-332`, `:480-481`).
- `in_progress` exige `responsavel` (`tools/harness.py:333-334`).
- `passing` exige `evidencia`; `not_started` exige `evidencia` nula (`tools/harness.py:335-338`).

Só o `hx` muda o estado (AGENTS.md, regra 2). O `hx feature start` passa a ficha a `in_progress` (`tools/harness.py:1329`). O `hx feature verify` grava `passing` com a evidência (data, commit e resultados) quando tudo passa. Se uma ficha `passing` falhar, ela volta a `regressed` e a evidência antiga fica para auditoria (`tools/harness.py:1040-1049`).

## Nomes proibidos (`LASTRO_NOMES_PROIBIDOS`)

O `hx check-clean` lê os nomes proibidos da variável de ambiente `LASTRO_NOMES_PROIBIDOS`, com os nomes separados por `;` (`tools/harness.py:603`, `:683-686`). A lista nunca é versionada: ela existe só na máquina de cada dev e como segredo da CI, porque no Git revelaria os nomes dos pilotos (`docs/SECURITY.md:64`). Sem a variável, o comando avisa "verificação de nomes pulada (variável não definida)" em stderr e segue com as outras checagens (`tools/harness.py:604`, `:802-804`).

## Fixtures sintéticas

O gerador é `tools/fixtures_sinteticas.py`. `gerar_arquivos(semente)` é uma função pura, que devolve um mapa de caminho relativo a `fixtures/` para bytes; a mesma semente gera os mesmos bytes. A **semente padrão é 1** (`SEMENTE_PADRAO`). `--semente` aceita inteiro ≥ 0. Antes de gravar, o `hx fixtures build` aborta se alguma linha gerada tiver achado do `check-clean` (`_exigir_sem_documentos` em `tools/harness.py`, trava D7). O reduzido seguido da classificação forma uma sequência de 8 a 27 dígitos; quando ela vira CPF ou CNPJ válido, o gerador passa ao reduzido seguinte, com limite de tentativas (`_TENTATIVAS_DO_REDUZIDO`) para que a trava aborte, em vez de travar o build, se tudo for acusado.

Caminhos, todos relativos a `fixtures/` (`tools/harness.py:732`):

- `cadastro.json` (`_cadastro` em `tools/fixtures_sinteticas.py`);
- `planos/<cliente>.txt`: o plano de contas no formato TXT de 78 colunas, em UTF-8 com CRLF (HAR-05; formato em `docs/modulos/registry.md`, "Leitura do plano de contas em TXT");
- `ofx/<cliente>-<nn>.ofx` e `gabaritos/<cliente>-<nn>.json`, um par por conta bancária (`_ofx` e `_gabarito` em `tools/fixtures_sinteticas.py`).

Formato do c6, o que a CAD-05 e a IA-02 leem:

- **`cadastro.json`:** `semente` e `escritorios`. Cada escritório tem `id`, `usuarios` e `clientes`. Cada cliente tem `id`, `nome`, `responsavel`, `socios`, `plano`, `plano_txt` e `contas_bancarias` (`banco`, `apelido`, `ofx` e `gabarito`). Não traz CNPJ nem movimentações (`_cadastro` em `tools/fixtures_sinteticas.py`). No `plano`, cada conta tem `codigo` (com pontos, ex.: `1.1.01`), `classificacao` (o código sem pontos, ex.: `1101`), `reduzido` (7 dígitos entre `0000001` e `9999999`, único no cliente; `0000000` é recusado pela CAD-02), `nome`, `tipo` (`S` grupo, `A` analítica) e `transitoria`. O plano tem 10 grupos e 13 analíticas, com os grupos antes das contas abaixo deles; a transitória é a analítica `9.9.99` (`9999`), abaixo de `9` e `9.9` (`PLANO_BASE` em `tools/fixtures_sinteticas.py`). Só analíticas aparecem como `conta_correta` no gabarito.
- **Gabarito:** `cliente`, `banco`, `apelido`, `saldo_inicial_centavos`, `saldo_final_centavos` e `movimentacoes` (`_gabarito` em `tools/fixtures_sinteticas.py`). Cada movimentação tem `data`, `valor_centavos`, `descricao`, `id_transacao` e `conta_correta` (`_movimentacoes` no mesmo arquivo).

`cnpjs_dos_clientes(semente)` devolve o CNPJ válido de cada cliente (id → CNPJ sem máscara), e o primeiro é alfanumérico. Esses CNPJs só existem em tempo de execução e nunca são gravados em arquivo (`tools/fixtures_sinteticas.py:11-12`, `:150-170`).

Nos testes, a fixture de sessão `synthetic_fixtures_dir` grava numa pasta temporária os mesmos bytes da semente padrão (`tests/conftest.py:25-37`).

## Códigos de saída e erros

| Código | Quando | Origem |
|---|---|---|
| 0 | Deu certo. | `tools/harness.py:11` |
| 1 | Falha esperada: teste vermelho, achado do `check-clean`, `fixtures/` fora de dia no `--check`. | `tools/harness.py:11`, `:812`, `:1448-1455` |
| 2 | Erro de uso (o argparse aborta com 2) ou de ambiente (`HarnessErro`). | `tools/harness.py:11`, `:1544`, `:1547-1549` |

Todo erro de negócio sai em stderr, em três linhas (`tools/harness.py:33-47`):

```text
ERRO: o que aconteceu
MOTIVO: por que aconteceu
CORREÇÃO: o que fazer
```

Só o bloco `if __name__ == "__main__"` chama `sys.exit`; `main()` devolve o código, o que permite testar (`tools/harness.py:12`, `:1541-1555`).
