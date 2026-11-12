---
title: Regras e revisão de PR
description: Regras de ouro, rubrica de revisão, regras de segurança e a regra dos centavos.
---

## Regras de ouro

- **Nenhum dado real no repositório:** extrato, CPF/CNPJ, nome de cliente ou escritório, chave de API. Ele é público.
- **Mexa só na pasta do seu módulo.** Precisa mudar um contrato? Abra issue `contrato:` e espere.
- **Nunca edite o estado de uma feature à mão.** Quem marca `passing` é o script, e a CI confere.
- **Testes antes do código.** Na sessão de implementação, o agente não altera os testes para fazê-los passar.
- **Decisão aberta (D-xx)?** Não decida: marque a feature como `blocked` e abra issue `decisao:`.
- **Falhou 2 vezes pelo mesmo motivo?** Pare, registre a causa no progress e peça ajuda.
- **Dinheiro sempre em centavos (inteiro). Nunca float.**
- **Um PR por feature**, pequeno, com a tabela critério → teste preenchida.

## A regra de ouro dos centavos

Todo valor monetário é um **inteiro em centavos**, do arquivo à planilha.

| Onde | Como |
|---|---|
| Código Python | `int` em centavos em todo o código; `Decimal` só na leitura do arquivo |
| Banco | BIGINT com sinal, em centavos |
| Contratos | `ExtratoLido` e `MovimentacaoLida` trazem valores e saldos em centavos |
| Conferência | Saldo calculado igual ao informado, por igualdade exata de inteiros |
| Exportação | Quantidade, entradas e saídas conferem em centavos com o extrato |

Exemplo fictício: R$ 1.250,00 é `125000`; um pagamento desse valor é `-125000`.

**Por quê:** um agente que usa decimal em vez de centavos faz o saldo deixar de fechar. Com a regra no `AGENTS.md`, o agente já começa sabendo.

## Revisão de PR

O PR segue o template `.github/pull_request_template.md`, que pede:

- a tabela critério → teste;
- a saída da verificação;
- o checklist de segurança.

Quem revisa:

1. Lê a ficha e confere a tabela critério → teste.
2. Roda `hx feature verify` na branch, sem confiar só na CI.
3. Preenche a rubrica (`docs/rubrica-revisao.md`).
4. Faz o merge por squash, com CI verde e aprovação.

Você não mescla o próprio PR. Um comentário que se repete em dois PRs vira check automático.

### Rubrica

A rubrica tem **6 itens, cada um de 0 a 2 pontos** (total 12).

| Item | Pontos |
|---|---|
| Correção | 0 a 2 |
| Verificação | 0 a 2 |
| Escopo | 0 a 2 |
| Item 4 | Pendente: não descrito nas fontes |
| Item 5 | Pendente: não descrito nas fontes |
| Item 6 | Pendente: não descrito nas fontes |

| Resultado | Quando |
|---|---|
| Aceitar | 9 ou mais de 12 e nenhum 0 em correção, verificação e escopo |
| Bloquear | 0 em correção ou verificação, ou dado real ou segredo no código |
| Pedir ajustes | Nos demais casos |

Exemplo: correção 2, verificação 2, escopo 2 e 5 dos 6 pontos restantes somam 11 de 12, e o PR é aceito.

A rubrica de 6 itens não muda sem decisão do grupo. Um PR que muda prompt ou modelo deve anexar o resultado do `verify` antes e depois (sugestão do estudo de avaliação com LLM).

## Regras de segurança

- Use só fixtures sintéticas. Recebeu um extrato real? Ele não entra no repositório: descreva a estrutura em `docs/bancos/` e gere uma fixture sintética equivalente.
- Chamadas a LLM passam somente por `src/lastro/ia/`, depois de `anonimizar()`.
- Rode `harness.py check-clean` antes do PR. Ele procura dado real, nomes proibidos e segredos.
- Chaves de API só em secrets (GitHub Actions ou provedor), nunca no código. Localmente, `.env` fora do git.
- O guardião de dados revisa os PRs que tocam em dado ou IA.

Fontes: Lastro: guia do harness v0.1; Fluxo de desenvolvimento do Lastro; Lastro — Arquitetura do Sistema, seções 5.2, 6 e 9; Banco de dados para o Lastro v1.0; Estudo de Avaliação com LLM.
