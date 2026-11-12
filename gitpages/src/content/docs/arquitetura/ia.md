---
title: IA
description: Gateway único, anonimização e o lugar da IA na classificação.
---

:::note[Status]
Recomendada, aguardando aprovação. A escolha de modelos está em aberto. Ver [Decisão: avaliação com LLM](/lastro-lancamentos/decisoes/avaliacao-llm/).
:::

A IA **sugere classificações e interpreta descrições**. Ela não calcula saldos nem decide a integridade financeira de um extrato: essas verificações são feitas por código determinístico. O contador sempre revisa.

## Gateway único

Toda chamada a LLM passa por um único módulo, `src/lastro/ia/`, que:

- anonimiza com `anonimizar()` antes de qualquer chamada;
- valida a saída por schema;
- aceita como resposta só as contas do plano do cliente;
- registra custo e versão de prompt.

Os provedores ficam atrás de uma interface (`ClassificadorLLM`), para trocar de modelo sem mexer no resto.

| Regra | Como é garantida |
|---|---|
| Só `ia/` importa SDK de provedor de LLM | Regra de dependência conferida pelo `harness.py verify` com `import-linter` |
| `validacao/` não importa `ia/` | Idem: a conferência de saldo nunca depende de modelo |
| Nada de CPF, CNPJ, agência ou conta na requisição | `anonimizar()` e um teste que falha se algum desses padrões sair (RF-SEG-03) |
| Saída fora do esquema ou conta inexistente | Rejeitada pelo gateway |

## O que é anonimizado

- **Sempre removido:** CPF, CNPJ, números de agência e de conta (RF-SEG-03).
- **Nomes de contrapartes:** dependem de D-03. Até a decisão, são trocados por pseudônimos, por exemplo `PESSOA_017`.
- **O que vai ao LLM:** só a descrição anonimizada, o valor e as contas candidatas.

A tabela de equivalências fica restrita. Se houver reversão, não se presume anonimato absoluto.

## Onde a IA entra na classificação

A IA é a **última camada**. Só recebe o que regras, histórico e parecidas não resolveram (RF-CLA-05).

| Camada | Quem resolve | Usa IA? |
|---|---|---|
| 1. Regras | Palavra-chave e tipo, com precedência documentada | Não |
| 2. Histórico | Contraparte normalizada e direção já aceitas pelo contador | Não |
| 3. Parecidas | Similaridade por trigramas (`pg_trgm`) no mesmo cliente | Não |
| 4. IA | Só o que sobrou, anonimizado | Sim |
| 5. Pergunta | Abaixo do limite de confiança (D-08), vira pergunta ao cliente | Não |

Cada chamada fica registrada com provedor, modelo, versão de prompt, latência e resultado sanitizado. Prompt bruto com dado pessoal não vai para os logs.

## Avaliação

- **Leitura, validação, conta sugerida e exportação:** medidas com código e gabarito sintético, em centavos.
- **Juiz LLM:** só para as perguntas ao cliente e a justificativa da conta. O juiz é de empresa diferente da do modelo que gera, e o prompt dele é versionado em `src/lastro/ia/`.
- **Nos testes:** provedor falso (sem custo e sem rede).
- **Conjunto fixo:** 40 a 60 casos, com cerca de 20% reservados como prova final.

## Foto e print

Fora do MVP (Should, D-01). Se entrar, será via modelo multimodal no mesmo gateway de IA, sempre com conferência de saldo.

Fontes: Lastro — Arquitetura do Sistema, seções 5.3, 5.4, 6 e 8; Banco de dados para o Lastro v1.0; Estudo de Avaliação com LLM; Documentação e Arquitetura do Projeto Contábil; Fluxo de desenvolvimento do Lastro.
