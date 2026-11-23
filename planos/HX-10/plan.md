# Plan — HX-10 · Rodar verify e check-clean na CI a cada push e pull request

**Status:** pronto para revisão (0 bloqueantes; 3 atenções para o humano decidir)
**Branch:** feat/HX-10-rodar-verify-e-check-clean-na-ci-a-cada · **Data:** 17/11/2026 · **Responsável:** caio-nascime
**Tasks:** planos/HX-10/tasks.md

## 1. A decidir (humano)
| # | Pergunta | Gravidade | Sugestão de padrão | Decide |
|---|---|---|---|---|
| 1 | c5 tem `[definir: falhar ou só avisar]`: sem `LASTRO_NOMES_PROIBIDOS`, o check-clean falha ou só avisa? | ATENÇÃO | **Só avisar** (`::warning::`) e seguir. Falhar bloquearia todo PR de fork, que nunca recebe segredo. A revisão humana é a 2ª barreira (SECURITY.md §7) | caio-nascime (dono do harness) |
| 2 | Ativar *branch protection* na `main` exigindo os checks `verify` e `check-clean`? Sem isso a CI avisa, mas não impede o merge. Config do GitHub, fora do repo | ATENÇÃO | Sim, depois de o workflow rodar uma vez (o nome do check só aparece após a 1ª execução) | dono do repositório |
| 3 | `deploy-docs.yml` usa actions por tag (`@v7`, `@v6`, `@v5`), não por SHA. Está fora desta ficha | ATENÇÃO | Abrir ficha própria para fixar por SHA. Não mexer aqui | caio-nascime |

Mudanças sugeridas na ficha (o humano aplica em PR):
- c5: trocar `[definir: falhar ou só avisar]` pela resposta da pergunta 1.
- c3: o exemplo não diz *como* o job chama o `hx`. Sugestão de texto: "o job roda `sh tools/hx verify`" (ver D3).

## 2. Decisões tomadas pelo agente
### D1 · Dois jobs independentes (`verify` e `check-clean`), sem `needs`
- **Alternativas:** A) dois jobs em paralelo · B) um job só com dois passos · C) `check-clean` depois de `verify`
- **Escolhida:** A — **motivo:** a ficha exige os dois nomes de job; em paralelo, uma falha não esconde a outra e o `check-clean` (rápido, sem Docker) dá resposta cedo.
- **Fontes:** `features/HX-10.json` c3
- **Impacto:** T2, T3 · c3
- [ ] confirmar

### D2 · Testes leem o YAML com `pyyaml` (biblioteca liberada pelo humano em 17/11)
- **Alternativas:** A) texto/regex · B) `pyyaml` em `requirements-dev.txt` · C) `ruamel.yaml`
- **Escolhida:** B — **motivo:** o humano liberou a escolha de bibliotecas (AGENTS.md regra 12 atualizada). `pyyaml` é a opção mais simples e comum; lê a estrutura de verdade, sem regex frágil. Cuidado: YAML 1.1 lê a chave `on` como booleano `True`; o teste deve aceitar `True` ou `"on"`. `ruamel.yaml` (YAML 1.2) resolveria isso, mas é mais pesada. Licença MIT e suporte ao Python 3.12 vêm do meu conhecimento, **não verificados nesta sessão**: conferir na T1.
- **Fontes:** AGENTS.md regra 12; `requirements-dev.txt` (hoje só ruff e pytest)
- **Impacto:** T1 adiciona `pyyaml` ao `requirements-dev.txt` (a imagem Docker precisa de rebuild: `docker compose build`) e usa `yaml.safe_load` nos testes
- [ ] confirmar

### D3 · Os jobs chamam o harness por `sh tools/hx <comando>`, com o `python3` do runner
- **Alternativas:** A) `sh tools/hx …` · B) `./tools/hx …` · C) `actions/setup-python` + `python tools/harness.py`
- **Escolhida:** A — **motivo:** `ubuntu-latest` já traz `python3` e Docker (o `hx verify` usa `docker compose`, e o harness já passa `-T` e `--user` para CI). Com `sh` não depende do bit de execução (no Windows o git pode gravar 644). Evita uma action a mais para fixar. A string `hx verify` continua no arquivo, como o teste espera.
- **Fontes:** `tools/hx`, `tools/harness.py` (`montar_comando_docker`, `cmd_verify`) · runner: documentação do GitHub, **não verificada nesta sessão** (confirmar na 1ª execução real)
- **Impacto:** T2, T3
- [ ] confirmar

