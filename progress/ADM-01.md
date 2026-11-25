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
(1 a 2 linhas: o comportamento que esta feature entrega)

## Próxima ação
Commitar `features/ADM-01.json` (evidência gravada em 25/11, commit `3c534de`) e abrir o PR com o template de `.github/`, avisando guin409 (NUC-03, RLS no primeiro acesso) e caio-nascime (ACE-02, contrato novo do `access`).

## Bloqueios e perguntas
- (nenhum) · Avisos pendentes para o PR: guin409 e caio-nascime (ver Próxima ação).
- Falta preencher o nome do revisor e a data na seção 8 do plan.

## Feito
- DD/MM · S1 ·
- 25/11 · S2 · Testes commitados antes (TDD: `a4b48df`, `e269ab9`, `d2e8ccc`) e implementação em `3c534de` (`access/admin.py` e o restante), feitos pelo dev fora desta sessão. Aqui só conferi.

## Rodei
- DD/MM · S1 · `comando` → resultado resumido
- 25/11 · S2 · `python3.14 tools/harness.py verify` → ruff OK, pytest OK; Arquitetura e E2E pulados (não implementados) → RESULTADO OK. (`./tools/hx` falha neste shell: `python3` do sistema é o 3.10.)
- 25/11 · S2 · `hx feature verify ADM-01` → c1 a c4 OK, `passing`, evidência no commit `3c534de`. A 1ª tentativa foi recusada por árvore suja; a 2ª, com a árvore limpa, gravou.
- 25/11 · S2 · `hx check-clean` → 0 achados, OK; a verificação de nomes foi pulada ("variável não definida").

## Falhou
- DD/MM · S1 · o que falhou e a causa, se souber
- 25/11 · S2 · `hx feature verify ADM-01` recusou na 1ª vez: "árvore de trabalho tem alterações não commitadas". Passou depois do commit.

## Decisões
- DD/MM · S1 · decisão e o porquê (se for D-xx, registre também em `docs/decisoes/DECISIONS.md`)
- 24/11 · S1 · Plan aprovado por jvsauma: D1 a D5 confirmadas; senha com mínimo de 8 caracteres.

## Fim de sessão
- [x] `hx verify` verde, ou a falha está descrita em "Falhou"
- [ ] Nada quebrado nem pela metade na branch; commit feito
- [ ] "Próxima ação" atualizada
- [ ] Nenhum dado real nem segredo nas anotações