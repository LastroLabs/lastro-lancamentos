# Tasks — HX-10 · Rodar verify e check-clean na CI a cada push e pull request

**Plan:** planos/HX-10/plan.md · **Ficha:** features/HX-10.json
**Ordem:** T1 → revisão humana dos testes → commit só-de-testes (anotar o hash) → T2 em diante (sessão nova, sem editar `tests/`)

---

## [ ] T1 · Escrever os testes dos critérios
- **Critérios da ficha:** c1, c2, c3, c4, c5
- **Regra de negócio (em linguagem simples):** a CI é a rede de segurança do time. Os testes garantem que o arquivo do workflow tem as travas combinadas (sem segredo à toa, só leitura, sem tag solta) e que ninguém as remove sem querer.
- **Critérios de aceite:**
  - [ ] Existe um teste para cada nome citado em `verificacao` da ficha: `test_dispara_em_push_e_pull_request_sem_filtro`, `test_nao_usa_pull_request_target`, `test_permissoes_somente_leitura`, `test_todo_job_tem_timeout`, `test_jobs_verify_e_check_clean`, `test_unico_segredo_e_nomes_proibidos`, `test_actions_fixadas_por_sha`, `test_avisa_quando_falta_o_segredo_de_nomes`
  - [ ] `pyyaml` entra em `requirements-dev.txt` (D2; conferir licença e Python 3.12) e a imagem é refeita com `docker compose build`
  - [ ] Os testes leem `.github/workflows/pr.yml` com `yaml.safe_load`, aceitando a chave `on` lida como `True`, com o caminho calculado a partir do arquivo de teste
  - [ ] Todos falham hoje porque o `pr.yml` está vazio (comportamento ausente)
  - [ ] Cada teste falha também com um texto inválido de exemplo (ex.: `pull_request_target`, `uses: actions/checkout@v7`, segundo `secrets.*`), montado em `tmp_path` com dado inventado
- **Exemplos:**
  - `on:` com `push:` e `pull_request:` sem `branches:` → passa; com `branches: [main]` → falha
  - `uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` → passa; `@v7` → falha
  - dois segredos (`secrets.LASTRO_NOMES_PROIBIDOS` e `secrets.CHAVE_FALSA`) → falha
  - o comentário `# não usar pull_request_target` não conta como uso: o teste ignora linhas de comentário
- **Arquivos:** `tests/ci/test_pr_workflow.py` (novo), `requirements-dev.txt` (acrescenta `pyyaml`)
- **Reaproveitar:** estilo de `tests/harness/test_fase_e.py` (docstring com contrato, só dados sintéticos) · **Não criar:** outra lib de YAML, `conftest` global
- **Fora do escopo:** o workflow; qualquer mudança em `tools/`
- **Decisões relacionadas:** D2
- **Pronto quando:** `docker compose run --rm dev pytest tests/ci/test_pr_workflow.py -q` mostra só falhas esperadas

## [ ] T2 · Gatilhos, permissões, timeouts e job `verify`
- **Critérios da ficha:** c1, c2, c3 (parte `verify`), c4 (parte actions)
- **Regra de negócio (em linguagem simples):** todo push e todo PR dispara a conferência, em qualquer branch. O workflow só lê o repositório (não consegue alterar nada) e nenhum job pode ficar rodando para sempre. PR de fora nunca recebe segredos, por isso o gatilho é `pull_request`, nunca `pull_request_target`.
- **Critérios de aceite:**
  - [ ] `on:` tem `push:` e `pull_request:` sem `branches` nem `paths`; `pull_request_target` não aparece, nem em comentário
  - [ ] `permissions:` com só `contents: read` no nível do workflow
  - [ ] Job `verify` (nome fixo) com `timeout-minutes` e `runs-on: ubuntu-latest`
  - [ ] Passos: checkout fixado por SHA e `sh tools/hx verify`
  - [ ] Comentários em português no estilo do `deploy-docs.yml` (o que cada trava protege)
- **Exemplos:** `uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1` · job sem `timeout-minutes` → teste falha
- **Arquivos:** `.github/workflows/pr.yml`
- **Reaproveitar:** `hx verify` (já roda `docker compose run --rm -T dev`) · **Não criar:** `setup-python`, passo de instalar dependências
- **Fora do escopo:** `check-clean`, `deploy-docs.yml`, `tools/`
- **Decisões relacionadas:** D1, D3, D4. Reconferir o SHA com `gh api repos/actions/checkout/git/ref/tags/v7.0.1`
- **Pronto quando:** `pytest tests/ci/test_pr_workflow.py -q -k "dispara or pull_request_target or permissoes or timeout or sha"` passa

## [ ] T3 · Job `check-clean`, segredo e aviso
- **Critérios da ficha:** c3 (parte `check-clean`), c4 (segredo), c5
- **Regra de negócio (em linguagem simples):** o `check-clean` procura dado real e segredo no repositório. A lista de nomes proibidos mora num segredo do GitHub, porque a lista no Git revelaria os nomes. PR de fork não recebe o segredo; nesse caso a CI não pode passar calada: deve mostrar um aviso amarelo dizendo que a varredura de nomes foi pulada (padrão sugerido: só avisar; ver plan, pergunta 1).
- **Critérios de aceite:**
  - [ ] Job `check-clean` (nome fixo) com `timeout-minutes`, checkout fixado por SHA e `sh tools/hx check-clean`
  - [ ] `LASTRO_NOMES_PROIBIDOS` entra só por `env: ${{ secrets.LASTRO_NOMES_PROIBIDOS }}`; é o único `secrets.*` do arquivo
  - [ ] Passo próprio, antes da varredura, que emite `::warning::` quando a variável está vazia e não imprime o valor
  - [ ] O aviso diz o que aconteceu e o que fazer, em português simples (RF-AVI-02)
- **Exemplos:** variável vazia → anotação "varredura de nomes pulada: o segredo não está disponível (PR de fork?); a revisão humana deve conferir nomes" · variável definida → sem aviso
- **Arquivos:** `.github/workflows/pr.yml`
- **Reaproveitar:** `AVISO_SEM_NOMES` e `cmd_check_clean` (continuam como estão) · **Não criar:** nova varredura, mudança em `tools/harness.py`
- **Fora do escopo:** falhar o job sem o segredo (depende da pergunta 1); branch protection (config do GitHub)
- **Decisões relacionadas:** D5
- **Pronto quando:** `pytest tests/ci/test_pr_workflow.py -q` passa inteiro

## [ ] T4 · Verificação final
- **Critérios de aceite:**
  - [ ] `git diff <hash-dos-testes> -- tests/` vazio
  - [ ] `ruff check .` limpo
  - [ ] Nenhum dado real nem segredo no `pr.yml` (`hx check-clean`)
  - [ ] `hx check-clean` e `hx verify` em OK
  - [ ] `hx feature verify HX-10` grava `passing`
  - [ ] No PR, o 1º run do GitHub mostra os jobs `verify` e `check-clean` (registrar o resultado em `progress/HX-10.md`)
- **Pronto quando:** `hx check-clean`, `hx verify` e `hx feature verify HX-10` terminam com código 0
