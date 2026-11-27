# Tasks — ADM-01 · Criar um escritório e o seu chefe por comando, para o primeiro acesso

**Plan:** planos/ADM-01/plan.md · **Ficha:** features/ADM-01.json
**Ordem:** T1 → revisão humana dos testes → commit só-de-testes (anotar o hash) → T2 em diante (sessão nova, sem editar `tests/`)

---

## [ ] T1 · Escrever os testes dos critérios
- **Critérios da ficha:** c1, c2, c3, c4
- **Regra de negócio (em linguagem simples):** o comando é a "chave da porta" da primeira vez: cria o escritório e o chefe juntos, ou não cria nada, e o chefe consegue entrar com a senha que foi dada por variável de ambiente.
- **Critérios de aceite:**
  - [ ] Existe um teste para cada nome da `verificacao`: `test_adm01_cria_escritorio_e_chefe_que_consegue_entrar`, `test_adm01_usuario_existente_recusado_sem_alterar`, `test_adm01_dado_faltando_ou_senha_no_comando_recusados`, `test_adm01_dois_escritorios_ficam_separados`
  - [ ] O comando roda como processo (`python -m lastro.access.admin ...`) com `DATABASE_URL` do banco de teste; a entrada e a identificação usam a rota `/api/v1/session` da ACE-01
  - [ ] c1 confere saída, código 0, contagens (1/1/1), papel `chefe` ativo, hash diferente da senha e verificável por `hash_password`/entrada, e que a senha não aparece em nenhuma coluna de texto, na saída nem no log
  - [ ] c3 cobre os 5 casos (a a e) em banco vazio, com `stdin` sem terminal, e confere 0/0/0 e a senha ausente da saída em (e)
  - [ ] Testes extras no mesmo arquivo: senha com 7 caracteres → código 2, "A senha do chefe deve ter pelo menos 8 caracteres." e 0/0/0; senha com 8 caracteres aceita; login só difere na caixa (`Chefe_1`) é "já existe"; falha forçada no meio da gravação deixa 0/0/0 (rollback)
  - [ ] Todos falham hoje pelo motivo certo (módulo `lastro.access.admin` não existe)
  - [ ] Só dados inventados; senhas de teste como na ficha ou geradas na hora
- **Exemplos:** `--escritorio 'ESCRITORIO TESTE 1' --usuario chefe_1 --nome 'CHEFE TESTE 1'` + variável → código 0 e "Escritório ESCRITORIO TESTE 1 criado. O chefe chefe_1 já pode entrar."; repetir com `chefe_1` → código 1 e "O usuário chefe_1 já existe. Nada foi alterado."
- **Arquivos:** `tests/access/test_office_admin.py` (reusa `head_database` e helpers de `tests/access/test_login.py`; não editar `conftest.py`)
- **Reaproveitar:** fixtures e `_client`, `_sign_in`, `_connect` · **Não criar:** outro conftest, outro banco
- **Fora do escopo:** código de produção
- **Pronto quando:** `docker compose run --rm dev pytest tests/access/test_office_admin.py -q` mostra só falhas esperadas

## [ ] T2 · Regra de criação: contrato, repositório e serviço
- **Critérios da ficha:** c1, c2, c4
- **Regra de negócio (em linguagem simples):** criar escritório, usuário e vínculo de chefe numa transação só. Se o usuário já existe (mesmo escrito de outro jeito de maiúsculas), nada é gravado, nem a senha antiga muda.
- **Critérios de aceite:**
  - [ ] `service.create_firm_with_manager` grava `escritorio`, `usuario` (login em minúsculas, hash Argon2) e `membro` (papel `chefe`, ativo) com um só `commit`
  - [ ] Login existente (qualquer caixa, ativo ou não) → `UsernameTakenError`, sem linha nova e sem alterar o hash
  - [ ] `IntegrityError` do login → rollback e o mesmo `UsernameTakenError`; qualquer outra falha → rollback e a exceção sobe
  - [ ] Não cria contador, cliente, convite nem sessão (c4)
  - [ ] SQL só em `repository.py`; senha nunca em log nem em `repr`
