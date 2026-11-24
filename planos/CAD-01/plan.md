# Plan — CAD-01 · Validar CNPJ numérico e alfanumérico do cliente

**Status:** aprovado (marrathomaz, 23/11/2026)
**Branch:** feat/CAD-01-validar-cnpj-numerico-e-alfanumerico-do · **Data:** 23/11/2026 · **Responsável:** marrathomaz
**Tasks:** planos/CAD-01/tasks.md

## 1. A decidir (humano)
Tudo que bloqueia ou depende de uma pessoa. Resolvida → mova para "5. Decisões".

| # | Pergunta | Gravidade | Sugestão de padrão | Decide |
|---|---|---|---|---|
| 1 | Espaços nas bordas (`"  <CNPJ>  "`), texto só com espaços (`"   "`) e pontuação mal posicionada (ex.: `123.456.789/0123-00`): como tratar? | ATENÇÃO | Aplicar `.strip()` antes de checar vazio (`"   "` → `'Informe o CNPJ do cliente.'`); aceitar apenas os 14 caracteres sem máscara ou a máscara oficial exata `XX.XXX.XXX/XXXX-XX`, recusando pontuação solta como inválido. | marrathomaz |
| 2 | CNPJ com todos os 14 caracteres iguais (ex.: `00.000.000/0000-00`), cujo cálculo de Módulo 11 fecha com DV `00`, deve ser recusado? | ATENÇÃO | Sim: recusar qualquer sequência com todos os 14 caracteres idênticos, seguindo a prática da RFB e o `tools/harness.py`. | marrathomaz |
| 3 | No CNPJ alfanumérico, aceitar todo o alfabeto ASCII `A–Z` nas 12 primeiras posições ou excluir letras visualmente ambíguas (`I`, `O`, `U`, `Q`, `F`)? | ATENÇÃO | Aceitar `A–Z` completo (e `a–z` normalizado para maiúsculas), conforme a fórmula oficial `ASCII − 48` da IN RFB nº 2.229/2024 e o critério c3 da ficha. | marrathomaz |
| 4 | A ficha pede `'O CNPJ informado não é válido. Confira os números.'` também para CNPJ alfanumérico (c3) e em `CAD-03` (c2). Manter o texto literal? | ATENÇÃO | Sim, manter literal para compatibilidade com `CAD-01` e `CAD-03`. Se quiserem trocar "números" por "caracteres", ajustar as duas fichas em PR próprio. | líder / marrathomaz |
| 5 | A ficha fixa nomes de teste em português (`test_cnpj_numerico_valido_...`), contra o `CODING_STANDARDS.md` §1 (inglês). Manter como na `NUC-02`? | ATENÇÃO | Sim: manter os nomes da ficha nos testes (`CODING_STANDARDS.md` §9.4) e escrever o código em `src/lastro/registry/` em inglês (§9.1). | marrathomaz |

Mudanças sugeridas na ficha (o humano aplica em PR): nenhuma obrigatória; opcionalmente explicitar em c4 o caso de sequência toda de zeros (`00.000.000/0000-00`) e espaços em branco.

## 2. Decisões tomadas pelo agente
Cada uma precisa de confirmação humana.

### D1 · Implementação própria em Python puro (sem biblioteca externa)
- **Alternativas:** A) Python puro com biblioteca padrão (`re`, `dataclasses`) · B) `validate-docbr` (PyPI v1.11.1, jun/2025, licença MIT, Python `>=3.10`, suporta CNPJ alfanumérico) · C) `python-stdnum` (PyPI, licença LGPL-2.1-or-later, Python 3+, suporta CNPJ alfanumérico)
- **Escolhida:** A — **motivo:** o algoritmo oficial (Módulo 11 com `ord(c) - 48`) tem ~30 linhas, evita dependência nova em `requirements-dev.txt`, funciona em Python 3.12 (`Dockerfile`) e 3.14 (ARQ-08) e dá controle exato sobre máscara, normalização e mensagens de erro. As libs B e C ainda exigiriam camada própria para diferenciar vazio vs inválido e formatar as mensagens da ficha; C traz ainda licença LGPL e centenas de validadores sem uso.
- **Fontes:** IN RFB nº 2.229/2024 (`http://normas.receita.fazenda.gov.br/sijut2consulta/link.action?idAto=141102`, acesso em 23/11/2026) · Receita Federal (`https://servicos.receitafederal.gov.br/`, acesso em 23/11/2026) · `validate-docbr` (`https://pypi.org/project/validate-docbr/`, acesso em 23/11/2026) · `python-stdnum` (`https://pypi.org/project/python-stdnum/`, acesso em 23/11/2026)
- **Impacto:** T2, T3, T4; critérios c1 a c4.
- [x] confirmar

