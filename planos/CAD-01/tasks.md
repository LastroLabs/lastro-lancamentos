# Tasks — CAD-01 · Validar CNPJ numérico e alfanumérico do cliente

**Plan:** planos/CAD-01/plan.md · **Ficha:** features/CAD-01.json
**Ordem:** T1 → revisão humana dos testes → commit só-de-testes (anotar o hash) → T2 em diante (sessão nova, sem editar `tests/`)

Mensagens oficiais da ficha (exatas):
- Vazio: `'Informe o CNPJ do cliente.'`
- Inválido (DV errado, tamanho errado, caractere fora do padrão, máscara malformada ou todos os caracteres iguais): `'O CNPJ informado não é válido. Confira os números.'`

---

## [x] T1 · Escrever os testes dos critérios
- **Critérios da ficha:** c1, c2, c3, c4
- **Regra de negócio (em linguagem simples):** garantir que o sistema aceita CNPJs numéricos (com ou sem máscara) e alfanuméricos no padrão de julho/2026 (maiúsculas ou minúsculas), devolve sempre o valor normalizado em 14 caracteres maiúsculos sem máscara, e recusa CNPJs vazios, com tamanho errado, caractere inválido, todos os dígitos iguais ou dígito verificador errado com as mensagens exatas da ficha.
- **Critérios de aceite:**
  - [x] Arquivo `tests/registry/test_cnpj.py` contém exatamente as 5 funções citadas em `verificacao`: `test_cnpj_numerico_valido_aceito_com_e_sem_mascara`, `test_cnpj_com_digito_errado_recusado`, `test_cnpj_alfanumerico_valido_aceito`, `test_cnpj_alfanumerico_com_digito_errado_recusado`, `test_cnpj_vazio_ou_fora_do_padrao_recusado`
  - [x] Cada teste chama `lastro.registry.service.validate_cnpj` e confere `is_valid`, `normalized` e `error_message`
  - [x] Os CNPJs válidos usados nos testes são montados em tempo de execução por uma função auxiliar local independente (cálculo Módulo 11 com `ASCII − 48`), sem nenhum CNPJ válido literal no arquivo (evita disparo no `hx check-clean` hoje e após `HAR-04`)
  - [x] c1 valida sem máscara e com máscara (`XX.XXX.XXX/XXXX-XX`) e confere que o `normalized` tem 14 caracteres e é igual nos dois casos; c2 altera o último dígito e confere a mensagem exata; c3 valida maiúsculas, minúsculas (e versão mascarada) e confere normalização em maiúsculas + recusa com DV trocado; c4 valida `""`, `"   "`, 13 caracteres, 15 caracteres, 14 caracteres com `'#'`, máscara mal posicionada e `00.000.000/0000-00`
  - [x] Todos os 5 testes falham hoje por ausência de `lastro.registry.service` (`ModuleNotFoundError`/`ImportError`), não por erro de sintaxe ou no próprio teste
- **Exemplos:** raiz sintética de 12 dígitos + DV calculado na hora (sem e com máscara) → `is_valid=True`, `normalized` com 14 dígitos iguais nos dois casos, `error_message=None`; mesma raiz + DV errado (`00`) → `is_valid=False`, `normalized=None`, `error_message='O CNPJ informado não é válido. Confira os números.'`; `""` → `is_valid=False`, `error_message='Informe o CNPJ do cliente.'`
- **Arquivos:** `tests/registry/test_cnpj.py`
- **Reaproveitar:** padrão de montagem dinâmica de dados sintéticos de `tests/harness/test_fase_b.py` · **Não criar:** código de produção, `conftest.py` compartilhado, nem literais de CNPJ com DV válido
- **Fora do escopo:** qualquer arquivo em `src/lastro/registry/`, persistência em banco, rotas HTTP
- **Decisões relacionadas:** D3, D5, D6; perguntas 1 a 5 (plan.md)
- **Pronto quando:** `docker compose run --rm dev pytest tests/registry/test_cnpj.py -q` falha apenas por módulo ausente e `hx check-clean` passa sem achados

