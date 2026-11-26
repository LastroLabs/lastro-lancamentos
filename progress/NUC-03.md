# NUC-03 · Isolar no banco os dados de cada escritório

- Responsável: jvsauma · Branch: `feat/NUC-03-isolar-no-banco-os-dados-de-cada-escrito` · Início: 26/11/2026
- Ficha: `features/NUC-03.json` (estado e critérios ficam lá; não repita aqui)

<!--
Como preencher (agente, ao encerrar a sessão):
- REESCREVA as seções do topo: Objetivo, Próxima ação, Bloqueios e perguntas.
- ACRESCENTE, sem apagar o que já existe, em Feito, Rodei, Falhou e Decisões.
  Cada linha começa com a data (DD/MM) e a sessão, ex.: "- 14/11 · S2 · ...".
- Registre só o que realmente rodou. Sem dado real, nome de cliente ou segredo.
- Não escreva estado (passing etc.) aqui: ele fica na ficha, gravado pelo script.
-->

## Objetivo
O banco esconde e protege as linhas de cada escritório (RLS forçada em 12 tabelas); sem escritório definido não se vê nada; as buscas anteriores ao escritório (sessão, vínculos, convite, login) passam por quatro funções `SECURITY DEFINER`.

## Próxima ação
T7: atualizar docs (`docs/modulos/access.md`, `registry.md`, `docs/SECURITY.md` §8, `ARCHITECTURE.md`) e rodar `hx check-clean`. Depois `hx verify` (a falha do build do front veio de `web/dist` do root, já apagado; confirmar). `features/NUC-03.json` está staged após desfazer o commit `ebb5150`: decidir se grava de novo com `hx feature verify NUC-03`.

## Bloqueios e perguntas
- Issue para a ACE-05 (função do link do cliente; `link_cliente` fica fechada até lá): a abrir por um humano (plan, resposta 4).
- Issue `contrato:` e aval do plan para as funções do banco, se mudarem (regra 11).

## Feito
- 26/11 · S1 · Migração `0005` (RLS forçada, política do dono, `credencial_hash` fechada ao app, 4 funções), `core/db.py` (`use_firm`, `after_begin`), `access/repository.py` (login e sessão pelas funções, `insert_firm_with_manager` com UUID do app). Commit `7419559`. T1 já estava feita; T7 e T8 pendentes.

## Rodei
- 26/11 · S1 · `pytest -q` completo no contêiner → 502 passaram; `ruff check .` → OK
- 26/11 · S1 · após o ajuste da busca da sessão: `test_isolamento_banco` 13 passaram, login/office_admin 21, `test_cliente` 9
- 26/11 · S1 · `hx verify` não rodado por mim nesta sessão (o `hx` não estava no meu PATH)

## Falhou
- 26/11 · S1 · `hx verify` do dev falhou em `test_web01...` (build do vite): `web/dist` e caches ficaram como root pelas minhas rodadas no contêiner. Apaguei os arquivos gerados do root; o teste isolado passou (5). Não reconfirmado pelo `hx verify`.

## Decisões
- 26/11 · S1 · `find_session` lê a sessão de novo por membro, `expira_em` e `encerrada_em` (não por hash), porque a função devolve só 4 colunas (c6) e o teste de c7 proíbe consulta direta por `hash_token`. Se houver 2 linhas iguais, recusa as duas (falha segura). Risco residual: praticamente nulo. Solução exata (função devolver `id` e `criada_em`) exige mudar ficha e teste; não feito. Alternativa: 5ª função, não adotada (fora do plano).
- 26/11 · S1 · Rodar o contêiner de teste como o usuário do dev, não como root, para não criar arquivos do root no repositório.

## Fim de sessão
- [ ] `hx verify` verde, ou a falha está descrita em "Falhou"
- [ ] Nada quebrado nem pela metade na branch; commit feito
- [ ] "Próxima ação" atualizada
- [ ] Nenhum dado real nem segredo nas anotações