# Lastro — rubrica de revisão de PR (v0.1, 13/11/2026)

Leia ao revisar um PR. O autor também deve ler antes de abrir o PR: é o critério que será cobrado.

A rubrica **não é gerada por script**. O revisor dá a nota à mão e posta em um comentário do PR. Os 6 itens e as faixas abaixo são uma proposta inicial: ajuste na auditoria semanal.

## Antes de dar nota (5 minutos)

1. Leia a ficha `features/<ID>.json` e o `progress/<ID>.md`.
2. Confira a tabela **critério → teste** do PR: todo critério da ficha aponta para um teste?
3. Confira o hash do commit "só testes" e rode `git diff <hash> -- tests/`. Vazio é o esperado.
4. Rode `hx feature verify <ID>` **na sua máquina**, na branch do PR. Não confie só na CI nem no relato do autor.
5. Passe os olhos no diff procurando dado real, nome de cliente ou escritório, e segredo.

## A nota

Cada item vale **0, 1 ou 2**. Total máximo: 12.

| Item | 0 | 1 | 2 |
|---|---|---|---|
| **Correção** | O comportamento não bate com o critério da ficha. | Bate na maioria; falha em algum caso ou exemplo. | Bate em todos os critérios, inclusive nos exemplos de entrada e saída da ficha. |
| **Verificação** | Há critério sem teste, ou teste que não prova nada (passaria com qualquer código). | Todo critério tem teste, mas algum é fraco, ou o `git diff` dos testes não está vazio e não foi explicado. | Todo critério tem teste real, escrito antes do código, e o `git diff` dos testes está vazio. |
| **Escopo** | Mexeu em outro módulo, fez o que a ficha não pede, ou mudou contrato sem issue `contrato:`. | Pequena sobra de escopo, explicada no PR. | Só o que a ficha pede, na pasta do módulo. |
| **Clareza** | Código ou mensagens de erro difíceis de entender; o revisor precisou adivinhar. | Legível, com pontos confusos. | Fácil de ler; erros no formato ERRO / MOTIVO / CORREÇÃO. |
| **Segurança** | Dado real, segredo, ou LLM fora de `src/lastro/ia/`. | Dúvida sobre algum ponto (por exemplo, um nome que parece real), ainda sem resposta. | Nada sensível; o checklist de segurança do PR confere com o diff. |
| **Documentação** | `progress/` desatualizado ou ausente. | `progress/` em dia; falta registrar em `docs/modulos/` ou em `DECISIONS.md`. | `progress/`, página do módulo e decisões em dia. |

## A decisão

| Decisão | Quando |
|---|---|
| **Aceitar** | Total **≥ 9 de 12** e **nenhum 0** em Correção, Verificação ou Escopo. |
| **Bloquear** | **0 em Correção ou em Verificação**, ou **qualquer dado real ou segredo**, mesmo que o total seja alto. |
| **Pedir ajustes** | Qualquer outro caso. |

Segurança é regra de bloqueio, não só nota: um PR com dado real é bloqueado com 12/12 nos outros itens. Se o dado real já foi publicado (push ou PR aberto), siga a seção 9 do `docs/SECURITY.md`, antes de qualquer outra coisa.

Ao **pedir ajustes**, o autor corrige e o revisor reavalia só os itens que estavam abaixo de 2.

## Como postar

Um comentário de revisão no PR, com a justificativa curta de cada nota abaixo de 2. Use o botão do GitHub (Approve ou Request changes) para a decisão.

```text
Rubrica <ID>
- Correção: 2 (...)
- Verificação: 2 (...)
- Escopo: 2
- Clareza: 2
- Segurança: 2
- Documentação: 1 (falta a armadilha em docs/modulos/)
Total: 11/12 → ACEITAR
```

Todo comentário de justificativa deve ser **específico**: arquivo e linha, ou o critério que falhou. "Melhorar o código" não é revisão.

## Regras de convivência

- **Quem revisa:** quem não escreveu o PR, de preferência em rodízio. O dono do módulo revisa mudanças de contrato.
- **Prazo:** responder em até 24 h. Passou disso, o autor avisa no canal e o líder reatribui o revisor.
- **Tamanho da revisão:** 15 a 25 minutos. Se o PR exige muito mais, ele é grande demais: peça para dividir a ficha.
- **Ninguém aprova o próprio PR.** Se a proteção da main não garantir isso, vale como acordo do time.
- **Revisão sem rodar o `feature verify` não vale.** A CI confirma, mas não substitui.

## Do comentário à regra

Se o mesmo ajuste aparece em **dois PRs** (por exemplo, "faltou teste do caso vazio"), ele sai da rubrica humana: abra uma issue `harness:` para virar teste, check ou regra automática. É assim que a revisão fica mais curta com o tempo.

## Manutenção

- Auditoria semanal (domingo): algum item nunca discriminou (todo mundo tira 2) ou sempre gera discussão? Reescreva a faixa.
- Se o item **Documentação** for sempre 1, o template de PR ou o `progress` talvez estejam pedindo demais.
- Quando o `harness.py` ganhar um comando para somar a nota, atualize "Como postar".