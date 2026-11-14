# Lastro — AGENTS.md (v0.2, 13/11/2026)

Responda e escreva textos de interface em português do Brasil. Este arquivo é um roteador: o detalhe fica em `docs/`. Limite: 100 linhas.

## 1. O que é

Lastro (nome provisório) lê o extrato bancário de clientes pequenos de escritórios contábeis (PDF digital BB/Inter e OFX de qualquer banco), confere o saldo por cálculo, sugere a conta de cada linha com motivo e confiança, pergunta ao cliente só o que não sabe e entrega o Excel no layout do Domínio. Papéis: chefe, contador, cliente final (celular, sem login). MVP em **07/12/2026**.

**Stack decidida:** Python 3.12, FastAPI, Docker. **Em aberto** (não decida; ver `docs/decisoes/DECISIONS.md`): front (React ou Vue), banco, hospedagem, provedor de LLM, layout do Domínio (D-05) e as demais D-xx.

## 2. Comandos

- `hx state`: painel de features e quem está com cada uma (responde "qual o progresso?")
- `hx feature start <ID> --owner <nome>`: pega a feature (branch, progress, estado)
- `hx verify`: lint e testes · `hx feature verify <ID>`: prova pela ficha e grava `passing`
- `hx check-clean`: procura dado real e segredo; rode antes de todo PR

Entrega: branch `feat/<ID>-...`, nunca direto na main; PR com o template de `.github/`.
O `hx` está em implementação. Se um comando não existir ainda, diga que não rodou. Nunca afirme que algo passou sem ter rodado.

**Encerrar a sessão:** quando o dev pedir para encerrar, antes de responder atualize `progress/<ID>.md`. Reescreva Objetivo, Próxima ação e Bloqueios; acrescente, com data e sem apagar, em Feito, Rodei, Falhou e Decisões. Registre só o que realmente rodou e nada de dado real. Rode `hx verify` se puder e mostre o resultado.

## 3. Regras inegociáveis

Cada regra traz `[origem]`. Sem `vale` ou `expira`, ela vale sempre e não expira. Mais críticas no topo e no fim.

1. **Nenhum dado real** (extrato, nome de cliente, escritório ou pessoa, CPF/CNPJ, chave) em arquivo, teste, log ou prompt. Só dados sintéticos. [LGPD e promessa aos pilotos]
2. **Nunca edite o `estado` de uma ficha à mão.** Só o script do harness (até ele existir, o dono do harness). [agente declarava vitória cedo]
3. **Testes antes do código; ao implementar, não edite `tests/`.** Se o teste parece errado, pare e avise. [agente corrigindo a própria prova · expira: quando a CI travar o hash dos testes]
4. **Saldo é conferido por código**, nunca por LLM. Extrato que não fecha não segue para classificação nem perguntas. [RF-VAL-01, Q-10 · vale em leitura e conferência]
5. **LLM é o último recurso** (regras → histórico → parecidas → IA) e só responde com conta da lista do cliente ou "não sei". Antes de enviar texto a serviço externo, remova CPF, CNPJ, agência e conta. Nomes de contrapartes: proibido até a D-03. [RF-CLA-01/05, RF-SEG-03 · vale ao chamar LLM · nomes expiram ao fechar a D-03]
6. **Nada é exportado sem revisão do contador.** Pendentes saem na conta transitória, marcados. [RF-REV-04, RF-EXP-02 · vale em exportação]
7. **Isolamento no servidor, em toda requisição:** escritório não vê outro escritório; contador só vê clientes atribuídos; link do cliente é imprevisível e expira. [RF-SEG-01/02, RF-AUT-02 · vale em API e telas]
8. **Dinheiro em centavos, inteiro.** Nunca float. [erro de arredondamento]
9. **Escopo é o de `docs/produto/requisitos_funcionais_v0.2.md`.** Não implemente o que é Won't. Mudou o escopo? Primeiro em `docs/` e na ficha, depois no código. [regra do time · expira: ao virar v1.0]
10. **Uma feature por pessoa e por sessão.** Termine (testes verdes, `progress/<ID>.md` atualizado) antes de abrir outra. [WIP=1 · expira: se o time mudar o fluxo]
11. **Contratos entre módulos estão em versão 0.** Mudou? Abra issue `contrato:` e avise o dono do módulo. [contratos não congelados · expira: após o esqueleto de ponta a ponta]
12. **Algo indefinido? Pare e pergunte.** Não invente requisito, número ou regra (use `[definir]`) e não escolha stack, banco, provedor ou biblioteca nova por conta própria: registre em `DECISIONS.md`. [sessões anteriores inventando detalhes]

## 4. Onde achar o resto (leia só quando a tarefa pedir)

- `features/<ID>.json`: o que entregar e como provar. Leia ao começar uma feature.
- `progress/<ID>.md`: de onde parou. Leia ao retomar; atualize ao terminar.
- `docs/produto/requisitos_funcionais_v0.2.md`: requisitos RF-xxx e decisões D-01 a D-09. Leia antes de qualquer feature.
- `docs/produto/proposta_v2.md`: visão, pilotos e plano até 07/12. Leia se faltar contexto de produto.
- `docs/produto/simulacao_fluxo_usuarios.md`: fluxo tela a tela dos 3 papéis e dúvidas Q-xx. Leia ao mexer em telas ou fluxo.
- `docs/ia/boas_praticas_llm.md`: como a IA entra no fluxo e formato do prompt. Leia antes de mexer em `ia/` ou chamar LLM.
- `docs/decisoes/DECISIONS.md`: decisões D-xx e arquitetura. Leia se algo parecer indefinido.
- `docs/SECURITY.md`: dados, anonimização, LGPD. Leia antes de mexer em fixtures ou chamar LLM.
- `docs/modulos/<modulo>.md`: regras do módulo. Leia antes de mexer nele. Regra específica de módulo vai lá, não aqui.
- `docs/design/` (a criar: DESIGN.md, microcopy.md): identidade, tokens e textos. Leia antes de mexer no front. Mensagens ao usuário: o que aconteceu + o que fazer, em português simples (RF-AVI-02).
- `docs/rubrica-revisao.md`: leia ao revisar um PR.