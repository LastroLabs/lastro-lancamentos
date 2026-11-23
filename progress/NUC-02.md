# NUC-02 · Decidir o acesso por escritório, papel e carteira

- Responsável: caio-nascime · Branch: `feat/NUC-02-decidir-o-acesso-por-escritorio-papel-e` · Início: 23/11/2026
- Ficha: `features/NUC-02.json` (estado e critérios ficam lá; não repita aqui)

<!--
Como preencher (agente, ao encerrar a sessão):
- REESCREVA as seções do topo: Objetivo, Próxima ação, Bloqueios e perguntas.
- ACRESCENTE, sem apagar o que já existe, em Feito, Rodei, Falhou e Decisões.
  Cada linha começa com a data (DD/MM) e a sessão, ex.: "- 14/11 · S2 · ...".
- Registre só o que realmente rodou. Sem dado real, nome de cliente ou segredo.
- Não escreva estado (passing etc.) aqui: ele fica na ficha, gravado pelo script.
-->

## Objetivo
Regra pura de acesso (sem banco nem HTTP): dado o vínculo do usuário, a ação (LIST, ACCESS, MANAGE_ASSIGNMENT) e o cliente, devolve ALLOWED, NOT_FOUND, NOT_ASSIGNED ou FORBIDDEN_ROLE, e filtra a lista de clientes visíveis (RF-SEG-01/02).

## Próxima ação
Aguardar revisão e merge do PR na `developer`. Depois, pegar a próxima feature (`hx state`) e ligar a regra à API quando houver sessão e carga do banco (`src/lastro/core/service.py`: `decide_access`, `filter_visible_clients`).

## Bloqueios e perguntas
- (nenhum)

## Feito
- 22/11 · S1 · Plano e tasks aprovados (commits `90219ed`, `da754b2`).
- 22/11 · S1 · Testes dos c1 a c8 em `tests/core/test_regra_acesso.py` (commit só de testes `b35734c`).
- 22/11 · S1 · Contratos em `core/contracts.py` e regra em `core/service.py` (commit `e983eeb`), sem editar `tests/` depois do commit de testes.
- 22/11 · S1 · `hx feature verify NUC-02` gravou `passing` e a evidência na ficha (c1 a c8 ok).

## Rodei
- 22/11 · S1 · `hx verify` → ruff OK, pytest OK; arquitetura e E2E pulados (ainda não implementados); RESULTADO: OK
- 22/11 · S1 · `git diff b35734c HEAD --stat -- tests` → vazio (testes intactos)
- 22/11 · S1 · `hx check-clean` → 0 achado(s), RESULTADO: OK (sem a variável de nomes proibidos; verificação de nomes pulada)

## Falhou
- 22/11 · S1 · `hx` no Git Bash e `python -m pytest` direto não rodam (sem Python no PATH do bash e sem pytest instalado fora do ambiente); usei `. .	ools\hx.ps1; hx verify` no PowerShell.

## Decisões
- 22/11 · S1 · Recusa é valor de retorno, não exceção (D2); cliente inexistente ou de outro escritório dá NOT_FOUND para não revelar existência (P-01); NOT_ASSIGNED só aparece para o chefe do mesmo escritório (P-09). Detalhes em `planos/NUC-02/plan.md`.

## Fim de sessão
- [x] `hx verify` verde, ou a falha está descrita em "Falhou"
- [x] Nada quebrado nem pela metade na branch; commit feito
- [x] "Próxima ação" atualizada
- [x] Nenhum dado real nem segredo nas anotações