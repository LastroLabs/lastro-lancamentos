# Tasks — {{ID}} · {{TITULO}}

<!--
Gerado por /planejar. Máximo 200 linhas, até 8 tasks. Sem código.
Marque [x] ao concluir. Cada task prova que terminou por um comando.
Decisões e perguntas ficam em planos/{{ID}}/plan.md.
-->

**Plan:** planos/{{ID}}/plan.md · **Ficha:** features/{{ID}}.json
**Ordem:** T1 → revisão humana dos testes → commit só-de-testes (anotar o hash) → T2 em diante (sessão nova, sem editar `tests/`)

---

## [ ] T1 · Escrever os testes dos critérios
- **Critérios da ficha:** c1, c2, …
- **Regra de negócio (em linguagem simples):** <o que o sistema deve fazer e por quê>
- **Critérios de aceite:**
  - [ ] Existe um teste para cada nome citado em `verificacao` da ficha
  - [ ] Todos falham hoje pelo motivo certo (comportamento ausente)
  - [ ] Só dados inventados
- **Exemplos:** <entrada → saída, com dado inventado>
- **Arquivos:** `tests/…`
- **Fora do escopo:** código de produção
- **Pronto quando:** `docker compose run --rm dev pytest <arquivo> -q` mostra só falhas esperadas

## [ ] T2 · <o que implementar>
- **Critérios da ficha:** c1
- **Regra de negócio (em linguagem simples):** <explicação para quem não conhece o domínio>
- **Critérios de aceite:**
  - [ ] <verificável 1>
  - [ ] <verificável 2>
- **Exemplos:** <entrada → saída>; <caso de borda → resultado>; <erro → mensagem ou código>
- **Arquivos:** `src/…` (ou `tools/…`)
- **Reaproveitar:** `<função ou classe existente>` · **Não criar:** `<o que não duplicar>`
- **Fora do escopo:** <o que NÃO fazer aqui>
- **Decisões relacionadas:** D1 (plan.md)
- **Pronto quando:** `pytest <teste da ficha> -q` passa

## [ ] T3 · <…>
(mesmo formato)

## [ ] TN · Verificação final
- **Critérios de aceite:**
  - [ ] `git diff <hash-dos-testes> -- tests/` vazio
  - [ ] `ruff check .` limpo
  - [ ] `hx check-clean` e `hx verify` em OK
  - [ ] `hx feature verify {{ID}}` grava `passing`
- **Pronto quando:** os três comandos do `hx` terminam com código 0
