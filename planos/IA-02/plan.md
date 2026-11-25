# Plan — IA-02 · Enviar ao serviço de IA só descrições anonimizadas

**Status:** pronto para revisão
**Branch:** feat/IA-02-enviar-ao-servico-de-ia-so-descricoes-an · **Data:** 25/11/2026 · **Responsável:** caio-nascime
**Tasks:** planos/IA-02/tasks.md

## 1. A decidir (humano)
Nenhuma pergunta BLOQUEANTE. As ATENÇÕES seguem o padrão sugerido até alguém dizer o contrário.
| # | Pergunta | Gravidade | Sugestão de padrão | Decide |
|---|---|---|---|---|
| 1 | **Contas candidatas:** a IA só pode escolher entre as contas do plano do cliente (regra 5). Para escolher, ela precisa ver essa lista (código e nome de cada conta). Enviar? Nome de conta pode ter nome de pessoa (ex.: conta de um sócio) | ATENÇÃO | Sim: enviar `código + nome`, com o **nome** passando pelo `anonymize()` junto com as descrições (D7). O código vai como está. Prompt, custo e provedor ficam fora | caio-nascime |
| 6 | **Valor:** a requisição leva o valor da movimentação (D8). Valor exato pode ajudar a ligar a requisição a um extrato se o provedor retiver dados (retenção ainda `[definir]`, `SECURITY.md` §5) | ATENÇÃO | Enviar o valor **exato em centavos, com sinal** (como no gabarito). Registrar em `docs/modulos/ai.md` e pedir ao líder (e ao guardião de dados, quando houver) que confirme antes do piloto; se não aceitarem, trocar por valor arredondado ou só o sinal (muda só a T4) | líder + caio-nascime |
| 5 | O plano da IA-01 está "pronto para revisão" (não aprovado) e todas as palavras das listas têm `revisado: pendente`. A IA-02 depende do comportamento do código dela | ATENÇÃO | Valer o que o código faz (passing, #55). Humano aprova ou ajusta o plan da IA-01 em separado | líder |

Mudanças sugeridas na ficha (o humano aplica em PR; sem isso o `hx feature verify` não prova a validação):
- **Novo c5:** "Conta sugerida que não existe no plano do cliente vira 'não sei'". Exemplo: serviço falso responde `9.9.99` para um cliente cujo plano não tem essa conta; resultado `None`. Em `verificacao`: `pytest tests/ai/test_gateway_vazamento.py::test_conta_fora_do_plano_vira_nao_sei -q`.
- c1 a c4: a requisição também leva `accounts` e o valor de cada descrição; o texto "nenhuma requisição contém" já os cobre. O c3 poderia dizer "cliente (escritório e cliente)" (pergunta 3, resolvida em §5).

## 2. Decisões tomadas pelo agente
Cada uma precisa de confirmação humana.
### D1 · Interface pública `suggest_accounts` em `ai/service.py`
- **Alternativas:** A) função que recebe itens de vários clientes e devolve uma lista na mesma ordem · B) função por cliente (o chamador agrupa) · C) classe com estado
- **Escolhida:** A — **motivo:** o c3 pede "num único pedido, cada uma marcada com o seu cliente"; a separação por cliente é garantia de privacidade e fica dentro do gateway, não nas mãos de cada chamador. Nomes em inglês (CODING_STANDARDS §1).
- **Forma:** `suggest_accounts(items, *, llm_client, accounts_by_client, partners_by_client=None, level=None) -> list[str | None]`; item `ClientDescription(firm_id, client_id, description, amount_cents)`; os dois mapas com chave `(firm_id, client_id)`; conta candidata `CandidateAccount(code, name)`. Lista vazia → `[]` sem chamar a porta (c4).
- **Impacto:** T2 a T5, e c1 a c4. [ ] confirmar

