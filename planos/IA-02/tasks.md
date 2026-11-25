# Tasks — IA-02 · Enviar ao serviço de IA só descrições anonimizadas

**Plan:** planos/IA-02/plan.md · **Ficha:** features/IA-02.json
**Ordem:** T1 → revisão humana dos testes → commit só-de-testes (anotar o hash) → T2 em diante (sessão nova, sem editar `tests/`)
**Nomes fixados pelo plan (D1, D2, D3, D7, D8):** em `lastro.ai.contracts`: `ClientDescription` (com `amount_cents`), `CandidateAccount`, `RequestEntry`, `LLMRequest`, `LLMClient`, `InvalidLLMResponseError`; em `lastro.ai.service`: `suggest_accounts`. Os testes importam esses nomes.
**Ficha:** o c5 (conta fora do plano vira "não sei") é sugestão do plan, ainda não está na ficha; o humano aplica em PR.

---

## [ ] T1 · Escrever os testes dos critérios
- **Critérios da ficha:** c1, c2, c3, c4
- **Regra de negócio (em linguagem simples):** antes de qualquer descrição ir ao serviço de IA, CPF, CNPJ, agência, conta e nomes têm de ter sumido, e cada pedido ao serviço leva só um cliente. Sem descrição, o serviço nem é chamado. A conta que a IA devolver só vale se existir no plano daquele cliente; senão vira "não sei".
- **Critérios de aceite:**
  - [ ] Existem, em `tests/ai/test_gateway_vazamento.py`, os 4 testes com os nomes de `verificacao`: `test_requisicao_sem_cpf_cnpj_agencia_conta`, `test_nome_de_socio_vai_como_pseudonimo`, `test_cada_requisicao_leva_um_unico_cliente`, `test_lista_vazia_nao_chama_servico`
  - [ ] Mais 9 (D6, D8): `test_conta_fora_do_plano_vira_nao_sei` (c5 sugerido), `test_valor_segue_a_descricao_certa`, `test_valor_float_e_recusado`, `test_nome_de_conta_vai_anonimizado`, `test_cliente_sem_contas_nao_chama_servico`, `test_resultado_volta_na_ordem_do_pedido`, `test_resposta_com_tamanho_errado_e_recusada`, `test_nivel_invalido_falha_antes_de_chamar_servico`, `test_gateway_nao_registra_texto_original_em_log`
  - [ ] O serviço falso (classe no próprio arquivo) implementa `LLMClient`, grava cada `LLMRequest` e nunca usa rede
  - [ ] Todos falham hoje pelo motivo certo (`suggest_accounts` e os contratos não existem)
  - [ ] Só dados da `synthetic_fixtures_dir` e inventados; CNPJ válido só em tempo de execução
- **Exemplos (dado inventado):**
  - c1: descrições de EMP-1 do gabarito (ex.: `TED ENVIADA CPF <com máscara> CNPJ <com máscara> AG 6512 CC 51233-0`) mais uma com CNPJ numérico (EMP-2) e uma com CNPJ alfanumérico (EMP-1), de `cnpjs_dos_clientes()` → requisição serializada sem o CPF, sem cada CNPJ (com máscara e só dígitos), sem `6512` e sem `51233` no contexto de agência e conta; o falso recebeu ao menos 1 requisição
  - c2: sócios de `cadastro.json` (`SOCIO TESTE 01`), `PIX SOCIO TESTE 01`, `PIX RECEBIDO MARIA TESTE SOUZA`, `BOLETO PADARIA TESTE LTDA` → nenhuma requisição contém `SOCIO TESTE`, `MARIA TESTE SOUZA` nem `PADARIA TESTE LTDA`; 2 pseudônimos `PESSOA_nnn` diferentes e 1 `EMPRESA_nnn`
  - c3: 3 descrições de EMP-1 (ESC-1) e 2 de EMP-9 (ESC-2), **distintas entre os dois clientes**, num só pedido → 2 requisições, com 3 e 2 descrições; nenhuma mistura · extra: o mesmo `client_id` em ESC-1 e ESC-2 → 2 requisições (agrupa por escritório e cliente)
  - c4: lista vazia → 0 requisições, resultado `[]`, sem erro
  - c5 (sugerido): plano de EMP-1 com `4.1.01` e `4.1.02`; falso responde `9.9.99` → `None`; responde `4.1.02` → `4.1.02` · EMP-9 com plano que não tem `4.1.02`, falso responde `4.1.02` → `None`
  - valor: movimentação do gabarito com `valor_centavos` `-4590` e outra `+800000` → a requisição tem `-4590` e `800000` nas entradas das descrições certas, como `int`; `45.90` (float) ou `True` → `TypeError`/`ValueError` e 0 requisições; o valor não aparece em `caplog`
  - contas: conta `ADIANTAMENTO SOCIO TESTE 01` do plano → na requisição sem `SOCIO TESTE`; código `4.1.04` igual ao original · EMP sem contas → 0 requisições, resultado `None`
  - extras: itens EMP-1, EMP-9, EMP-1 → resposta na posição de cada item; falso devolve 1 resposta para 2 descrições → `InvalidLLMResponseError`; nível `medio` → erro e 0 requisições; `caplog` sem CPF, CNPJ nem nome originais
