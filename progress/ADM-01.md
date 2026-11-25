# ADM-01 · Criar um escritório e o seu chefe por comando, para o primeiro acesso

- Responsável: jvsauma · Branch: `feat/ADM-01-criar-um-escritorio-e-o-seu-chefe-por-co` · Início: 24/11/2026
- Ficha: `features/ADM-01.json` (estado e critérios ficam lá; não repita aqui)

<!--
Como preencher (agente, ao encerrar a sessão):
- REESCREVA as seções do topo: Objetivo, Próxima ação, Bloqueios e perguntas.
- ACRESCENTE, sem apagar o que já existe, em Feito, Rodei, Falhou e Decisões.
  Cada linha começa com a data (DD/MM) e a sessão, ex.: "- 14/11 · S2 · ...".
- Registre só o que realmente rodou. Sem dado real, nome de cliente ou segredo.
- Não escreva estado (passing etc.) aqui: ele fica na ficha, gravado pelo script.
-->

## Objetivo
Um comando (`python -m lastro.access.admin criar-escritorio`) cria, numa transação só, o escritório, o chefe e o vínculo `chefe` ativo, para o primeiro acesso antes da ACE-02. A senha vem só da variável `LASTRO_SENHA_CHEFE`; login que já existe é recusado sem alterar nada.

## Próxima ação
Atualizar o PR da ADM-01 com o número da issue `contrato:` (#68) no item "Contrato mudou?" e pedir nova revisão. Depois, em PRs de ficha: acertar o texto da c1 ("papel chefe" na identificação é `manager` na API) e decidir se entram em c3 "nome vazio", "senha menor que 8" e "senha no terminal".

## Bloqueios e perguntas
- Nenhum bloqueio. A issue `contrato:` (#68) já avisa caio-nascime (ACE-02) e guin409 (NUC-03).
- Falta o revisor humano preencher o nome e a data na seção 8 do plan (só um humano marca).

## Feito
- 25/11 · S3 · Revisão pediu ajustes: abri a issue `contrato:` #68 (CreatedFirm, UsernameTakenError, create_firm_with_manager) e fechei este progress.
- 25/11 · S2 · Testes commitados antes (TDD: `a4b48df`, `e269ab9`, `d2e8ccc`) e implementação em `3c534de` (`access/admin.py` e o restante), feitos pelo dev fora desta sessão. Aqui só conferi.

## Rodei
- 25/11 · S2 · `python3.14 tools/harness.py verify` → ruff OK, pytest OK; Arquitetura e E2E pulados (não implementados) → RESULTADO OK. (`./tools/hx` falha neste shell: `python3` do sistema é o 3.10.)
- 25/11 · S2 · `hx feature verify ADM-01` → c1 a c4 OK, `passing`, evidência no commit `3c534de`. A 1ª tentativa foi recusada por árvore suja; a 2ª, com a árvore limpa, gravou.
- 25/11 · S2 · `hx check-clean` → 0 achados, OK; a verificação de nomes foi pulada ("variável não definida").

## Falhou
- 25/11 · S2 · `hx feature verify ADM-01` recusou na 1ª vez: "árvore de trabalho tem alterações não commitadas". Passou depois do commit.

## Decisões
- 25/11 · S3 · Papel na identificação: o banco guarda `chefe` e a API devolve `manager`; o teste foi ajustado a isso antes da implementação (`e269ab9`). Texto da c1 fica para PR de ficha.
- 24/11 · S1 · Plan aprovado por jvsauma: D1 a D5 confirmadas; senha com mínimo de 8 caracteres.

## Fim de sessão
- [x] `hx verify` verde, ou a falha está descrita em "Falhou"
- [x] Nada quebrado nem pela metade na branch; commit feito
- [x] "Próxima ação" atualizada
- [x] Nenhum dado real nem segredo nas anotações