### D2 · Serviço de IA atrás de uma porta (`LLMClient`), sem provedor e sem SDK
- **Alternativas:** A) `Protocol` com um método `suggest(request) -> list[str | None]`, implementado por um falso nos testes · B) falso no nível HTTP (`httpx.MockTransport`) · C) escolher o provedor agora
- **Escolhida:** A — **motivo:** provedor está em aberto (`DECISIONS.md`, regra 12); B exigiria cliente HTTP e URL de um provedor que não existe. A porta é o que `ia.md` chama de `ClassificadorLLM`; o nome fica em inglês. Biblioteca nova: nenhuma (`typing.Protocol`, `dataclasses`).
- **Limite honesto:** o teste prova o que chega à porta. O adaptador do provedor, quando existir, precisa de teste próprio (ver riscos).
- **Impacto:** T2, T5. [ ] confirmar

### D3 · A requisição leva `entries` (descrição + valor) e `accounts`, sem ids
- **Alternativas:** A) `LLMRequest(entries, accounts)`, com `RequestEntry(description, amount_cents)` · B) listas paralelas `descriptions` e `amounts_cents` · C) incluir também `firm_id`/`client_id`
- **Escolhida:** A — **motivo:** enviar o mínimo útil (`SECURITY.md` §5). Sem as contas a IA não tem como responder; o valor ajuda a classificar (ver D8); id de escritório e cliente não ajudam e ligam a requisição a um titular. Descrição e valor no mesmo objeto evitam listas fora de ordem (B). O teste do c3 separa por contagem e conteúdo, não por id.
- **Impacto:** T1, T2, T4. [ ] confirmar

### D4 · Uma requisição por cliente, um `anonymize()` por cliente, ordem de primeira aparição
- Agrupa por `(firm_id, client_id)` na ordem em que o cliente aparece; cada grupo vira **um** `anonymize(descriptions, partners=…, level=…)` e **uma** chamada à porta; a resposta volta à posição de origem. Pseudônimo reinicia por cliente (nenhum vínculo entre clientes). O nível é lido **uma vez**, antes de qualquer chamada: nível inválido falha sem chamar a porta.
- Resposta da porta com tamanho diferente do pedido → `InvalidLLMResponseError` (nova, em `contracts.py`); sem isso não há como devolver cada sugestão à sua descrição.
- **Validação da resposta (regra 5):** cada código devolvido é conferido contra as contas **daquele cliente**; código fora da lista vira `None` ("não sei"), sem erro. Cliente sem contas: não chama a porta e devolve `None` para os itens dele. Validação em código, nunca por LLM.
- **Impacto:** T3 a T5. [ ] confirmar

### D8 · Valor da movimentação: inteiro em centavos, com sinal, exato
- **Alternativas:** A) exato, centavos com sinal (saída negativa, como no gabarito HAR-03) · B) arredondado em faixas · C) só o sinal (entrada/saída) · D) sem valor
- **Escolhida:** A — **motivo:** pedido do responsável em 25/11; é o que mais ajuda a classificar (tarifa de R$ 45 × aluguel de R$ 8.000) e não é CPF, CNPJ, agência, conta nem nome. `ia.md` já prevê "descrição, valor e contas candidatas". Risco de reidentificação: pergunta 6. Regra 8: só `int`; `float` e `bool` são recusados com erro (`TypeError`/`ValueError`). O valor não passa pelo `anonymize()` (é número, não texto) e não entra em log.
- **Impacto:** T1, T2, T4, T5, T6. [ ] confirmar

### D7 · Nomes das contas anonimizados no mesmo lote das descrições
- **Alternativas:** A) um só `anonymize()` por cliente com descrições + nomes de conta, depois separa · B) `anonymize()` só nas descrições, nomes de conta em claro · C) enviar só os códigos
- **Escolhida:** A — **motivo:** nome de conta pode ter nome de pessoa; no mesmo lote o pseudônimo é o mesmo nas duas partes, e a IA ainda liga "PESSOA_001" da descrição à conta de mesmo nome. C descarta o nome, que é o que ajuda a IA a escolher. O código da conta não é anonimizado. A validação usa o código original.
- **Impacto:** T2, T4. [ ] confirmar

