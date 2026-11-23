# Plan — DB-01 · Identidade e carteira

**Status:** aprovado
**Branch:** feat/DB-01-criar-as-tabelas-de-identidade-e-carteir · **Data:** 23/11/2026
**Responsável:** conforme `features/DB-01.json` · **Tasks:** `planos/DB-01/tasks.md`

## 1. A decidir (humano)

Sem dúvida técnica bloqueante. Plano e tasks aprovados explicitamente por `guin409` em 23/11/2026, com as decisões registradas. A aprovação foi concedida pelo responsável humano; esta sessão permanece restrita ao registro e commit documental.

| # | Revisão concluída | Resultado | Autoriza |
|---|---|---|---|
| R1 | Complementos de c1/c2/c5/c6 aplicados em 23/11/2026. | Seis comandos de teste, c3/c4, estado e evidência preservados. | Responsável DB-01 |
| R2 | Verificador atualizado para 28 entidades e presença explícita de CONVITE. | Demais checagens preservadas; verificações estruturais e de interações passaram em 23/11/2026. | Responsável DB-01 |

**Complementos autorizados e aplicados à ficha em 23/11/2026:**
- **c1:** explicitar NOT NULL de F1, somente defaults temporais já definidos, UUID v4 no banco, seis índices auxiliares F5 e convenção D2; referenciar recorte físico confirmado em 23/11. Preservar sete tabelas/colunas e recorte da DB-02.
- **c2:** enumerar FKs diretas de membro/cliente para escritório; todas as FKs com ON DELETE/UPDATE NO ACTION e NOT DEFERRABLE; acrescentar caso de autor de convite de outro escritório e escritório inexistente.
- **c5:** explicitar revogação de convite expirado ainda pendente antes da reemissão; 48 h é apenas exemplo.
- **c6:** ampliar o exemplo de DML do papel app às sete tabelas, mantendo DROP negado e reversão; reiterar NUC-03 obrigatória antes de dados de piloto.
- **verificacao:** preservar seis nomes obrigatórios. Testes adicionais autorizados; propor inclusão de nomes adicionais ao defini-los, se precisarem de evidência própria (PROC-04).

## 2. Decisões tomadas pelo agente e confirmadas pelo responsável

### D1 · UUID v4 gerado pelo banco

