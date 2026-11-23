# Uma feature do começo ao PR: o harness do Lastro em uso

> **Para quem é:** qualquer pessoa do time que vai pegar a primeira feature. Leia do começo ao fim uma vez; depois use como roteiro.
> **A história:** Caio vai fazer a **HAR-02** ("Filtrar `hx state` por estado e resumir só o que pede atenção"), no Windows com PowerShell.
> **Aviso:** as saídas de terminal e os trechos de arquivo abaixo são **ilustrativos**. Mostram o formato esperado; os textos exatos dependem da implementação. Nomes de testes e de arquivos vêm das fichas e dos guias.
> **Pré-requisito:** o harness já está construído e as fichas `HX-01` a `HX-09` estão `passing`. A HAR-02 depende da `HX-09`.

---

## Visão geral

```
 0. Ficha existe e foi aprovada em PR
 1. Preparar a máquina e ver o estado       hx state
 2. Abrir a feature                         hx feature start HAR-02
 3. Planejar com o agente                   /planejar HAR-02
 4. Revisar o plano (humano)
 5. Sessão 1: gerar os testes
 6. Revisar os testes e ver falharem        (humano)
 7. Commitar só os testes e anotar o hash
 8. Sessão 2: implementar
 9. Conferir: testes verdes, tests/ intacto, ruff
10. Comandos finais                         hx check-clean · hx verify · hx feature verify
11. Fechar a sessão e subir o PR
12. CI, revisão com a rubrica e merge
```

| Quem | Faz |
|---|---|
| **Dev** (Caio) | conduz o fluxo, responde perguntas, revisa plano e testes, decide |
| **Agente de planejamento** | pesquisa o repo, avalia a ficha, escreve o plano (`/planejar`) |
| **Agente de testes (sessão 1)** | escreve **só** testes |
| **Agente de implementação (sessão 2)** | escreve **só** código, sem tocar em `tests/` |
| **Script `hx`** | valida, abre a feature, roda verificações e **é o único que muda `estado` e `evidencia`** |
| **Revisor** | aplica a rubrica no PR e decide aceitar ou pedir mudança |

Cada sessão do agente é **nova**. Um agente não herda o raciocínio do outro; herda só o que está em arquivo (ficha, plano, testes, `progress`). Isso é de propósito.

---

## Capítulo 0 — A ficha já existe

Semanas antes, alguém abriu um PR criando `features/HAR-02.json`, seguindo o `feature_template.md`. O revisor conferiu: 4 critérios, cada um com exemplo de entrada e saída, cada um com comando de verificação (`pytest ...` ou `ruff ...`), `estado: not_started`, `evidencia: null`. O PR foi mesclado.

Trecho da ficha (resumido):

```json
{
  "id": "HAR-02",
  "titulo": "Filtrar hx state por estado e resumir só o que pede atenção",
  "modulo": "harness",
  "estado": "not_started",
  "responsavel": "caio",
  "depende_de": ["HX-09"],
  "criterios": [
    { "id": "c1", "descricao": "hx state aceita um ou mais estados e lista só as fichas desses estados", "exemplo": { "...": "..." } }
  ],
  "verificacao": [
    { "criterio": "c1", "comando": "pytest tests/harness/test_state_filtro.py::test_filtro_um_estado -q" }
  ],
  "evidencia": null
}
```

**Regra do capítulo:** a ficha diz **o quê** e **como provar**. Não diz como implementar, não guarda progresso, não tem datas.

---

## Capítulo 1 — Segunda-feira, 9h: preparar e olhar o estado

Caio abre o PowerShell na raiz do repositório e atualiza a `main`:

```powershell
git switch main
git pull
. .\tools\hx.ps1        # carrega o atalho "hx" nesta janela (só uma vez por janela)
```

Depois, o primeiro comando de qualquer dia de trabalho:

```powershell
hx state
```

Saída (ilustrativa):

```
Lastro — estado das features
ID      Estado       Resp.   Prior.  Título
HAR-02  not_started  caio    P1      Filtrar hx state por estado e resumir só o que pede atenção
HX-01   passing      caio    P0      Ter o esqueleto do hx com erros padronizados
...
Resumo: 9 passing · 0 in_progress · 1 not_started · 0 blocked · 0 regressed
```

**Como ler:** `not_started` e sem ninguém em `in_progress` significa que Caio pode pegar a HAR-02. Se alguma ficha estivesse inválida, o `hx state` **não** listaria nada e mostraria ERRO / MOTIVO / CORREÇÃO.