### D5 · O teste mede a requisição inteira, serializada
- O falso grava o `LLMRequest` recebido; o teste serializa tudo (`dataclasses.asdict` → JSON) e procura os documentos originais em **todos os campos**, nas formas com máscara e só dígitos. Agência e conta saem da própria descrição de teste (`AG 6512`, `CC 51233-0`), sem copiar valor à mão. CNPJ válido: `cnpjs_dos_clientes()` (HAR-03 c5), um alfanumérico (EMP-1) e um numérico (EMP-2 ou EMP-9).
- **Impacto:** T1. [ ] confirmar

### D6 · Sem log do texto original; extras de teste além da ficha
- O gateway não usa `logging` com texto original (`SECURITY.md` §5, §8). Testes extras com nomes próprios, além dos 4 da ficha: ordem de volta, tamanho errado da resposta, nível inválido sem chamada, ausência do original no log, nome de conta anonimizado, cliente sem contas, valor sai com a descrição certa e valor `float` recusado. O `test_conta_fora_do_plano_vira_nao_sei` é o do c5 sugerido. **Impacto:** T1. [ ] confirmar

## 3. Resumo e abordagem
Um gateway em `ai/` recebe descrições de vários clientes, separa por cliente, anonimiza cada grupo com o `anonymize()` da IA-01 e chama uma porta de IA com uma requisição por cliente, só com o texto anonimizado.
1. T1: testes da ficha (e os extras) com um serviço falso, usando `synthetic_fixtures_dir`.
2. T2: contratos (`ClientDescription`, `CandidateAccount`, `RequestEntry`, `LLMRequest`, `LLMClient`, `InvalidLLMResponseError`).
3. T3: agrupar por cliente, lista vazia, validar a resposta contra o plano e voltar à ordem de origem (c3, c4, c5 sugerido).
4. T4: montar a requisição só com texto anonimizado (descrições e nomes de conta), o valor de cada descrição e os sócios do cliente (c1, c2).
5. T5: `suggest_accounts` público, nível lido uma vez, nada de log do original.
6. T6: documentação do módulo e do contrato. T7: verificação final.

