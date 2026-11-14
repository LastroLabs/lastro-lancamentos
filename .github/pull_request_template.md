## Feature
- Ficha: `features/<ID>.json` · Progress: `progress/<ID>.md`
- Requisitos atendidos: RF-...
- O que muda (1 a 3 linhas):

## Critério → teste
| Critério da ficha | Teste que prova |
|---|---|
| c1: ... | `tests/...::test_...` |

## Testes antes do código
- Commit só de testes: `<hash>`
- `git diff <hash> -- tests/`:  [ ] vazio  [ ] mudou (explique abaixo; a ficha foi alterada neste PR?)

## Evidências
- [ ] `hx verify` verde
- [ ] `hx feature verify <ID>` verde
- [ ] `hx check-clean` verde (com `LASTRO_NOMES_PROIBIDOS` definida)

Resumo da saída do `feature verify` (sem dado real):

```text
(cole aqui)
```

## Segurança (docs/SECURITY.md)
- [ ] Nenhum dado real, nome de cliente ou escritório, nem segredo (inclusive em print e log)
- [ ] Fixtures sintéticas, CPF/CNPJ de teste com dígito verificador inválido
- [ ] LLM só por `src/lastro/ia/`, depois de `anonimizar()` (ou: não se aplica)

## Escopo e contratos
- [ ] Mexi só na pasta do meu módulo (ou: explique)
- [ ] Contrato mudou? Issue `contrato:` nº __ (ou: não)
- [ ] Depende de decisão aberta (D-xx)? (ou: não)
- [ ] Não editei o `estado` da ficha à mão (o `passing` veio do `feature verify`)

## Progress
- [ ] `progress/<ID>.md` atualizado (feito, rodei, falhou, decisões, próxima ação)

<!--
Revisor: use docs/rubrica-revisao.md e poste a nota em um comentário.
Aceitar com 9 ou mais de 12 e nenhum 0 em Correção, Verificação e Escopo.
Bloquear se houver dado real, segredo, ou 0 em Correção ou Verificação.
-->