- **Arquivos:** `tests/ai/test_gateway_vazamento.py`
- **Fora do escopo:** código de produção; editar `tests/ai/test_anonimizar.py`
- **Decisões relacionadas:** D1, D2, D3, D5, D6 (plan.md)
- **Pronto quando:** `docker compose run --rm dev pytest tests/ai/test_gateway_vazamento.py -q` mostra só falhas esperadas (importação de `suggest_accounts`/contratos)

## [ ] T2 · Contratos e porta do serviço de IA
- **Critérios da ficha:** c3, c4 (base)
- **Regra de negócio (em linguagem simples):** o resto do sistema fala com a IA por um formato fixo: uma descrição marcada com escritório e cliente entra; uma requisição com só texto anonimizado sai para o serviço. Quem fala com o provedor depois implementa a mesma porta.
- **Critérios de aceite:**
  - [ ] `ClientDescription` (`firm_id`, `client_id`, `description`, `amount_cents`: `int` com sinal), `CandidateAccount` (`code`, `name`), `RequestEntry` (`description`, `amount_cents`) e `LLMRequest` (`entries`: tupla de `RequestEntry`; `accounts`: tupla de `CandidateAccount`) são `dataclass(frozen=True, slots=True)`
  - [ ] `amount_cents` que não for `int` (inclui `float` e `bool`) é recusado na construção, com mensagem em português (regra 8)
  - [ ] `LLMClient` é um `Protocol` com um método `suggest(request) -> list[str | None]` (`None` = "não sei")
  - [ ] `InvalidLLMResponseError` com mensagem em português: o que aconteceu e o que fazer
  - [ ] Docstrings em inglês e tipos em tudo; `ruff check` limpo
- **Exemplos:** `LLMRequest` tem `entries` (descrição + valor) e `accounts`, e não tem campo de cliente nem de escritório (D3) · `ClientDescription(..., amount_cents=-4590)` vale; `amount_cents=45.9` ou `True` → erro
- **Arquivos:** `src/lastro/ai/contracts.py` (só acrescenta; não muda `NameProtectionLevel`)
- **Reaproveitar:** estilo de `contracts.py` da IA-01 · **Não criar:** outro arquivo de contratos, tipo próprio de dinheiro, id na requisição
- **Fora do escopo:** adaptador de provedor, SDK, prompt, validar conta contra o plano
- **Decisões relacionadas:** D1, D2, D3, D8
- **Pronto quando:** `docker compose run --rm dev ruff check src/lastro/ai` limpo e os testes de T1 passam da importação