## 4. Contexto encontrado
- **Planos lidos:** `planos/IA-01/plan.md` (**rascunho**, "pronto para revisão": decisões são intenção, mas o código já foi integrado, #55); `planos/HAR-03/plan.md` (**aprovado**, camposs04, 24/11); `progress/IA-01.md`, `progress/HAR-03.md`. Fora das dependências: nenhum.
- **Conferência com o código:** **confere** — `anonymize(descriptions, *, partners=(), level=None)` e `load_name_protection_level()` (`src/lastro/ai/service.py`); `NameProtectionLevel` e `InvalidNameProtectionLevelError` (`contracts.py`); pseudônimo estável por chamada e por ordem de aparição (rodei `anonymize` em descrições do gabarito); `synthetic_fixtures_dir` (`tests/conftest.py`); `cnpjs_dos_clientes()` (1 alfanumérico, 2 numéricos); gabaritos com 30 e 19 (EMP-1), 22 (EMP-2) e 22 (EMP-9) movimentações; descrição com `CPF`, `CNPJ`, `AG 6512 CC 51233-0` no formato que a IA-01 reconhece.
- **Confere, com ressalva:** os sócios sintéticos têm número (`SOCIO TESTE 01`); o número é lido como número e fica em claro (`PIX SOCIO TESTE 01` → `PIX PESSOA_001 01`). Nome real não tem dígito, então não é vazamento, mas o teste do c2 deve procurar `SOCIO TESTE`, e não só o nome inteiro.
- **Divergente (documental, vale o código):** `gitpages/.../arquitetura/ia.md`, `seguranca.md` e `visao-geral.mdx` citam `src/lastro/ia/`, `anonimizar()` e `ClassificadorLLM`; o código usa `ai/`, `anonymize()`. Correção vai ao humano, em PR de docs. O `AGENTS.md` cita `docs/modules/`, mas `ai.md` está em `docs/modulos/`: esta feature atualiza o arquivo onde ele está.
- **Reaproveitar:** `lastro.ai.service.anonymize`, `load_name_protection_level`; `synthetic_fixtures_dir`; `fixtures_sinteticas.cnpjs_dos_clientes`.
- **Não criar:** outro anonimizador ou detector de documento, cliente de rede ou SDK, persistência, `utils.py`, fixture escrita à mão.
- **Pesquisa externa:** sem pesquisa externa necessária (sem biblioteca nova; provedor em aberto).

## 5. Decisões (já resolvidas)
- 25/11 · Pergunta 2: o formato de `suggest_accounts` é registrado já como contrato `ai → classification`, versão 0, na tabela do `ARCHITECTURE.md` §6 (T6), por caio-nascime. **Sem abrir issue `contrato:` agora**: não há consumidor nem dono da `classification` para avisar. A issue passa a valer quando a ficha da classificação existir e quando o formato mudar (regra 11).
- 25/11 · Pergunta 3: agrupar por `(firm_id, client_id)`; dois escritórios nunca dividem requisição, mesmo com `client_id` igual (regra 7), por caio-nascime. A T1 ganha um caso com o mesmo `client_id` em dois escritórios.
- 25/11 · Pergunta 4: `AGENTS.md` (regra 5), `SECURITY.md` §5 e `ARCHITECTURE.md` §10 ainda dizem "nomes proibidos até a D-03", mas a D-03 está aprovada (18/11). Concordado por caio-nascime: a correção vai em PR de docs separado, fora desta branch; o plan segue a D-03.
- 25/11 · Escopo: a IA-02 inclui a validação da resposta contra o plano do cliente (regra 5), por caio-nascime. Prompt, custo e provedor seguem fora.
- 25/11 · Escopo: a IA-02 também envia o valor da movimentação (D8), por caio-nascime. Exato ou arredondado: pergunta 6.
- 18/11 · D-03: todo nome de contraparte vira `PESSOA_nnn` ou `EMPRESA_nnn`, ligado por padrão (`DECISIONS.md`).
- 18/11 · ARQ-06: só `src/lastro/ai/` fala com LLM, depois de anonimizar.

## 6. Avaliação da ficha
| # | Achado | Gravidade | Critério |
|---|---|---|---|
| 1 | Ficha não nomeia função, nem formato da resposta: fixados em D1 e D2 (contrato v0 aceito em 25/11, §5) | ATENÇÃO | todos |
| 1a | Validação da resposta não tem critério na ficha: sugerido o c5 (§1); sem ele o `hx feature verify` não a prova | ATENÇÃO | novo c5 |
| 2 | "Cliente" sem escritório (pergunta 3) | ATENÇÃO | c3 |
| 3 | "Nenhuma requisição contém…" depende de o falso gravar a requisição inteira (D5); com descrições iguais em dois clientes o teste não separa por conteúdo: usar descrições distintas por cliente | ATENÇÃO | c3 |
| 4 | Agência e conta (`6512`, `51233`) podem coincidir com outro número da requisição; o teste procura o número no contexto da descrição | ATENÇÃO | c1 |
| 5 | Número no nome do sócio sintético fica em claro (ressalva do §4) | ATENÇÃO | c2 |
| 6 | 4 critérios, um módulo, uma função: cabe numa sessão de testes e numa de implementação | — | todos |
| 7 | Verificação por `pytest` (comando permitido); exemplos têm dado inventado; sem dado real | — | c1–c4 |

## 7. Riscos
- Adaptador de provedor futuro enviar campo além de `entries` e `accounts` → o teste de vazamento da ficha de provedor deve passar pelo mesmo falso, no nível HTTP.
- Palavra de extrato fora da lista da IA-01 vira pseudônimo (`CPF`, `CNPJ`, `IMPOSTOS`, `FOLHA`, `VENDA`), piorando a classificação, não a privacidade → medir na ficha de classificação; corrigir as listas na IA-01.
- Nome de conta com dado pessoal (nome de pessoa, CNPJ) → D7 anonimiza o nome; o teste do c1/c2 inclui um nome de conta com sócio.
- Mudar o contrato depois exige issue `contrato:` (regra 11).
- Chamada ao serviço real em teste → proibido (`SECURITY.md` §5): só falso.

## 8. Aprovação
- [ ] Perguntas ATENÇÃO respondidas ou padrão aceito
- [ ] Decisões do agente confirmadas (D1 a D8)
- [ ] Plan e tasks revisados por ________ em __/__
