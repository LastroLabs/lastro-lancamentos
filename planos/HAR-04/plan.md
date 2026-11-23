# Plan — HAR-04 · Alinhar validação de fichas e check-clean às decisões de 18/11

**Status:** pronto para revisão
**Branch:** feat/HAR-04-alinhar-validacao-de-fichas-e-check-clea · **Data:** 23/11/2026 · **Responsável:** caio-nascime
**Tasks:** planos/HAR-04/tasks.md
**Versão:** recorte enxuto (v2). Fica: c1, c2 só o regex, c3, c4 simplificado, c5, c6, c7 só nome único, c9. Sai: sigla do módulo no ID, formato rígido do comando, arquivo único, MoSCoW cruzada e c8 (dependência na mesma onda).

## 1. A decidir (humano)
Nenhuma pendente. A ficha foi ajustada ao recorte, `web` foi aceito e a opção A foi escolhida (ver §5).

## 2. Decisões tomadas pelo agente
### D1 · Ler os handles do `equipe.ts` por expressão regular
- **Alternativas:** A) regex sobre `github: '<handle>'` · B) gerar JSON a partir do TS · C) copiar a lista em `tools/`
- **Escolhida:** A — **motivo:** arquivo simples e estável; o harness só usa a biblioteca padrão; C duplicaria a fonte. Nenhum handle lido → erro (nunca "aceita todos").
- **Fontes:** `gitpages/src/data/equipe.ts`; sem pesquisa externa.
- **Impacto:** T4 (c6).
- [ ] confirmar

### D2 · Mensagem: `<ID> (<campo>): <problema>`
- **Alternativas:** A) campo entre parênteses na linha existente · B) um bloco por ficha
- **Escolhida:** A — **motivo:** c1–c7 pedem "citando a ficha e o campo"; reaproveita o `MOTIVO` em lista e o código 2 do `main`. No nome repetido (c7), a linha cita as duas fichas.
- [ ] confirmar

### D3 · CNPJ alfanumérico: ampliar o detector atual
- **Alternativas:** A) ampliar `_CNPJ` e `cnpj_valido` (valor do caractere = ASCII − 48; maiúsculas antes do cálculo) · B) detector novo ao lado
- **Escolhida:** A — **motivo:** o numérico é caso particular do alfanumérico; um só tipo (`TIPO_CNPJ`), como pede c9. Pesos e "resto < 2 → 0" já estão em `_digito_verificador`.
- **Fontes:** Receita Federal, perguntas e respostas: https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/perguntas-e-respostas/cnpj/cnpj-alfanumerico.pdf · Serpro, cálculo do DV: https://serpro.gov.br/menu/noticias/videos/calculodvcnpjalfanaumerico.pdf (acesso em 23/11/2026, por resultado de busca; PDFs não abertos na íntegra). **Contradição:** um resumo do Serpro diz "DV = 11 − resto" sem tratar resto 0 ou 1; guias de terceiros dizem "resto < 2 → 0". Teste local: o exemplo com letras publicado pela Receita (não reproduzido aqui, para o `check-clean` não o marcar) fecha com "resto < 2 → 0". Conferir na rotina oficial do Serpro na T6.
- **Impacto:** T6 (c9).
- [ ] confirmar

### D4 · Regras novas numa função própria, ligada só ao carregador do painel
- **Alternativas:** A) função nova `validar_regras_do_projeto(fichas, raiz)` chamada por `_carregar_fichas_validas` · B) dentro de `_problemas_da_ficha`
- **Escolhida:** A — **motivo:** `test_fase_a` chama `validar_fichas` direto e não é afetado; `hx state`, `feature verify` e `feature start` (que usam `_carregar_fichas_validas`) passam a recusar. Com a opção A (escolhida), a função só roda se `equipe.ts` existir na raiz.
- **Impacto:** T2 a T5.
- [ ] confirmar

### D5 · Sem biblioteca nova; constantes ao lado de `CAMPOS_OBRIGATORIOS`
- [ ] confirmar

## 3. Resumo e abordagem
Cada ficha passa a ser conferida contra um pequeno conjunto de regras de formato (campos exatos, ID, módulo, prioridade, onda, campos fixos, responsável, nome de teste único), e o check-clean passa a achar CNPJ com letras.
Tudo em `tools/harness.py`. T1 escreve os testes; T2 cria a função de regras e entrega c1, c4 e c5; T3 acrescenta ID e módulo; T4, o responsável; T5, o nome de teste único; T6, o CNPJ; T7 verifica. Nenhuma ficha existente precisa mudar (conferido por simulação, ver §4).

