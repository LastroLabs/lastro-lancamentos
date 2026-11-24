# Módulo `registry`: validação de CNPJ (CAD-01)

`src/lastro/registry/` reúne o domínio de cadastro do cliente (cliente, contas bancárias, sócios, plano de contas e configuração). A **CAD-01** entrega a validação e normalização pura de CNPJ numérico e alfanumérico (padrão julho/2026, IN RFB nº 2.229/2024), sem acesso a banco nem HTTP. Decisões em `planos/CAD-01/plan.md`.

## Contrato público (versão 0)

- **Função:** `validate_cnpj(cnpj: str) -> CnpjValidationResult` em `lastro.registry.service`
- **Tipo de retorno:** `CnpjValidationResult` (`@dataclass(frozen=True, slots=True)`) em `lastro.registry.contracts`

```python
from lastro.registry.service import validate_cnpj

result = validate_cnpj(raw_cnpj)
```

| Campo | Tipo | Semântica |
|---|---|---|
| `is_valid` | `bool` | `True` quando o formato e os dois dígitos verificadores passam; `False` caso contrário |
| `normalized` | `str \| None` | 14 caracteres ASCII maiúsculos, sem máscara, quando válido; `None` quando recusado |
| `error_message` | `str \| None` | `None` quando válido; mensagem oficial em português simples quando recusado |

### Mensagens oficiais

| Situação | `error_message` |
|---|---|
| Entrada vazia ou só com espaços | `"Informe o CNPJ do cliente."` |
| Tamanho errado, caractere fora do padrão, máscara mal posicionada, 14 caracteres iguais ou dígito verificador incorreto | `"O CNPJ informado não é válido. Confira os números."` |

> **Versionamento (v0):** qualquer mudança de campo, assinatura ou mensagem oficial deve avisar a responsável pela `CAD-03` (`RaissaOliveira19`), consumidora direta deste contrato.

## Regras de validação e normalização

- Remove espaços nas bordas (`.strip()`) antes de verificar se a entrada está vazia.
- Aceita apenas caracteres ASCII (`re.ASCII`), normalizando letras para maiúsculas:
  - sem máscara: `^[A-Z0-9]{12}[0-9]{2}$`
  - máscara oficial exata: `XX.XXX.XXX/XXXX-XX` (com letras/dígitos nas 12 primeiras posições e apenas dígitos nos 2 verificadores).
- Recusa sequências com todos os 14 caracteres idênticos (ex.: `00.000.000/0000-00`).
- Calcula os dois dígitos verificadores pelo Módulo 11 com `ord(char) - 48` (unificando numérico e alfanumérico), pesos `(5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)` e `(6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)`.

## Consumidores e impactos conhecidos

- **CAD-03 (consumidora direta, `not_started`):** a ficha `features/CAD-03.json` (critério `c2`, linha 35) está alinhada com `"O CNPJ informado não é válido. Confira os números."`. Ainda assim, ao implementar a `CAD-03`, consumir `result.error_message` diretamente em vez de duplicar a string.
- **DB-01 (`cliente.cnpj_normalizado`):** a persistência precisa aceitar 14 caracteres alfanuméricos em texto (`TEXT`), nunca inteiro nem restrição apenas de dígitos.
- **P-13 (status HTTP de dado inválido):** continua pendente em `docs/decisoes/DECISIONS.md`. Este contrato devolve apenas a mensagem de erro; a tradução para status HTTP (RFC 9457) pertence à camada `api/`.
- **`tools/harness.py` (`check-clean`):** a função `cnpj_valido` do harness é propositalmente separada de `src/lastro/` (o código de produção não importa `tools/`). A `HAR-04` trata a parte alfanumérica no harness; manter atenção para que as duas regras não divirjam.
- **Demais contratos de `registry`:** os contratos `registry → classification/export` seguem `[definir]` em `ARCHITECTURE.md` (seção 10).

## Armadilhas

- **Não commitar literais de CNPJ com DV válido:** em testes e exemplos escritos, gere o DV em tempo de execução ou use exemplos com DV inválido (`docs/SECURITY.md` §3).
- **Pontuação fora do lugar não é removida:** o validador não faz `re.sub` genérico de não-alfanuméricos para evitar aceitar caracteres inválidos (como `#`) ou máscaras quebradas.
- **Sem acoplamento com HTTP ou banco:** `src/lastro/registry/cnpj.py` é interno ao módulo; outros módulos devem importar apenas `lastro.registry.service` e `lastro.registry.contracts`.
