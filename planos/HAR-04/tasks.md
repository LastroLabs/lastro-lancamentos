# Tasks — HAR-04 · Alinhar validação de fichas e check-clean às decisões de 18/11

**Plan:** planos/HAR-04/plan.md · **Ficha:** features/HAR-04.json
**Ordem:** (ficha já ajustada em 23/11) → T1 → revisão humana dos testes → commit só-de-testes (anotar o hash) → T2 em diante (sessão nova, sem editar `tests/`)
**Escopo (v2, recorte enxuto):** c1, c2 (só o regex), c3, c4 (prioridade e onda), c5, c6, c7 (só nome único), c9. Não entram: sigla do módulo, formato do comando, arquivo único, MoSCoW cruzada, c8.

---

## [ ] T1 · Escrever os testes dos critérios
- **Critérios da ficha:** c1 a c7 e c9 
- **Regra de negócio (em linguagem simples):** a ficha é o contrato de cada feature. Com campo sobrando, ID fora do padrão, módulo inexistente ou dono fora da equipe, o painel não monta nada. O check-clean precisa reconhecer o CNPJ com letras, que a Receita passou a emitir.
- **Critérios de aceite:**
  - [ ] `tests/harness/test_validacao_lote.py` tem um teste por nome citado em `verificacao` da ficha atualizada: `test_campo_extra_recusado`, `test_id_fora_do_padrao_recusado`, `test_modulo_desconhecido_recusado`, `test_prioridade_e_onda_validadas`, `test_campos_fixos_validados`, `test_responsavel_fora_da_equipe_recusado`, `test_nome_de_teste_repetido_entre_fichas_recusado`, `test_check_clean_detecta_cnpj_alfanumerico`
  - [ ] Cada recusa confere: código 2, `ERRO:`, `MOTIVO:` e `CORREÇÃO:` em stderr, ID da ficha e campo na mensagem, e nenhuma ficha listada no stdout
  - [ ] c1(a) roda `hx state` na raiz real (código 0); os demais usam cópia em `tmp_path` com `equipe.ts` copiado (é o que liga as regras, ver D4)
  - [ ] c9: CNPJ montado em tempo de execução, nunca literal válido; confere que o valor não aparece na saída
  - [ ] Nenhum teste antigo é editado (opção A, escolhida); se algum quebrar mesmo assim, ajustar só IDs e handles dos ajudantes, sem mudar asserção (autorizado por caio-nascime em 23/11)
  - [ ] Os testes novos falham hoje pelo motivo certo; os antigos seguem verdes
- **Exemplos:** ficha `HAR-91` válida + campo `notas` → código 2, motivo cita `HAR-91 (notas)`; arquivo com a linha 5 `12.abc.345/01de-` + DV certo → achado `arquivo:5  CNPJ com dígito verificador válido`
- **Arquivos:** `tests/harness/test_validacao_lote.py` (novo)
- **Fora do escopo:** código de produção, fichas, docs
- **Pronto quando:** `docker compose run --rm dev pytest tests/harness/test_validacao_lote.py -q` mostra só falhas esperadas e `pytest tests/harness -q` não regride nos antigos

## [ ] T2 · Camada de regras, campos exatos, fixos, prioridade e onda
- **Critérios da ficha:** c1, c4, c5
- **Regra de negócio (em linguagem simples):** a ficha tem exatamente os 15 campos, nem mais nem menos. `essencial` é sempre `false` e `tipo_verificacao` sempre `comando`. `bloqueada_por` só é preenchido quando o estado é `blocked`. A prioridade é must, should ou could, e a onda é a semana do cronograma, de 1 a 4.
- **Critérios de aceite:**
  - [ ] Existe `validar_regras_do_projeto(fichas, raiz)`, chamada por `_carregar_fichas_validas` e só quando `gitpages/src/data/equipe.ts` existe na raiz (D4)
  - [ ] Campo fora de `CAMPOS_OBRIGATORIOS` → problema `<ID> (<campo>)`
  - [ ] `essencial` ≠ `false`, `tipo_verificacao` ≠ `comando` ou `bloqueada_por` preenchido fora de `blocked` → um problema cada
  - [ ] Prioridade fora de must/should/could → `(prioridade)`; onda não inteira (booleano não conta) ou fora de 1..4 → `(onda)`
- **Exemplos:** campo `notas` → recusa; `essencial: true` → recusa; `urgente` → recusa; onda 5 → recusa; `not_started` com `bloqueada_por: "D-05"` → recusa
- **Arquivos:** `tools/harness.py`
- **Reaproveitar:** `_vazio`, `CAMPOS_OBRIGATORIOS`, `HarnessErro` · **Não criar:** outro carregador de fichas
- **Fora do escopo:** conferir a prioridade contra a MoSCoW dos RFs
- **Decisões relacionadas:** D2, D4, D5
- **Pronto quando:** `pytest tests/harness/test_validacao_lote.py::test_campo_extra_recusado tests/harness/test_validacao_lote.py::test_prioridade_e_onda_validadas tests/harness/test_validacao_lote.py::test_campos_fixos_validados -q` passa

