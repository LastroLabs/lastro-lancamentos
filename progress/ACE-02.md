# ACE-02 · Cadastrar contador por convite e atribuir cliente pelo chefe

- Responsável: jvsauma · Branch: `feat/ACE-02-cadastrar-contador-por-convite-e-atribui` · Início: 27/11/2026
- Ficha: `features/ACE-02.json` (estado e critérios ficam lá; não repita aqui)

<!--
Como preencher (agente, ao encerrar a sessão):
- REESCREVA as seções do topo: Objetivo, Próxima ação, Bloqueios e perguntas.
- ACRESCENTE, sem apagar o que já existe, em Feito, Rodei, Falhou e Decisões.
  Cada linha começa com a data (DD/MM) e a sessão, ex.: "- 14/11 · S2 · ...".
- Registre só o que realmente rodou. Sem dado real, nome de cliente ou segredo.
- Não escreva estado (passing etc.) aqui: ele fica na ficha, gravado pelo script.
-->

## Objetivo
O chefe cadastra contador por convite (link com código aleatório, validade de 48 h), o contador cria a própria senha pelo link, e o chefe atribui cliente sem responsável a um membro ativo, inclusive a si mesmo.


## Próxima ação
Commitar a correção da corrida de convites (em commit separado, no PR #85): `src/lastro/access/repository.py`, `src/lastro/access/service.py` e o teste novo `tests/access/test_convite_corrida.py`, hoje só na árvore de trabalho. Antes, rodar `hx verify` e `hx check-clean` e conferir o resultado. Depois pedir a revisão do PR #85 pela `docs/rubrica-revisao.md`. Decidir se o aceite também toma a trava do membro (ver Bloqueios).

## Bloqueios e perguntas
- Aceite × gerar convite: `accept_invitation` não toma a trava do membro; janela estreita em que um convite novo pode sobreviver a um aceite simultâneo (e um aceite posterior sobrescreveria a senha). Fechar com uma linha no aceite ou registrar como risco aceito? Decisão do responsável.
- O teste novo foi criado em arquivo separado; o responsável deve confirmar que aceita um teste extra fora do `verificacao` (regra 3).
- Causa da falha intermitente do build do front no `hx verify` (uma vez) segue desconhecida.


## Feito
- 26/11 · S2 · Migração `0007` (`usuarios_com_senha`), `LASTRO_CONVITE_HORAS`, `credencial_hash` deferred, contratos, repositório, serviço e 7 rotas (cadastro, lista, convite novo/cancelado, aceite, atribuição e consulta); `registry.client_exists`.
- 26/11 · S2 · Docs: `docs/modulos/access.md`, `ARCHITECTURE.md` (seção 6), `DECISIONS.md` (ACE-02/F5), ficha com rotas em inglês e 422; OpenAPI e `web/src/api/schema.d.ts` regenerados.
- 26/11 · S2 · `AccountantAlreadyActiveError` (antes com "Password" no nome) para o `check-clean` não acusar segredo.
- 26/11 · S2 · Commit único da feature, push e PR #85 aberto com o template de `.github/`.
- 27/11 · S2 · `hx feature verify ACE-02` rodado pelo responsável: ficha `passing` (commit `f1a9c33`).
- 27/11 · S3 · Revisão achou corrida em `issue_invitation`: dois "gerar convite" simultâneos para o mesmo contador davam 500 (violação do índice único de convite pendente). Correção: `repository.lock_member` (`FOR NO KEY UPDATE` no membro), chamada em `issue_invitation` (antes de todas as checagens) e em `cancel_invitation`. Sem commit ainda.
- 27/11 · S3 · Teste novo `tests/access/test_convite_corrida.py` (gerar × gerar, duas conexões reais), fora do `verificacao`; os 19 testes antigos não foram editados.
## Rodei
- 26/11 · S2 · `pytest tests/access/test_cadastro_contador.py` → 19 passaram.
- 26/11 · S2 · `hx verify` (container) → 521 passaram, 1 falhou (OpenAPI/`schema.d.ts` desatualizados); corrigido e `pytest tests/web` → 5 passaram. `hx verify` completo não foi repetido depois.
- 26/11 · S2 · `ruff check .` (container) → limpo; `hx check-clean` → 0 achados, depois de o responsável trocar o CNPJ do teste do c8.
- 26/11 · S2 · `docker compose run --rm dev pytest -q` (suíte inteira, sem mais nada em paralelo) → 522 passaram, 0 falharam.
- 27/11 · S3 · `pytest tests/access/test_convite_corrida.py` antes da correção → 1 falhou (`UniqueViolation` em `uq_convite_escritorio_id_membro_id_pendente`).
- 27/11 · S3 · Depois da correção: `pytest tests/access/test_convite_corrida.py tests/access/test_cadastro_contador.py` (container) → 20 passaram. `ruff check` sem achados nos arquivos alterados.

## Falhou
- 27/11 · S3 · `pytest tests/access` inteiro estourou o tempo limite da ferramenta (sem resultado); rodei só os dois arquivos da ACE-02.
- 27/11 · S3 · `ruff format --check src tests/access` aponta 8 arquivos a reformatar; não conferi se algum é das minhas mudanças.
- 26/11 · S2 · `hx check-clean` acusou CNPJ válido em `tests/access/test_cadastro_contador.py:687`; o responsável trocou o literal (única edição em `tests/`, feita por ele).
- 26/11 · S2 · Fora do container, `tests/web` falha por Node 22 (pede 24) e por `PYTHONPATH`; é ambiente local, passa no container.
- 26/11 · S2 · `hx verify` do responsável: `tests/web` (build do front, vite) falhou uma vez; não reproduziu em `pytest tests/web` nem na suíte inteira. Hipótese não confirmada: corrida pela pasta `web/` com outro comando.
- 27/11 · S3 · `hx verify` não rodou: no host falhou com `ImportError: cannot import name 'UTC'` (Python 3.10 do sistema); dentro do container, `python tools/harness.py verify` parou com "Docker indisponível" (`docker info` falha lá). Rodar `hx verify` pelo terminal do responsável, com Docker Desktop ligado.

## Decisões
- 26/11 · S2 · Tudo resolvido na própria feature, sem issue `contrato:` nem pendência para outras fichas (responsável). Ver `DECISIONS.md`, ACE-02/F5.
- 26/11 · S2 · `access` importa `ManagerOnlyError` e `ClientNotFoundError` de `registry.contracts`; `MIN_PASSWORD_LENGTH` foi para `access/passwords.py`; o aceite recusa quem já tem senha.
- 27/11 · S3 · Trava só em gerar e cancelar, como sugerido na revisão; o aceite ficou de fora (ver Bloqueios). Gerar × cancelar não tem teste: o estado final é igual ao de uma execução em série.

## Fim de sessão
- [x] `hx verify` verde, ou a falha está descrita em "Falhou"
- [ ] Nada quebrado nem pela metade na branch; commit feito (correção da corrida ainda sem commit)
- [x] "Próxima ação" atualizada
- [x] Nenhum dado real nem segredo nas anotações