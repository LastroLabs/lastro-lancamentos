# Tasks — DB-01 · Identidade e carteira

**Plan:** `planos/DB-01/plan.md` · **Ficha:** `features/DB-01.json`
**Pré-condição:** B1–B4, F1–F5, D1–D3 e A1–A5 confirmados; R1/R2 concluídos. Plano e tasks aprovados explicitamente por `guin409` em 23/11/2026. Nenhuma task foi executada; T1 fica para sessão posterior, pois esta sessão só registra a aprovação e faz o commit documental.
**Ordem:** T1 → revisão humana dos testes → commit só de testes com hash registrado → T2 em diante em sessão nova, sem editar `tests/`.
**Nomes físicos:** tabelas/colunas portuguesas da ficha, conforme B1; classes e convenção conforme D2 confirmado.
**Comandos:** executar da raiz; testes no serviço `dev` com Docker disponível. Se alguma prova parecer errada na implementação, parar e avisar.

## [ ] T1 · Escrever os testes dos critérios

- **Critérios da ficha:** c1–c6.
- **Regra de negócio:** o próprio banco impede vínculos entre escritórios, duplicidade e intervalos inválidos; só existe um responsável aberto por cliente e um convite pendente por membro.
- **Critérios de aceite:**
  - [ ] Existem os seis pontos de entrada obrigatórios da ficha; testes adicionais e parametrização são permitidos:
    - `test_migracao_db01_cria_tabelas_de_identidade_com_colunas_e_chaves`
    - `test_db01_fk_de_outro_escritorio_recusada`
    - `test_db01_um_responsavel_ativo_por_cliente`
    - `test_db01_unicidades_de_cadastro`
    - `test_db01_convite_guarda_so_o_hash_e_um_pendente_por_membro`
    - `test_db01_migracao_reverte_e_usuario_da_aplicacao_nao_e_dono`
  - [ ] PostgreSQL 18 descartável, sem skips e sem SQLite; Alembic roda como owner e a aplicação conecta como app; nenhum dado real ou serviço externo.
  - [ ] c1 inspeciona catálogo: sete tabelas, colunas exatas, tipos, nulabilidade, defaults no servidor, PKs, FKs, CHECKs, índices parciais e unicidades aprovados; UUID gerado sem informar id e ausência de dados após migração. Confere localização e paridade dos modelos, sem conexão no import.
  - [ ] c2 cobre os cinco casos da ficha e convite.criado_por de outro escritório; também FKs diretas de escritório aprovadas em B4. Falha por ForeignKeyViolation, sem linha residual; transações/savepoints não contaminam os casos seguintes.
  - [ ] c3 cobre segunda atribuição aberta recusada, troca atômica preservando histórico, intervalo inválido e chefe responsável permitido; índice usa escritório e cliente.
  - [ ] c4 cobre CNPJ duplicado no mesmo escritório e permitido no outro, login global único, vínculo duplicado recusado e outro escritório permitido, papel inválido recusado.
  - [ ] c5 cobre hash inválido/duplicado, segundo pendente, revogar e reemitir, expiração igual/anterior à criação e uso+revogação simultâneos; catálogo não contém token/código claro. Convite expirado ainda pendente deve ser revogado antes da reemissão, conforme A3; 48 h permanece apenas exemplo.
  - [ ] c6 reverte só DB-01, verifica ausência das sete tabelas, versão `0001` e preservação da base; reaplica e compara catálogo; app faz DML nas sete e não pode apagar tabela, não é dono/superusuário/BYPASSRLS.
  - [ ] Coleta isolada e conjunta com `tests/core/` funciona sem colisão de conftest; os seis testes obrigatórios e os adicionais de comportamento ausente falham antes do código pelo comportamento ausente, sem erro de infraestrutura disfarçado de falha esperada.
