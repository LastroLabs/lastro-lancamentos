# Módulo `ai`: anonimização antes da IA (IA-01)

`src/lastro/ai/` é o único lugar que chama um LLM (ARQ-06). Antes de qualquer envio, o texto
passa por `anonymize()`. Os documentos antigos chamam essa função de `anonimizar()`; no código o
nome é em inglês (CODING_STANDARDS §1). Decisões em `planos/IA-01/plan.md`.

## Uso

```python
from lastro.ai.service import anonymize

anonymize(descricoes_do_cliente, partners=nomes_dos_socios)
```

- Recebe as descrições **de um cliente** e devolve na mesma ordem.
- O pseudônimo (`PESSOA_nnn`, `EMPRESA_nnn`) é estável **dentro da chamada**. Duas chamadas
  podem dar números diferentes para o mesmo nome: mande o lote do cliente de uma vez (IA-02, c3).
- `partners`: nomes dos sócios cadastrados. Nome truncado no extrato (um é prefixo do outro, com
  6+ caracteres) recebe o pseudônimo do sócio.

## O que sai e o que fica

| Entrada | Saída | Níveis |
|---|---|---|
| CPF (com, sem ou com máscara parcial `***.123.456-**`) | `[CPF]` | todos |
| CNPJ numérico ou alfanumérico, DV certo ou errado | `[CNPJ]` | todos |
| `AG 1234`, `AGENCIA:0001` | `[AGENCIA]` | todos |
| `C/C 56789-0`, `CC:1122-3`, `CONTA 98765-4` | `[CONTA]` | todos |
| Contraparte (pessoa ou empresa) | `PESSOA_nnn` ou `EMPRESA_nnn` | `estrito`, `pessoas_protegidas` |
| Palavra de atividade (`POSTO`, `FARMACIA`) | em claro | só `pessoas_protegidas` |
| Palavra de operação, número, data, valor | em claro | todos |

## Configuração

| Variável | Valores | Padrão |
|---|---|---|
| `NAME_PROTECTION_LEVEL` | `estrito`, `pessoas_protegidas`, `desligado` | `estrito` (D-03) |

Valor desconhecido faz o `create_app()` falhar com "Nível de proteção de nomes inválido: ...".
A API não sobe sem proteção de nomes.

## Listas (`src/lastro/ai/preservation_lists.yaml`)

- `operacao`: ficam em claro. Fonte é documento público (BCB, Planalto, gov.br) onde a palavra
  aparece inteira, com data de acesso.
- `atividade`: em claro só no nível intermediário. Fonte é a subclasse CNAE 2.3 que tem a palavra
  (singular ou plural) na descrição ou nas observações, conferida na API do IBGE.
- `conflito`: palavra de atividade que também é prenome no Censo 2010 (API de nomes do IBGE).
  Nunca fica em claro.
- `revisado`: handle de quem conferiu a fonte, ou `pendente`.

Para incluir palavra: confira a fonte, escreva-a em maiúsculas sem acento, procure-a na API de
nomes do IBGE (se aparecer, vai para `conflito`) e rode
`pytest tests/ai/test_anonimizar.py -q`.

## Armadilhas

- **Contraparte é o que sobra.** Toda palavra que não está em `operacao` (nem é número, data,
  valor ou marcador) vira parte de um nome. Palavra de extrato que falta na lista (ex.: `DEB`) é
  escondida junto com o nome: piora a classificação, não a privacidade. Corrija na lista.
- **Nome igual a palavra de operação sai em claro** (ex.: o prenome `TED`). Risco aceito no plan.
- **Pessoa ou empresa:** empresa quando há sufixo societário (`LTDA`, `SA`, `S/A`, `EIRELI`,
  `SLU`, `CIA`) ou palavra de atividade. `ME`, `MEI`, `EPP` e `EI` saem do nome e não decidem.
  Se o mesmo nome aparece sozinho em outra descrição do lote, ele é pessoa em todas.
- **Palavra colada** (`POSTOTESTE`) nunca casa com a lista: vira pseudônimo inteiro.
- **Sem log:** este módulo não registra o texto original. Log do que vai à IA só com o texto já
  anonimizado (SECURITY.md §5).