### D4 · Única action: `actions/checkout`, fixada em `v7.0.1` = `3d3c42e5aac5ba805825da76410c181273ba90b1`
- **Alternativas:** A) checkout v7.0.1 (última release) · B) manter a tag móvel `@v7` (como o deploy-docs) · C) `git clone` manual
- **Escolhida:** A — **motivo:** c4 exige SHA de 40 hex. Comentário `# v7.0.1` ao lado do SHA para facilitar atualização.
- **Fontes:** `gh api repos/actions/checkout/git/ref/tags/v7.0.1` e `releases/latest` (acesso em 17/11/2026). O SHA deve ser reconferido na T2.
- **Impacto:** T2, T3 · c4
- [ ] confirmar

### D5 · O aviso de c5 vem de um passo do workflow, não de mudança no `hx`
- **Alternativas:** A) passo `if [ -z "$LASTRO_NOMES_PROIBIDOS" ]` que emite `::warning::` · B) alterar `tools/harness.py` para imprimir `::warning::`
- **Escolhida:** A — **motivo:** o `hx check-clean` já avisa em texto no stderr (`AVISO_SEM_NOMES`), mas não como anotação visível do GitHub. Mexer em `tools/` está fora do módulo `ci` e exige o dono (CODEOWNERS). O passo só testa se a variável está vazia; nunca imprime o valor.
- **Fontes:** `tools/harness.py:441-442,606-616`
- **Impacto:** T3 · c5
- [ ] confirmar

## 3. Resumo e abordagem
Preencher `.github/workflows/pr.yml` (hoje vazio, 0 bytes) com um workflow de 2 jobs. Primeiro os testes (`tests/ci/test_pr_workflow.py`, lendo o arquivo como texto), depois o cabeçalho (gatilhos, permissões), o job `verify` e o job `check-clean` com o aviso.
Ordem: T1 testes → T2 gatilhos, permissões, timeouts e job `verify` → T3 job `check-clean`, segredo e aviso → T4 verificação final.
O segredo `LASTRO_NOMES_PROIBIDOS` só entra por `env` no passo do check-clean. Nada de chave de LLM.

## 4. Contexto encontrado
- **Código relacionado:** `.github/workflows/pr.yml` (vazio, criado em 1ff4398); `tools/harness.py` (`cmd_verify`, `cmd_check_clean`, `VARIAVEL_NOMES`, `AVISO_SEM_NOMES`); `tools/hx`; `docker-compose.yml` (serviço `dev`); `.github/workflows/deploy-docs.yml` (modelo de estilo e comentários)
- **Dependências:** nenhuma (`depende_de: []`)
- **Reaproveitar:** `hx verify` e `hx check-clean` como estão; estilo de comentário do `deploy-docs.yml`; padrão dos testes em `tests/harness/` (Path relativo ao repo, só dados inventados)
- **Não criar:** outra lib de YAML além do `pyyaml`, outro workflow, outra lógica de varredura, mudança em `tools/`
- **Pesquisa externa:** só a consulta do SHA do checkout (D4); sem outra pesquisa necessária
- **Aviso do repo:** `hx verify` ainda marca Arquitetura e E2E como PULADO; a CI herda isso

## 5. Decisões (já resolvidas)
- (nenhuma ainda)

## 6. Avaliação da ficha
| # | Achado | Gravidade | Critério |
|---|---|---|---|
| 1 | `[definir: falhar ou só avisar]` ainda aberto | ATENÇÃO | c5 |
| 2 | Testes só provam o **texto** do YAML; não provam que o workflow roda de verdade. A prova real é o 1º run no GitHub (ver risco 1) | ATENÇÃO | c1–c5 |
| 3 | c4 "nenhuma chave de LLM": o teste só confere que o único `secrets.*` é o de nomes; nomes de variáveis `env` não são checados | ATENÇÃO | c4 |
| 4 | Ficha `features/HX-10.json` está `in_progress` e sem dependências; tamanho adequado (5 critérios, 1 módulo) | OK | — |
| 5 | Verificações são `pytest` (permitido pelo SECURITY.md §7) e cobrem cada critério | OK | c1–c5 |
| 6 | Risco de dado real: nenhum; o workflow não carrega dados | OK | — |

## 7. Riscos
1. Workflow passa nos testes mas falha no GitHub (Docker, permissões) → abrir o PR e conferir o 1º run antes de aprovar; ajustar pelo log (sem imprimir valores).
2. `fetch-depth` padrão (1) basta, pois o check-clean usa `git ls-files`. Se o git falhar, o harness percorre a árvore.
3. Fork não recebe segredo → aviso `::warning::` e a varredura de nomes é pulada; a revisão humana cobre.
4. Se o SHA do checkout for mal copiado, o run falha → T2 reconfere por `gh api`.
5. Com `contents: read`, o `GITHUB_TOKEN` não escreve nada; nenhum passo precisa de escrita.

## 8. Aprovação
- [ ] Perguntas BLOQUEANTES respondidas (nenhuma aberta)
- [ ] Decisões do agente D1–D5 confirmadas
- [ ] Plan e tasks revisados por <nome> em DD/MM
