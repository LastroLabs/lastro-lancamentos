# Tasks — HX-11 · Espelhar as fichas no Project da organização com issues, responsáveis e bloqueios

**Plan:** planos/HX-11/plan.md · **Ficha:** features/HX-11.json
**Ordem:** T1 → revisão humana dos testes → commit só-de-testes (anotar o hash) → T2 em diante (sessão nova, sem editar `tests/`)
**Antes de tudo:** a nova versão da ficha (c1, c2) está aplicada. Os nomes de teste de c1 e c2 abaixo vêm da versão atual: na T1, use os da ficha nova.
**Colunas (20/11):** A FAZER, FAZENDO, EM REVISÃO, FINALIZADA, REGREDIU. `blocked` não move.

---

## [ ] T1 · Escrever os testes dos critérios
- **Critérios da ficha:** c1, c2, c3, c4
- **Regra de negócio (em linguagem simples):** o quadro do time (Project) deve refletir as fichas sem ninguém copiar à mão. Os testes provam isso com uma "API falsa" em memória que guarda issues, itens, colunas, responsáveis e bloqueios e registra toda chamada de escrita. Nada de rede.
- **Critérios de aceite:**
  - [ ] Existe um teste para cada nome em `verificacao`: `test_cria_issue_para_ficha_sem_item`, `test_nao_duplica_e_segunda_execucao_nao_altera`, `test_responsavel_desconhecido_avisa_sem_falhar`, `test_branch_move_so_o_proprio_card`, `test_pr_aberto_vai_para_em_revisao`, `test_developer_nunca_recua_status`, `test_passing_em_developer_finaliza_e_fecha_issue`, `test_reconcilia_responsavel`, `test_reconcilia_bloqueios`, `test_ficha_removida_nao_apaga_issue`, `test_dry_run_nao_escreve`, `test_falha_api_exit_2_sem_tocar_fichas`
  - [ ] O contrato assumido fica na docstring do arquivo: módulo `tools/project_sync.py` com `main(argv, raiz, api=None) -> int`; argumentos de D7; `api` é objeto com métodos de leitura (`listar_issues`, `listar_itens`, `listar_branches`, `listar_prs`, `login_existe`) e de escrita (`criar_issue`, `atualizar_titulo`, `adicionar_ao_projeto`, `definir_coluna`, `definir_responsaveis`, `definir_bloqueios`, `fechar_issue`, `reabrir_issue`)
  - [ ] Todos falham hoje porque o módulo não existe
  - [ ] Cada teste monta as fichas em `tmp_path` com IDs e logins inventados (HX-20, `dev-um`); o teste de 401 confere o hash de `features/` antes e depois
- **Exemplos:** os do `exemplo` de cada critério da ficha, com logins inventados; 2ª execução → lista de chamadas de escrita vazia
- **Arquivos:** `tests/ci/test_project_sync.py` (novo)
- **Reaproveitar:** estilo de `tests/ci/test_pr_workflow.py` e `sys.path.insert` de `tests/harness/` · **Não criar:** `conftest` global, fixture com dado que pareça real
- **Fora do escopo:** código de produção
- **Pronto quando:** `docker compose run --rm dev pytest tests/ci/test_project_sync.py -q` mostra só falhas esperadas

## [ ] T2 · Plano de mudanças e criação de issues sem duplicar (c1)
- **Critérios da ficha:** c1
- **Regra de negócio (em linguagem simples):** só em `developer`, para cada ficha em `features/`, procura o issue cujo título casa com `^<ID>: `. Se não existe, cria `ID: título`, põe o card no Project na coluna do estado e define o responsável. Se o título da ficha mudou, atualiza o título do issue. Se já está tudo certo, não faz nada, então rodar duas vezes não muda nada. Responsável que não existe no GitHub fica em branco e o log avisa.
- **Critérios de aceite:**
  - [ ] Ficha sem issue gera uma mudança "criar" com a coluna do mapa (`not_started`→A FAZER...)
  - [ ] Issue existente não é criado de novo; `HX-2: ...` não casa com `HX-20` (expressão exata)
  - [ ] Título diferente gera "atualizar título"; segunda execução devolve lista vazia
  - [ ] Login desconhecido: sem responsável, aviso no log, exit 0
  - [ ] Issue já existente fora do Project só é adicionado ao Project
