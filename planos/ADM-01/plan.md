# Plan — ADM-01 · Criar um escritório e o seu chefe por comando, para o primeiro acesso

**Status:** aprovado
**Branch:** feat/ADM-01-criar-um-escritorio-e-o-seu-chefe-por-co · **Data:** 24/11/2026 · **Responsável:** jvsauma
**Tasks:** planos/ADM-01/tasks.md

## 1. A decidir (humano)
Nenhuma pergunta aberta. As 6 perguntas foram respondidas em 24/11 (ver seção 5).

Mudanças sugeridas na ficha (o humano aplica em PR): acrescentar a c3 os casos "nome do chefe vazio", "senha com menos de 8 caracteres" e "senha digitada no terminal"; nada mais.

## 2. Decisões tomadas pelo agente
Cada uma precisa de confirmação humana.
### D1 · Interface de linha de comando com `argparse` (biblioteca padrão)
- **Alternativas:** A) `argparse` · B) `typer`/`click` (dependência nova) · C) script em `tools/`
- **Escolhida:** A — **motivo:** um só subcomando; sem dependência nova (regra 12); o caminho `python -m lastro.access.admin` já está na ficha, então C não serve. Os erros do `argparse` saem em inglês, então o código captura o erro e escreve as mensagens em português com código 2.
- **Impacto:** T2, T3. [x] confirmado (jvsauma, 24/11)

### D2 · Regra no `service.py`, comando fino em `admin.py`
- **Escolhida:** `access/service.py` ganha `create_firm_with_manager(db, firm_name, username, name, password)`; `access/repository.py` ganha as três inserções e a busca do login; `access/contracts.py` ganha `CreatedFirm` e `UsernameTakenError`. `admin.py` só lê argumentos, chama o serviço e escreve a saída. Motivo: ARCHITECTURE §3 (regra no serviço, SQL só no repositório) e a ACE-02 vai criar usuário e vínculo também; a regra não pode ficar presa a uma CLI.
- **Contrato novo em versão 0** (regra 11): avisar caio-nascime (ACE-02) no PR.
- **Impacto:** T2. [x] confirmado (jvsauma, 24/11)

### D3 · Uma transação; o login é a chave de "já existe"
- **Escolhida:** `escritorio`, `usuario` e `membro` entram numa transação só, com um único `commit`. Antes de inserir, busca o login pela mesma regra da ACE-01 (minúsculas, sem espaços nas pontas, `repository.find_users_by_login`). Se aparecer `IntegrityError` (corrida entre dois comandos), faz rollback e dá a mesma resposta de "já existe". O login é gravado já em minúsculas (aviso do `docs/modulos/access.md`).
- **Efeito:** `Chefe_1` e `chefe_1` contam como o mesmo usuário; usuário inativo também conta como existente.
- **Impacto:** T2; testes de borda em T1. [x] confirmado (jvsauma, 24/11)

### D4 · Ordem das recusas e senha só por variável
- **Escolhida:** primeiro `--senha` (e), depois escritório (a), usuário (b), nome (pergunta 3), senha (c, d) e tamanho mínimo de 8 caracteres (pergunta 2). Cada recusa para na primeira e não toca no banco. A senha vem de `LASTRO_SENHA_CHEFE` e é passada ao `hash_password` do serviço da ACE-01; nunca vai a `logging`, saída, erro ou `repr`. `--senha` existe no parser só para ser recusado (e) e some do `--help`, para a senha digitada não ser eco no erro do `argparse`.
- **Impacto:** T3. [x] confirmado (jvsauma, 24/11)

### D5 · Saída com `sys.stdout`/`sys.stderr`, sem `print` nem log da senha
- **Escolhida:** CODING_STANDARDS §3 proíbe `print` fora de `tools/`. Sucesso na saída padrão; recusas na saída de erro. Código 0 sucesso, 1 "já existe" ou banco, 2 uso errado. Textos exatamente como na ficha.
- **Impacto:** T2, T3. [x] confirmado (jvsauma, 24/11)

## 3. Resumo e abordagem
Um comando cria, na mesma transação, o escritório, o chefe e o vínculo `chefe` ativo, para o primeiro acesso antes de existir a ACE-02. O chefe entra pela rota da ACE-01 sem que nada de login seja reescrito.
1. T1: testes da ficha em `tests/access/test_office_admin.py` (mais as bordas das decisões).
2. T2: contrato, repositório e serviço (regra e transação).
3. T3: `admin.py` (argumentos, mensagens, códigos).
4. T4: documentação do módulo e do primeiro acesso.
5. T5: verificação final.

