---
title: Stack
description: O que usar em cada camada, com as versões do documento de arquitetura.
---

:::note[Status]
Recomendada, aguardando aprovação. A escolha de React está aguardando confirmação do time: a reunião de 10/11 deixou "React ou Vue" em aberto. Ver o [índice de decisões](/lastro-lancamentos/decisoes/).
:::

Uma linguagem por lado: **TypeScript no frontend e Python no backend, no worker e na IA**. O documento conferiu as versões em 10/11/2026 e pede fixar sempre a versão exata no lockfile. As versões abaixo estão copiadas dele.

## Resumo por camada

| Camada | Escolha |
|---|---|
| Frontend | React 19.2 + TypeScript, Vite 8, TanStack Router e Query, Tailwind 4 + shadcn/ui, fonte Inter; cliente da API gerado do OpenAPI |
| Backend | Python 3.14, FastAPI (versão menor fixada), Pydantic 2, SQLAlchemy 2 + Alembic, sessão no servidor |
| Processamento | Worker Procrastinate; ofx-br / ofxparse para OFX, pdfplumber para PDF de BB e Inter; conferência só em código |
| IA | `src/lastro/ia/` como único ponto de chamada, saída com schema, contas do cliente como únicas respostas válidas |
| Dados | PostgreSQL 18 (RLS, `pg_trgm`), centavos em BIGINT; arquivos em S3 privado |
| Infra | Docker Compose no dev (Postgres + SeaweedFS); piloto em São Paulo (Postgres gerenciado + PaaS); GitHub Actions |

## Frontend

| Item | Escolha | Por quê |
|---|---|---|
| Linguagem | TypeScript (modo `strict`) | Tipos gerados da API eliminam erro de contrato entre front e back |
| Biblioteca de UI | React 19.2 | Mais gente do grupo conhece; maior ecossistema de componentes |
| Build | Vite 8, como SPA estática | Sem SSR: o app do contador fica atrás de login e a página do cliente é uma tela só |
| Rotas | TanStack Router 1.x | Rotas e parâmetros de busca tipados (filtros da revisão na URL) |
| Dados do servidor | TanStack Query 5 | Cache, paginação, reenvio e atualização otimista na revisão |
| Estilo | Tailwind CSS 4 + componentes shadcn/ui | Componentes acessíveis copiados para o repositório, sem tema fechado |
| Fonte | Inter | Recomendação do estudo de UX/UI |
| Formulários | React Hook Form + Zod | Validação no cliente com os mesmos limites da API |
| Cliente da API | `openapi-typescript` + `openapi-fetch`, gerados do OpenAPI do FastAPI | Mudou o contrato no back, o front deixa de compilar: o erro aparece no PR |
| Testes | Vitest 4 + Testing Library; Playwright para E2E | Playwright cobre a jornada completa no `verify --e2e` |
| Lint e formatação | Biome | Uma ferramenta só, rápida |

Duas entradas no mesmo app:

- **Área do contador:** desktop primeiro. Carteira, revisão em tabela e exportação.
- **Página do cliente em `/enviar/:token`:** celular primeiro. Envio e perguntas com um toque.

A área administrativa do chefe é um conjunto de telas dentro da área do contador, liberadas pelo papel.

## Backend (API)

| Item | Escolha | Por quê |
|---|---|---|
| Linguagem | Python 3.14 | Estável há um ano; o 3.15 saiu em out/2026, mas parte do ecossistema ainda não declara suporte |
| Framework | FastAPI, versão menor fixada (ex.: `>=0.148,<0.149`) | Está abaixo da 1.0 e versões menores podem quebrar |
| Validação e schemas | Pydantic 2 | Os mesmos modelos geram o OpenAPI que o front consome |
| Acesso a dados | SQLAlchemy 2 (async) + driver psycopg 3 | Consultas tipadas; `SET LOCAL` do contexto de RLS por transação |
| Migrações | Alembic, uma migração por PR que muda o esquema | Migração versionada, exigida pelo estudo de banco |
| Autenticação | Sessão no servidor (cookie `HttpOnly`, `Secure`, `SameSite=Lax`) + senha com Argon2 | Permite revogar acesso na hora (RF-AUT-04) |
| Dinheiro | `int` em centavos em todo o código; `Decimal` só na leitura do arquivo | Regra de ouro do harness |
| Gerenciador de pacotes | uv | Já previsto no harness |
| Testes | pytest + Testcontainers com PostgreSQL 18 | Mesmo motor da produção; nada de SQLite nos testes |
| Lint e tipos | Ruff + mypy (ou pyright) | Rodam no `harness.py verify` |

## Worker e leitura de extratos

| Item | Escolha | Por quê |
|---|---|---|
| Fila | Procrastinate (fila no próprio PostgreSQL) | Sem Redis no MVP; a tarefa nasce na mesma transação que grava o envio |
| OFX | ofx-br (MIT), com ofxparse (MIT) como alternativa | ofx-br trata SGML sem fechamento, cp1252 e FITID dos bancos brasileiros. É jovem: entra só se passar no gabarito na semana 1. Evitar `ofxtools` (GPL-3) |
| PDF digital | pdfplumber (MIT), um leitor por banco (BB, Inter) | Extrai texto e tabelas com coordenadas. Evitar PyMuPDF no MVP: licença AGPL |
| Excel do Domínio | openpyxl lendo `layouts/dominio.yaml` | Colunas vêm do YAML, nunca do código |
| Foto e print (Should, D-01) | Fora do MVP; se entrar, via modelo multimodal no gateway de IA, sempre com conferência de saldo | Evita manter OCR próprio |

## Dados, arquivos e infraestrutura

| Item | Desenvolvimento e CI | Piloto (dados reais) |
|---|---|---|
| Banco | PostgreSQL 18 no Docker Compose | PostgreSQL 18 gerenciado em São Paulo: Supabase Pro (`sa-east-1`) ou Fly Managed Postgres (`gru`). Usar só o Postgres e o Storage, sem o Auth do Supabase |
| Arquivos | SeaweedFS no Compose (API S3) | Armazenamento S3 privado na mesma região (Supabase Storage ou AWS S3 `sa-east-1`) |
| API e worker | Containers no Compose | Dois processos do mesmo container em PaaS com região São Paulo, ex.: Fly.io `gru` |
| Frontend | Vite dev server | Arquivos estáticos em CDN (Cloudflare Pages ou equivalente) |
| Segredos | `.env` local fora do git | Secrets do provedor e do GitHub Actions |
| CI | GitHub Actions: `verify` em todo PR, `noturno.yml` às 03:00 | Igual |
| Observabilidade | Logs estruturados em JSON | Sentry (erros) + logs do provedor; nada de dado pessoal nos logs |

**Por que não MinIO:** a edição comunitária foi arquivada em abril de 2026 e não recebe mais correções de segurança. O SeaweedFS fala a mesma API S3, então o código não muda entre dev e piloto.

**Custo no piloto:** na faixa de US$ 30 a 60 por mês (banco gerenciado, duas máquinas pequenas e armazenamento), mais IA. É estimativa: conferir os preços no dia da contratação.

**Fonte:** Lastro — Arquitetura do Sistema (10/11/2026), seções 1 e 5.
