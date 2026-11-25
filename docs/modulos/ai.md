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

# Gateway ao serviço de IA (IA-02)

`suggest_accounts()` é a única entrada para pedir à IA a conta de uma movimentação. Decisões em
`planos/IA-02/plan.md` (D1 a D8). Contrato `ai → classification`, versão 0 (`ARCHITECTURE.md` §6).

## Uso

```python
from lastro.ai.contracts import CandidateAccount, ClientDescription
from lastro.ai.service import suggest_accounts

sugestoes = suggest_accounts(
    [ClientDescription(firm_id, client_id, descricao, valor_centavos), ...],
    llm_client=adaptador,                      # implementa LLMClient
    accounts_by_client={(firm_id, client_id): (CandidateAccount("4.1.01", "Aluguel"), ...)},
    partners_by_client={(firm_id, client_id): ("NOME DO SOCIO",)},
)
```

- Devolve uma conta (código) ou `None` ("não sei") por item, na ordem da entrada.
- Agrupa por `(firm_id, client_id)`: **cada requisição leva um único cliente**; o mesmo
  `client_id` em dois escritórios gera duas requisições. Cada cliente passa por um `anonymize()`.
- Lista vazia devolve `[]` sem chamar o serviço. Cliente sem contas não é enviado: `None`.
- O nível de proteção de nomes é lido uma vez, antes de qualquer chamada. Nível inválido falha
  sem chamar o serviço.
- `amount_cents` só aceita `int` (centavos, com sinal). `float` e `bool` dão `TypeError`.

## O que vai na requisição (`LLMRequest`)

| Campo | Conteúdo |
|---|---|
| `entries[].description` | descrição já anonimizada (IA-01): sem CPF, CNPJ, agência, conta; nomes como `PESSOA_nnn`/`EMPRESA_nnn` |
| `entries[].amount_cents` | valor **exato** em centavos, com sinal (D8) |
| `accounts[].code` | código da conta, sem alteração |
| `accounts[].name` | nome da conta sem documentos, agência, conta e sem nomes de sócios cadastrados (D7, opção B) |

**Fica de fora:** id de escritório e de cliente, texto original, qualquer outro campo.

- **Sócio no nome da conta** vira o mesmo pseudônimo que ele tem nas descrições do lote
  (comparação palavra a palavra, sem caixa nem acento). Nome truncado do sócio no nome da conta
  não é reconhecido.
- **O plano de contas não deve levar nome de pessoa.** Nome de pessoa que não é sócio
  cadastrado (ex.: "Empréstimo Fulano") segue em claro no nome da conta: risco aceito em 25/11.
- **Valor exato aguarda confirmação** do líder (e do guardião de dados, quando houver) antes do
  piloto (pergunta 6 do plan). Se não aceitarem, troca-se por valor arredondado ou só o sinal.

## Resposta

- O serviço devolve uma resposta por descrição, na mesma ordem. Tamanho diferente →
  `InvalidLLMResponseError`, e nenhuma sugestão do pedido é usada.
- Cada código é conferido **em código** contra as contas daquele cliente; código fora da lista
  vira `None` (regra 5 do `AGENTS.md`).

## Armadilhas

- **Sem log do original:** o gateway não registra descrição, nome nem valor. Log do que vai à IA,
  se um dia existir, só com o texto já anonimizado (SECURITY.md §5, §8).
- **O teste prova o que chega à porta `LLMClient`.** O adaptador do provedor, quando existir,
  precisa de teste próprio de vazamento no nível HTTP.
- **Pseudônimo reinicia por cliente:** `PESSOA_001` de um cliente não tem relação com o de outro.