## [ ] T3 · Agrupar por cliente, validar a resposta e devolver na ordem de origem
- **Critérios da ficha:** c3, c4 (e c5, sugerido)
- **Regra de negócio (em linguagem simples):** itens de clientes diferentes nunca vão juntos. Cada cliente recebe um pedido, e as respostas voltam para a posição certa da lista original. Lista vazia não faz pedido nenhum. A conta que a IA devolve só vale se estiver no plano daquele cliente (regra 5); se não, o resultado é "não sei". Quem confere é o código, nunca a IA.
- **Critérios de aceite:**
  - [ ] Agrupa por `(firm_id, client_id)`, na ordem da primeira aparição; mesmo `client_id` em dois escritórios gera dois grupos (pergunta 3)
  - [ ] Itens do mesmo cliente não vizinhos entram no mesmo grupo e voltam às posições originais
  - [ ] Lista vazia devolve `[]` sem chamar a porta
  - [ ] Resposta de tamanho diferente do grupo levanta `InvalidLLMResponseError`
  - [ ] Código devolvido que não está nas contas do cliente vira `None`, sem erro; `None` da IA segue `None`
  - [ ] Cliente sem contas: não chama a porta e devolve `None` nos itens dele
- **Exemplos:** EMP-1, EMP-9, EMP-1 → 2 grupos (EMP-1 com 2, EMP-9 com 1); respostas `["4.1.01", None, "4.1.02"]` voltam nas posições 0, 1, 2 · `[]` → `[]` · porta devolve 1 resposta para 2 descrições → erro · `9.9.99` fora do plano → `None`
- **Arquivos:** `src/lastro/ai/gateway.py` (interno ao módulo)
- **Reaproveitar:** contratos da T2 · **Não criar:** `utils.py`, estado global, outro agrupador em outro módulo
- **Fora do escopo:** anonimizar (T4); logging
- **Decisões relacionadas:** D4
- **Pronto quando:** `pytest tests/ai/test_gateway_vazamento.py::test_cada_requisicao_leva_um_unico_cliente tests/ai/test_gateway_vazamento.py::test_lista_vazia_nao_chama_servico -q` passa (com a T5 ligada, se for preciso para importar)

## [ ] T4 · Montar a requisição só com texto anonimizado
- **Critérios da ficha:** c1, c2
- **Regra de negócio (em linguagem simples):** o que vai ao serviço é o resultado da anonimização, nunca o texto original. Os sócios cadastrados do cliente ajudam a reconhecer o nome mesmo cortado no extrato. As contas candidatas (código e nome) vão junto para a IA escolher; o nome da conta também é anonimizado, porque pode ter nome de pessoa.
- **Critérios de aceite:**
  - [ ] Cada grupo passa por **um** `anonymize(descrições + nomes das contas, partners=…, level=…)` da IA-01 (D7), separa a saída e monta a `LLMRequest` **só** com ela; o código da conta vai sem alteração
  - [ ] Cada `RequestEntry` leva o `amount_cents` do mesmo item de origem, sem alteração e sem passar pelo `anonymize()` (D8)
  - [ ] Os sócios de cada cliente vêm de `partners_by_client` (chave `(firm_id, client_id)`); cliente sem sócios usa `()`
  - [ ] O texto original não é guardado em campo da requisição nem em exceção
  - [ ] Nenhum CPF, CNPJ (numérico ou alfanumérico), agência, conta, nome de sócio, de pessoa ou de empresa aparece na requisição
- **Exemplos:** `PIX SOCIO TESTE 01` com sócio `SOCIO TESTE 01` → `PIX PESSOA_001 01`; `BOLETO PADARIA TESTE LTDA` → `BOLETO EMPRESA_001`; `AG 6512 CC 51233-0` → `[AGENCIA] [CONTA]`
- **Arquivos:** `src/lastro/ai/gateway.py`
- **Reaproveitar:** `lastro.ai.service.anonymize` · **Não criar:** outro anonimizador, regex de CPF/CNPJ, lista de nomes
- **Fora do escopo:** mudar as listas ou regras da IA-01 (se faltar palavra, abrir issue na IA-01)
- **Decisões relacionadas:** D4, D5, D7, D8
- **Pronto quando:** `pytest tests/ai/test_gateway_vazamento.py::test_requisicao_sem_cpf_cnpj_agencia_conta tests/ai/test_gateway_vazamento.py::test_nome_de_socio_vai_como_pseudonimo tests/ai/test_gateway_vazamento.py::test_nome_de_conta_vai_anonimizado tests/ai/test_gateway_vazamento.py::test_valor_segue_a_descricao_certa -q` passa

