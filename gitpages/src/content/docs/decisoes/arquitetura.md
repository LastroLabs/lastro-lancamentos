---
title: "Decisão: arquitetura do sistema"
description: Monólito modular em Python, SPA React, sessão no servidor, fila no PostgreSQL e gateway único de IA.
---

| Status | Data | Fonte |
|---|---|---|
| Recomendada, aguardando aprovação | 10/11/2026 | Lastro — Arquitetura do Sistema |

## Contexto

Os 56 Must da v0.2 precisam caber em pouco tempo, com um time pequeno e sem infraestrutura que o grupo não consiga operar. Oito requisitos decidem a forma do sistema: isolamento checado no servidor, revogação imediata, envio sem login, leitura assíncrona, saldo só em código, IA anonimizada, rastreabilidade e planilha importável sem edição.

## Decisão

- Monólito modular em Python 3.14 + FastAPI, num único repositório (ARQ-01).
- Frontend React 19 + TypeScript com Vite, como SPA estática (ARQ-02).
- Sessão no servidor, não JWT (ARQ-03).
- Fila no próprio PostgreSQL, com Procrastinate (ARQ-04).
- Cliente da API gerado do OpenAPI (ARQ-05).
- Um único gateway de IA em `src/lastro/ia/`, atrás de uma interface (ARQ-06).
- SeaweedFS no desenvolvimento e S3 gerenciado no piloto (ARQ-07).
- Python 3.14 e FastAPI com versão menor fixada (ARQ-08).

| ID | Decisão | Alternativa descartada e por quê |
|---|---|---|
| ARQ-01 | Monólito modular em Python, um repositório | Microsserviços: custo de operação que 4,5 semanas não pagam |
| ARQ-02 | React + Vite como SPA estática | Next.js: segundo servidor e SSR sem necessidade |
| ARQ-03 | Sessão no servidor, não JWT | JWT impede a revogação imediata de RF-AUT-04 |
| ARQ-04 | Fila no PostgreSQL (Procrastinate) | Celery + Redis: mais um serviço para operar e monitorar |
| ARQ-05 | Cliente da API gerado do OpenAPI | Tipos escritos à mão: divergem do backend sem aviso |
| ARQ-06 | Um único gateway de IA (`src/lastro/ia/`) atrás de interface | Chamar o SDK de dentro de cada módulo: vaza dado e prende a um provedor |
| ARQ-07 | SeaweedFS no dev, S3 gerenciado no piloto | MinIO: edição comunitária arquivada em 2026 |
| ARQ-08 | Python 3.14, FastAPI com versão menor fixada | Python 3.15: lançado em out/2026, ecossistema ainda atrasado |

## Alternativas consideradas

- **Microsserviços, Kubernetes, fila dedicada (Redis/RabbitMQ) e banco vetorial:** excluídos pela restrição de prazo.
- **Next.js:** traria um segundo servidor, renderização no servidor que não é usada e mais um lugar para checar permissão.
- **JWT com a carteira embutida:** não permite revogar o acesso na hora.
- **Celery + Redis:** mais um serviço para operar.
- **MinIO:** a edição comunitária foi arquivada em abril de 2026 e não recebe mais correções de segurança.
- **Python 3.15:** parte do ecossistema ainda não declara suporte.
- **Leitores:** evitar `ofxtools` (GPL-3) e PyMuPDF no MVP (AGPL).

## Consequências

**Destrava:**

- a estrutura do repositório (`src/lastro/<modulo>/`), com um dono por módulo, como o harness pede;
- contratos imutáveis entre módulos, conferidos pelo `harness.py verify` com `import-linter`;
- a ordem de construção semana a semana, com uma jornada E2E demonstrável ao fim de cada semana;
- tipos do frontend gerados do backend: mudou o contrato, o front deixa de compilar no PR.

**Custa:**

- disciplina nas regras de dependência: uma violação reprova o PR;
- versões fixadas no lockfile e conferidas a cada atualização;
- infraestrutura do piloto estimada em US$ 30 a 60 por mês, mais IA (estimativa; conferir os preços no dia da contratação).

## Pendências ligadas

| Pendência | Como afeta a arquitetura |
|---|---|
| D-05 layout do Domínio | Bloqueia a exportação final; pedir exemplo aos dois escritórios na semana 1 |
| D-03 nomes para a IA | Define se `anonimizar()` pseudonimiza nomes; até lá, pseudonimiza |
| D-06 arquivo e link | Proposta: 20 MiB e 7 dias |
| D-09 chefe e vários contadores | O esquema já aceita vários vínculos; a regra fica em configuração |
| Provedor do piloto (sem ID) | Supabase ou Fly Managed Postgres, ambos em São Paulo |
| Modelo da tarefa e do juiz (sem ID) | Ver [Avaliação com LLM](/lastro-lancamentos/decisoes/avaliacao-llm/) |
| React ou Vue (sem ID) | A Arquitetura recomenda React; aguardando confirmação do time |

Detalhes técnicos em [Arquitetura](/lastro-lancamentos/arquitetura/visao-geral/) e [Stack](/lastro-lancamentos/arquitetura/stack/).

**Fonte:** Lastro — Arquitetura do Sistema (10/11/2026), seções 1, 3, 5 e 10.
