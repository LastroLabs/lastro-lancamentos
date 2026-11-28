# Plan — CAD-02 · Ler o plano de contas em TXT e apontar linha inválida

**Status:** aprovado (caio-nascime, 27/11/2026). A ficha segue sem `hx feature start` (seção 5, pergunta 1).
**Branch:** `feat/CAD-02-ler-a-planilha-do-plano-de-contas-e-apon` · **Data:** 27/11/2026 · **Responsável:** marrathomaz
**Tasks:** `planos/CAD-02/tasks.md`

## 1. A decidir (humano)
Nenhuma pergunta aberta. As 3 perguntas desta seção foram respondidas em 27/11 e estão na seção 5.

Mudanças sugeridas na ficha (o humano aplica em PR): nenhuma. A D2 foi confirmada (`OSError` para `Path` inexistente), então o c9 não precisa de exemplo novo.

## 2. Decisões tomadas pelo agente
### D1 · Os testes importam o serviço dentro de uma função auxiliar, não no topo do arquivo
- **Alternativas:** A) `from lastro.registry.service import read_chart_of_accounts` no topo · B) import dentro de um auxiliar (`importlib`), como fazia o `test_planilha_plano.py`.
- **Escolhida:** B. **Motivo:** com A, no commit só de testes, o `pytest -q` inteiro para na coleta ("Interrupted: 1 error during collection"). O `hx verify` e a CI ficam vermelhos para toda a suíte e escondem outras falhas. Com B, só os 10 testes da ficha falham, cada um pelo motivo certo.
- **Fontes:** `tests/registry/test_planilha_plano.py` (docstring do módulo; precedente no repositório).
- **Impacto:** T1. O patch de referência usa A; não copiar essa parte.
- [x] confirmado por caio-nascime em 27/11

### D2 · `Path` de arquivo inexistente ou ilegível levanta `OSError`; o tamanho é conferido pelo `stat()` antes de ler
- **Alternativas:** A) ler tudo e depois conferir os 20 MiB · B) `stat()` antes de ler; um `OSError` sobe ao chamador · C) devolver recusa para qualquer `OSError`.
- **Escolhida:** B. **Motivo:** "nunca levanta exceção" vale para **conteúdo** ruim (ficha c9; `registry.md`). Arquivo inexistente é erro de quem chama: a CAD-05 passa bytes do upload. O `stat()` evita carregar na memória um arquivo enorme, como já fazia o leitor `.xlsx`.
- **Impacto:** T2. A docstring registra o `Raises: OSError`.
- [x] confirmado por caio-nascime em 27/11

### D3 · O reduzido `0000000` não conta como repetição (E6)
- **Alternativas:** A) duas linhas `0000000` dão E6 · B) cada uma dá só E2z (tolerável na analítica folha).
- **Escolhida:** B. **Motivo:** o `registry.md`, passo 6, fala em "reduzido **válido** que já apareceu", e `0000000` não é válido (E2z). Também é o que o patch da simulação faz.
- **Impacto:** T4. Sem teste próprio na ficha; vai como caso extra no T4.
- [x] confirmado por caio-nascime em 27/11

### D4 · `uv lock` roda dentro do contêiner (`docker compose run --rm dev uv lock`)
- **Alternativas:** A) `uv lock` no host · B) dentro do contêiner, com o uv 0.13.9 fixado no `Dockerfile`.
- **Escolhida:** B. **Motivo:** o host não tem `uv`. O patch da simulação, gerado com outro uv, trocou `revision = 5` por `3` no `uv.lock`. O `Dockerfile` roda `uv sync --locked`, então o lockfile tem de bater com o uv da imagem.
- **Impacto:** T6. Depois, `docker compose build dev` (armadilha do roteiro).
- [x] confirmado por caio-nascime em 27/11

### D5 · O leitor fica dividido em funções pequenas e privadas em `chart_txt.py`
- **Alternativas:** A) uma função grande, como no patch (cerca de 130 linhas) · B) funções separadas: decodificar, ler a linha, erro próprio, repetições, hierarquia, classificação final e mensagem.
- **Escolhida:** B. **Motivo:** o `CODING_STANDARDS.md` §2 pede "mais de ~40 linhas, reavalie", e cada etapa do `registry.md` vira uma função testável pelo resultado.
- **Impacto:** T2 a T5.
- [x] confirmado por caio-nascime em 27/11

## 3. Resumo e abordagem
Trocar o leitor `.xlsx` por um leitor do TXT de 78 colunas do Domínio. Ele devolve as contas com reduzido, classificação, nome, tipo e conta superior, mais os erros tolerados, os avisos e uma recusa única. A regra completa está em `docs/modulos/registry.md` ("Leitura do plano de contas em TXT") e no `DECISIONS.md` §11. O plan só organiza a execução e não repete a regra.

Ordem:
1. Testes da ficha e remoção do `test_planilha_plano.py` (T12). Commit só de testes; o `hx feature verify` grava `regressed`.
2. Contrato e fachada novos, com o leitor `.xlsx` removido junto.
3. Leitura do arquivo (recusas de arquivo, decodificação, linhas).
4. Erro próprio de cada linha.
5. Repetições e hierarquia.
6. Tolerância, mensagem de recusa e avisos.
7. Saída do `openpyxl`.
8. Verificação final.

Sem banco nem HTTP: a gravação é da CAD-05.

