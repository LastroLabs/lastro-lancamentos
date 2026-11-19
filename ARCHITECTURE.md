# Lastro — ARCHITECTURE.md (v0.1, 19/11/2026)

Mapa do código para quem vai criar arquivo, mover código ou importar outro módulo. Diz **onde fica cada coisa** e **o que nunca pode acontecer**. O porquê e o detalhe ficam na fonte: `gitpages/src/content/docs/arquitetura/visao-geral.mdx` (aprovada em 18/11/2026, ARQ-01 a ARQ-08 e BD-01 a BD-08 em `docs/decisoes/DECISIONS.md`). Se este arquivo e a fonte divergirem, vale a fonte; avise.

Este arquivo não lista fichas, estados nem progresso (isso é o `hx state`). Muda pouco: só quando a arquitetura mudar.

## 1. Visão em poucas linhas

- **Monólito modular** em Python 3.14 + FastAPI. Um só código Python, dois processos: **API** e **worker** (Procrastinate, fila no próprio PostgreSQL).
- **PostgreSQL 18** com Row-Level Security por escritório e carteira; `pg_trgm` para "parecidas"; dinheiro em centavos (BIGINT).
- **Arquivos** em armazenamento S3 privado (SeaweedFS no dev; gerenciado no piloto).
- **Frontend** SPA React 19 + TypeScript (Vite), estático. Área do chefe e do contador (desktop, com login) e página do cliente `/enviar/:token` (celular, sem login).
- **Externos:** o provedor de LLM (só recebe texto anonimizado, só pelo módulo `ai/`) e o Domínio (recebe a planilha que o contador baixa e importa).
- O navegador **só** fala com a API (`/api/v1`). Nunca com banco, arquivos ou LLM.

## 2. Mapa do código

```
src/lastro/                 backend, um pacote por módulo
  core/                     config, sessão, permissões, contexto RLS, dinheiro em centavos
  access/                   escritório, usuário, papel, atribuição, link do cliente
  registry/                 cliente, contas bancárias, sócios, plano de contas, configuração
  uploads/                  upload, quarentena, status por cliente e mês
  parsing/                  detecção de formato, leitores OFX e PDF (BB, Inter)
  validation/               saldo, continuidade, cobertura do mês (só código)
  classification/           regras → histórico → parecidas → IA
  questions/                agrupamento por contraparte, página do cliente, respostas
  review/                   três grupos, aceitar/trocar/pendente, aprendizado
  export/                   fotografia imutável, planilha do Domínio, conciliação
  ai/                       único lugar que chama LLM; anonimiza antes
  observability/            registro de decisões e métricas do piloto
  api/                      rotas FastAPI finas
  worker/                   tarefas Procrastinate
web/src/                    frontend (scaffold na ficha WEB-01)
  api/                      cliente HTTP de /api/v1
  components/               componentes compartilhados
  copy/                     textos de interface
  pages/manager/            chefe
  pages/accountant/         contador
  pages/client/             cliente final (celular)
tests/<module>/             testes de cada módulo, mesmo nome da pasta de src/lastro/
tests/harness/, tests/ci/   testes do harness e da CI (não mexer ao implementar feature)
migrations/                 Alembic, uma migração por PR
fixtures/                   dados sintéticos gerados (`hx fixtures build`, HAR-03)
layouts/dominio.yaml        layout da planilha do Domínio (PROVISÓRIO, D-05)
features/ planos/ progress/ processo: fichas, planos e diário (ver AGENTS.md)
tools/                      harness: harness.py, hx, hx.ps1
docs/                       decisões, requisitos, segurança, templates; docs/modules/ (a criar)
gitpages/                   site de documentação (Astro/Starlight, pnpm)
```

Hoje os pacotes de `src/lastro/` e `web/src/` existem vazios. Nomes de pastas e arquivos em inglês; textos de interface, documentos e fichas em português.