**Antes de abrir:** conferir `AGENTS.md` (regras) e a ficha. A pergunta é: "eu entendo o que é pedido?". Dúvida grande aqui é normal, e o passo 3 existe para tratá-la.

---

## Capítulo 2 — Abrir a feature

```powershell
hx feature start HAR-02
```

O `hx` faz, nesta ordem (sem rede primeiro):

1. confere que a ficha existe e que **todas** as fichas são válidas;
2. confere que `responsavel` é você;
3. confere o estado (`not_started` ou `regressed`) e que `HX-09` está `passing`;
4. confere que você não tem outra feature aberta (uma por pessoa);
5. busca o remoto, vê que ninguém abriu branch `feat/HAR-02-*`, e confere árvore limpa.

Depois **pergunta** se você quer criar a branch a partir de `origin/developer` (`[s/N]`).

- **Sim:** cria a branch a partir de `origin/developer`, cria `progress/HAR-02.md` a partir do template, muda o estado para `in_progress`, commita e dá push.
- **Não** (ou `--sem-branch`): não cria branch, não commita e não dá push. Só muda a ficha para `in_progress` e cria o `progress/HAR-02.md` no seu disco. Você cria a sua branch (por exemplo, a partir da de um colega) e faz o primeiro commit com esses dois arquivos.
- Fora de um terminal (CI, scripts), assume sim.

Saída (ilustrativa):

```
Branch criada: feat/HAR-02-filtrar-hx-state-por-estado-e-resumir-so
progress/HAR-02.md criado
Estado: not_started -> in_progress
Próximo passo: rode /planejar HAR-02 em uma sessão nova do Claude Code
```

**Conferir:**

```powershell
git branch --show-current
git log --oneline -1
```

Você já está **dentro da branch** da feature. Todo trabalho daqui em diante acontece nela.

O `progress/HAR-02.md` nasce assim (trecho): cabeçalho com ID, título, responsável, branch e data; as seções **Objetivo**, **Próxima ação** e **Bloqueios e perguntas** (reescritas a cada sessão) e **Feito**, **Rodei**, **Falhou**, **Decisões** (só acrescenta, linhas com `DD/MM · S1 ·`).

**Se der erro:** o `hx` explica o motivo e a correção. Os mais comuns: "responsável diferente", "você já tem uma feature aberta", "árvore suja" (commit ou guarde o que está pendente) e "dependência não está passing".

---

## Capítulo 3 — O agente avalia e planeja

Caio abre o Claude Code **em uma sessão nova** e roda:

```
/planejar HAR-02
```

O agente:
- lê `AGENTS.md`, `SECURITY.md`, a ficha, o `progress` e as fichas de que a HAR-02 depende;
- procura código e testes do módulo, e lista o que já existe e deve ser reaproveitado;
- pesquisa também na web, **só quando a feature exige escolha** (biblioteca, formato, regra técnica), sempre com o link da fonte; se não exige, registra "sem pesquisa externa necessária";
- avalia a ficha e classifica cada achado como **BLOQUEANTE** ou **ATENÇÃO**;
- escreve **dois documentos** em `planos/HAR-02/`:
  - `plan.md`: no topo, **A decidir** (o que depende de um humano, com sugestão de padrão); em seguida, as **decisões tomadas pelo agente**, cada uma com alternativas, motivo, fonte e `[ ] confirmar`; depois avaliação da ficha, contexto, riscos e aprovação;
  - `tasks.md`: até 8 tasks, cada uma com regra de negócio explicada, critérios de aceite, exemplos, arquivos, reaproveitar/não criar e o comando de "pronto quando". A **T1 é sempre** escrever os testes.

**Não faz:** não escreve código, não edita fichas, não toca em `estado` nem `evidencia`.

Resposta no chat (ilustrativa):

```
Status: rascunho (aguardando respostas)
Achados: 1 bloqueante, 2 atenção
Plano: planos/HAR-02/plan.md · Tasks: planos/HAR-02/tasks.md
Perguntas principais:
1. `hx state in_progress --resumo` é erro ou combinação válida? Sugestão: erro, código 2.
2. O filtro aceita estado repetido (`in_progress in_progress`)? Sugestão: ignorar a repetição.
3. Filtro sem resultado imprime mensagem e sai com 0? Sugestão: sim.
```

---

## Capítulo 4 — Revisar o plano (portão humano)

Caio abre `planos/HAR-02/plan.md` e `planos/HAR-02/tasks.md` e faz cinco coisas:

1. **Responde as perguntas** de "A decidir" no `plan.md`, movendo-as para "Decisões":
   ```
   - 16/11 · combinar filtro com --resumo é erro, código 2 (pergunta 1)
   ```