## [ ] T5 · Função pública `suggest_accounts`, nível e logs
- **Critérios da ficha:** c1, c2, c3, c4
- **Regra de negócio (em linguagem simples):** é a única porta de entrada para pedir sugestão de conta à IA. Lê o nível de proteção de nomes uma vez, antes de tudo, e nunca escreve o texto original em log.
- **Critérios de aceite:**
  - [ ] `suggest_accounts(items, *, llm_client, accounts_by_client, partners_by_client=None, level=None) -> list[str | None]` em `lastro/ai/service.py`, com docstring (Args, Returns, Raises)
  - [ ] `level=None` lê `load_name_protection_level()` uma vez; nível inválido levanta `InvalidNameProtectionLevelError` antes de qualquer chamada à porta
  - [ ] Nenhum `logging` do texto original nem do valor; se registrar algo, só o já anonimizado (`SECURITY.md` §5, §8)
  - [ ] Os 4 testes da ficha e os 9 extras passam
- **Exemplos:** `suggest_accounts([], llm_client=falso)` → `[]` · `NAME_PROTECTION_LEVEL=medio` → erro "Nível de proteção de nomes inválido: medio. …", 0 requisições
- **Arquivos:** `src/lastro/ai/service.py`
- **Reaproveitar:** `load_name_protection_level`, `anonymize` · **Não criar:** leitura de variável de ambiente nova, SDK, segredo, `.env`
- **Fora do escopo:** adaptador do provedor, prompt, custo, arredondar ou faixar o valor (pergunta 6), rotas em `api/`
- **Decisões relacionadas:** D1, D4, D6, D8
- **Pronto quando:** `docker compose run --rm dev pytest tests/ai/test_gateway_vazamento.py -q` passa (13 testes)

## [ ] T6 · Documentar o módulo e o contrato
- **Critérios da ficha:** (suporte: regras 9 e 11 do `AGENTS.md`)
- **Regra de negócio (em linguagem simples):** quem for classificar ou ligar um provedor precisa achar como chamar o gateway e o que ele garante.
- **Critérios de aceite:**
  - [ ] `docs/modulos/ai.md` ganha seção do gateway: uso, o que sai na requisição, o que vai (descrições e nomes de conta anonimizados, código da conta e valor exato em centavos com sinal), o que fica de fora (ids de escritório e cliente), o aviso de que o valor exato aguarda confirmação do líder/guardião antes do piloto (pergunta 6), a validação da resposta contra o plano, regra de não registrar o original
  - [ ] `ARCHITECTURE.md` §6: linha `ai → classification` com `ClientDescription`, `CandidateAccount`, `suggest_accounts` (versão 0), no mesmo PR (§9), com uma nota: "sem consumidor ainda; avisar o dono da `classification` por issue `contrato:` quando a ficha existir"
  - [ ] Nenhuma issue `contrato:` é aberta nesta feature (decisão de 25/11, plan §5)
  - [ ] Nenhum dado real; sem copiar nome real de provedor ou cliente
- **Arquivos:** `docs/modulos/ai.md`, `ARCHITECTURE.md`
- **Reaproveitar:** estilo do `ai.md` atual · **Não criar:** outro arquivo de docs
- **Fora do escopo:** corrigir `gitpages/` e as regras de nomes do `AGENTS.md` e do `SECURITY.md` (pergunta 4 e divergências do §4 do plan: PR de docs do humano)
- **Pronto quando:** `ruff check .` limpo e o diff só toca os dois arquivos

## [ ] T7 · Verificação final
- **Critérios de aceite:**
  - [ ] `git diff <hash-dos-testes> -- tests/` vazio
  - [ ] `ruff check .` limpo
  - [ ] `hx check-clean` e `hx verify` em OK
  - [ ] `hx feature verify IA-02` grava `passing`
  - [ ] `progress/IA-02.md` atualizado
- **Pronto quando:** os três comandos do `hx` terminam com código 0
