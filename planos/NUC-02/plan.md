# Plan — NUC-02 · Decidir o acesso por escritório, papel e carteira

**Status:** pronto para revisão
**Branch:** feat/NUC-02-decidir-o-acesso-por-escritorio-papel-e · **Data:** 22/11/2026 · **Responsável:** caio-nascime
**Tasks:** planos/NUC-02/tasks.md

## 1. A decidir (humano)
Nenhuma pergunta aberta: as 4 foram respondidas em 22/11 com o padrão sugerido (ver seção 5).

Mudanças sugeridas na ficha (o humano aplica em PR):
- `requisitos`: hoje só `BD-02` (decisão de banco, não RF). Sugerir acrescentar `RF-AUT-02`, `RF-AUT-03` e `RF-SEG-02`.
- c4: acrescentar um exemplo de membro inativo, se a resposta à pergunta 1 for o padrão.

## 2. Decisões tomadas pelo agente
Cada uma precisa de confirmação humana.
### D1 · Regra pura, sem banco nem HTTP
- **Alternativas:** A) função pura que recebe o vínculo, a ação e o cliente já carregado · B) função que consulta o banco · C) dependência do FastAPI
- **Escolhida:** A — **motivo:** `depende_de` é vazio (DB-01 e NUC-01 não existem); I-4 separa a autorização em `core/` do RLS (NUC-03). Quem consome (ACE-03, CAD-04, ACE-05) carrega o cliente pelo próprio `repository.py` e chama a regra.
- **Fontes:** ARCHITECTURE.md §1 e I-4; `gitpages/.../decisoes/banco-de-dados.md` (linha 41, duas camadas).
- **Impacto:** T2 a T5; todos os critérios.
- [ ] confirmar

### D2 · Quatro resultados, não um booleano
- **Alternativas:** A) `ALLOWED`, `NOT_FOUND`, `NOT_ASSIGNED`, `FORBIDDEN_ROLE` · B) `True`/`False` · C) exceções
- **Escolhida:** A — **motivo:** a ficha distingue "inexistente" (404, P-01), "falta de atribuição" (403 da P-09, c6/c7) e "negado pelo papel" (403 da P-01, c8). A API traduz cada um em status e mensagem; o texto "Atribua este cliente a você…" fica na API (I-14), não aqui.
- **Fontes:** DECISIONS.md P-01 e P-09; ficha c6, c7 e c8.
- **Impacto:** T2, T4, T5.
- [ ] confirmar

### D3 · Três ações num enum
- **Escolhida:** `Action.LIST` ("ver na lista"), `Action.ACCESS` ("acessar"), `Action.MANAGE_ASSIGNMENT` ("gerir atribuição"). Nomes em inglês pelo glossário (`firm`, `manager`, `accountant`, `client`). Alternativa (strings soltas) aceitaria ação digitada errado sem erro.
- **Impacto:** T2. [ ] confirmar

### D4 · Cliente inexistente entra como `None`
- **Motivo:** c7 (d) pede o mesmo resultado para identificador inexistente e para cliente de outro escritório. A regra recebe `None` e devolve `NOT_FOUND`, sem caminho separado. [ ] confirmar

### D5 · Ordem das checagens igual à P-09 (5)
- Vínculo inválido ou sem papel → `NOT_FOUND`; cliente `None` ou de outro escritório → `NOT_FOUND`; depois a regra da ação. Em `MANAGE_ASSIGNMENT`, contador do mesmo escritório → `FORBIDDEN_ROLE` (c8). Alternativa (checar papel antes do escritório) vazaria a existência do cliente de outro escritório. [ ] confirmar

### D6 · Filtro de lista preserva a ordem de entrada
- c5 mostra a saída na ordem da entrada; ordenar é tarefa de quem lista (ACE-03). [ ] confirmar

### D7 · Sem biblioteca nova
- Só `dataclasses` e `enum` da biblioteca padrão; o código roda em 3.12 (Dockerfile) e 3.14 (ARQ-08). [ ] confirmar

