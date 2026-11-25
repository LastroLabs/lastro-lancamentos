# Registry — esquema da DB-02

A revisão Alembic `0003` acrescenta `plano_contas`, `conta_contabil`, `conta_bancaria` e `socio`. Cada tabela usa a chave primária `(escritorio_id, cliente_id, id)` e uma FK composta para `cliente`. A coluna `id` recebe UUID gerado pelo banco.

`plano_contas` pertence a um cliente, tem versão positiva e única por cliente, e registra o membro do mesmo escritório que importou o plano. `conta_contabil` pertence a uma versão do plano do mesmo cliente; a conta pai precisa estar na mesma versão. O código contábil é texto e único apenas dentro daquela versão. `conta_bancaria` guarda o código do banco como texto e só referencia uma conta contábil do próprio cliente. `socio` guarda nome e nome normalizado.

`cliente.plano_atual_id` aponta para um plano do próprio cliente. As contas transitória, de entrada de sócio e de saída de sócio só podem apontar para contas desse plano. A troca do plano exige limpar ou trocar uma conta configurada que não exista no plano novo na mesma operação. Uma conta configurada não pode permanecer quando o plano atual é nulo. A DB-02 não implementa a carga de planilha nem a escolha dessas contas pela API.

O downgrade da `0003` remove as quatro colunas de configuração e as quatro tabelas, preservando as tabelas e os registros da DB-01. Ele elimina os dados próprios da DB-02; deve ser executado apenas conforme o procedimento de migração do ambiente.

As políticas RLS serão criadas na NUC-03. A DB-02 garante integridade referencial, mas o uso com dados de piloto depende da conclusão da NUC-03, conforme `docs/SECURITY.md` §8.

## Leitura de planilha do plano de contas (CAD-02, contrato v0)

A **CAD-02** (`RF-CAD-03`) entrega a leitura e validação pura de planilhas `.xlsx` de plano de contas em `src/lastro/registry/`, sem acesso a banco nem HTTP. A implementação interna fica em `src/lastro/registry/chart_spreadsheet.py` e é exposta apenas via `service.py` e `contracts.py`. Decisões registradas em `planos/CAD-02/plan.md`.

### Contrato público (versão 0)

- **Função:** `read_chart_of_accounts_spreadsheet(source: bytes | Path) -> ChartSpreadsheetResult` em `lastro.registry.service`
- **Tipos de retorno:** `ChartAccountEntry` e `ChartSpreadsheetResult` (`@dataclass(frozen=True, slots=True)`) em `lastro.registry.contracts`

```python
from pathlib import Path

from lastro.registry.service import read_chart_of_accounts_spreadsheet

result = read_chart_of_accounts_spreadsheet(Path("plano.xlsx"))
```

| Tipo | Campo | Tipo Python | Semântica |
|---|---|---|---|
| `ChartAccountEntry` | `code` | `str` | Código da conta em texto normalizado (preserva zeros à esquerda e pontos) |
| `ChartAccountEntry` | `name` | `str` | Nome da conta sem espaços nas bordas |
| `ChartSpreadsheetResult` | `accounts` | `tuple[ChartAccountEntry, ...]` | Contas válidas aceitas, na ordem exata das linhas da planilha |
| `ChartSpreadsheetResult` | `errors` | `tuple[str, ...]` | Mensagens em português simples para linhas inválidas, códigos repetidos ou recusa inteira |

### Mensagens oficiais

| Situação | Mensagem | `accounts` |
|---|---|---|
| Arquivo não-`.xlsx`, texto renomeado, vazio, ZIP inválido/corrompido ou acima de 20 MiB | `"Este arquivo não é uma planilha. Envie um arquivo .xlsx."` | `()` |
| Linha 1 ausente ou sem as colunas `código` e `nome` | `"A planilha precisa ter as colunas 'código' e 'nome' na primeira linha."` | `()` |
| Apenas cabeçalho ou apenas linhas totalmente vazias após o cabeçalho | `"A planilha não tem nenhuma conta."` | `()` |
| Linha `n` com nome preenchido e código vazio (ou só espaços) | `"Linha {n}: falta o código da conta."` | Demais linhas válidas |
| Linha `n` com código preenchido e nome vazio (ou só espaços) | `"Linha {n}: falta o nome da conta."` | Demais linhas válidas |
| Código já aceito anteriormente na linha `primeira` | `"Linha {n}: o código {codigo} já apareceu na linha {primeira}."` | Primeira ocorrência e demais linhas válidas |

### Regras, limites e suposições

- **Leitura segura:** usa `openpyxl.load_workbook(..., read_only=True, data_only=True)` sempre sobre a primeira aba (`worksheets[0]`), com fechamento garantido em `finally`. Valida o conteúdo real do arquivo (não confia na extensão) e aplica limite padrão de **20 MiB** (`MAX_SPREADSHEET_BYTES`, alinhado à D-06).
- **Cabeçalho (P-10):** supõe cabeçalho na linha 1 com `código` e `nome`, aceitando variações de caixa, acento e espaços nas bordas, colunas em qualquer ordem e colunas extras ignoradas. Caso os pilotos tragam planilhas com cabeçalho em outra linha ou outros nomes de coluna, a detecção isolada em `_locate_header_columns` deverá evoluir com aviso aos consumidores.
- **Normalização de células:** strings recebem `.strip()` preservando zeros à esquerda e pontos (`"01.01"` permanece `"01.01"`); `int` vira `str(value)`; `float` finito sem parte fracionária (`205.0`) remove `.0` (`"205"`).
- **Linhas vazias:** linhas com código e nome vazios (ou só espaços) são ignoradas preservando o número real da linha do Excel nas mensagens de erro. Planilha cujas linhas de dados são todas inválidas devolve `accounts == ()` e todos os erros linha a linha (sem trocar pela mensagem de planilha vazia).

### Impacto para consumidores (`CAD-05` e `api/`)

- **CAD-05 (consumidora direta):** chama `read_chart_of_accounts_spreadsheet(source)` (aceitando `bytes` de upload HTTP ou `Path`), persiste as contas válidas quando aplicável e reaproveita `result.errors` sem duplicar strings.
- **Camada `api/` (`P-13`):** o contrato nunca lança exceção de negócio nem define código HTTP; a tradução de recusa para status HTTP e RFC 9457 pertence à `api/`.