- **Alternativas:** `gen_random_uuid()` (aleatório e simples); `uuidv7()` (ordena por tempo, expõe instante aproximado).
- **Confirmada:** UUID v4 com `gen_random_uuid()` como default de todo `id`; sem extensão adicional. UUID não substitui token nem autorização.
- **Licença/manutenção/compatibilidade:** funções nativas do PostgreSQL 18, PostgreSQL License; independentes de Python, inclusive 3.12. Projeto permanece em 3.14.
- **Fontes:** [UUID](https://www.postgresql.org/docs/18/functions-uuid.html), [licença](https://www.postgresql.org/about/licence/) (acesso em 23/11/2026).
- **Impacto:** c1, T1–T3.
- [x] Confirmada pelo responsável em 23/11/2026.

### D2 · Base declarativa comum e convenção central

- **Alternativas:** uma Base/MetaData (resolve referências por strings entre módulos); bases independentes (exigem coordenar referências e convenções duplicadas).
- **Confirmada:** `Base` em `src/lastro/core/models.py`; seis modelos em `access/models.py`, cliente em `registry/models.py`. Cada módulo importa só a base, sem importar modelos internos vizinhos.
- **Classes:** `Firm`, `User`, `Member`, `Session`, `Invitation`, `Client`, `Assignment`; tabelas e colunas mantêm os nomes físicos portugueses da ficha, conforme B1.
- **Convenção:** `pk_<table>`, `fk_<table>_<columns>_<target>`, `uq_<table>_<columns>`, `ck_<table>_<rule>`, `ix_<table>_<columns>`; até 63 caracteres, regras CHECK nomeadas explicitamente. Colunas compostas integram o nome, evitando colisões.
- **Motivo:** FKs compostas resolvidas em uma coleção de tabelas e nomes reproduzíveis.
- **Licença/manutenção/compatibilidade:** SQLAlchemy existente, MIT, documentação mantida; sem requisito adicional de Python 3.12. Prova real em 3.14, sem atualizar bibliotecas.
- **Fontes:** [SQLAlchemy](https://docs.sqlalchemy.org/en/20/core/constraints.html), [Alembic](https://alembic.sqlalchemy.org/en/latest/naming.html), [licença/manutenção](https://www.sqlalchemy.org/download.html) (acesso em 23/11/2026).
- **Impacto:** c1/c2, T1/T2; caminhos autorizados em A1.
- [x] Confirmada pelo responsável em 23/11/2026.

### D3 · Migração explícita independente dos modelos vivos

- **Alternativas:** operações Alembic manuais (controle direto de CHECKs/índices); autogenerate revisado (menos digitação, exige conectar metadata e revisar omissões).
- **Confirmada:** uma revisão filha de `0001`, preservando `target_metadata = None`; sem `create_all()` nem imports de modelos vivos na revisão histórica.
- **Motivo:** segue o env atual, permite revisão exata e downgrade estável. Índices parciais e FKs compostas já são exigências da ficha.
- **Licença/manutenção/compatibilidade:** Alembic existente, MIT, sem biblioteca ou restrição Python 3.12 nova; execução em 3.14 a provar.
- **Fontes:** `migrations/env.py`; [Alembic](https://alembic.sqlalchemy.org/en/latest/naming.html), [constraints](https://www.postgresql.org/docs/18/ddl-constraints.html), [índices parciais](https://www.postgresql.org/docs/18/indexes-partial.html) (acesso em 23/11/2026).
- **Impacto:** c1–c6, T3/T4.
- [x] Confirmada pelo responsável em 23/11/2026.

## 3. Resumo e abordagem

Criar esquema de identidade e carteira com integridade no banco, sem implementar login ou autorização HTTP.
B1–B4, F1–F5, D1–D3 e A1–A5 resolvidos; R1/R2 concluídos. Plano e tasks aprovados por `guin409` em 23/11/2026; a etapa T1 será iniciada em sessão posterior.
T1 prepara provas; revisão humana e commit só de testes congelam os arquivos e seu hash.
Em nova sessão, T2 define modelos; T3/T4 completam uma única migração e sua reversão; T5 verifica o conjunto.
Nenhuma task de testes ou implementação está autorizada nesta revisão documental.

## 4. Contexto encontrado

- **Ficha:** DB-01 `in_progress`; branch corresponde ao progresso. Somente c1/c2/c5/c6 complementados com autorização; seis comandos, c3/c4, estado e evidência preservados.
- **Dependência:** NUC-01 `passing`, evidência de 23/11/2026 lida da ficha, não reexecutada aqui.
- **Código reutilizável:** `core/db.py`: `Database`, `get_session`; `core/config.py`: `get_settings`. Definição de modelo não abre conexão.
- **Base:** `migrations/versions/0001_base_privileges.py`, revisão `0001`; grants padrão owner/app. Não repetir grants nem editar migração aplicada.
- **Infra de testes:** `tests/core/conftest.py`: `PostgresServer`, `FreshDatabase`, `connect`, `postgres_server`, `fresh_database`, `migrated_database`, `run_alembic_upgrade`.
- **Reuso planejado:** carregar o conftest existente por caminho e nome exclusivo em `tests/access/conftest.py`, reexportando fixtures/auxiliares; sem editar testes NUC-01 nem importar `conftest` global ambíguo. Provar coleta isolada e conjunta em T1.
- **Ausências:** modelos DB-01, testes DB-01 e `docs/modules/` não existem; gerador `hx fixtures build` indisponível no harness lido.
- **Modelagem:** CONVITE incluído em entidades, modelo lógico/físico, índice JSON, vínculos RF-AUT-01/03 e diagrama de identidade; demais entidades e vínculos preservados. Modelo contém 28 entidades.
- **Escopo:** RF-AUT-01/03, BD-02, D-09 e P-09 consultados; chefe pode ser responsável, usuário pode ter vínculos em dois escritórios; contas/plano do cliente só na DB-02.
- **Ambiente:** Python 3.14, PostgreSQL 18, SQLAlchemy, Alembic, psycopg e Testcontainers existentes; sem biblioteca nova, sem SQLite.
- **Harness:** `cmd_verify` e `cmd_feature_verify` em `tools/harness.py`; feature verify exige árvore limpa e grava estado/evidência. Não executado nesta revisão.
- **Pesquisa:** comparações técnicas e fontes primárias em D1–D3, consultadas no planejamento inicial.

## 5. Decisões resolvidas — responsável, 23/11/2026

- **B1:** nomes físicos da ficha; exceção ao inglês/plural registrada em CODING_STANDARDS.md.
- **B2:** políticas RLS na NUC-03, concluída antes de dados de piloto; sem política permissiva de contorno.
- **B3:** dados sintéticos determinísticos enquanto o gerador estiver indisponível; nomes fictícios, hashes inventados e CNPJ com DV inválido nos testes sem validação fiscal.
- **B4/F1–F5:** modelagem completada; NOT NULL enumerados, sem defaults temporais adicionais, FKs diretas membro/cliente, NO ACTION/NOT DEFERRABLE sem cascata e seis índices auxiliares, sem unicidade global extra de id.
- **D1–D3:** UUID v4 no banco, Base comum/convenção e migração explícita confirmados.
- **A1/A2:** caminhos propostos autorizados, ficha única e sessões separadas de testes/implementação.
- **A3/A4:** revogar convite expirado ainda pendente antes de reemitir; 48 h só exemplo; seis testes obrigatórios e cobertura adicional autorizada.
- **A5:** sincronizar CONVITE nos dados/diagramas interativos preservando o restante; alteração documental realizada.
- **Anteriores:** stack, BD, D-09 e P-09 aprovadas no registro de decisões; não estão em votação nesta revisão.

## 6. Avaliação da ficha

| Referência | Situação | Classificação |
|---|---|---|
| B1–B4/F1–F5/D1–D3/A1–A5 | Resolvidos pelo responsável; detalhes registrados no modelo físico e em DECISIONS.md. | RESOLVIDO |
| R1 | Complementos autorizados aplicados a c1/c2/c5/c6, preservando demais campos. | CONCLUÍDO |
| R2 | Verificador exige 28 entidades e CONVITE; checagens documentais passaram. | CONCLUÍDO |

## 7. Riscos

- FK/CHECK contornados por NULL → testar NOT NULL de F1 e vínculos cruzados por SQL direto, sem resíduos.
- ORM divergir do DDL → catálogo e metadata conferem colunas, defaults, constraints e índices.
- Downgrade apagar a base → remover só objetos DB-01 em ordem inversa, sem CASCADE; retornar a `0001`.
- Dados em provas → geração sintética autorizada em B3; sem token claro, URLs ou segredos em relatórios.
- Unicidade não substitui serviço de reatribuição, preservação do histórico por autorização ou RLS; NUC-03 continua obrigatória antes do piloto.

## 8. Aprovação

- [x] B1–B4/F1–F5 e D1–D3/A1–A5 confirmados pelo responsável.
- [x] R1 e R2 autorizados pelo responsável e concluídos; verificações documentais passaram.
- [x] Plano e tasks aprovados explicitamente por `guin409` em 23/11/2026, com as decisões registradas.

Verificação em 23/11/2026: `node scripts/verificar-modelagem.mjs` passou (28 entidades, 56 Must, 64 vínculos, 227 links); `node scripts/verificar-interacoes-modelagem.mjs` passou. A falha anterior de contagem foi resolvida em R2. Nenhum teste DB-01 ou código de produto escrito. Aprovação humana registrada acima.
