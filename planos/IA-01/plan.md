# Plan — IA-01 · Anonimizar descrições: remover CPF, CNPJ, agência e conta, e proteger nomes por nível, preservando palavras de operação e de atividade

**Status:** pronto para revisão
**Branch:** feat/IA-01-anonimizar-descricoes-remover-cpf-cnpj-a · **Data:** 23/11/2026 · **Responsável:** arthurlleite
**Tasks:** planos/IA-01/tasks.md

## 1. A decidir (humano)
Nenhuma pergunta BLOQUEANTE. As ATENÇÕES abaixo seguem o padrão sugerido até alguém dizer o contrário.
| # | Pergunta | Gravidade | Sugestão de padrão | Decide |
|---|---|---|---|---|
| 1 | O c4 pede que um nível inválido "impeça a aplicação de iniciar". Isso exige uma linha em `api/app.py` (`create_app` lê o nível) e a variável no `docker-compose.yml` e no `.env.example`, fora da pasta `ai/`. Aceita essa sobra de escopo? | ATENÇÃO | Sim: é a única forma de provar o c4 de ponta a ponta; o resto fica em `ai/` | arthurlleite + dono da NUC-01 (camposs04) |
| 2 | O campo `revisado` das listas começa `pendente` em todas as palavras. Quem revisa? | ATENÇÃO | O revisor do PR (sugestão: caio-nascime, dono da IA-02) troca para o próprio handle no PR de revisão | líder |
| 3 | O pseudônimo é estável dentro de uma chamada (o lote de descrições de um cliente). Estabilidade entre chamadas (ex.: mês a mês) exigiria guardar a tabela de equivalências. | ATENÇÃO | Por chamada nesta ficha; a IA-02 manda um lote por cliente (IA-02, c3). Persistir fica para quando a classificação precisar | arthurlleite + caio-nascime |
| 4 | Palavras de operação que também aparecem como prenome no Censo 2010 (TED, 544 pessoas; DEPOSITO, 55) ficam em claro. | ATENÇÃO | Aceitar: são essenciais para classificar; o risco fica registrado na seção 7 | líder |

Mudanças sugeridas na ficha (o humano aplica em PR): nenhuma. A leitura de "pedaço de 3 letras" do c8 está na D8 abaixo.

## 2. Decisões tomadas pelo agente
Cada uma precisa de confirmação humana.
### D1 · Interface pública em `ai/service.py` e `ai/contracts.py`
- **Alternativas:** A) `anonymize(descriptions, *, partners=(), level=None) -> list[str]` sobre um lote · B) uma função por descrição · C) classe com estado
- **Escolhida:** A — **motivo:** o c3 e o c7 pedem pseudônimo estável "anonimizando juntas"; o lote é a unidade natural (IA-02, c3: uma requisição por cliente). Nome em inglês (CODING_STANDARDS §1); os docs que citam `anonimizar()` passam a apontar para `anonymize()` em `docs/modulos/ai.md`.
- **Contratos:** `NameProtectionLevel` (`STRICT="estrito"`, `PEOPLE_PROTECTED="pessoas_protegidas"`, `OFF="desligado"`) e `InvalidNameProtectionLevelError` em `ai/contracts.py`; `load_name_protection_level()` em `ai/service.py`.
- **Impacto:** T1 a T6. [ ] confirmar

### D2 · Marcadores com o tipo: `[CPF]`, `[CNPJ]`, `[AGENCIA]`, `[CONTA]`
- **Alternativas:** A) marcador entre colchetes · B) asteriscos (`***`) · C) remover o trecho
- **Escolhida:** A — **motivo:** o c1 e o c2 pedem um marcador que diga o tipo; colchetes não colidem com texto de extrato nem com `PESSOA_nnn`. Agência e conta trocam a palavra-chave junto com o número (`AG 1234` → `[AGENCIA]`).
- **Impacto:** T2, T3. [ ] confirmar

