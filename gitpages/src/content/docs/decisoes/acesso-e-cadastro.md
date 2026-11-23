---
title: "Decisão: acesso e cadastro"
description: Status HTTP de recusa, cadastro de cliente pelo chefe, acesso do chefe só aos clientes atribuídos a ele e as suposições do plano de contas, decididos em 18/11 e 22/11.
---

| Status | Data | Fonte |
|---|---|---|
| Aprovada (P-01, P-02, P-02a); assumida (P-10, P-11); pendente (P-13) | 18/11/2026 | `docs/decisoes/DECISIONS.md`, seção 4 |
| Aprovada (P-09) | 22/11/2026 | `docs/decisoes/DECISIONS.md`, seção 4 |

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

### O chefe vê a lista; só o responsável acessa (P-09, 22/11)

- **Lista:** o chefe vê todos os clientes do escritório, só com `id`, nome, CNPJ e responsável ativo (ou "sem responsável"). Contas, plano, transitória, sócios, links, extratos e movimentações não aparecem na lista. O contador vê só a própria carteira.
- **Acessar** é só do **responsável ativo**, seja contador ou chefe. Acessar inclui abrir o cliente, ler o cadastro, alterar, gerar ou invalidar link e, no futuro, revisar e exportar.
- O chefe pode **atribuir um cliente a si mesmo**. No escritório de uma pessoa só, o chefe atende os próprios clientes (P-02). Cliente sem responsável não é acessado por ninguém até ser atribuído.
- A **gestão de atribuição** (atribuir, consultar o responsável e reatribuir) só exige ser chefe do mesmo escritório, sem ser o responsável.
- A lista de contadores (`GET /api/v1/contadores`) passa a trazer também o chefe, para ele poder se escolher como responsável.

Ordem das checagens ao acessar um cliente:

| Ordem | Situação | Status | Corpo |
|---|---|---|---|
| 1 | Sem sessão | **401** | Mensagem pedindo para entrar |
| 2 | Cliente inexistente ou de outro escritório | **404** | Idêntico ao de inexistente |
| 3 | O usuário é o responsável ativo | permitido | — |
| 4 | O usuário é chefe do mesmo escritório | **403** | "Atribua este cliente a você para fazer isso.", sem dado do cliente |
| 5 | Qualquer outro caso (contador de outra carteira) | **404** | Idêntico ao de inexistente |

O 403 e o 404 saem antes de validar o corpo do pedido, para a recusa não vazar por erro de validação. O 403 do passo 4 é a única exceção à P-01: o chefe já vê o cliente na lista, então não há o que esconder.

### Plano de contas (P-10 e P-11, assumidas)

- A planilha do plano tem cabeçalho `código` e `nome` na linha 1. É uma suposição, a confirmar com os pilotos.
- Uma nova carga do plano **substitui** o anterior.
- Se a conta transitória não estiver no plano novo, o cliente fica sem transitória.

## Pendentes

| ID | Pergunta | Onde aparece |
|---|---|---|
| P-13 | Recusa por dado inválido (CNPJ inválido, nome vazio, conta fora do plano): 400 ou 422? | As fichas usam `[definir P-13]` |

## Consequências

- As fichas de acesso e cadastro (em revisão) trazem um critério de isolamento entre escritórios (ESC-1 × ESC-2) que espera 404 com corpo idêntico.
- Enquanto a P-13 estiver pendente, a recusa por dado inválido aparece nas fichas como `[definir P-13]`.
- Pela P-09, CAD-04 a CAD-07 e ACE-05 ganham um critério com o chefe não atribuído (403) e o chefe atribuído (permitido). NUC-02, ACE-02, ACE-03, ACE-04 e DB-01 passam a aceitar o chefe como responsável.

Fichas afetadas (em revisão): ACE-01 a ACE-05, CAD-02 a CAD-07, HAR-03, NUC-02, DB-01. Ver [Rastreabilidade](/lastro-lancamentos/requisitos/rastreabilidade/).

Fonte: `docs/decisoes/DECISIONS.md` (18/11/2026), seção 4.

## Relação com a modelagem

As entidades [MEMBRO](/lastro-lancamentos/modelagem/entidades/#membro), [CLIENTE](/lastro-lancamentos/modelagem/entidades/#cliente), [PLANO_CONTAS](/lastro-lancamentos/modelagem/entidades/#plano_contas) e [CONTA_CONTABIL](/lastro-lancamentos/modelagem/entidades/#conta_contabil) incorporam os efeitos de P-01/P-02/P-02a/P-09 e das suposições P-10/P-11. P-13 permanece pendente na [especificação das operações](/lastro-lancamentos/modelagem/modelo-fisico/).