## 4. Contexto encontrado
- **Código relacionado:** `tools/harness.py`: `CAMPOS_OBRIGATORIOS`, `_problemas_da_ficha`, `validar_fichas`, `_carregar_fichas_validas`, `cmd_state`; `_CNPJ`, `cnpj_valido`, `_digito_verificador`, `tipos_da_linha`, `varrer`.
- **Dependências:** nenhuma em `depende_de`. A HAR-03 (camposs04) depende desta.
- **Reaproveitar:** `HarnessErro`/`mostrar_erro` e o código 2 de `main`; `ficha`, `gravar_todas` de `tests/harness/test_state_filtro.py`; em `test_fase_b.py`, o CNPJ montado por concatenação (o repo é varrido pelo check-clean).
- **Não criar:** outro carregador de fichas, outro formato de erro, outro tipo de achado de CNPJ.
- **Simulação (23/11), regras do recorte sobre as 28 fichas atuais:** 0 recusadas (campos, ID, módulo com `web`, prioridade, onda, fixos, handles, nome de teste único). O c1(a) fecha sem mexer em ficha.
- **Pesquisa externa:** só o c9 (D3). Protótipo do detector sobre os arquivos versionados: 0 achados.

## 5. Decisões (já resolvidas)
- 23/11 · Ficha `features/HAR-04.json` ajustada ao recorte por caio-nascime (autorização na sessão; o agente editou só `criterios` e `verificacao`, sem tocar em `estado`, `responsavel` nem `evidencia`): c2 só o regex; c3 com 17 módulos em inglês; c4 sem MoSCoW; c7 só nome único; c8 removido; teste do c2 renomeado para `test_id_fora_do_padrao_recusado`; 8 testes em `verificacao`. Ficha segue válida no `hx state`.
- 23/11 · Opção A para os testes antigos: as regras de 18/11 só valem se existir `gitpages/src/data/equipe.ts` na raiz; nenhum teste antigo é editado (caio-nascime).
- 23/11 · `web` aceito como 17º módulo (caio-nascime).
- 23/11 · c9 mantém CNPJ em minúsculas; ficha não será dividida (sem HAR-05); docs atualizados no mesmo PR da feature, sem PR separado (caio-nascime). Docs: `processo.md` e `orquestracao.mdx`; `SECURITY.md` §7 e `seguranca.md` seguem corretos (a allowlist `pytest`/`ruff` não muda).
- 23/11 · Recorte enxuto: sigla, formato do comando, arquivo único, MoSCoW cruzada e c8 saem (pedido de caio-nascime: fichas mais livres, prazo curto, HX-11 e HX-12 já implementados).

## 6. Avaliação da ficha
| # | Achado | Gravidade | Critério |
|---|---|---|---|
| 1 | Ficha citava critérios e testes descartados | resolvido em 23/11 | c2, c4, c7, c8 |
| 2 | Testes antigos usam IDs e handles que as regras recusariam | ATENÇÃO | c2, c6 |
| 3 | `web` fora dos "14 + harness + ci" | resolvido (aceito) | c3 |
| 4 | Nomes de módulo em português no exemplo do c2(b) e no c3 | ATENÇÃO | c2, c3 |
| 5 | c9 não pode ter CNPJ válido literal no teste (o check-clean do repo o acharia) | ATENÇÃO | c9 |
| 6 | Feature com 8 critérios em duas áreas | aceito, sem dividir | c9 |

## 7. Riscos
- Validação mais rígida trava `hx state`, `verify` e `start` de todo o time se uma ficha futura fugir → a mensagem diz ficha, campo e correção.
- Ler TS por regex quebra se o formato do `equipe.ts` mudar → erro explícito se nenhum handle for lido (D1).
- Falso positivo de CNPJ alfanumérico em texto de 14 caracteres → o DV elimina quase todos; 0 no repo.
- Teste de c9 com CNPJ válido literal sujaria o check-clean → montar o valor em tempo de execução.

## 8. Aprovação
- [x] Sem pergunta BLOQUEANTE (ficha ajustada em 23/11)
- [ ] Decisões do agente confirmadas (D1 a D5)
- [ ] Plan e tasks revisados por <nome> em DD/MM