- **Exemplos inventados:** ESCRITORIO_TESTE_A/B, CHEFE_TESTE_A, CONTADOR_TESTE_B, CLIENTE_TESTE_001; CNPJ gerado com DV inválido conforme B3; instante fixo `2026-01-01T12:00:00Z`, expiração 48 h depois apenas como caso; hash fictício com 64 caracteres hexadecimais.
- **Arquivos:** `tests/access/test_identity_schema.py`, `tests/access/conftest.py`; nenhum teste de implementação nesta sessão de planejamento.
- **Reaproveitar:** carregar por caminho e nome exclusivo `tests/core/conftest.py` e reexportar fixtures/classes/auxiliares necessários; não alterar esse arquivo. Dados gerados conforme B3.
- **Não criar:** outro ambiente Docker, outro bootstrap de papéis, banco fixo, helper com nome global `conftest` ambíguo, fixture manual contrariando SECURITY.md.
- **Fora do escopo:** código de produção, mudanças na ficha e testes de API/login/RLS. Testes adicionais rodam no arquivo completo e no hx verify; se exigirem evidência própria em verificacao, apresentar proposta ao responsável (PROC-04).
- **Pronto quando:** `docker compose run --rm dev pytest tests/access/test_identity_schema.py -q` apresenta falhas esperadas por esquema/modelos ausentes nos testes obrigatórios e adicionais pertinentes, sem exigir contagem exata de falhas; `docker compose run --rm dev pytest tests/core tests/access --collect-only -q` termina sem erro; humano revisa a prova e registra hash do commit só de testes.

## [ ] T2 · Definir os modelos e a metadata comum

- **Critérios da ficha:** c1/c2; declarações de c3–c5 espelhadas no ORM.
- **Regra de negócio:** escritório delimita os vínculos; identidade de usuário é global e cliente pertence a um escritório; papel pertence ao membro.
- **Critérios de aceite:**
  - [ ] NOT NULL nos campos F1; sem defaults temporais adicionais (F2); FKs diretas membro/cliente → escritório (F3), sem duplicação redundante.
  - [ ] Todas as FKs com NO ACTION em DELETE/UPDATE e NOT DEFERRABLE (F4); seis índices auxiliares F5 e convenção D2, sem unicidade global extra de id.
  - [ ] Base comum e convenção de nomes conforme D2/A1, com sete modelos nos caminhos exigidos e só as colunas aprovadas em B1/B4.
  - [ ] FKs compostas declaram escritório e destino juntos, com tipos UUID e campos obrigatórios não anuláveis; sem importar modelos internos de outro módulo.
  - [ ] Defaults, CHECKs, unicidades e índices coincidem com a especificação aprovada; credencial é opcional e instantes são timestamptz.
  - [ ] Importar os modelos não abre conexão; metadata resolve os sete modelos quando ambos os módulos são carregados; sem criar tabelas por ORM no teste.
- **Exemplos:** usuário TESTE pode pertencer a A e B; cliente de A não recebe membro de B; cliente novo não ganha colunas de plano contábil.
- **Arquivos:** `src/lastro/core/models.py`, `src/lastro/access/models.py`, `src/lastro/registry/models.py` (A1); nomes de classes conforme D2 confirmado.
- **Reaproveitar:** SQLAlchemy existente, `Database`/`get_session` sem alterações; **não criar:** engine/base por módulo ou relações ORM que importem modelos vizinhos.
- **Fora do escopo:** serviços, repositórios, rotas, autenticação, normalização de login/CNPJ, DB-02 e alterações em `tests/`.
- **Decisões relacionadas:** B1/B4, A1, D1/D2.
- **Pronto quando:** após T3/T4, `docker compose run --rm dev pytest tests/access/test_identity_schema.py::test_migracao_db01_cria_tabelas_de_identidade_com_colunas_e_chaves -q` passa; T2 isolada ainda não satisfaz o catálogo, pois a migração é T3.

## [ ] T3 · Criar a única migração com integridade no banco

- **Critérios da ficha:** c1–c5.
- **Regra de negócio:** gravar diretamente no banco deve respeitar as mesmas fronteiras e regras de cadastro; uma troca encerra a linha anterior e preserva o histórico.
- **Critérios de aceite:**
  - [ ] Uma revisão filha de `0001`, arquivo proposto `0002_create_identity_tables.py` (reconfirmar head ao implementar), sem seeds, extensão nova ou alterações da revisão aplicada.
  - [ ] Cria escritório e usuário antes de membro/cliente, depois sessão, convite e atribuição; FKs, nulabilidade e ações seguem B4.
  - [ ] Todo id tem UUID default no banco; cliente só tem as colunas do recorte DB-01 e versão de acesso BIGINT >= 0 default 0.
  - [ ] Unicidades por escritório, login e hashes; papel limitado a chefe/contador; índices parciais exatos para atribuição aberta e convite não usado/não revogado.
  - [ ] CHECKs de intervalo e convite, formato hexadecimal de hash de convite, sem guardar segredo em claro; grants herdados da revisão base.
  - [ ] Não criar políticas RLS na DB-01, conforme B2; exigir conclusão da NUC-03 antes de usar dados de piloto, sem políticas permissivas de contorno. O passing da DB-01 não libera esse uso.