- **Exemplos:** `chefe_1` novo → `CreatedFirm(firm_name='ESCRITORIO TESTE 1', username='chefe_1')`; `CHEFE_1` depois → `UsernameTakenError`; falha ao inserir o `membro` → 0 escritórios
- **Arquivos:** `src/lastro/access/contracts.py`, `repository.py`, `service.py`
- **Reaproveitar:** `models.Firm/User/Member`, `find_users_by_login`, `hash_password` · **Não criar:** segunda função de hash, migração, RLS
- **Fora do escopo:** argumentos e mensagens da linha de comando; rota HTTP
- **Decisões relacionadas:** D2, D3 (plan.md)
- **Pronto quando:** `pytest tests/access/test_office_admin.py::test_adm01_usuario_existente_recusado_sem_alterar -q` passa

## [ ] T3 · Comando `criar-escritorio`
- **Critérios da ficha:** c1, c2, c3, c4
- **Regra de negócio (em linguagem simples):** a pessoa que instala o sistema roda um comando; ele valida o que foi digitado, lê a senha só da variável de ambiente e fala em português simples o que aconteceu e o que fazer.
- **Critérios de aceite:**
  - [ ] `python -m lastro.access.admin criar-escritorio --escritorio --usuario --nome` funciona; ordem das recusas como na D4
  - [ ] Códigos: 0 sucesso, 1 "já existe" (e banco inacessível, pergunta 6), 2 uso errado; sucesso na saída padrão, recusas na de erro
  - [ ] Mensagens exatas da ficha (a, b, c, d, e e "já existe"); `--nome` vazio: "Informe o nome do chefe."; senha com menos de 8 caracteres: "A senha do chefe deve ter pelo menos 8 caracteres." (código 2; vale também para a senha digitada no terminal)
  - [ ] `--senha` recusado e fora do `--help`; a senha não aparece na saída em nenhum caso
  - [ ] Sem a variável: com terminal, pede a senha sem eco duas vezes (pergunta 1); sem terminal, recusa (c)
  - [ ] Erros do `argparse` saem em português; sem `print`; sem traceback com a URL do banco
- **Exemplos:** `--escritorio ''` → código 2, "Informe o nome do escritório."; variável vazia → código 2, "Defina a senha do chefe na variável LASTRO_SENHA_CHEFE."; `--senha x` → código 2, "Não escreva a senha no comando. Use a variável LASTRO_SENHA_CHEFE."
- **Arquivos:** `src/lastro/access/admin.py`
- **Reaproveitar:** `core.config.get_settings`, `core.db.Database`, `access.service` · **Não criar:** dependência de CLI, rota, script em `tools/`
- **Fora do escopo:** criar contador, cliente ou convite; trocar senha; listar escritórios
- **Decisões relacionadas:** D1, D4, D5; perguntas 1, 3, 6
- **Pronto quando:** `pytest tests/access/test_office_admin.py -q` passa (os 4 da ficha e os extras)

## [ ] T4 · Documentar o primeiro acesso
- **Critérios da ficha:** c1 (uso), c3
- **Regra de negócio (em linguagem simples):** quem instala precisa saber o comando, a variável e o que fazer se o usuário já existe.
- **Critérios de aceite:**
  - [ ] `docs/modulos/access.md` ganha a seção "Primeiro acesso (ADM-01)": comando com **placeholders** (`<nome do escritório>`, senha só pela variável), códigos de saída, mensagens, nome do escritório repetido permitido (pergunta 4) e o aviso da NUC-03 (pergunta 5)
  - [ ] Nenhum nome, senha ou segredo reais; `hx check-clean` limpo
- **Arquivos:** `docs/modulos/access.md`
- **Reaproveitar:** estrutura do doc atual · **Não criar:** doc novo
- **Fora do escopo:** `README.md`, site `gitpages/`
- **Pronto quando:** `hx check-clean` retorna 0

## [ ] T5 · Verificação final
- **Critérios de aceite:**
  - [ ] `git diff <hash-dos-testes> -- tests/` vazio
  - [ ] `ruff check .` limpo
  - [ ] `hx check-clean` e `hx verify` em OK
  - [ ] `hx feature verify ADM-01` grava `passing`
- **Pronto quando:** os três comandos do `hx` terminam com código 0