## [x] T2 · Criar o contrato do resultado e a fachada pública do módulo
- **Critérios da ficha:** base de c1 a c4
- **Regra de negócio (em linguagem simples):** definir o formato fixo da resposta da validação (se passou, o CNPJ normalizado pronto para salvar no banco e, quando recusado, a mensagem em português simples) e expor uma única função pública no ponto de entrada do módulo `registry`.
- **Critérios de aceite:**
  - [x] `src/lastro/registry/contracts.py` define `CnpjValidationResult` como `@dataclass(frozen=True, slots=True)` com os campos `is_valid: bool`, `normalized: str | None` e `error_message: str | None`
  - [x] `src/lastro/registry/service.py` expõe `validate_cnpj(cnpj: str) -> CnpjValidationResult` delegando para `lastro.registry.cnpj`
  - [x] Docstrings em inglês (estilo Google), tipos explícitos (`X | None`), zero imports de fora da biblioteca padrão ou do próprio módulo `registry`
  - [x] `ruff check src/lastro/registry` limpo
- **Exemplos:** válido → `CnpjValidationResult(is_valid=True, normalized=<14 chars>, error_message=None)`; inválido → `CnpjValidationResult(is_valid=False, normalized=None, error_message='...')`
- **Arquivos:** `src/lastro/registry/contracts.py`, `src/lastro/registry/service.py`
- **Reaproveitar:** estilo de `src/lastro/core/contracts.py` e `src/lastro/core/service.py` · **Não criar:** modelo de banco, tabela `cliente` (`DB-01`), rota FastAPI ou `utils.py`
- **Fora do escopo:** algoritmo de validação (T3/T4), cadastro de cliente (`CAD-03`), leitura de plano de contas (`CAD-02`)
- **Decisões relacionadas:** D2, D3, D5
- **Pronto quando:** `docker compose run --rm dev python -c "import lastro.registry.contracts, lastro.registry.service"` termina com código 0 (após esqueleto mínimo em `cnpj.py` ou delegação pronta na T3)

## [x] T3 · Implementar normalização e validação de vazio, tamanho, formato e repetidos
- **Critérios da ficha:** c4 (e preparação de c1 e c3)
- **Regra de negócio (em linguagem simples):** antes de calcular o dígito verificador, o sistema limpa espaços nas bordas, recusa texto vazio dizendo para informar o CNPJ, converte letras para maiúsculas e aceita somente um texto com 14 caracteres alfanuméricos no padrão (12 posições de `0–9`/`A–Z` e 2 dígitos finais `0–9`), sem máscara ou com a máscara oficial `XX.XXX.XXX/XXXX-XX`. Também recusa sequências com todos os 14 caracteres iguais (como `00.000.000/0000-00`).
- **Critérios de aceite:**
  - [x] `""` e `"   "` retornam `is_valid=False`, `normalized=None`, `error_message='Informe o CNPJ do cliente.'`
  - [x] Regex com `re.ASCII` aceita exclusivamente sem máscara (`^[A-Z0-9]{12}[0-9]{2}$`) ou máscara oficial (`^[A-Z0-9]{2}\.[A-Z0-9]{3}\.[A-Z0-9]{3}/[A-Z0-9]{4}-[0-9]{2}$`) após `.strip().upper()`
  - [x] Tamanho diferente de 14 (13 ou 15), caractere fora do padrão (`'#'`, letra acentuada, dígito não-ASCII), letra nos 2 últimos dígitos, pontuação mal posicionada e 14 caracteres todos iguais (`00000000000000`) retornam `is_valid=False`, `normalized=None`, `error_message='O CNPJ informado não é válido. Confira os números.'`
  - [x] Entradas bem formadas produzem string normalizada de 14 caracteres em maiúsculas sem `.`, `/` ou `-` para a etapa de DV