## 4. Contexto encontrado
- **Planos lidos:** `planos/ACE-01/plan.md` (Status "pronto para revisão", não marcado como aprovado; as decisões valem aqui como **intenção**, e cada uma foi conferida com o código) e `planos/DB-01/plan.md` (só para o recorte físico). `progress/ACE-01.md` e `progress/DB-01.md` lidos. Fora de `depende_de`: nenhum.
- **Conferência com o código:** `hash_password` em `access/service.py` e `passwords.py` (Argon2) — **confere**; `find_users_by_login` com `lower()` e `strip()` em `sign_in` — **confere**; um vínculo ativo por usuário (`MultipleFirmsError`) — **confere**; rota `POST/GET /api/v1/session` — **confere** (ver `docs/modulos/access.md`); `tests/access/conftest.py` fixa a revisão `0002` — **confere** (usar `head_database` de `test_login.py`). Nenhuma divergência.
- **Dependências:** DB-01 `passing` (tabelas `escritorio`, `usuario`, `membro`, modelos `Firm`, `User`, `Member`); ACE-01 `passing` (entrada, identificação, `hash_password`).
- **Reaproveitar:** `access/models.py` (`Firm`, `User`, `Member`); `repository.find_users_by_login`; `service.hash_password`; `core/config.get_settings`; `core/db.Database`; no teste, `head_database`, `_client`, `_sign_in`, `_connect` de `tests/access/test_login.py`.
- **Não criar:** migração (as tabelas existem), outra função de hash, rota HTTP, tela, convite, contador, cliente, política RLS, `utils.py`, dependência nova.
- **Pontos de atenção:** nenhum `__main__` ou CLI existe hoje em `src/`; `docs/modulos/access.md` não fala de primeiro acesso.
- **Pesquisa externa:** sem pesquisa externa necessária (biblioteca padrão e Argon2 já decidido na ACE-01).

## 5. Decisões (já resolvidas)
- 18/11 · P-02/RF-AUT-03: o chefe existe antes do primeiro contador; este comando só cria o primeiro chefe.
- 24/11 · ACE-01 D10: um vínculo ativo por usuário; vale para o comando (um chefe novo por escritório novo).
- 24/11 · Pergunta 2: senha com **mínimo de 8 caracteres**; menor que isso é recusada com código 2 e "A senha do chefe deve ter pelo menos 8 caracteres." (resposta de jvsauma). A política vale só para este comando; a ACE-02 decide a sua.
- 24/11 · Pergunta 1: com terminal e sem a variável, pede a senha sem eco, duas vezes; sem terminal, recusa como em c3-c (padrão aceito por jvsauma).
- 24/11 · Pergunta 3: `--nome` vazio → "Informe o nome do chefe.", código 2 (padrão aceito).
- 24/11 · Pergunta 4: nome de escritório repetido é permitido (padrão aceito).
- 24/11 · Pergunta 5: avisar guin409 no PR sobre o RLS da NUC-03 (padrão aceito).
- 24/11 · Pergunta 6: banco inacessível → "Não foi possível acessar o banco de dados. Confira a conexão e tente de novo.", código 1 (padrão aceito).

## 6. Avaliação da ficha
| # | Achado | Gravidade | Critério |
|---|---|---|---|
| 1 | Exemplos claros, com dado inventado e mensagens exatas. Cada critério vira um teste direto. | — | c1–c4 |
| 2 | "Sem terminal interativo" implica um caminho com terminal que a ficha não descreve; senha mínima e nome vazio também faltam (perguntas 1 a 3, respondidas). | ATENÇÃO | c3 |
| 3 | "A senha não aparece em nenhuma coluna em texto": o teste confere varrendo todas as colunas das três tabelas (e `sessao`) por texto, não só `credencial_hash`. | — | c1 |
| 4 | Cobertura de "nada é gravado" em falha no meio da transação não está na ficha; entra como teste extra em T1 (rollback). | ATENÇÃO | c1, c2 |
| 5 | 4 critérios, um módulo, uma ou duas sessões: tamanho adequado. | — | todos |

## 7. Riscos
- Senha na linha de comando vazaria em `ps` e no histórico do shell → só por variável; teste (e) prova que não aparece na saída.
- Dois comandos ao mesmo tempo com o mesmo login → unicidade do banco e D3 (rollback, mesma resposta).
- RLS da NUC-03 pode barrar a gravação (pergunta 5) → aviso no PR.
- `SignedInMember` e `service.py` mudam pouco; novo contrato em versão 0 (D2) → issue `contrato:` se mudar depois.
- Exemplo de uso em doc com senha → só placeholder, nunca senha real; `hx check-clean` antes do PR.

## 8. Aprovação
- [x] Perguntas ATENÇÃO respondidas ou padrão aceito
- [x] Decisões do agente confirmadas
- [x] Plan e tasks revisados por ________ em __/__