## 3. Dentro de um módulo

| Arquivo | Papel | Quem pode importar |
|---|---|---|
| `service.py` | Interface pública: as funções que o resto do sistema chama | qualquer módulo, `api/`, `worker/` |
| `contracts.py` | Dataclasses imutáveis trocadas entre módulos | qualquer módulo |
| `repository.py` | Único lugar que lê e grava as tabelas do módulo | só o próprio módulo |
| `models.py` | Modelos internos | só o próprio módulo |
| `routes.py` | Só em `api/`: rotas que autorizam e chamam `service.py` | o app FastAPI |

Um módulo pode ter outros arquivos internos (ex.: um leitor por banco em `parsing/`), privados ao módulo.

## 4. Direção das dependências

**Aprovado (fonte, "Regras de dependência"):** as setas só descem.

1. `api/` e `worker/` chamam serviços dos módulos; nunca acessam tabela direto.
2. Um módulo chama outro só por `service.py` e `contracts.py`, nunca pelos modelos internos.
3. Só `ai/` importa SDK de provedor de LLM. Só `uploads/` e `export/` falam com o armazenamento de arquivos.
4. `validation/` não importa `ai/`.

```
            api/      worker/            (entrada: só via service.py)
               \       /
   módulos de domínio: uploads, parsing, validation, classification,
                       questions, review, export, access, registry
               |        \
              ai/        \               (gateway de LLM; validation nunca chega aqui)
               |          \
            core/    observability/      (base)
```

**Proposta deste arquivo, `[definir]` até aprovação:** `core/` não depende de nenhum módulo do Lastro; nenhum módulo importa `api/` nem `worker/`. Qualquer dependência fora das regras 1 a 4: pergunte antes de criar.

## 5. Invariantes

| # | Regra | Por quê | Quem confere hoje |
|---|---|---|---|
| I-1 | Só `ai/` importa SDK de provedor de LLM, e só depois de anonimizar (CPF, CNPJ, agência, conta e nomes de contraparte, D-03) | vazamento de dado pessoal; troca de provedor | ninguém ainda (planejado: import-linter no `hx verify`); IA-01/IA-02 testam a anonimização |
| I-2 | `validation/` não importa `ai/`. Saldo é conferido por código; extrato que não fecha não segue para classificação nem perguntas | RF-VAL-01 | ninguém ainda (planejado: import-linter) |
| I-3 | Dinheiro é `int` em centavos (BIGINT no banco). Nunca `float` | arredondamento | testes de cada ficha |
| I-4 | Isolamento no servidor em toda requisição: escritório não vê outro; contador só vê clientes atribuídos. Duas camadas: autorização em `core/`/`api/` e RLS no banco | RF-SEG-01/02, RF-AUT-02 | testes NUC-02, NUC-03, ACE-03 |
| I-5 | Sessão no servidor (não JWT com carteira embutida); reatribuir cliente revoga o acesso na hora, mesmo com sessão aberta | RF-AUT-04 | teste ACE-04 |
| I-6 | Link do cliente: token de 32 bytes, guardado só como hash, com validade (D-06) e revogável. Rotas públicas só em `/api/v1/publico/{token}/…` | RF-SEG-01 | teste ACE-05 |
| I-7 | `api/` e `worker/` nunca leem ou gravam tabela direto; só `repository.py` do próprio módulo toca as tabelas do módulo | fronteiras e RLS | ninguém ainda (planejado: import-linter) |
| I-8 | Só `uploads/` e `export/` falam com o armazenamento de arquivos. Download sempre mediado pela API; sem URL assinada longa para contador | revogação imediata | ninguém ainda |
| I-9 | Gravar o envio e criar a tarefa na fila é uma única transação (fila no Postgres) | não perder tarefa | sem ficha ainda |
| I-10 | Nada é exportado sem revisão; pendentes saem na conta transitória, marcados. A exportação grava uma fotografia imutável e o hash do arquivo | RF-REV-04, RF-EXP-02 | sem ficha ainda |
| I-11 | Layout do Domínio só em `layouts/dominio.yaml`; nenhuma coluna fixa no código | D-05 provisória | sem ficha ainda |
| I-12 | Nenhum dado real em arquivo, teste, log ou prompt. Fixtures só sintéticas, geradas por semente | LGPD | `hx check-clean` (local e CI de PR) |
| I-13 | Sugestões, revisões e chamadas de IA são gravadas como eventos versionados | RF-OBS-01, RF-CLA-06 | sem ficha ainda |
| I-14 | Erros da API em RFC 9457 (`application/problem+json`), mensagem em português simples: o que aconteceu + o que fazer | RF-AVI-02 | sem ficha ainda |