### D3 · Documento detectado por formato, sem exigir DV válido
- **Escolhida:** CPF com e sem máscara (11 dígitos; também a máscara parcial dos bancos, `***.123.456-**`); CNPJ numérico (14 dígitos) e alfanumérico (12 caracteres + 2 dígitos, maiúsculas ou minúsculas, com e sem máscara). Sem máscara, o alfanumérico precisa de ao menos uma letra e um dígito nos 12 primeiros ou DV válido, para não engolir palavras. **Motivo:** o c1 pede DV certo ou errado; errar para o lado de esconder é o lado seguro.
- **Fontes:** herdadas do plano da HAR-04 (aprovado), D3: Receita Federal, perguntas e respostas do CNPJ alfanumérico (https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/perguntas-e-respostas/cnpj/cnpj-alfanumerico.pdf). Conferido com o código: `tools/harness.py` (`cnpj_valido`) calcula o DV com valor `ord(c) - 48` e "resto < 2 → 0" (**confere**).
- **Impacto:** T2. [ ] confirmar

### D4 · Contraparte = sequência de palavras que não são operação, número, data, valor nem marcador
- Cada descrição vira palavras; operação, conector na borda (`DE`, `DA`, `DO`, `DOS`, `DAS`, `E`), número, data, valor, `R$` e marcador ficam como estão. Cada sequência contínua do resto é **uma** contraparte e vira **um** pseudônimo. Palavra colada (`POSTOTESTE`) nunca casa com lista (c8).
- **Empresa ou pessoa:** é empresa a contraparte com sufixo societário (`LTDA`, `SA`, `S/A`, `EIRELI`, `SLU`, `CIA`) ou com palavra de atividade; `ME`, `MEI`, `EPP` e `EI` saem do nome e não decidem o tipo (c8: `MARIA TESTE SOUZA ME` é pessoa). No lote, se o mesmo nome aparece sozinho em algum lugar, ele é pessoa em todos (c8: `BOLETO ADVOCACIA MARIA TESTE SOUZA` usa o mesmo `PESSOA_nnn` de `PIX MARIA TESTE SOUZA`).
- **Alternativa descartada:** lista de nomes próprios (a D-03 pede proteção "sem depender de lista de nomes").
- **Impacto:** T4, T5. [ ] confirmar

### D5 · Numeração por ordem de primeira aparição no lote, contadores separados
- `PESSOA_001`, `PESSOA_002`... e `EMPRESA_001`... com 3 dígitos (`{:03d}`). Sem hash nem segredo: o número não revela nada do nome. **Impacto:** T4. [ ] confirmar

### D6 · Sócio truncado casa por prefixo
- O nome do extrato casa com o sócio cadastrado quando um é prefixo do outro (texto normalizado, sem acento, espaços simples) e o mais curto tem ao menos 6 caracteres; os dois recebem o mesmo `PESSOA_nnn` (c3, c8; RF-CLA-02c). **Impacto:** T4. [ ] confirmar

### D7 · Listas em `src/lastro/ai/preservation_lists.yaml`, lidas com PyYAML
- **Alternativas:** A) PyYAML (MIT, mantida, já no `uv.lock` como dependência de teste) · B) ruamel.yaml (MIT, mais pesada; preserva comentários, o que não precisamos) · C) JSON da biblioteca padrão (a ficha exige `.yaml`)
- **Escolhida:** A, com `yaml.safe_load`, passando de `dependency-groups.dev` para `dependencies` no `pyproject.toml` e `uv.lock` regenerado.
- **Fontes das palavras (acesso em 23/11/2026):** operação, em normativos do BCB (Res. CMN 3.919, tabela de tarifas, Regulamento do Pix), Planalto (Decreto 6.306/2007, LC 123/2006), gov.br (GPS × DARF) e uma tabela de tarifas pública de banco (abreviação `PAGTO`); atividade, código CNAE 2.3 conferido na API de subclasses do IBGE (a palavra, no singular ou plural, está na descrição ou nas observações da subclasse), e ADVOCACIA na Lei 8.906/1994; conflito, as palavras de atividade presentes na API de nomes do Censo 2010 do IBGE.
- **Impacto:** T5, T6. [ ] confirmar

### D8 · Como o teste do c8 entende "pedaço de 3 letras ou mais"
- Nenhuma palavra da saída (fora pseudônimos e marcadores) pode ser igual a uma palavra de nome de pessoa da entrada com 3+ letras, nem a um prefixo de 3+ letras dela (nome truncado). Comparar trechos soltos de 3 letras daria falso alarme (`LOPES` contém `PES`, que está em `PESSOA`). **Impacto:** T1, T5. [ ] confirmar