2. **Confirma cada decisão do agente:** concorda com a alternativa escolhida e com a fonte? Marca `[x] confirmar`, ou anota a mudança.
3. **Confere o contexto:** o plano aponta para código que existe de verdade? Algo a reaproveitar que ficou de fora?
4. **Confere as tasks** no `tasks.md`: a T1 é "escrever os testes"? Cada task tem regra de negócio, critérios de aceite, exemplos, arquivos e comando de "pronto quando"?
5. **Decide se a ficha muda.** Uma resposta que altere critério (por exemplo, a combinação filtro + `--resumo` passar a ser erro) muda a **ficha**, e isso entra por PR separado: a ficha é o contrato.

Quando não houver pergunta bloqueante pendente, Caio marca:

```
- [x] Perguntas BLOQUEANTES respondidas
- [x] Plano revisado por Caio em 16/11
```
e muda o `Status` para `aprovado`.

Se as respostas mudarem muita coisa, vale rodar `/planejar HAR-02` de novo em sessão nova, com o plano atualizado.

Depois ele commita:

```powershell
git add planos/HAR-02/ progress/HAR-02.md
git commit -m "docs(HAR-02): plano aprovado"
```

---

## Capítulo 5 — Sessão 1: só os testes

Sessão **nova** do Claude Code. Prompt base (troque `<ID>` e os caminhos):

```
Leia AGENTS.md, features/<ID>.json, planos/<ID>/plan.md e planos/<ID>/tasks.md.

Tarefa: escrever APENAS os testes da feature <ID>, em tests/<caminho>/test_<nome>.py.
NÃO crie nem edite código de produção (src/ ou tools/). NÃO edite a ficha nem o plano.

Regras:
- Os nomes de teste citados em "verificacao" da ficha são OBRIGATÓRIOS e devem existir exatamente com esses nomes.
- Um teste por critério, no mínimo; cubra também os casos de borda e os erros descritos no plano.
- Use apenas dados inventados. Nenhum dado real, nenhum segredo.
- Git, docker e relógio, quando necessários, entram por funções injetáveis; os testes não fazem rede.
- Cada teste deve falhar hoje pelo motivo certo (comportamento ainda não existe), não por erro de sintaxe ou import.

Ao terminar:
1. Rode: docker compose run --rm dev pytest <arquivo de teste> -q
2. Diga quais testes falham e por quê.
3. Liste os testes que escreveu, um por critério.
```

Para a HAR-02, o resultado é `tests/harness/test_state_filtro.py`, com `test_filtro_um_estado`, `test_filtro_varios_estados`, `test_filtro_resumo_conta_todas`, `test_filtro_sem_resultado_exit_0`, `test_filtro_estado_invalido_exit_2`, `test_filtro_nao_esconde_ficha_invalida`, `test_resumo_mostra_so_atencao` e `test_resumo_conta_demais`.

**Por que sessão separada:** quem escreve o teste não pode ser o mesmo que depois escreve o código, senão o teste tende a espelhar a implementação em vez de provar o comportamento.

---

## Capítulo 6 — Verificar que os testes falham (e revisá-los)

Caio roda ele mesmo:

```powershell
docker compose run --rm dev pytest tests/harness/test_state_filtro.py -q
```

Saída esperada: **todos falhando**, e pelo motivo certo.

```
FAILED ... test_filtro_um_estado - ... (o comando não aceita o argumento de estado)
...
8 failed
```

**Duas conferências:**

| Se… | Significa | Faça |
|---|---|---|
| todos falham por "comportamento ausente" | ✅ teste válido | siga |
| algum **passa** | o teste não prova nada novo | peça para refazer ou fortalecer |
| falha por `SyntaxError` ou import quebrado | teste mal escrito | peça correção |

Depois, a **revisão humana dos testes**, com o checklist:

1. Cada falha é pelo motivo certo?
2. Os `assert` comparam **valores concretos** (código de saída, texto, campos), e não só "não levantou exceção"?
3. O teste substitui só a dependência externa, nunca a coisa testada?
4. Os caminhos de erro têm teste?
5. Tem literal de dado sensível? (CPF/CNPJ válido, chave, nome real)
6. Algum teste depende de ordem, relógio real ou rede?
7. Todos os testes que a ficha cita existem com o nome exato?

Esse é o **único** ponto que impede o agente de aprovar o próprio trabalho. Não pule.

---

## Capítulo 7 — Commitar só os testes e anotar o hash

```powershell
git add tests/
git commit -m "test(HAR-02): testes dos criterios (so testes)"
git rev-parse --short HEAD
```

