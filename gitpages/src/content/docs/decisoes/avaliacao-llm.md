---
title: "Decisão: avaliação com LLM e modelos"
description: Medir com código e gabarito onde há resposta certa e usar um LLM como juiz só para texto.
---

| Status | Data | Fonte |
|---|---|---|
| Recomendada, aguardando aprovação | Sem data no documento; fontes consultadas em 09 e 10/11/2026 | Estudo de Avaliação com LLM – Lastro |

## Contexto

O contador precisa confiar na conta sugerida e nas perguntas enviadas ao cliente. Revisar tudo à mão a cada mudança de prompt ou de modelo não escala, e "parece bom" não é critério de aceite. A avaliação precisa caber no harness (`features/`, `tools/harness.py`, `noturno.yml`) e respeitar o `docs/SECURITY.md`.

## Decisão

- **Sem juiz onde há resposta certa.** Leitura, validação, conta sugerida e exportação se medem com código e gabarito sintético, em centavos.
- **Juiz LLM só para texto:** perguntas ao cliente e justificativa da conta.
- **Formato do juiz:** rubrica passa/falha, raciocínio curto antes do veredito e saída em JSON com schema.
- **Validar o juiz antes de confiar nele.** Medir kappa e TPR/TNR contra os rótulos da contadora. Nenhum juiz entra no `verify` sem passar por essa etapa.
- **Tarefa e juiz de empresas diferentes**, por causa da autopreferência, com uma opção local para sigilo e custo.

### Avaliação por módulo

| Módulo | Saída | Tipo de avaliação | Métrica |
|---|---|---|---|
| Leitura | Transações extraídas | Determinística com gabarito | Precisão e recall por linha; valor em centavos e data exatos |
| Leitura | Formato detectado | Determinística | Acurácia por tipo |
| Validação | Saldo e continuidade | Determinística | Saldo calculado igual ao informado (inteiros em centavos); TPR/TNR na detecção de mês ou página faltando |
| Classificação | Conta sugerida | Determinística com gabarito | Acurácia exata, acurácia no grupo da conta, matriz de confusão |
| Classificação | Sugerir ou perguntar | Determinística | Acurácia das sugestões confiantes; taxa de perguntas geradas |
| Classificação | Justificativa da conta | Código e LLM como juiz com referência | Percentual de justificativas fiéis |
| Perguntas | Pergunta e opções de toque | LLM como juiz com rubrica binária e código | Percentual de perguntas aprovadas em todos os critérios críticos |
| Revisão | Contador aceitou, editou ou rejeitou | Revisão humana (sinal de produção) | Taxa de aceite sem edição, por conta e por banco |
| Exportação | Planilha do Domínio | Determinística | Colunas e tipos válidos; soma das linhas igual à movimentação do extrato |

### Modelos considerados

Preços consultados em 09/11/2026. Custo por 1.000 julgamentos é estimativa do estudo (1.500 tokens de entrada e 300 de saída), não medido.

| Modelo | Papel sugerido | Pontos de atenção |
|---|---|---|
| Claude Sonnet 5.5 (Anthropic) | Tarefa (classificação e perguntas) | Só via API, exige `anonimizar()`; cerca de US$ 6 por 1.000 julgamentos |
| Claude Haiku 5.5 (Anthropic) | Tarefa, como teste de custo contra o Sonnet | Qualidade na tarefa não medida; não pode julgar a tarefa feita pelo Sonnet |
| Gemini 3.5 Flash (Google) | Juiz principal, se a tarefa for Claude | JSON com schema não verificado no estudo |
| gpt-6.1-terra (OpenAI) | Juiz alternativo ou segundo juiz | JSON com schema não verificado no estudo |
| gpt-oss-20b (OpenAI, open-weights) | Juiz local, por sigilo e custo zero de API | Qualidade em português e na rubrica não medida; custo de hardware |

O estudo avisa que não encontrou benchmarks de juízes para esses modelos. A escolha final sai da validação contra a contadora, não de ranking.

## Alternativas consideradas

| Método | Veredito do estudo |
|---|---|
| Nota direta com rubrica binária | Sim: método padrão para perguntas e justificativas |
| Comparação par a par | Depois: útil para comparar duas versões de prompt, não como métrica do dia a dia |
| Juiz com referência | Sim, só para a justificativa da conta, medindo com e sem referência |
| Raciocínio antes da nota com saída estruturada | Sim: é o formato do prompt do juiz |
| Painel de juízes | Depois: começar com um juiz; segundo juiz só onde o primeiro discordar da contadora |
| Juiz especializado (fine-tuned) | Não no MVP; reavaliar com rótulos acumulados do piloto |
| LLM como juiz de valores, somas e saldos | Não: juízes LLM erram matemática |
| Juiz no lugar da revisão do contador | Não: o juiz serve para desenvolvimento e regressão; não aprova lançamento |

## Consequências

**Destrava:**

- critérios de aceite com métrica e limiar nas fichas `features/<ID>.json`, marcados `passing` só pelo script;
- métricas determinísticas em todo `verify`;
- uma feature "juiz de perguntas validado";
- regressão de qualidade detectada pelo `noturno.yml`.

**Custa:**

- **Tempo da contadora:** é o gargalo, não o custo de API. O estudo sugere sessões curtas e semanais de rotulagem.
- **Rótulos:** de 100 a 150 perguntas rotuladas (número estimado pelo estudo); abaixo de cerca de 60 exemplos a medida fica pouco confiável.
- **Custo:** chave de API do juiz como secret do GitHub Actions e custo recorrente se o juiz rodar no CI.

### Plano em fases

| Fase | Entregável | Dependência |
|---|---|---|
| 0. Golden set | Rótulos da contadora (fora do repositório) convertidos em casos do `fixtures build` | Tempo da contadora; onde guardar os rótulos reais |
| 1. Métricas determinísticas | Leitura, validação, classificação e exportação medidas no `verify --e2e` | Fase 0 |
| 2. Juiz de perguntas | Prompt versionado em `src/lastro/ia/`, rubrica e feature "juiz validado" | Fase 0; modelo do juiz |
| 3. Noturno e sinal de produção | Métricas e juiz no `noturno.yml`; registro de aceitou/editou na revisão | Fases 1 e 2; piloto; orçamento |
| 4. Depois do MVP | Segundo juiz, par a par entre versões, juiz fine-tuned | Rótulos acumulados do piloto |

## Pendências ligadas

| Pendência | Status |
|---|---|
| Modelo da tarefa e do juiz | Em aberto, sem ID |
| Valores dos limiares das features | Em aberto, sem ID |
| Orçamento mensal de API e frequência do juiz no noturno | Em aberto, sem ID |
| Onde guardar os rótulos reais | Em aberto, sem ID |
| D-03 nomes para a IA | Em aberto; afeta o que o juiz e a tarefa recebem |
| D-08 limite de confiança (RF-CLA-07 [definir]) | Em aberto; a calibragem usa as métricas deste estudo |

Como a IA entra no sistema: [Arquitetura · IA](/lastro-lancamentos/arquitetura/ia/).

**Fonte:** Estudo de Avaliação com LLM – Lastro.