### D9 · Corpo sintético do c8 gerado no teste
- 200 nomes `<PRENOME> TESTE <SOBRENOME>` (20 prenomes × 10 sobrenomes, incluindo ROSA e MARINA, que estão em conflito), com operações variadas. Nenhum dado real; o `TESTE` no meio marca o nome como falso (SECURITY.md §3). **Impacto:** T1. [ ] confirmar

## 3. Resumo e abordagem
Uma função anonimiza um lote de descrições de um cliente antes de qualquer envio à IA: troca CPF, CNPJ, agência e conta por marcadores e, conforme o nível, troca cada contraparte por um pseudônimo estável no lote.
1. T1: testes da ficha em `tests/ai/test_anonimizar.py`, com documentos gerados na hora.
2. T2: contratos e detecção de CPF e CNPJ (numérico e alfanumérico).
3. T3: agência e conta.
4. T4: segmentação da contraparte e pseudônimos no nível estrito, com sócios.
5. T5: listas versionadas e nível `pessoas_protegidas`.
6. T6: configuração do nível e recusa ao iniciar o app.
7. T7: verificação final.

## 4. Contexto encontrado
- **Código relacionado:** `src/lastro/ai/__init__.py` vazio; `tests/ai/` vazio. `src/lastro/core/config.py` (`Settings`, pydantic-settings) e `src/lastro/api/app.py` (`create_app`) da NUC-01.
- **Dependências:** nenhuma (`depende_de` vazio). Consome esta ficha: IA-02 (caio-nascime), que passa os sócios e manda um lote por cliente.
- **Planos lidos:** `planos/NUC-01/plan.md` (aprovado): `create_app()` e `get_settings()` conferem com o código. `planos/NUC-02/plan.md` (aprovado): sem relação com `ai/`.
- **Reaproveitar:** a regra do DV alfanumérico de `tools/harness.py` (`cnpj_valido`) como referência (o harness não é importado por `src/`).
- **Não criar:** cliente de LLM, rede, persistência da tabela de equivalências, `utils.py`.
- **Pesquisa externa:** fontes da D7; nenhuma busca levou dado do projeto.

## 5. Decisões (já resolvidas)
- 18/11 · D-03: todo nome de contraparte vira `PESSOA_nnn` ou `EMPRESA_nnn`, ligado por padrão e configurável (DECISIONS.md).
- 18/11 · ARQ-06: só `src/lastro/ai/` chama LLM, depois de anonimizar.

## 6. Avaliação da ficha
| # | Achado | Gravidade | Critério |
|---|---|---|---|
| 1 | 8 critérios (> 4). Um só módulo e uma função pura; cabe em uma sessão de testes e uma de implementação. Não sugiro dividir. | ATENÇÃO | todos |
| 2 | "Pedaço de 3 letras" precisa de leitura operacional (D8). | ATENÇÃO | c8 |
| 3 | "Impede a aplicação de iniciar" toca `api/app.py` (pergunta 1). | ATENÇÃO | c4 |
| 4 | "Fonte pública verificável" vira regra checável: palavra presente na subclasse CNAE ou no documento citado (D7). | ATENÇÃO | c6 |
| 5 | Exemplos claros, com dado inventado e documentos gerados na hora; `hx check-clean` não pega nada fixo. | — | c1–c8 |

## 7. Riscos
- Nome de pessoa igual a palavra de operação ou atividade (ex.: TED; sobrenome que é atividade) sai em claro → conflito com o Censo e registro aqui; a lista se revisa no piloto.
- Falso positivo (palavra comum virando pseudônimo) piora a classificação, não a privacidade → aceitável; medir na IA-02.
- `revisado: pendente` em todas as palavras → pergunta 2.
- Mudar a interface depois exige issue `contrato:` (regra 11).

## 8. Aprovação
- [ ] Perguntas ATENÇÃO respondidas ou padrão aceito
- [ ] Decisões do agente confirmadas
- [ ] Plan e tasks revisados por ________ em __/__
