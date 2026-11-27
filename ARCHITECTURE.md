# Lastro — ARCHITECTURE.md (v0.2)

Mapa do código para quem vai criar arquivo, mover código ou importar outro módulo. Diz **onde fica cada coisa** e **o que nunca pode acontecer**. O porquê e o detalhe ficam na fonte: `gitpages/src/content/docs/arquitetura/visao-geral.mdx` (aprovada em 18/11/2026, ARQ-01 a ARQ-08 e BD-01 a BD-08 em `docs/decisoes/DECISIONS.md`). Se este arquivo e a fonte divergirem, vale a fonte; avise.

**Este arquivo não guarda estado:** nem fichas, nem o que já existe ou falta, nem quem confere cada regra hoje. Isso vem do repositório, do `hx state` e de `docs/qualidade.md`. Ele só muda quando a arquitetura mudar (seção 9).

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
web/src/                    frontend
  api/                      cliente HTTP de /api/v1
  components/               componentes compartilhados
  copy/                     textos de interface
  pages/manager/            chefe
  pages/accountant/         contador
  pages/client/             cliente final (celular)
tests/<module>/             testes de cada módulo, mesmo nome da pasta de src/lastro/
tests/harness/, tests/ci/   testes do harness e da CI (não mexer ao implementar feature)
tests/conftest.py           fixtures comuns a todos os módulos (`synthetic_fixtures_dir`, HAR-03)
migrations/                 Alembic, uma migração por PR
fixtures/                   dados sintéticos gerados (`hx fixtures build`)
layouts/dominio.yaml        layout da planilha do Domínio (PROVISÓRIO, D-05)
features/ planos/ progress/ processo: fichas, planos e diário (ver AGENTS.md)
tools/                      harness: harness.py, hx, hx.ps1
tools/fixtures_sinteticas.py gerador do `hx fixtures build` (só biblioteca padrão, HAR-03)
docs/                       decisões, requisitos, segurança, templates, docs/modulos/
gitpages/                   site de documentação (Astro/Starlight, pnpm)
```

Nomes de pastas e arquivos em inglês; textos de interface, documentos e fichas em português.

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

A direção **entre** módulos de domínio é a da tabela de contratos (seção 6): quem produz um contrato não importa quem o consome.

**Proposta, `[definir]` até aprovação:** `core/` não depende de nenhum módulo do Lastro; nenhum módulo importa `api/` nem `worker/`. Qualquer dependência fora das regras 1 a 4: pergunte antes de criar.

## 5. Invariantes de arquitetura

Regras que a estrutura precisa garantir. As de negócio e de dados (centavos, saldo por código, exportação revisada, dado real) ficam no `AGENTS.md` (regras 1, 4, 6 e 8) e no `docs/SECURITY.md`, e **não se repetem aqui**. Os números seguem os do v0.1 (I-3 e I-12 saíram); não renumere.

| # | Regra | Por quê |
|---|---|---|
| I-1 | Só `ai/` importa SDK de provedor de LLM, e só depois de anonimizar, nos termos da regra 5 do `AGENTS.md` e da D-03 | vazamento de dado pessoal; troca de provedor |
| I-2 | `validation/` não importa `ai/`. Extrato que não fecha não segue para classificação nem perguntas | RF-VAL-01 |
| I-4 | Isolamento no servidor em toda requisição, em duas camadas: autorização em `core/` e `api/`, e RLS no banco. Escritório não vê outro; contador só vê clientes atribuídos | RF-SEG-01/02, RF-AUT-02 |
| I-5 | Sessão no servidor (não JWT com carteira embutida). Reatribuir cliente revoga o acesso na hora, mesmo com sessão aberta | RF-AUT-04 |
| I-6 | Link do cliente: token de 32 bytes, guardado só como hash, com validade (D-06) e revogável. Rotas públicas só em `/api/v1/publico/{token}/…` | RF-SEG-01 |
| I-7 | `api/` e `worker/` nunca leem ou gravam tabela direto; só o `repository.py` do próprio módulo toca as tabelas do módulo | fronteiras e RLS |
| I-8 | Só `uploads/` e `export/` falam com o armazenamento. Download sempre mediado pela API; sem URL assinada longa para contador | revogação imediata |
| I-9 | Gravar o envio e criar a tarefa na fila é uma única transação (fila no Postgres) | não perder tarefa |
| I-10 | A exportação grava uma fotografia imutável e o hash do arquivo | RF-EXP-02 |
| I-11 | Layout do Domínio só em `layouts/dominio.yaml`; nenhuma coluna fixa no código | D-05 provisória |
| I-13 | Sugestões, revisões e chamadas de IA são gravadas como eventos versionados | RF-OBS-01, RF-CLA-06 |
| I-14 | Erros da API em RFC 9457 (`application/problem+json`), mensagem em português simples: o que aconteceu + o que fazer | RF-AVI-02 |

**Conferência:** I-1, I-2, I-7 e I-8 são de import e serão conferidas por import-linter no `hx verify`; as demais, por testes das fichas e pela revisão do PR. Quem confere cada uma hoje está em `docs/qualidade.md`. Sem checagem automática, quebrar a regra reprova na revisão, não no `hx verify`.

## 6. Contratos entre módulos (versão 0)

| De → para | Contrato |
|---|---|
| registry → api (`CAD-03`) | `CnpjValidationResult`, `ClientSummary` e os erros de cliente (`lastro.registry.contracts`); `validate_cnpj`, `register_client`, `list_clients`, `get_client` (`lastro.registry.service`). Lista e abertura recebem `access.service.responsible_member_ids` por parâmetro (o `registry` não lê `atribuicao`). Detalhes em `docs/modulos/registry.md` |
| registry → api (`CAD-02`, `CAD-05`) | `ChartAccountEntry`, `ChartOfAccountsResult` (`lastro.registry.contracts`); `read_chart_of_accounts` (`lastro.registry.service`). Detalhes em `docs/modulos/registry.md` |
| parsing → validation | `ExtratoLido` |
| parsing → classification | `MovimentacaoLida` |
| validation → review, export | `ResultadoConferencia` |
| classification → review | `Sugestao` |
| questions → review | `RespostaCliente` |
| review → export | `ItemRevisado` |
| access → api e módulos com rota protegida | `SignedInMember` (`access/contracts.py`, ACE-01): quem está conectado, com `member_id`, `firm_id` e `role` |
| ai → classification (`IA-02`) | `ClientDescription`, `CandidateAccount` (`lastro.ai.contracts`), `suggest_accounts` (`lastro.ai.service`). Sem consumidor ainda; avisar o dono da `classification` por issue `contrato:` quando a ficha existir. Detalhes em `docs/modulos/ai.md` |

**`registry` (`CnpjValidationResult` / `validate_cnpj`, versão 0):**
- **Assinatura:** `validate_cnpj(cnpj: str) -> CnpjValidationResult` (`src/lastro/registry/service.py`).
- **Campos (`CnpjValidationResult` em `src/lastro/registry/contracts.py`):** `is_valid: bool`, `normalized: str | None` (14 caracteres maiúsculos, sem máscara, quando válido; `None` caso contrário) e `error_message: str | None` (`None` quando válido).
- **Mensagens oficiais:** vazio → `"Informe o CNPJ do cliente."`; inválido → `"O CNPJ informado não é válido. Confira os números."`.
- **Fronteira e impactos:** o contrato devolve apenas a mensagem de recusa — o status HTTP de dado inválido (`P-13`) fica na camada `api/`. Qualquer mudança de campo, assinatura ou mensagem deve avisar o responsável pela `CAD-03` (consumidora direta). Detalhes, notas para `CAD-03`, `DB-01` e `tools/harness.py` ficam em `docs/modulos/registry.md`. Os demais contratos `registry → classification/export` seguem `[definir]` na seção 10.

`[definir]` em qual `contracts.py` cada contrato vive (proposta: no do módulo que o produz). Os campos estão na fonte (seção "Contratos entre módulos"). Mudar um contrato: issue `contrato:`, um PR que atualize os dois lados e o `docs/modulos/` dos dois módulos. Nomes de contratos, tabelas e identificadores do código continuam em português até haver decisão.

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
| dado de teste | gerado em `fixtures/`; nunca copiado de extrato real |
| regra específica de um módulo | `docs/modulos/<module>.md`, não aqui |
| um módulo ou pasta de primeiro nível novos | não crie: registre em `DECISIONS.md` e pergunte |

## 8. Fichas e pastas

**Exceção DB-01/A1 confirmada pelo responsável em 23/11/2026:** seis modelos em `src/lastro/access/models.py`, cliente em `src/lastro/registry/models.py`, Base comum em `src/lastro/core/models.py` e uma revisão em `migrations/versions/`. A ficha permanece única, com sessões separadas para testes e implementação (A2); módulos não importam modelos internos uns dos outros.

**Exceção DB-02 para testes da DB-01 (23/11/2026, autorizada pela responsável):** `tests/access/conftest.py` e `tests/access/test_identity_schema.py` foram ajustados no PR #54 para validar a DB-01 na revisão `0002` e aceitar a extensão de `cliente` pela DB-02. O ajuste preserva os critérios da DB-01; ver `progress/DB-02.md` e o PR #54.

**Divisão DB-01/NUC-03 (23/11/2026, decisão do responsável DB-01):** esquema e restrições na DB-01; políticas RLS na NUC-03, obrigatoriamente concluída antes de usar dados de piloto. Sem políticas permissivas de contorno. Nomes físicos da DB-01 seguem a ficha em português singular, como exceção ao CODING_STANDARDS.md. Esta divisão não declara o isolamento implementado nem altera a I-4 do produto. Ver `docs/decisoes/DECISIONS.md`, seção 5.

**RLS implementada (NUC-03, 26/11/2026):** a segunda camada da I-4 existe. `core/db.py` leva o escritório ao banco (`use_firm`, reaplicado a cada transação); as migrações `0005` e `0006` ligam a RLS forçada nas 12 tabelas com escritório e criam as cinco funções de busca sem escritório. Tabela nova com `escritorio_id` precisa de RLS e políticas na própria migração. Ver `docs/modulos/access.md` ("Isolamento no banco") e `docs/decisoes/DECISIONS.md`, seção 10.

- O campo `modulo` da ficha é o nome da pasta (`core`, `access`, `registry`, `ai`...) ou `harness`/`ci`. A ficha só cria código na pasta do seu módulo e testes em `tests/<module>/`.
- O prefixo do ID é histórico e não deriva da pasta: NUC → `core`, ACE → `access`, CAD → `registry`, IA → `ai`, HAR → `harness`, HX → `ci`.

## 9. Manter este arquivo

Mudou pasta, regra de dependência, invariante ou contrato? Atualize este arquivo **no mesmo PR**. O `/planejar` lê este arquivo e checa cada task contra as seções 4 e 7; o revisor confere no item **Escopo** da rubrica. Doc desatualizada é pior do que nenhuma: na dúvida, apague a linha.

## 10. Em aberto (não decida sozinho)

- `[definir]` Divergência de versão: a arquitetura fixa Python 3.14 (ARQ-08); o `Dockerfile` usa `python:3.12-slim`.
- `[definir]` As propostas marcadas nas seções 4 e 6, e a checagem automática das invariantes de import (import-linter no `hx verify`).
- `[definir]` Alinhar a I-1 à regra 5 do `AGENTS.md` (nomes de contraparte são proibidos até a D-03).
- `[definir]` Contratos que parecem faltar na seção 6 (conferir na fonte): `uploads → parsing`, `registry → classification/export`, `classification → questions`.
- `[definir]` Hospedagem, provedor de LLM, D-01 e D-08 (ver `docs/decisoes/DECISIONS.md`).
- `[definir]` Se `planos/`, `docs/decisoes/` e `docs/requisitos/` passam para inglês.