A saída do último comando é o **hash dos testes** (por exemplo, `a1b2c3d`). Caio o anota no `progress/HAR-02.md`, em "Feito":

```
16/11 · S1 · Testes commitados, hash a1b2c3d, 8 testes, todos falhando pelo motivo certo
```

e atualiza "Próxima ação": `T2 — implementar o filtro por estado (sessão 2)`.

O hash é a **âncora**: depois da implementação, `git diff a1b2c3d -- tests/` precisa sair vazio.

---

## Capítulo 8 — Sessão 2: só a implementação

Sessão **nova**. Prompt base:

```
Leia AGENTS.md, features/<ID>.json, planos/<ID>/plan.md e planos/<ID>/tasks.md.

Tarefa: implementar a feature <ID> até que os testes em tests/<caminho>/test_<nome>.py passem.

PROIBIDO editar qualquer arquivo dentro de tests/. Se um teste parecer errado ou contraditório,
PARE e explique o problema, em vez de alterá-lo.
Reaproveite o que o plano manda reaproveitar e não crie o que ele manda não criar.
Siga a abordagem, os contratos e os casos de borda do plano. Não implemente nada fora do escopo.

Ao terminar:
1. Rode todos os testes: docker compose run --rm dev pytest -q
2. Rode o lint: docker compose run --rm dev ruff check .
3. Mostre as saídas e liste os arquivos que alterou.
```

O agente trabalha as tasks do plano em ordem e marca cada uma como concluída. Ao longo da sessão ele atualiza o `progress` quando Caio pede para encerrar (regra do `AGENTS.md`).

**Se o agente discordar de um teste:** ele para e explica. Caio decide: se o teste está errado, **ele mesmo** corrige em um commit separado (ou refaz a sessão 1), e anota a decisão no `progress`. O agente de implementação nunca corrige o teste que precisa satisfazer.

---

## Capítulo 9 — Conferir o trabalho do agente

Não confie só no relatório dele. Caio confere:

```powershell
# 1. Os testes continuam intactos? (precisa sair VAZIO)
git diff a1b2c3d -- tests/

# 2. Testes da feature
docker compose run --rm dev pytest tests/harness/test_state_filtro.py -q

# 3. Lint
docker compose run --rm dev ruff check .
```

| Resultado | Significa |
|---|---|
| diff vazio, testes verdes, lint limpo | ✅ pode seguir |
| **diff com linhas** | o agente mexeu nos testes. Descarte a sessão: `git restore tests/` e refaça a sessão 2 |
| teste ainda falhando | volte à sessão 2 com a saída do erro |

**Teste manual rápido** (cinco minutos, vale a pena):

```powershell
hx state in_progress
hx state feito          # deve recusar com código 2 e listar os estados válidos
hx state --resumo
```

**"Quebre de propósito":** altere uma linha da implementação (por exemplo, inverta o filtro) e confirme que pelo menos um teste falha. Reverta em seguida. Se nada falhar, os testes não protegem aquele trecho.

---

## Capítulo 10 — Os comandos finais

Commite o código antes, porque o `hx feature verify` exige árvore limpa:

```powershell
git add src/ tools/ planos/ progress/
git commit -m "feat(HAR-02): filtro de estado e --resumo no hx state"
```

Depois, em ordem:

```powershell
hx check-clean
hx verify
hx feature verify HAR-02
```

1. **`hx check-clean`** procura dado real e segredo no repositório. Esperado: `RESULTADO: OK`. Se acusar algo, mostra arquivo, linha e **tipo** (nunca o valor). Remova e rode de novo.
2. **`hx verify`** roda `ruff check .` e `pytest -q` no container. Esperado:
   ```
   [1/2] ruff check .   OK
   [2/2] pytest -q      OK
   Arquitetura: PULADO (ainda não implementado)
   E2E: PULADO (ainda não implementado)
   RESULTADO: OK
   ```
3. **`hx feature verify HAR-02`** roda **cada comando de verificação da ficha**, na ordem. Se tudo passar, ele (e só ele) muda a ficha para `passing` e grava a evidência (data, commit e resultados). Se algum falhar, a ficha não muda e ele diz qual critério falhou.

A ficha mudou, então há uma alteração a commitar:

```powershell
git add features/HAR-02.json
git commit -m "chore(HAR-02): verificada (passing) por hx feature verify"
```

**Nunca** edite `estado` ou `evidencia` à mão. A rubrica de revisão bloqueia isso.

---

## Capítulo 11 — Fechar a sessão e subir o PR