## 4. Contexto encontrado
- **Planos lidos:** só o próprio `planos/CAD-02/plan.md` antigo (aprovado em 25/11, leitor `.xlsx`). As decisões D1 a D6 dele (`openpyxl`, cabeçalho, células numéricas) são **divergentes** do `DECISIONS.md` §11 T1 e ficam substituídas; seguem no histórico do git. A ficha não tem `depende_de`, então não há outros planos.
- **`DECISIONS.md` lido:** §11 inteiro (T1 a T5, T11 e T12 citam a CAD-02) e a P-10, agora `substituída (§11 T1)`.
- **Conferência do roteiro `docs/refatoracoes/CAD-02.md` com o código:**
  - passo 1, merge da `developer`: **confere**. Feito em `be01caa`, com conflito em 4 arquivos e não 3 como o roteiro diz (`docs/modules/registry.md` era o quarto); `hx verify` OK;
  - "nenhum outro código ou teste importa o leitor `.xlsx`": **confere**. Só `service.py`, `contracts.py` e `test_planilha_plano.py` o citam;
  - linha do contrato no `ARCHITECTURE.md` §6: **confere** (linha 118);
  - planos reais aceitos e 1.200 embaralhamentos: **não verificável**. Os dados ficam fora do repositório (regra 1).
- **Código relacionado:**
  - `src/lastro/registry/service.py`: `read_chart_of_accounts_spreadsheet` (sai) e as funções da CAD-03 (ficam);
  - `src/lastro/registry/contracts.py`: `ChartAccountEntry(code, name)` e `ChartSpreadsheetResult` (mudam ou saem) e os tipos da CAD-03 (ficam);
  - `src/lastro/registry/chart_spreadsheet.py` (sai).
- **Reaproveitar:** o padrão de fachada da CAD-01 (`service` chama a função `_privada` do arquivo interno); `MAX_SPREADSHEET_BYTES` de 20 MiB, que vira a constante do TXT.
- **Não criar:** `utils.py` ou `helpers.py`; outro ponto de entrada além de `read_chart_of_accounts`; mensagens fora das tabelas do `registry.md`.
- **Pesquisa externa:** sem pesquisa externa necessária. Formato, codificação (UTF-8 → cp1252 com `replace`), `split("\n")` e mensagens já foram decididos pela equipe (§11 e `registry.md`), sem biblioteca nova.

## 5. Decisões (já resolvidas)
- 26/11 · T1: só TXT de 78 colunas; o `openpyxl` sai; substitui a P-10 (equipe, §11).
- 26/11 · T2: a hierarquia vem do maior prefixo próprio, independente da máscara e da ordem (§11).
- 26/11 · T3: só a analítica folha com E2, E2z ou E4 é tolerada; o resto recusa com uma única mensagem (§11).
- 26/11 · T4: reduzido ou classificação repetidos recusam o arquivo, em qualquer ordem (§11).
- 26/11 · T5: `ChartOfAccountsResult(accounts, errors, warnings, refusal)` e `read_chart_of_accounts(bytes | Path)` (§11).
- 26/11 · T11 e T12: CAD-02 refeita na própria branch; apagar `test_planilha_plano.py` está autorizado. T12 aprovada por caio-nascime em 27/11.
- 27/11 · T13: sem issue `contrato:`; a mudança do contrato v0 → v1 fica registrada no `DECISIONS.md` §11 (resposta à antiga pergunta 3, por caio-nascime).
- 27/11 · D1 a D5 confirmadas por caio-nascime.
- 27/11 · Pergunta 1: seguir sem `hx feature start`; o `hx feature verify` grava `regressed` depois do commit de testes e `passing` no fim (T11 e roteiro), por caio-nascime.
- 27/11 · Pergunta 2: arquivo e nomes de teste em português, como estão na ficha (`CODING_STANDARDS.md` §9); o código de `src/` fica em inglês, por caio-nascime.
- 27/11 · Pergunta 3: o `SECURITY.md` §3 ("planilha") é corrigido no PR da HAR-05, fora da CAD-02, por caio-nascime.

## 6. Avaliação da ficha
| # | Achado | Gravidade | Critério |
|---|---|---|---|
| 1 | 10 critérios, acima do limite de 4. Mas é um módulo só, uma função pública e regra fechada em doc; cabe em 1 ou 2 sessões | ATENÇÃO | todos |
| 2 | O c8 (byte inválido → E5a) depende do deslocamento causado por acentos em cp1252: o teste fica frágil se o nome de exemplo mudar | ATENÇÃO | c8 |
| 3 | O c4(c) cobre 6 erros num teste só; uma falha não diz qual caso quebrou sem mensagem no `assert` | ATENÇÃO | c4 |
| 4 | `Path` inexistente não tem exemplo (ver D2) | ATENÇÃO | c1, c9 |
| 5 | Mensagens: com 1 causa, "Corrija essa linha..."; com várias, "Há mais N... Corrija e envie...". Ficha e `registry.md` concordam | ok | c4, c5, c10 |
| 6 | Cada critério tem um teste na `verificacao`, e nenhum nome se repete em outra ficha (`hx state` OK) | ok | todos |

## 7. Riscos
- Copiar os patches de `referencia_simulacao/` sem revisar → o import no topo (D1) e o `uv.lock` com `revision = 3` (D4) entrariam errados. Usar só para consulta.
- Imagem `lastro-dev` desatualizada → reconstruir no fim (T6; armadilha do roteiro).
- Sequência de dígitos reduzido+classificação lida como CPF ou CNPJ pelo `check-clean` → nos testes, o reduzido e a classificação são literais separados, e a linha de 78 colunas só existe em tempo de execução. Rodar `hx check-clean` no T7.
- `progress/CAD-02.md` ainda descreve o `.xlsx` → reescrever Objetivo e Próxima ação ao encerrar a sessão (T7).

## 8. Aprovação
- [x] Perguntas 1 a 3 respondidas (caio-nascime, 27/11)
- [x] Decisões D1 a D5 confirmadas (caio-nascime, 27/11)
- [x] Plan e tasks revisados e aprovados por caio-nascime em 27/11