"Ninguém ainda" quer dizer: o `hx verify` mostra `Arquitetura: PULADO`. Quebrar a regra não reprova nada hoje, mas reprova na revisão do PR.

## 6. Contratos entre módulos (versão 0)

| De → para | Contrato |
|---|---|
| parsing → validation | `ExtratoLido` |
| parsing → classification | `MovimentacaoLida` |
| validation → review, export | `ResultadoConferencia` |
| classification → review | `Sugestao` |
| questions → review | `RespostaCliente` |
| review → export | `ItemRevisado` |

`[definir]` em qual `contracts.py` cada contrato vive (proposta: no do módulo que o produz). Os campos estão na fonte (seção "Contratos entre módulos"). Mudar um contrato: issue `contrato:`, um PR que atualize os dois lados e o `docs/modules/` dos dois módulos. Os nomes dos contratos, das tabelas e dos identificadores do código continuam em português até haver decisão.

## 7. Onde colocar código novo

| Preciso de… | Vai em |
|---|---|
| uma rota HTTP | `api/routes.py`, fina: autoriza e chama `service.py` |
| uma tarefa em segundo plano | `worker/`, chamando `service.py` |
| ler ou gravar tabela | `repository.py` do módulo dono da tabela |
| expor algo a outro módulo | `service.py` (função) e `contracts.py` (dado) |
| chamar LLM | `ai/`; a resposta é uma conta do plano do cliente ou "não sei" |
| mudar esquema do banco | uma migração em `migrations/` por PR |
| um leitor de banco novo | `parsing/` (D-04: banco novo não é entrega confirmada) |
| texto para o usuário | `web/src/copy/` no front; mensagem do erro RFC 9457 no back |
| dado de teste | gerado em `fixtures/` (HAR-03); nunca copiado de extrato real |
| regra específica de um módulo | `docs/modules/<module>.md`, não aqui |

## 8. Fichas e pastas

- O campo `modulo` da ficha é o nome da pasta (`core`, `access`, `registry`, `ai`...) ou `harness`/`ci`. A ficha só cria código na pasta do seu módulo e testes em `tests/<module>/`.
- O prefixo do ID é histórico e não deriva da pasta: NUC → `core`, ACE → `access`, CAD → `registry`, IA → `ai`, HAR → `harness`, HX → `ci`.

## 9. Em aberto (não decida sozinho)

- `[definir]` Divergência de versão: a arquitetura fixa Python 3.14 (ARQ-08); o `Dockerfile` usa `python:3.12-slim`. A NUC-01 (c5) cobre o ambiente de verificação.
- `[definir]` As propostas marcadas nas seções 4 e 6.
- `[definir]` Checagem automática das seções 4 e 5 (import-linter no `hx verify`): ainda sem ficha.
- `[definir]` Hospedagem, provedor de LLM, D-01 e D-08 (ver `docs/decisoes/DECISIONS.md`).
- `[definir]` HAR-04 ainda usa os nomes antigos dos módulos.
- `[definir]` Se `planos/`, `docs/decisoes/` e `docs/requisitos/` passam para inglês.
