# Harness — contrato v0 do `hx`

O `hx` roda no host e só usa a biblioteca padrão do Python. Este documento registra o que outros módulos e fichas consomem dele: os comandos, o formato da ficha, a lista de nomes proibidos, as fixtures sintéticas e os códigos de saída. O contrato está em versão 0 (AGENTS.md, regra 11): mudou, abra issue `contrato:` e avise o dono do harness. Cada item cita o arquivo e a linha de onde foi tirado.

## Entrada

`tools/hx` procura `python3` e, se não achar, `python`; sem nenhum dos dois, sai com 1 e uma mensagem (`tools/hx:3-10`). Depois só repassa os argumentos para `tools/harness.py` (`tools/hx:11`). No PowerShell, o equivalente é `tools/hx.ps1`.

## Comandos

| Comando | O que faz | Origem |
|---|---|---|
| `hx state [--estado E]... [--atencao]` | Painel das fichas. `--estado` filtra e pode repetir; `--atencao` mostra só `blocked` e `regressed`. | `tools/harness.py:1485`, `:1488`, `:1494`, `:539`, `:563` |
| `hx check-clean` | Procura dado real e segredo; relata arquivo, linha e tipo, nunca o valor. | `tools/harness.py:1500`, `:800` |
| `hx verify` | Roda `ruff check .` e `pytest -q` no container Docker; os dois rodam mesmo que o primeiro falhe. Pytest sem teste coletado (código 5) conta como falha. | `tools/harness.py:1503`, `:820-821`, `:869` |
| `hx feature verify <ID>` | Roda os comandos de `verificacao` da ficha e grava estado e evidência. Só verifica fichas `in_progress`, `regressed` ou `passing`. | `tools/harness.py:1508`, `:909`, `:991` |
| `hx feature start <ID> [--sem-branch]` | Abre a feature: valida, pergunta se cria a branch a partir de `origin/developer`, cria o progress e passa a ficha a `in_progress`. Só inicia fichas `not_started` ou `regressed`, com todas as dependências `passing`. A identidade vem de `HX_USUARIO` ou de `git config user.name`. | `tools/harness.py:1513`, `:1518`, `:1062-1063`, `:1087-1088`, `:1118`, `:1142`, `:1265`, `:1329` |
| `hx fixtures build [--semente N] [--check]` | Gera `fixtures/` a partir da semente. Sem `--check`, apaga de `fixtures/` o que o gerador não produz, menos `.gitkeep`. Com `--check`, só compara com o disco e não grava nada. | `tools/harness.py:1528`, `:1540`, `:1544`, `:1369`, `:1449`, `:1459` |

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

O gerador é `tools/fixtures_sinteticas.py`. `gerar_arquivos(semente)` é uma função pura, que devolve um mapa de caminho relativo a `fixtures/` para bytes; a mesma semente gera os mesmos bytes (`tools/fixtures_sinteticas.py:3`, `:437`). A **semente padrão é 1** (`tools/fixtures_sinteticas.py:28`). `--semente` aceita inteiro ≥ 0 (`tools/harness.py:1372-1380`). Antes de gravar, o `hx fixtures build` aborta se alguma linha gerada tiver achado do `check-clean` (`tools/harness.py:1400-1401`, `:1472`).

Caminhos, todos relativos a `fixtures/` (`tools/harness.py:732`):

- `cadastro.json` (`tools/fixtures_sinteticas.py:440`);
- `planos/<cliente>.xlsx` (`tools/fixtures_sinteticas.py:237`);
- `ofx/<cliente>-<nn>.ofx` e `gabaritos/<cliente>-<nn>.json`, um par por conta bancária (`tools/fixtures_sinteticas.py:218-219`).

Formato do c6, o que a CAD-05 e a IA-02 leem:

- **`cadastro.json`:** `semente` e `escritorios`. Cada escritório tem `id`, `usuarios` e `clientes`. Cada cliente tem `id`, `nome`, `responsavel`, `socios`, `plano`, `plano_planilha` e `contas_bancarias` (`banco`, `apelido`, `ofx` e `gabarito`). Não traz CNPJ nem movimentações (`tools/fixtures_sinteticas.py:260-283`). No `plano`, cada conta tem `codigo`, `nome` e `transitoria`; a transitória é a `9.9.99` (`tools/fixtures_sinteticas.py:37`, `:232-235`).
- **Gabarito:** `cliente`, `banco`, `apelido`, `saldo_inicial_centavos`, `saldo_final_centavos` e `movimentacoes` (`tools/fixtures_sinteticas.py:420-429`). Cada movimentação tem `data`, `valor_centavos`, `descricao`, `id_transacao` e `conta_correta` (`tools/fixtures_sinteticas.py:190-196`).

`cnpjs_dos_clientes(semente)` devolve o CNPJ válido de cada cliente (id → CNPJ sem máscara), e o primeiro é alfanumérico. Esses CNPJs só existem em tempo de execução e nunca são gravados em arquivo (`tools/fixtures_sinteticas.py:11-12`, `:150-170`).

Nos testes, a fixture de sessão `synthetic_fixtures_dir` grava numa pasta temporária os mesmos bytes da semente padrão (`tests/conftest.py:25-37`).

## Códigos de saída e erros

| Código | Quando | Origem |
|---|---|---|
| 0 | Deu certo. | `tools/harness.py:11` |
| 1 | Falha esperada: teste vermelho, achado do `check-clean`, `fixtures/` fora de dia no `--check`. | `tools/harness.py:11`, `:812`, `:1459-1466` |
| 2 | Erro de uso (o argparse aborta com 2) ou de ambiente (`HarnessErro`), como `fixtures` existir como arquivo (em `fixtures build` e `--check`). | `tools/harness.py:11`, `:1555`, `:1558-1560`, `:1390-1397`, `:1455` |

Todo erro de negócio sai em stderr, em três linhas (`tools/harness.py:33-47`):

```text
ERRO: o que aconteceu
MOTIVO: por que aconteceu
CORREÇÃO: o que fazer
```

Só o bloco `if __name__ == "__main__"` chama `sys.exit`; `main()` devolve o código, o que permite testar (`tools/harness.py:12`, `:1552-1566`).
