# Tasks — DB-02 · Tabelas de cadastro e plano de contas

**Plan:** `planos/DB-02/plan.md` · **Ficha:** `features/DB-02.json`
**Ordem:** aprovação humana do plano → T1 testes → revisão humana dos testes → commit só de testes (anotar hash) → T2–T5 sem editar `tests/`.

## [ ] T1 · Testes de esquema e integridade
- **Critérios:** c1–c4.
- Criar `tests/registry/test_registry_schema.py` com os quatro nomes exatos da ficha.
- Reutilizar o PostgreSQL descartável; gerar apenas registros sintéticos transitórios aprovados no plano.
- c1: catálogo confirma colunas, tipos, nulos, defaults, PK, FKs, UNIQUE e CHECK das quatro tabelas e das novas colunas de `cliente`.
- c2: inserções de conta em plano de outro cliente, pai de outro plano, conta bancária de outro cliente e código repetido falham; código igual em outra versão passa.
- c3: plano ou conta de outro cliente, troca com transitória antiga e conta sem plano falham; troca com limpeza da transitória passa.
- c4: zeros e pontos em `codigo` e `banco` sobrevivem; downgrade preserva dados DB-01 e remove só DB-02; upgrade restaura o esquema.
- **Pronto quando:** os quatro testes falham pelo comportamento ausente, sem `skip` ou `xfail`.

## [ ] T2 · Migração Alembic
- **Critérios:** c1–c4.
- Criar `migrations/versions/0003_create_registry_tables.py`, `down_revision = "0002"`.
- Criar tabelas na ordem de dependência: `plano_contas`, `conta_contabil`, `conta_bancaria`, `socio`; adicionar quatro colunas e FKs de `cliente` depois.
- PKs e FKs compostas preservam escritório, cliente e plano; `UNIQUE` de código inclui o plano; `CHECK` de intervalo, versão e situação.
- Downgrade remove FKs/colunas de `cliente` antes das tabelas, sem tocar na DB-01.
- **Pronto quando:** quatro testes da ficha passam no PostgreSQL 18.

## [ ] T3 · Modelos ORM
- **Critérios:** c1–c3.
- Estender `src/lastro/registry/models.py` com as quatro classes e as colunas/configurações de `Client`, refletindo exatamente a migração.
- Reusar `Base` e a convenção de nomes; não usar `create_all` nem alterar modelos da DB-01.
- **Pronto quando:** metadados dos modelos e catálogo conferem, e os testes da ficha seguem verdes.

## [ ] T4 · Documentação do módulo
- Documentar `docs/modules/registry.md`: chaves, plano atual, configuração, downgrade, ausência temporária de RLS e dependência da NUC-03.
- Atualizar `progress/DB-02.md` com decisões e evidências reais.
- **Pronto quando:** documentação explica o esquema entregue sem prometer fluxo de API ou importação de planilha.

## [ ] T5 · Verificação, commit e PR
- Confirmar `git diff <hash-dos-testes> HEAD -- tests/` vazio.
- Rodar `hx verify`, `hx check-clean` e `hx feature verify DB-02`; registrar resultados sem dados reais.
- Commitar a evidência gerada pelo harness; abrir PR para `developer` com o template e a tabela critério → teste.
- **Pronto quando:** ficha `passing`, árvore limpa, PR aberto e CI verde.