- **Exemplos:** `""` → `'Informe o CNPJ do cliente.'`; `"1234567890123"` (13 chars) → `'O CNPJ informado não é válido. Confira os números.'`; `"123456789012345"` (15 chars) → inválido; `"123456#8901234"` → inválido; `"00.000.000/0000-00"` → inválido
- **Arquivos:** `src/lastro/registry/cnpj.py`, `src/lastro/registry/service.py`
- **Reaproveitar:** `CnpjValidationResult` da T2 · **Não criar:** import de `tools/harness.py`, biblioteca externa ou substituição genérica de qualquer pontuação fora de lugar
- **Fora do escopo:** cálculo de dígito verificador (T4), formatação de exibição com máscara
- **Decisões relacionadas:** D1, D4; perguntas 1, 2 e 3
- **Pronto quando:** `docker compose run --rm dev pytest tests/registry/test_cnpj.py::test_cnpj_vazio_ou_fora_do_padrao_recusado -q` passa

## [x] T4 · Implementar cálculo de dígito verificador numérico e alfanumérico (Módulo 11)
- **Critérios da ficha:** c1, c2, c3
- **Regra de negócio (em linguagem simples):** conferir matematicamente os 2 últimos dígitos do CNPJ pela regra oficial da Receita Federal (julho/2026): cada um dos 12 primeiros caracteres vira um número subtraindo 48 do seu código ASCII (`0–9` continuam `0–9`; `A` vira `17`, `B` vira `18`, ..., `Z` vira `42`), multiplica-se pelos pesos do Módulo 11 para obter o 1º dígito verificador e repete-se com o 1º dígito incluído para o 2º. Se os dois baterem, o CNPJ é aceito e devolvido normalizado; se qualquer um divergir, é recusado.
- **Critérios de aceite:**
  - [x] Cálculo do 1º DV usa os 12 primeiros caracteres com pesos `(5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)` e `valor = ord(char) - 48`; resto `< 2` gera `0`, senão `11 - resto`
  - [x] Cálculo do 2º DV usa os 12 primeiros caracteres mais o 1º DV com pesos `(6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)` e a mesma regra de resto
  - [x] Funciona igualmente para CNPJs puramente numéricos e alfanuméricos (com ou sem máscara, maiúsculas ou minúsculas na entrada), devolvendo `normalized` com 14 caracteres maiúsculos sem máscara
  - [x] Qualquer divergência no 1º ou no 2º DV retorna `is_valid=False`, `normalized=None`, `error_message='O CNPJ informado não é válido. Confira os números.'`
  - [x] Nenhum literal de CNPJ válido em código ou docstrings
- **Exemplos:** `<CNPJ numérico válido>` sem máscara e com máscara → ambos `is_valid=True` e mesmo `normalized`; último dígito trocado → `is_valid=False` com mensagem de c2; `<CNPJ alfanumérico válido>` em maiúsculas e minúsculas → ambos `is_valid=True` e mesmo `normalized` em maiúsculas; DV alterado → `is_valid=False` com mensagem de c3
- **Arquivos:** `src/lastro/registry/cnpj.py`
- **Reaproveitar:** normalização e validação de formato da T3 · **Não criar:** duas funções separadas para numérico e alfanumérico (a fórmula `ord(c) - 48` unifica os dois)
- **Fora do escopo:** cadastro de cliente (`CAD-03`), anonimização em descrições (`IA-01`), detector do harness (`HAR-04`)
- **Decisões relacionadas:** D1, D4; pergunta 4
- **Pronto quando:** `docker compose run --rm dev pytest tests/registry/test_cnpj.py -q` passa todos os 5 testes

## [x] T5 · Verificação final
- **Critérios de aceite:**
  - [x] `git diff <hash-dos-testes> -- tests/` vazio
  - [x] `ruff check .` e `ruff format --check src/lastro/registry tests/registry` limpos
  - [x] `hx check-clean` e `hx verify` em OK
  - [x] `hx feature verify CAD-01` grava `passing`
  - [x] `progress/CAD-01.md` atualizado com o que foi feito, rodado e decidido
- **Pronto quando:** os três comandos do `hx` (`hx check-clean`, `hx verify` e `hx feature verify CAD-01`) terminam com código 0