- **Exemplos:** segunda atribuição aberta de CLIENTE_TESTE_001 falha; encerrar anterior e inserir nova na mesma transação aceita e deixa duas linhas; cancelar convite fictício permite outro; hash `abc` falha.
- **Arquivos:** `migrations/versions/0002_create_identity_tables.py`, iniciado aqui e completado em T4; número sujeito ao head real.
- **Reaproveitar:** Alembic, revisão `0001`, privilégios padrão de `lastro_owner`/`lastro_app`; **não criar:** segunda migração, `create_all()`, grants duplicados, imports de modelos vivos na revisão ou alteração de `migrations/env.py`.
- **Fora do escopo:** cálculo de prazo padrão de convite/sessão, login, validação fiscal, atribuição via API, incremento de versão em serviço e mudanças nos testes.
- **Decisões relacionadas:** B1/B2/B4, A3, D1/D3.
- **Pronto quando:** `docker compose run --rm dev pytest tests/access/test_identity_schema.py -q -k "not migracao_reverte"` passa os cinco testes obrigatórios c1–c5 e os adicionais selecionados, sem skips.

## [ ] T4 · Completar reversão e conferir permissões

- **Critérios da ficha:** c6, regressão de c1–c5.
- **Regra de negócio:** desfazer DB-01 remove só seu esquema; a aplicação pode usar dados sem ter poder de destruir a estrutura.
- **Critérios de aceite:**
  - [ ] Downgrade remove tabelas dependentes antes das referenciadas, sem CASCADE amplo e sem revogar privilégios da NUC-01.
  - [ ] Versão retorna à revisão anterior e reaplicar produz estrutura idêntica, sem dados criados pela migração.
  - [ ] Conexão como app consegue operações autorizadas nas sete tabelas e recebe InsufficientPrivilege ao tentar DROP; owner permanece separado, sem superusuário/BYPASSRLS.
- **Exemplos:** desfazer/reaplicar em banco sintético limpo retorna às sete tabelas; app insere ESCRITORIO_TESTE_A, mas não apaga sua tabela.
- **Arquivos:** o mesmo arquivo de migração de T3; nenhum teste editado.
- **Reaproveitar:** `downgrade()` e privilégios da base como referência; **não criar:** scripts de reset, novo papel ou migração extra.
- **Fora do escopo:** reversão com dados de produção, backup, políticas RLS atribuídas à NUC-03 e concessão de DDL à aplicação.
- **Decisões relacionadas:** B2/B4, D3.
- **Pronto quando:** `docker compose run --rm dev pytest tests/access/test_identity_schema.py -q` passa os seis testes obrigatórios e os adicionais, incluindo c6, sem skips.

## [ ] T5 · Verificação final pelo harness

- **Critérios da ficha:** c1–c6.
- **Regra de negócio:** a ficha só é entregue quando as provas passam no ambiente oficial; o script registra o resultado, nunca o agente à mão.
- **Critérios de aceite:**
  - [ ] `git diff <hash-dos-testes> -- tests/` vazio; substituir pelo hash real registrado em T1.
  - [ ] `hx check-clean` e `hx verify` terminam com código 0; avisos ou falhas de ambiente são relatados como tais.
  - [ ] Na execução futura, progress atualizado com fatos e próxima ação; alterações revisadas e commitadas na branch da feature, árvore limpa antes de feature verify.
  - [ ] `hx feature verify DB-01` termina com código 0 e registra evidência/estado pelo script; a execução pertence à futura implementação autorizada, não a esta revisão documental.
- **Exemplos:** prova c2 aceita FK cruzada → falha impede entrega; provas obrigatórias e adicionais verdes → harness pode registrar passing da DB-01, sem liberar dados de piloto antes da NUC-03.
- **Arquivos:** na execução futura, `progress/DB-01.md`; `features/DB-01.json` exclusivamente pelo harness. Nesta sessão, nenhum desses arquivos é alterado.
- **Reaproveitar:** `tools/hx.ps1`/`tools/harness.py`, Compose dev e testes congelados; **não criar:** atalho para marcar estado, prova paralela ou edição de tests/harness.
- **Fora do escopo:** aprovar plano pelo agente, merge/publicação, novas features, dados reais.
- **Pronto quando:** carregar `. .\tools\hx.ps1` se necessário; executar `hx check-clean`, `hx verify` e, após commit/árvore limpa, `hx feature verify DB-01`, todos com código 0. Não executados no planejamento.