**Fechar a sessão.** Caio diz ao agente: "vou encerrar a sessão". Pela regra do `AGENTS.md`, o agente atualiza `progress/HAR-02.md`:
- reescreve **Objetivo**, **Próxima ação** e **Bloqueios e perguntas**;
- acrescenta linhas datadas em **Feito**, **Rodei**, **Falhou** e **Decisões**;
- marca o checklist de fim de sessão.

Caio lê, corrige se preciso e commita.

**Subir:**

```powershell
git push
gh pr create --fill     # ou abra pelo site do GitHub
```

O corpo do PR segue `.github/pull_request_template.md`:

```
Feature: HAR-02
Critério -> teste:
  c1 -> test_filtro_um_estado, test_filtro_varios_estados
  c2 -> test_filtro_resumo_conta_todas, test_filtro_sem_resultado_exit_0
  c3 -> test_filtro_estado_invalido_exit_2, test_filtro_nao_esconde_ficha_invalida
  c4 -> test_resumo_mostra_so_atencao, test_resumo_conta_demais
Commit só-de-testes: a1b2c3d   ->   git diff a1b2c3d -- tests/   (vazio)
Evidência: [x] hx verify  [x] hx feature verify  [x] hx check-clean
Segurança: [x] sem dado real  [x] sem segredo
Escopo/contratos: <o que mudou e o que não mudou>
Progress atualizado: [x]
```

**Dica:** o `gh pr create` precisa da GitHub CLI instalada e autenticada. Se não tiver, abra o PR pela interface web e cole o modelo.

---

## Capítulo 12 — CI, revisão e merge

1. **CI de PR** roda sozinha: `check-clean` e `verify`, sem chave de LLM e só com permissão de leitura. Verde é obrigatório.
2. **O revisor** (não o autor) abre o PR e:
   - confere o hash e o `git diff <hash> -- tests/`;
   - confere que `estado` e `evidencia` da ficha vieram de um commit do `hx`;
   - preenche a **rubrica** (6 itens de 0 a 2: Correção, Verificação, Escopo, Clareza, Segurança, Documentação) como comentário no PR;
   - **aceita** com ≥ 9 de 12 e nenhum zero em Correção, Verificação ou Escopo; **bloqueia** com zero em Correção ou Verificação, ou se houver dado real ou segredo.
3. Merge na `main`. Caio apaga a branch e atualiza:

```powershell
git switch main
git pull
hx state
```

Agora a HAR-02 aparece como `passing`, e o fluxo recomeça na próxima feature.

---

## Quando o fluxo quebra

| Situação | O que fazer |
|---|---|
| `/planejar` deixa pergunta **BLOQUEANTE** | não siga para os testes; responda ou escale para quem decide |
| Teste da sessão 1 **passa** logo de cara | o teste é fraco; peça para fortalecer ou refaça |
| `git diff <hash> -- tests/` **não está vazio** | descarte a sessão 2 (`git restore tests/`) e refaça |
| Teste parece errado durante a sessão 2 | o agente para e explica; **você** corrige o teste, em commit separado, e registra no `progress` |
| `hx feature verify` falha | corrija o código e rode de novo; a ficha só muda quando tudo passa |
| `hx` recusa por "árvore suja" | commite ou guarde o que está pendente |
| Ficha precisa mudar no meio | pare, abra PR da ficha, e só depois siga |
| CI falha só no GitHub | rode `hx verify` local; diferença de ambiente costuma ser Docker, variável de ambiente ou dependência |
| Precisa interromper no meio | peça ao agente para encerrar a sessão (atualiza o `progress`); outro dev retoma a partir dele e do plano |

---

## Resumo de uma página

```
hx state                         ver o que existe
hx feature start <ID>            abrir: branch + progress + in_progress
/planejar <ID>                   agente avalia e escreve planos/<ID>/plan.md e tasks.md
(humano responde e aprova o plano)
SESSÃO 1  só testes   ->  ver falhar  ->  revisar  ->  commit + hash
SESSÃO 2  só código   ->  git diff <hash> -- tests/  (vazio)  ->  ruff + pytest
hx check-clean
hx verify
hx feature verify <ID>           único que grava passing + evidência
encerrar sessão (progress)  ->  PR  ->  CI  ->  rubrica  ->  merge
```

**As cinco regras que seguram tudo:**
1. Ficha = contrato; o `hx` é o único que muda `estado` e `evidencia`.
2. Teste primeiro, em sessão separada, revisado por humano.
3. Quem implementa não toca em `tests/`; o diff contra o hash prova isso.
4. Sem dado real, sem segredo, em nenhum arquivo.
5. Dúvida ou ambiguidade: pare e pergunte. Agente não inventa resposta.