### D2 · Regra pura em `registry/`, sem banco nem HTTP
- **Alternativas:** A) função pura em `registry/cnpj.py` exposta por `registry/service.py` · B) validador Pydantic na camada `api/` · C) validação no `repository.py`
- **Escolhida:** A — **motivo:** `depende_de` é vazio (`DB-01` e `api/` ainda não existem) e `ARCHITECTURE.md` §3 define `service.py` como interface pública do módulo e arquivos internos (`cnpj.py`) como privados. Prepara o consumo direto pela `CAD-03` sem criar acoplamento com HTTP (`P-13` fica fora daqui).
- **Fontes:** `ARCHITECTURE.md` §3, §4 e §7; `features/CAD-03.json`.
- **Impacto:** T2 a T4; todos os critérios.
- [x] confirmar

### D3 · Retorno estruturado (`CnpjValidationResult`) em vez de exceção
- **Alternativas:** A) `@dataclass(frozen=True, slots=True)` com `is_valid`, `normalized` e `error_message` · B) função que retorna `str` e lança `InvalidCnpjError` · C) tupla `(bool, str)`
- **Escolhida:** A — **motivo:** segue o mesmo padrão sem exceção para recusa esperada adotado em `NUC-02` (`core/contracts.py`), expressa diretamente "aceito + valor normalizado" e "recusado + mensagem em português" (c1–c4) e permite à `CAD-03` validar nome e CNPJ sem `try/except`.
- **Fontes:** `planos/NUC-02/plan.md` (D2); `CODING_STANDARDS.md` §2; ficha c1–c4.
- **Impacto:** T1 a T4.
- [x] confirmar

### D4 · Algoritmo oficial de normalização e validação (IN RFB nº 2.229/2024)
- **Alternativas:** A) regex estrita ASCII para formato sem máscara (`[A-Z0-9]{12}[0-9]{2}`) ou máscara exata (`XX.XXX.XXX/XXXX-XX`), normalização para maiúsculas sem máscara, rejeição de 14 caracteres iguais e Módulo 11 com `ord(c) - 48` (pesos `5..2, 9..2` e `6..2, 9..2`) · B) remover qualquer caractere não alfanumérico antes de checar tamanho
- **Escolhida:** A — **motivo:** a alternativa B aceitaria lixo no meio do texto (como `#` ou pontos soltos), falhando c4(d). Usar `[A-Z0-9]` e `[0-9]` com `re.ASCII` evita falso positivo com dígitos/letras Unicode fora do padrão.
- **Fontes:** IN RFB nº 2.229/2024 (acesso em 23/11/2026); ficha c1–c4.
- **Impacto:** T3, T4; critérios c1 a c4.
- [x] confirmar

### D5 · Nomes da interface pública (fixados pelos testes da T1)
- **`lastro.registry.contracts`:** `CnpjValidationResult(is_valid: bool, normalized: str | None, error_message: str | None)`
- **`lastro.registry.service`:** `validate_cnpj(cnpj: str) -> CnpjValidationResult`
- **`lastro.registry.cnpj`:** implementação interna (privada ao módulo `registry`)
- **Motivo:** segue `ARCHITECTURE.md` §3 e `CODING_STANDARDS.md` §2 (`is_valid`, nomes em inglês, sem `utils.py`). Evita colisão com `CAD-02` (leitor da planilha do plano de contas) e entrega contrato estável v0 para `CAD-03`.
- **Impacto:** T1 a T4; futura `CAD-03`.
- [x] confirmar

### D6 · Geração dinâmica dos CNPJs válidos nos testes (segurança)
- **Motivo:** `docs/SECURITY.md` §3/§7 e `hx check-clean` proíbem literais de CNPJ com DV válido no repositório (numéricos hoje; alfanuméricos após `HAR-04`). Os testes em `tests/registry/test_cnpj.py` gerarão os DVs em tempo de execução a partir de raízes sintéticas de 12 caracteres, de forma independente do código de produção, conforme c1 e c3 da ficha.
- **Impacto:** T1 e T5 (`hx check-clean`).
- [x] confirmar

## 3. Resumo e abordagem
Validação e normalização pura de CNPJ numérico e alfanumérico (padrão julho/2026 da Receita Federal) no módulo `registry`, devolvendo o valor em 14 caracteres maiúsculos sem máscara ou a mensagem em português simples da ficha.
1. T1: criar `tests/registry/test_cnpj.py` com os 5 testes da ficha e geração dinâmica de DV em tempo de execução.
2. T2: criar `src/lastro/registry/contracts.py` (`CnpjValidationResult`) e expor `validate_cnpj` em `src/lastro/registry/service.py`.
3. T3: implementar limpeza, checagem de vazio, formato com/sem máscara (ASCII estrito) e rejeição de caracteres repetidos em `src/lastro/registry/cnpj.py`.
4. T4: implementar o cálculo dos dois dígitos verificadores (Módulo 11, `ord(c) - 48`) em `src/lastro/registry/cnpj.py` e concluir a integração com `service.py`.
5. T5: verificação final com `ruff`, `hx check-clean`, `hx verify` e `hx feature verify CAD-01`.