## [ ] T3 · Padrão do ID e módulo conhecido
- **Critérios da ficha:** c2, c3
- **Regra de negócio (em linguagem simples):** o ID tem de 2 a 4 letras maiúsculas, hífen e 2 dígitos, para todo mundo reconhecer uma ficha. O módulo é uma das pastas de `src/lastro/`, `harness`, `ci` ou `web`. Não se exige que o ID comece pela sigla do módulo.
- **Critérios de aceite:**
  - [ ] ID fora de `^[A-Z]{2,4}-\d{2}$` → `(id)`
  - [ ] Módulo fora dos 17 → `(modulo)`, e a CORREÇÃO lista os 17 (14 pastas em inglês, `harness`, `ci`, `web`)
  - [ ] Fichas atuais continuam aceitas (inclui `HX-10` e `WEB-01`)
- **Exemplos:** `ACE-1` → recusa; `CI-01` e `HX-10` → aceitas; módulo `financeiro` → recusa e lista os 17; `CAD-08` com módulo `access` → aceita (sigla não é conferida)
- **Arquivos:** `tools/harness.py`
- **Reaproveitar:** `_id_da_ficha` · **Não criar:** mapa de siglas
- **Fora do escopo:** renomear fichas; ligar sigla e módulo
- **Decisões relacionadas:** D2, D5
- **Pronto quando:** `pytest tests/harness/test_validacao_lote.py::test_id_fora_do_padrao_recusado tests/harness/test_validacao_lote.py::test_modulo_desconhecido_recusado -q` passa

## [ ] T4 · Responsável da equipe
- **Critérios da ficha:** c6
- **Regra de negócio (em linguagem simples):** só quem está na equipe pode ser dono de ficha; um handle errado faria o `hx feature start` recusar a pessoa certa.
- **Critérios de aceite:**
  - [ ] Handles lidos de `gitpages/src/data/equipe.ts` (campo `github`)
  - [ ] `responsavel` preenchido e fora da lista → `(responsavel)`; vazio continua permitido onde já era
  - [ ] Arquivo sem nenhum handle lido → erro claro, nunca "aceita todos"
- **Exemplos:** `fulano-inexistente` → recusa; `caio-nascime` → aceita
- **Arquivos:** `tools/harness.py`
- **Reaproveitar:** `HarnessErro` · **Não criar:** cópia da equipe em `tools/`
- **Fora do escopo:** mudar `_identidade_do_dev`
- **Decisões relacionadas:** D1
- **Pronto quando:** `pytest tests/harness/test_validacao_lote.py::test_responsavel_fora_da_equipe_recusado -q` passa

## [ ] T5 · Nome de teste não se repete entre fichas
- **Critérios da ficha:** c7 (versão reduzida)
- **Regra de negócio (em linguagem simples):** se duas fichas citam o mesmo nome de teste, a evidência de uma poderia "provar" a outra. Cada nome vale para uma só ficha.
- **Critérios de aceite:**
  - [ ] Nome após `::` repetido em duas fichas → problema `(verificacao)` citando as duas
  - [ ] Repetir o nome dentro da mesma ficha (dois critérios usando o mesmo teste) não é recusado
  - [ ] Comandos sem `::` (ex.: `ruff check ...`) são ignorados; o formato do comando não é cobrado
- **Exemplos:** `HAR-91` e `HAR-92` com `test_faz_x` → recusa citando `HAR-91` e `HAR-92`
- **Arquivos:** `tools/harness.py`
- **Reaproveitar:** `validar_fichas`/a nova função de regras · **Não criar:** segundo parser de comando
- **Fora do escopo:** pasta do módulo, arquivo único, `-q`
- **Decisões relacionadas:** D2
- **Pronto quando:** `pytest tests/harness/test_validacao_lote.py::test_nome_de_teste_repetido_entre_fichas_recusado -q` passa

## [ ] T6 · CNPJ alfanumérico no check-clean
- **Critérios da ficha:** c9
- **Regra de negócio (em linguagem simples):** a Receita passou a emitir CNPJ com letras nas 12 primeiras posições; os 2 últimos são dígitos verificadores. Cada caractere vale seu código ASCII − 48 (A = 17), com os pesos do CNPJ numérico. CNPJ com DV válido sugere dado real; o relatório traz só arquivo, linha e tipo.
- **Critérios de aceite:**
  - [ ] Detecta com e sem máscara, em maiúsculas e minúsculas
  - [ ] DV errado ou todos os caracteres iguais → nenhum achado
  - [ ] CNPJ numérico segue detectado (`test_fase_b.py` verde)
  - [ ] O valor nunca aparece na saída; código 1 com achados
  - [ ] Regra do resto conferida na rotina oficial (D3); `hx check-clean` no repo segue OK
- **Exemplos:** exemplo da Receita `12.ABC.345/01DE` com DV correto → achado; com DV trocado → nada
- **Arquivos:** `tools/harness.py`
- **Reaproveitar:** `_CNPJ`, `cnpj_valido`, `_digito_verificador`, `TIPO_CNPJ`, `tipos_da_linha` · **Não criar:** tipo de achado novo
- **Fora do escopo:** CPF; validação de CNPJ no produto
- **Decisões relacionadas:** D3
- **Pronto quando:** `pytest tests/harness/test_validacao_lote.py::test_check_clean_detecta_cnpj_alfanumerico tests/harness/test_fase_b.py -q` passa

## [ ] T7 · Verificação final
- **Critérios de aceite:**
  - [ ] `git diff <hash-dos-testes> -- tests/` vazio
  - [ ] `ruff check .` limpo
  - [ ] `hx state` na raiz real com código 0 (c1(a))
  - [ ] `hx check-clean` e `hx verify` em OK
  - [ ] `hx feature verify HAR-04` grava `passing`
- **Pronto quando:** `hx check-clean`, `hx verify` e `hx feature verify HAR-04` terminam com código 0
