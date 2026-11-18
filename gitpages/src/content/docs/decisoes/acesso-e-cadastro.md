---
title: "Decisão: acesso e cadastro"
description: Status HTTP de recusa, cadastro de cliente pelo chefe e as suposições do plano de contas, decididos em 18/11.
---

| Status | Data | Fonte |
|---|---|---|
| Aprovada (P-01, P-02, P-02a); assumida (P-10, P-11); pendente (P-09, P-13) | 18/11/2026 | `docs/decisoes/DECISIONS.md`, seção 4 |

## Contexto

As fichas de acesso (ACE) e cadastro (CAD) da onda S1 precisavam dizer o que um cliente HTTP vê quando o acesso é negado e quem pode cadastrar cliente. Dois RFs se contradiziam:

- o RF-CAD-01 dizia que o contador cadastra;
- o RF-AUT-03 diz que só o chefe cadastra.

## Decisão

### Status HTTP de recusa (P-01)

| Situação | Status | Corpo |
|---|---|---|
| Sem sessão, ou com sessão encerrada | **401** | Mensagem pedindo para entrar |
| Com sessão, mas o papel não permite (ex.: contador tentando cadastrar cliente) | **403** | Mensagem dizendo que só o chefe pode |
| Recurso de outra carteira, de outro escritório ou inexistente | **404** | **Idêntico** ao de um recurso inexistente, inclusive em rotas que alteram dados |

O 404 com corpo idêntico impede descobrir se um cliente de outro escritório existe.

### Cadastro de cliente pelo chefe (P-02 e P-02a)

- **Só o chefe cadastra cliente.** Um contador sozinho no escritório é o próprio chefe.
- O RF-CAD-01 é relido assim:
  - requisito: "o chefe deve poder cadastrar um cliente com nome e CNPJ";
  - critério: "o cliente aparece no escritório depois de salvo e, atribuído, na carteira do contador".
- A releitura já está nos [Requisitos v0.2](/lastro-lancamentos/visao/requisitos/#rf-cad-01), com a nota "Ajustado em 18/11". Não leva o selo AJUSTADO, que marca só o que mudou na v0.2.

### Plano de contas (P-10 e P-11, assumidas)

- A planilha do plano tem cabeçalho `código` e `nome` na linha 1. É uma suposição, a confirmar com os pilotos.
- Uma nova carga do plano **substitui** o anterior.
- Se a conta transitória não estiver no plano novo, o cliente fica sem transitória.

## Pendentes

| ID | Pergunta | Onde aparece |
|---|---|---|
| P-09 | O chefe edita o cadastro de um cliente (contas, plano, transitória, sócios) e gera link, mesmo sem estar atribuído? | CAD-04 a CAD-07, ACE-05 |
| P-13 | Recusa por dado inválido (CNPJ inválido, nome vazio, conta fora do plano): 400 ou 422? | As fichas usam `[definir P-13]` |

## Consequências

- As fichas de acesso e cadastro (em revisão) trazem um critério de isolamento entre escritórios (ESC-1 × ESC-2) que espera 404 com corpo idêntico.
- Enquanto a P-13 estiver pendente, a recusa por dado inválido aparece nas fichas como `[definir P-13]`.

Fichas afetadas (em revisão): ACE-01 a ACE-05, CAD-02 a CAD-07, HAR-03. Ver [Rastreabilidade](/lastro-lancamentos/requisitos/rastreabilidade/).

Fonte: `docs/decisoes/DECISIONS.md` (18/11/2026), seção 4.

## Relação com a modelagem

As entidades [MEMBRO](/lastro-lancamentos/modelagem/entidades/#membro), [CLIENTE](/lastro-lancamentos/modelagem/entidades/#cliente), [PLANO_CONTAS](/lastro-lancamentos/modelagem/entidades/#plano_contas) e [CONTA_CONTABIL](/lastro-lancamentos/modelagem/entidades/#conta_contabil) incorporam os efeitos de P-01/P-02/P-02a e das suposições P-10/P-11. P-09 e P-13 permanecem pendentes na [especificação das operações](/lastro-lancamentos/modelagem/modelo-fisico/).