## 4. Contexto encontrado
- **Código relacionado:** `src/lastro/registry/__init__.py` vazio; `tests/registry/` só tem `.gitkeep`. Referência de estilo em `src/lastro/core/contracts.py` e `src/lastro/core/service.py` (NUC-02). `tools/harness.py` (`cnpj_valido`, linhas 500–532) implementa só CNPJ numérico para o `check-clean`, mas `src/lastro/` não importa `tools/`.
- **Dependências:** nenhuma (`depende_de` vazio). Consome esta ficha: `CAD-03` (`not_started`, `RaissaOliveira19`). `DB-01` define a coluna `cliente.cnpj_normalizado text not null`.
- **Reaproveitar:** convenção de contratos imutáveis de `src/lastro/core/contracts.py` e padrão de montagem dinâmica de dados sintéticos de `tests/harness/test_fase_b.py`.
- **Não criar:** consulta ao banco, rota FastAPI, status HTTP (`P-13`), `utils.py`, nem import de `tools/harness.py`.
- **Pesquisa externa:** IN RFB nº 2.229/2024 (CNPJ alfanumérico a partir de jul/2026: 12 posições `0–9`/`A–Z`, 2 DVs `0–9`, Módulo 11 com `ASCII − 48`, pesos `5..2,9..2` e `6..2,9..2`); comparadas `validate-docbr` (MIT, PyPI v1.11.1) e `python-stdnum` (LGPL-2.1+) contra implementação própria (detalhes em D1; acesso em 23/11/2026).

## 5. Decisões (já resolvidas)
- 18/11 · `ARQ-08` (Python 3.14; `Dockerfile` ainda em 3.12) e `BD-01` (`cnpj_normalizado` como texto, nunca inteiro).
- 23/11 . Aceitar apenas os 14 caracteres sem máscara ou a máscara oficial exata `XX.XXX.XXX/XXXX-XX`, conforme e organização sugerida (pergunta 1, Thomaz).
- 23/11 . CNPJs com todos os 14 caracteres iguais devem ser recusados, conforme a organização sugerida (pergunta 2, Thomaz).
- 23/11 . Aceitar todo o alfabeto ASCII `A–Z` nas 12 primeiras posições, conforme a organização sugerida (pergunta 3, Thomaz).
- 24/11 . Manter o texto literal original `'O CNPJ informado não é válido. Confira os números.'` para compatibilidade com `CAD-01` e `CAD-03` (reversão da troca anterior de 23/11, seguindo o padrão sugerido da pergunta 4 sem alterar texto ao usuário sem aprovação prévia da liderança; Thomaz).
- 23/11 . Sim: manter os nomes da ficha nos testes (`CODING_STANDARDS.md` §9.4) e escrever o código em `src/lastro/registry/` em inglês (§9.1), conforme a orientação sugerida (pergunta 5, Thomaz).

## 6. Avaliação da ficha
| # | Achado | Gravidade | Critério |
|---|---|---|---|
| 1 | Espaços nas bordas, texto só de espaços e máscara malformada não estão exemplificados (pergunta 1). | ATENÇÃO | c1, c4 |
| 2 | Sequência de 14 caracteres iguais (ex.: `00.000.000/0000-00`) passa no Módulo 11 se não houver checagem explícita (pergunta 2). | ATENÇÃO | c2 |
| 3 | Escopo de letras permitidas (`A–Z` completo vs exclusão de `I/O/U/Q/F`) não está citado explicitamente (pergunta 3). | ATENÇÃO | c3 |
| 4 | Mensagem literal de c3 diz "Confira os números." mesmo para CNPJ alfanumérico (pergunta 4). | ATENÇÃO | c3 |
| 5 | Nomes de teste em português na ficha divergem de `CODING_STANDARDS.md` §1 (pergunta 5); mensagens ao usuário exigidas no domínio divergem da nota de §1 sobre textos ficarem na API. | ATENÇÃO | todos |
| 6 | Risco de falso positivo no `hx check-clean` (e futuro `HAR-04` c9) se testes ou docstrings contiverem literal de CNPJ com DV válido (mitigado por D6). | ATENÇÃO | c1, c3 |
| 7 | Escopo enxuto (4 critérios, 1 módulo, 5 comandos em `verificacao` cobrindo 100% dos critérios); não precisa dividir. | — | todos |

## 7. Riscos
- Literal de CNPJ válido vazar em teste, docstring ou plano e quebrar `hx check-clean` (hoje ou após `HAR-04`) → gerar DVs apenas em tempo de execução nos testes e usar somente DVs inválidos (ex.: final `00`) em exemplos escritos.
- Regex com `\d` ou `.upper()` aceitar dígitos/letras não-ASCII → usar exclusivamente `[0-9]`, `[A-Z]` e `re.ASCII`.
- Contrato de `registry/service.py` mudar quando `CAD-03` começar → contrato é v0 (regra 11); mudanças futuras abrem issue `contrato:` avisando a dona da `CAD-03`.
- Divergência Python 3.12 (`Dockerfile`) × 3.14 (`ARQ-08`) → usar apenas recursos comuns às duas versões.

## 8. Aprovação
- [x] Perguntas ATENÇÃO respondidas ou padrão aceito
- [x] Decisões do agente confirmadas (D1 a D6)
- [x] Plan e tasks revisados por marrathomaz em 23/11
