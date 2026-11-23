# Tasks — NUC-02 · Decidir o acesso por escritório, papel e carteira

**Plan:** planos/NUC-02/plan.md · **Ficha:** features/NUC-02.json
**Ordem:** T1 → revisão humana dos testes → commit só-de-testes (anotar o hash) → T2 em diante (sessão nova, sem editar `tests/`)

Estado de referência dos exemplos (inventado, igual ao da ficha):
- ESC-1: chefe_1 (chefe), contador_a e contador_b (contadores), usuario_sem_papel (em ESC-1, sem papel).
- ESC-2: chefe_2 (chefe), contador_x (contador). usuario_sem_escritorio não tem vínculo.
- Clientes: EMP-1 → contador_a; EMP-2 → contador_b; EMP-3 sem responsável; EMP-4 → chefe_1 (todos em ESC-1); EMP-9 → contador_x (ESC-2).

---

## [ ] T1 · Escrever os testes dos critérios
- **Critérios da ficha:** c1 a c8
- **Regra de negócio (em linguagem simples):** cada teste reproduz um exemplo da ficha: monta o estado acima em memória, pergunta à regra "este usuário pode fazer esta ação neste cliente?" e confere a resposta.
- **Critérios de aceite:**
  - [ ] Arquivo `tests/core/test_regra_acesso.py` com as 8 funções citadas em `verificacao`: `test_chefe_ve_todos_na_lista`, `test_contador_acessa_so_atribuidos`, `test_outro_escritorio_sempre_negado`, `test_usuario_sem_escritorio_ou_papel_negado`, `test_filtro_de_lista_devolve_so_visiveis`, `test_chefe_acessa_so_atribuidos_a_ele`, `test_recusa_por_falta_de_atribuicao_so_para_chefe`, `test_gerir_atribuicao_exige_chefe_do_escritorio`
  - [ ] Cada teste cobre todos os pares (usuário, ação, cliente) do exemplo, não só um
  - [ ] c7 confere que (b), (c) e (d) dão **o mesmo** resultado
  - [ ] Todos falham hoje por falta de `lastro.core` (ImportError ou equivalente), não por erro no teste
  - [ ] Só dados inventados (ids como `ESC-1`, `EMP-1`); nenhum CNPJ
- **Exemplos:** c1: chefe_1, LIST, EMP-1/2/3 → ALLOWED nos 3; c8: contador_a, MANAGE_ASSIGNMENT, EMP-1 → FORBIDDEN_ROLE
- **Arquivos:** `tests/core/test_regra_acesso.py` (o estado pode ficar em funções auxiliares no próprio arquivo)
- **Fora do escopo:** código de produção; `conftest.py` compartilhado
- **Pronto quando:** `docker compose run --rm dev pytest tests/core/test_regra_acesso.py -q` mostra só falhas esperadas

## [ ] T2 · Contratos da regra de acesso
- **Critérios da ficha:** base de c1 a c8
- **Regra de negócio (em linguagem simples):** para decidir, a regra precisa saber quem pede (o vínculo da sessão: membro, escritório, papel, se está ativo), o que quer fazer (ver na lista, acessar, gerir atribuição) e de qual cliente (escritório e responsável ativo). A resposta diz se pode e, se não, por quê.
- **Critérios de aceite:**
  - [ ] `Role` (`MANAGER`, `ACCOUNTANT`), `Action` (`LIST`, `ACCESS`, `MANAGE_ASSIGNMENT`) e `AccessDecision` (`ALLOWED`, `NOT_FOUND`, `NOT_ASSIGNED`, `FORBIDDEN_ROLE`) como enums
  - [ ] Vínculo e escopo do cliente como `@dataclass(frozen=True, slots=True)`; escritório e papel do vínculo aceitam `None`; o responsável do cliente aceita `None`
  - [ ] Ids são opacos (comparados só por igualdade); nada de tipo de banco
  - [ ] Docstrings em inglês; `ruff check src/lastro/core` limpo
- **Exemplos:** vínculo de chefe_1 = (membro chefe_1, ESC-1, MANAGER, ativo); EMP-3 = (EMP-3, ESC-1, responsável `None`)
- **Arquivos:** `src/lastro/core/contracts.py`
- **Reaproveitar:** glossário do CODING_STANDARDS §7 (`firm`, `manager`, `accountant`, `client`) · **Não criar:** modelo de banco, campo de nome/CNPJ (a regra não precisa)
- **Fora do escopo:** sessão, login, carregamento do banco
- **Decisões relacionadas:** D2, D3, D4, D7; perguntas 2 e 4
- **Pronto quando:** `docker compose run --rm dev python -c "import lastro.core.contracts"` termina sem erro

## [ ] T3 · Checagens comuns: vínculo válido e mesmo escritório
- **Critérios da ficha:** c3, c4 (e o caso (c) e (d) de c7)
- **Regra de negócio (em linguagem simples):** antes de olhar a ação, a regra descarta quem não tem escritório, não tem papel conhecido ou está inativo, e descarta cliente que não existe ou é de outro escritório. Em todos esses casos a resposta é "inexistente", para ninguém descobrir que um cliente de outro escritório existe (P-01). Nem o chefe passa por cima disso.
- **Critérios de aceite:**
  - [ ] Vínculo sem escritório, sem papel ou inativo → `NOT_FOUND` em qualquer ação e qualquer cliente
  - [ ] Cliente `None` ou de outro escritório → `NOT_FOUND`, antes de olhar papel ou responsável
  - [ ] Sem `if` repetido por ação: as checagens comuns ficam num só lugar