- **Exemplos:** HX-20 (`not_started`, já tem issue) → nada; HX-21 (`in_progress`, login `inexistente-xyz`) → cria em FAZENDO, sem responsável, aviso
- **Arquivos:** `tools/project_sync.py` (novo)
- **Reaproveitar:** `harness.carregar_fichas` · **Não criar:** outro leitor de fichas
- **Fora do escopo:** coluna por origem (T3), bloqueios (T4), chamadas HTTP reais (T6)
- **Decisões relacionadas:** D5, D6, D7
- **Pronto quando:** `pytest tests/ci/test_project_sync.py::test_cria_issue_para_ficha_sem_item tests/ci/test_project_sync.py::test_nao_duplica_e_segunda_execucao_nao_altera tests/ci/test_project_sync.py::test_responsavel_desconhecido_avisa_sem_falhar -q` passa

## [ ] T3 · Coluna do card conforme a origem (c2)
- **Critérios da ficha:** c2
- **Regra de negócio (em linguagem simples):** o card anda conforme onde o trabalho está, e nada de branch de feature roda com segredo. A execução agendada não lê `features/`: pergunta ao GitHub quais branches `feat/<ID>-*` e quais PRs existem. PR aberto → EM REVISÃO. PR fechado sem merge → FAZENDO. Branch sem PR com card em A FAZER → FAZENDO. Em `developer` o card só avança (A FAZER < FAZENDO < EM REVISÃO < FINALIZADA) e REGREDIU fica fora da ordem: `passing` → FINALIZADA e fecha o issue; `regressed` → REGREDIU e reabre o issue; `blocked` não move. Só developer cria card: na agendada, card inexistente gera só aviso.
- **Critérios de aceite:**
  - [ ] `--origem agendada`: branch `feat/HX-20-...` sem PR com card em A FAZER → FAZENDO; ignora branch fora do padrão e não toca card que não esteja em A FAZER
  - [ ] Agendada: PR aberto → EM REVISÃO; PR fechado sem merge → FAZENDO; PR com merge não é tocado
  - [ ] `--origem developer` nunca reduz a posição, exceto `regressed` → REGREDIU (reabre) e `passing` vindo de REGREDIU → FINALIZADA (fecha)
  - [ ] Cruzamentos (seção 5 do plan): a agendada só mexe em A FAZER, FAZENDO e EM REVISÃO; com mais de um PR vale o mais recente; em developer, `in_progress` não tira card de REGREDIU nem de FINALIZADA
  - [ ] Card inexistente na agendada → aviso, nenhuma criação; a agendada nunca chama `features/`
- **Exemplos:** branches `feat/HX-20-x` e `docs/y` → só HX-20 em FAZENDO; PR aberto de `feat/HX-21-y` com card em FAZENDO → EM REVISÃO; HX-22 `not_started` com card em FAZENDO, origem developer → continua FAZENDO; HX-23 `passing` → FINALIZADA e fechado; HX-24 `regressed` com card em FINALIZADA → REGREDIU e reaberto
- **Arquivos:** `tools/project_sync.py`
- **Reaproveitar:** a lista de mudanças da T2 · **Não criar:** segundo caminho de decisão; leitura de `features/` da branch
- **Fora do escopo:** o workflow e o agendamento (HX-12)
- **Decisões relacionadas:** D7
- **Pronto quando (nomes da ficha atual; trocar pelos da ficha nova):** `pytest tests/ci/test_project_sync.py::test_branch_move_so_o_proprio_card tests/ci/test_project_sync.py::test_pr_aberto_vai_para_em_revisao tests/ci/test_project_sync.py::test_developer_nunca_recua_status tests/ci/test_project_sync.py::test_passing_em_developer_finaliza_e_fecha_issue -q` passa

## [ ] T4 · Reconciliar responsável e bloqueios (c3)
- **Critérios da ficha:** c3
- **Regra de negócio (em linguagem simples):** só em `developer`, o issue deve ter exatamente o responsável da ficha e ser bloqueado exatamente pelos issues das fichas em `depende_de`. O que sobrou do lado do GitHub é removido; o que falta é adicionado. Ficha apagada não apaga issue: ele fica aberto e o log avisa.
- **Critérios de aceite:**
  - [ ] Troca de responsável (logins inventados nos testes, ex.: `dev-um` → `dev-dois`) deixa só o novo
  - [ ] `depende_de` de `[HX-01]` para `[HX-02]` remove o bloqueio antigo e adiciona o novo
  - [ ] Dependência sem issue ainda: aviso e segue
  - [ ] Issue sem ficha: não é tocado e gera aviso
- **Exemplos:** HX-20 com `depende_de: [HX-02]` → bloqueada só por HX-02; issue de HX-23 (ficha removida) → aberto, aviso
- **Arquivos:** `tools/project_sync.py`
- **Reaproveitar:** mudanças da T2 · **Não criar:** outra forma de marcar bloqueio (D3)
- **Fora do escopo:** o campo `bloqueada_por` (D-xx)
- **Decisões relacionadas:** D3
- **Pronto quando:** `pytest tests/ci/test_project_sync.py::test_reconcilia_responsavel tests/ci/test_project_sync.py::test_reconcilia_bloqueios tests/ci/test_project_sync.py::test_ficha_removida_nao_apaga_issue -q` passa

