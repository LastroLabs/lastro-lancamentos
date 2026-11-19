---
title: Regras e revisão de PR
description: Regras de ouro, rubrica de revisão, regras de segurança e a regra dos centavos.
---

## Regras de ouro

- **Nenhum dado real no repositório:** extrato, CPF/CNPJ, nome de cliente ou escritório, chave de API. Ele é público.
- **Mexa só na pasta do seu módulo.** Precisa mudar um contrato? Abra issue `contrato:` e espere.
- **Nunca edite o estado de uma feature à mão.** Quem grava `in_progress`, `passing` e `regressed` é o `hx`.
- **Testes antes do código.** Na sessão de implementação, o agente não altera os testes para fazê-los passar.
- **Decisão pendente (D-xx ou P-xx)?** Não decida: abra issue `decisao:` e pegue outra feature. A ficha só vira `blocked` por PR do dono do harness (nenhum comando grava `blocked` ainda).
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

- a ficha, o progress e os RFs atendidos;
- a tabela critério → teste;
- o hash do commit "só testes" e o resultado de `git diff <hash> -- tests/`;
- as evidências: `hx verify`, `hx feature verify <ID>` e `hx check-clean` verdes;
- o checklist de segurança, de escopo e contratos, e o progress atualizado.

O PR de feature vai para a `developer`, nunca para a `main` (PROC-01).

### Antes de dar nota

Pela `docs/rubrica-revisao.md`, quem revisa gasta 5 minutos nisto:

1. Lê a ficha `features/<ID>.json` e o `progress/<ID>.md`.
2. Confere a tabela critério → teste: todo critério aponta para um teste?
3. Roda `git diff <hash> -- tests/` com o hash do commit "só testes". Vazio é o esperado.
4. Roda `hx feature verify <ID>` **na própria máquina**, na branch do PR. Não confia só na CI nem no relato do autor.
5. Passa os olhos no diff procurando dado real, nome de cliente ou escritório, e segredo.

### Rubrica

A rubrica tem **6 itens, cada um de 0 a 2 pontos** (total 12). O revisor dá a nota à mão e posta em um comentário do PR. Nenhum script soma a nota.

| Item | 0 | 1 | 2 |
|---|---|---|---|
| **Correção** | O comportamento não bate com o critério da ficha | Bate na maioria; falha em algum caso ou exemplo | Bate em todos os critérios, inclusive nos exemplos de entrada e saída da ficha |
| **Verificação** | Há critério sem teste, ou teste que não prova nada (passaria com qualquer código) | Todo critério tem teste, mas algum é fraco, ou o `git diff` dos testes não está vazio e não foi explicado | Todo critério tem teste real, escrito antes do código, e o `git diff` dos testes está vazio |
| **Escopo** | Mexeu em outro módulo, fez o que a ficha não pede, ou mudou contrato sem issue `contrato:` | Pequena sobra de escopo, explicada no PR | Só o que a ficha pede, na pasta do módulo |
| **Clareza** | Código ou mensagens de erro difíceis de entender; o revisor precisou adivinhar | Legível, com pontos confusos | Fácil de ler; erros no formato ERRO / MOTIVO / CORREÇÃO |
| **Segurança** | Dado real, segredo, ou LLM fora de `src/lastro/ia/` | Dúvida sobre algum ponto (por exemplo, um nome que parece real), ainda sem resposta | Nada sensível; o checklist de segurança do PR confere com o diff |
| **Documentação** | `progress/` desatualizado ou ausente | `progress/` em dia; falta registrar em `docs/modulos/` ou em `DECISIONS.md` | `progress/`, página do módulo e decisões em dia |

| Decisão | Quando |
|---|---|
| **Aceitar** | Total **≥ 9 de 12** e **nenhum 0** em Correção, Verificação ou Escopo |
| **Bloquear** | **0 em Correção ou em Verificação**, ou **qualquer dado real ou segredo**, mesmo que o total seja alto |
| **Pedir ajustes** | Qualquer outro caso |

Segurança é regra de bloqueio, não só nota: um PR com dado real é bloqueado mesmo com 12/12 nos outros itens. Se o dado real já foi publicado, siga a seção 9 do `docs/SECURITY.md` antes de qualquer outra coisa.

Ao pedir ajustes, o autor corrige e o revisor reavalia só os itens que estavam abaixo de 2.

Exemplo de comentário:

```text
Rubrica <ID>
- Correção: 2 (...)
- Verificação: 2 (...)
- Escopo: 2
- Clareza: 2
- Segurança: 2
- Documentação: 1 (falta registrar a decisão no DECISIONS.md)
Total: 11/12 → ACEITAR
```

### Regras de convivência

- **Quem revisa:** quem não escreveu o PR, de preferência em rodízio. O dono do módulo revisa mudanças de contrato.
- **Prazo:** resposta em até 24 h. Passou disso, o autor avisa no canal e a líder reatribui o revisor.
- **Tamanho:** 15 a 25 minutos de revisão. Se o PR exige muito mais, peça para dividir a ficha.
- **Ninguém aprova o próprio PR.**
- **Revisão sem rodar o `hx feature verify` não vale.** A CI confirma, mas não substitui.
- **Do comentário à regra:** o mesmo ajuste em dois PRs vira issue `harness:` para virar teste, check ou regra automática.

Um PR que muda prompt ou modelo deve anexar o resultado do `verify` antes e depois (sugestão do estudo de avaliação com LLM).

## Regras de segurança

- Use só fixtures sintéticas. CPF e CNPJ de teste em arquivo versionado têm dígito verificador inválido. Recebeu um extrato real? Ele não entra no repositório: descreva só a estrutura e gere uma fixture sintética equivalente.
- Chamadas a LLM passam somente por `src/lastro/ia/`, depois de `anonimizar()`.
- Rode `hx check-clean` antes do PR, com `LASTRO_NOMES_PROIBIDOS` definida. A CI roda o mesmo comando em todo push e PR (`.github/workflows/pr.yml`).
- Chaves de API só em secrets (GitHub Actions ou provedor), nunca no código. Localmente, `.env` fora do git.
- O guardião de dados revisa os PRs que tocam em dado ou IA.

Fontes: `docs/rubrica-revisao.md`, `.github/pull_request_template.md`, `.github/workflows/pr.yml`, `AGENTS.md` e `docs/SECURITY.md` (branch `developer`, 18/11/2026); `docs/decisoes/DECISIONS.md` (18/11/2026); Lastro — Arquitetura do Sistema, seções 5.2, 6 e 9; Estudo de Avaliação com LLM.