- **Exemplos:** chefe_2, ACCESS, EMP-1 → NOT_FOUND; chefe_1, LIST, EMP-9 → NOT_FOUND; usuario_sem_papel, LIST, EMP-1 → NOT_FOUND; chefe_1, ACCESS, `None` → NOT_FOUND
- **Arquivos:** `src/lastro/core/service.py`
- **Reaproveitar:** contratos da T2 · **Não criar:** exceção para recusa (a recusa é um valor, D2)
- **Fora do escopo:** status HTTP e mensagem (fica na API, I-14)
- **Decisões relacionadas:** D4, D5; pergunta 1
- **Pronto quando:** `pytest tests/core/test_regra_acesso.py::test_outro_escritorio_sempre_negado tests/core/test_regra_acesso.py::test_usuario_sem_escritorio_ou_papel_negado -q` passa

## [ ] T4 · Ver na lista e acessar
- **Critérios da ficha:** c1, c2, c6, c7
- **Regra de negócio (em linguagem simples):** na **lista**, o chefe vê todos os clientes do escritório; o contador vê só os que estão com ele. Para **acessar** (abrir, ler, alterar), só o responsável ativo entra, seja chefe ou contador. Se o chefe do mesmo escritório tenta abrir um cliente que não é dele, a resposta é "falta de atribuição" (ele já vê o cliente na lista, então não há o que esconder, P-09). Para qualquer outro, a resposta é "inexistente".
- **Critérios de aceite:**
  - [ ] LIST: chefe do escritório → ALLOWED sempre; contador → ALLOWED só se for o responsável, senão NOT_FOUND
  - [ ] ACCESS: responsável ativo → ALLOWED; chefe do escritório não responsável → NOT_ASSIGNED; demais → NOT_FOUND
  - [ ] Cliente sem responsável: ACCESS dá NOT_ASSIGNED para o chefe e NOT_FOUND para o contador
- **Exemplos:** contador_a, ACCESS, EMP-1 → ALLOWED; contador_a, ACCESS, EMP-2 → NOT_FOUND; chefe_1, ACCESS, EMP-4 → ALLOWED; chefe_1, ACCESS, EMP-3 → NOT_ASSIGNED; contador_a, LIST, EMP-3 → NOT_FOUND
- **Arquivos:** `src/lastro/core/service.py`
- **Reaproveitar:** checagens da T3 · **Não criar:** segunda função de decisão por papel
- **Fora do escopo:** reatribuição e revogação de sessão (ACE-04), listagem real (ACE-03)
- **Decisões relacionadas:** D2, D5
- **Pronto quando:** `pytest tests/core/test_regra_acesso.py -q -k "chefe_ve_todos or contador_acessa or chefe_acessa or falta_de_atribuicao"` passa

## [ ] T5 · Gerir atribuição e filtro de lista
- **Critérios da ficha:** c8, c5
- **Regra de negócio (em linguagem simples):** **gerir atribuição** (atribuir, ver quem é o responsável, trocar) é tarefa do chefe do mesmo escritório, mesmo que o cliente não esteja com ele ou esteja sem ninguém. O contador é recusado pelo papel, mesmo sendo o responsável. O **filtro** recebe uma lista de clientes e devolve só os que o usuário pode ver na lista, na mesma ordem.
- **Critérios de aceite:**
  - [ ] MANAGE_ASSIGNMENT: chefe do escritório → ALLOWED (com ou sem responsável); contador do escritório → FORBIDDEN_ROLE; outro escritório → NOT_FOUND
  - [ ] Filtro usa a mesma decisão de LIST (não reimplementa a regra) e preserva a ordem
  - [ ] Lista vazia → lista vazia; usuário sem escritório → lista vazia
- **Exemplos:** filtro [EMP-1, EMP-2, EMP-3, EMP-9]: contador_a → [EMP-1]; chefe_1 → [EMP-1, EMP-2, EMP-3]; chefe_2 → [EMP-9]; chefe_2, MANAGE_ASSIGNMENT, EMP-1 → NOT_FOUND
- **Arquivos:** `src/lastro/core/service.py`
- **Reaproveitar:** decisão da T3/T4 · **Não criar:** consulta ao banco para filtrar (o filtro no banco é da ACE-03 e do RLS da NUC-03)
- **Fora do escopo:** gravar atribuição (ACE-02), histórico (RF-AUT-05)
- **Decisões relacionadas:** D2, D5, D6
- **Pronto quando:** `pytest tests/core/test_regra_acesso.py::test_gerir_atribuicao_exige_chefe_do_escritorio tests/core/test_regra_acesso.py::test_filtro_de_lista_devolve_so_visiveis -q` passa

## [ ] T6 · Verificação final
- **Critérios de aceite:**
  - [ ] `git diff <hash-dos-testes> -- tests/` vazio
  - [ ] `ruff check .` limpo
  - [ ] `hx check-clean` e `hx verify` em OK
  - [ ] `hx feature verify NUC-02` grava `passing`
  - [ ] `progress/NUC-02.md` atualizado; dono da NUC-01 avisado sobre `core/contracts.py` e `core/service.py` (pergunta 4)
- **Pronto quando:** os três comandos do `hx` terminam com código 0