## 3. Resumo e abordagem
Uma regra única em `core/` responde, para um vínculo (membro), uma ação e um cliente: permitido, inexistente, falta de atribuição ou negado pelo papel. Um filtro aplica "ver na lista" a uma coleção.
1. T1: testes da ficha em `tests/core/test_regra_acesso.py`, com o estado dos exemplos montado em memória.
2. T2: contratos imutáveis (vínculo, escopo do cliente, ação, resultado) em `core/contracts.py`.
3. T3: checagens comuns (vínculo válido, mesmo escritório) em `core/service.py`.
4. T4: regra de "ver na lista" e "acessar".
5. T5: "gerir atribuição" e o filtro de lista.
6. T6: verificação final.

## 4. Contexto encontrado
- **Código relacionado:** `src/lastro/core/__init__.py` vazio; nenhum código de produção ainda. `tests/core/` só tem `.gitkeep`.
- **Dependências:** nenhuma (`depende_de` vazio). Consomem a regra: ACE-03, CAD-03, CAD-04, CAD-05, CAD-07, ACE-05 (todas `not_started`).
- **Modelo:** MEMBRO (`id; escritorio_id; usuario_id; papel; ativo`) e ATRIBUICAO (`cliente_id; membro_id; inicio; fim`) em `gitpages/src/content/docs/modelagem/entidades.md`. Responsável = membro.
- **Execução:** `Dockerfile` define `PYTHONPATH=/app/src`; não há `conftest.py` nem config de pytest.
- **Reaproveitar:** nada no código. Glossário do CODING_STANDARDS §7 para nomes.
- **Não criar:** consulta ao banco, rota, mensagem ao usuário, `utils.py`.
- **Pesquisa externa:** sem pesquisa externa necessária (regra de negócio já decidida na P-09; sem biblioteca).

## 5. Decisões (já resolvidas)
- 22/11 · Membro inativo é tratado como c4: negado como inexistente em tudo (resposta à pergunta 1, padrão aceito por caio-nascime).
- 22/11 · A regra recebe o vínculo ativo da sessão (membro), não o usuário; o responsável é comparado por `membro_id` (pergunta 2, caio-nascime).
- 22/11 · Mantidos os nomes de teste e de arquivo da ficha, em português (pergunta 3, caio-nascime).
- 22/11 · NUC-02 cria `core/contracts.py` e `core/service.py` só com a regra de acesso; o dono da NUC-01 é avisado (pergunta 4, caio-nascime).
- 22/11 · P-09: chefe vê a lista, só o responsável ativo acessa, gestão de atribuição exige chefe do mesmo escritório (líder, DECISIONS.md).
- 18/11 · P-01 (404 idêntico ao inexistente; 403 por papel), D-07 (carteira individual), D-09 (um responsável ativo).

## 6. Avaliação da ficha
| # | Achado | Gravidade | Critério |
|---|---|---|---|
| 1 | 8 critérios (> 4). Mitigação: um só módulo e uma função pura; cabe em uma sessão. Não sugiro dividir. | ATENÇÃO | todos |
| 2 | Membro inativo não coberto (pergunta 1). | ATENÇÃO | c4 |
| 3 | `requisitos` cita só BD-02; faltam os RF de acesso. | ATENÇÃO | — |
| 4 | A verificação prova a regra, não que ela roda "em toda requisição" (I-4). Isso fica para as fichas que consomem (ACE-03 etc.). | ATENÇÃO | c1–c8 |
| 5 | Nomes de teste em português contra o CODING_STANDARDS (pergunta 3). | ATENÇÃO | — |
| 6 | c2 e c3 dizem "negado como inexistente" também em "ver na lista": na lista isso significa "não aparece". Coerente com c5. | ATENÇÃO | c2, c3 |
| 7 | Exemplos claros e com dados inventados (ESC-1, EMP-1, chefe_1); sem risco de dado real. | — | todos |

## 7. Riscos
- Contrato de `core/` virar dependência de 6 fichas → é versão 0 (regra 11); mudança abre issue `contrato:`.
- Futuro com vários responsáveis ativos (D-09 provisória) → o escopo do cliente guarda um só responsável; mudar é mudança de contrato, registrada.
- Divergência 3.12 × 3.14 → só recursos comuns às duas versões.

## 8. Aprovação
- [x] Perguntas ATENÇÃO respondidas ou padrão aceito (22/11, caio-nascime)
- [ ] Decisões do agente confirmadas
- [ ] Plan e tasks revisados por ________ em __/__