## [ ] T5 · Aplicar, `--dry-run` e erros com código 2 (c4)
- **Critérios da ficha:** c4
- **Regra de negócio (em linguagem simples):** primeiro o script decide o que mudar; depois aplica. Com `--dry-run` só mostra a lista e não escreve nada. Se a API recusar a credencial (401), o script para com código 2 e a mensagem ERRO/MOTIVO/CORREÇÃO manda conferir `APP_CLIENT_ID` e `APP_PRIVATE_KEY`. Nunca imprime o token. Nunca grava em `features/`.
- **Critérios de aceite:**
  - [ ] `--dry-run` com 2 mudanças lista as 2 e a API falsa não registra escrita
  - [ ] 401 → código 2, 3 linhas ERRO/MOTIVO/CORREÇÃO em stderr, texto cita os dois nomes, token ausente da saída
  - [ ] Hash de `features/` igual antes e depois
  - [ ] `ruff check tools/project_sync.py tests/ci/test_project_sync.py` limpo
- **Exemplos:** dry-run → "2 mudanças pendentes", 0 escritas; 401 → exit 2
- **Arquivos:** `tools/project_sync.py`
- **Reaproveitar:** `HarnessErro`, `mostrar_erro`, padrão de `harness.main` · **Não criar:** formato de erro novo
- **Decisões relacionadas:** D6, D7
- **Pronto quando:** `pytest tests/ci/test_project_sync.py::test_dry_run_nao_escreve tests/ci/test_project_sync.py::test_falha_api_exit_2_sem_tocar_fichas -q` e `ruff check tools/project_sync.py tests/ci/test_project_sync.py` passam

## [ ] T6 · Cliente real do GitHub (`urllib`)
- **Critérios da ficha:** c1–c4 (é o que liga as peças à API de verdade)
- **Regra de negócio (em linguagem simples):** a classe que de fato fala com o GitHub: issues e bloqueios por REST, itens e colunas do Project por GraphQL (2 passos: adicionar item, depois definir a coluna pelo ID da opção). Lê o token de `GH_TOKEN`; 401 e 403 viram `HarnessErro`.
- **Critérios de aceite:**
  - [ ] Bloqueio usa o campo numérico `id` do issue, não o `number` (decisão de 20/11); confirmado com uma chamada real, feita à mão num issue de teste, e o resultado anotado no `progress/HX-11.md`
  - [ ] `listar_branches` e `listar_prs` paginam; `listar_prs` devolve branch de origem, estado (aberto/fechado) e se houve merge
  - [ ] Leitura do Project com paginação
  - [ ] Transporte trocável: os testes injetam um falso, nenhum teste chama a rede
  - [ ] Pausa curta entre escritas (limite secundário de taxa)
- **Arquivos:** `tools/project_sync.py`
- **Não criar:** dependência nova (D1) · **Fora do escopo:** workflow (HX-12) e criação do App (pré-requisito)
- **Decisões relacionadas:** D1, D2, D3
- **Pronto quando:** `pytest tests/ci/test_project_sync.py -q` inteiro passa

## [ ] T7 · Documentar o módulo
- **Regra de negócio (em linguagem simples):** quem for ligar o sync precisa saber o que criar fora do repositório.
- **Critérios de aceite:**
  - [ ] `docs/modulos/ci.md` descreve: comando, as 2 origens (`developer`, `agendada`) e `--dry-run`, variáveis (`GH_TOKEN`, org `LastroLabs`, `PROJECT_NUMBER`), o campo `Status` com as 5 opções e o mapa de estados, e o que o script nunca faz (escrever em `features/`, ler código de branch de feature). O App aparece só como pré-requisito, com link para a HX-12
  - [ ] Sem segredo, sem nome real, sem exemplo com dado real
- **Arquivos:** `docs/modulos/ci.md` (novo) · **Fora do escopo:** o workflow
- **Pronto quando:** `hx check-clean` em OK

## [ ] T8 · Verificação final
- **Critérios de aceite:**
  - [ ] `git diff <hash-dos-testes> -- tests/` vazio
  - [ ] `ruff check .` limpo
  - [ ] `hx check-clean` e `hx verify` em OK
  - [ ] `hx feature verify HX-11` grava `passing`
- **Pronto quando:** os três comandos do `hx` terminam com código 0
