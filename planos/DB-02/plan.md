# Plan — DB-02 · Tabelas de cadastro e plano de contas

**Status:** pronto para revisão; testes aguardam aprovação humana
**Branch:** `feat/DB-02-criar-as-tabelas-de-cadastro-e-plano-de` · **Data:** 23/11/2026 · **Responsável:** RaissaOliveira19
**Tasks:** `planos/DB-02/tasks.md`

## 1. A decidir (humano)

| # | Pergunta | Gravidade | Proposta | Decide |
|---|---|---|---|---|
| 1 | HAR-03 ainda não gerou fixtures. Os testes de esquema podem criar registros sintéticos transitórios? A exceção DB-01/B3 não se estende automaticamente. | BLOQUEANTE | Reutilizar o banco descartável e os auxiliares de `tests/access/conftest.py`; gerar UUIDs e nomes claramente fictícios dentro dos testes, sem arquivo de fixture ou CNPJ válido. Registrar a extensão pontual em `docs/decisoes/DECISIONS.md` antes dos testes. | Raissa |
| 2 | A ficha fixa tabelas, colunas e nomes de testes em português, embora `CODING_STANDARDS.md` prefira inglês. | BLOQUEANTE | Manter os nomes físicos e os quatro testes exatamente como a ficha; classes e auxiliares Python em inglês, como na DB-01. Renomeação futura exigirá ficha própria. | Raissa |
| 3 | O recorte DB-02 deixa as políticas de RLS para NUC-03, enquanto o padrão geral pede RLS na mesma migração. | ATENÇÃO | Seguir c4 da ficha e a divisão já registrada em `docs/SECURITY.md` §8; não usar dados de piloto antes de NUC-03. | Raissa |

Mudanças sugeridas na ficha: nenhuma. Os quatro comandos de verificação permanecem os da ficha.

## 2. Decisões técnicas propostas

### D1 · Uma migração `0003_create_registry_tables.py`, sem editar a `0002`
- **Alternativas:** migração única; migração por tabela.
- **Escolhida:** única, como exige c1; `down_revision = "0002"`. O downgrade remove primeiro FKs/colunas de `cliente` e depois as quatro tabelas.
- **Impacto:** c1–c4, T2–T4.
- [ ] Confirmada pela responsável.

### D2 · FKs compostas com uma chave auxiliar para a conta dentro do plano
- A PK de `conta_contabil` é `(escritorio_id, cliente_id, id)`; a FK do pai e as FKs das contas de configuração precisam também de `plano_id`. Será criada `UNIQUE (escritorio_id, cliente_id, plano_id, id)` para servir de alvo, sem mudar a PK.
- Todas as FKs seguem DB-01: `ON DELETE/UPDATE NO ACTION`, `NOT DEFERRABLE`. Sem cascata ou trigger.
- **Impacto:** c2, c3, T2–T4.
- [ ] Confirmada pela responsável.

### D3 · Modelos ORM espelham a migração
- Estender `registry/models.py` com `Client` e quatro classes; somente a migração altera o banco. `core/models.py` fornece a base e a convenção de nomes.
- **Impacto:** c1–c3, T3.
- [ ] Confirmada pela responsável.

## 3. Abordagem

T1 escreve os quatro testes da ficha antes do código. Os testes inspecionam o catálogo do PostgreSQL 18, tentam inserções válidas e inválidas em transações independentes, verificam as referências de plano e contas e executam downgrade/upgrade sobre banco descartável. Após a revisão humana e o commit só de testes, T2 cria a migração e T3 atualiza os modelos. T4 registra as regras do módulo e confere a reversão. T5 roda as verificações finais, grava o estado com `hx feature verify`, atualiza o progresso e abre PR para `developer`.

## 4. Contexto

- DB-01 está `passing` na `developer`; `0002_create_identity_tables.py` criou `cliente(escritorio_id,id)` e `membro(escritorio_id,id)`.
- `registry/models.py` já define `Client`; `core/models.py` contém a convenção de nomes. Não criar módulo ou tabela fora da ficha.
- Fonte da modelagem: `gitpages/src/content/docs/modelagem/entidades.md` e `modelo-logico.md`; P-11 define a troca de plano e da transitória.
- `tests/access/conftest.py` reaproveita o PostgreSQL descartável da NUC-01. Não usar SQLite, `create_all`, dados reais ou fixture persistida.
- Não há `docs/modules/registry.md`; documentar o recorte físico e a dependência de NUC-03 ali.
- Sem biblioteca nova nem pesquisa externa necessária.

## 5. Avaliação da ficha

| # | Achado | Tratamento |
|---|---|---|
| 1 | A FK do pai exige chave alvo `(escritorio_id, cliente_id, plano_id, id)` não fornecida pela PK. | D2. |
| 2 | A ficha pede testes com dados enquanto HAR-03 não existe. | Pergunta 1 antes de T1. |
| 3 | Nomes físicos/testes em português divergem do padrão geral. | Pergunta 2; preservar contrato da ficha. |
| 4 | RLS foi separada para NUC-03 pela ficha e por `SECURITY.md`. | Pergunta 3; registrar risco. |

## 6. Riscos

- FK parcial com valor nulo não restringe outra coluna: cada conta de configuração recebe `CHECK (conta_x IS NULL OR plano_atual_id IS NOT NULL)` além da FK composta.
- A troca de plano com conta antiga deve falhar sem alteração parcial; os testes fazem uma gravação direta e conferem o estado anterior.
- Downgrade só em banco descartável; não apagar dados existentes fora dos testes.
- As novas tabelas ainda não terão RLS; NUC-03 é requisito antes de qualquer dado de piloto.

## 7. Aprovação

- [ ] Perguntas bloqueantes respondidas pela responsável.
- [ ] D1–D3 confirmadas pela responsável.
- [ ] Plan e tasks revisados por Raissa em DD/MM.
