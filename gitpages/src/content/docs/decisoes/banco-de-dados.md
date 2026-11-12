---
title: "Decisão: banco de dados"
description: PostgreSQL relacional, isolamento por escritório e carteira, centavos em BIGINT.
---

| Status | Data | Fonte |
|---|---|---|
| Recomendada, aguardando aprovação | 10/11/2026 | Banco de dados para o Lastro, v1.0 |

O documento apresenta a escolha como "decisão recomendada" e diz que as escolhas são "propostas concretas deste estudo". Por isso o status aqui é recomendada, não aceita.

## Contexto

O banco precisa sustentar a confiança no fluxo: explicar de onde veio cada sugestão, reproduzir o que foi exportado e manter isolados escritórios e carteiras. O estudo não incluiu implementação, teste de carga nem teste real de importação no Domínio.

## Decisão

- PostgreSQL 18 como banco principal, com migrações SQL versionadas (BD-01).
- Esquema compartilhado entre escritórios, com isolamento por escopo, autorização e Row-Level Security (BD-02).
- Arquivos em armazenamento de objetos privado; no banco ficam metadados, hash e vínculo com o processamento (BD-03).
- Versões e eventos para um histórico auditável, sem event sourcing integral (BD-04).
- Dinheiro em BIGINT com sinal, em centavos (BD-05).
- Similaridade textual (`pg_trgm`) primeiro, sem embeddings no MVP (BD-06).
- CI separada do piloto, com PostgreSQL e fixtures sintéticas (BD-07).
- Serviço gerenciado no piloto, condicionado a backup e recuperação verificáveis (BD-08).

## Alternativas consideradas

| Opção | Por que não | Encaminhamento |
|---|---|---|
| MySQL / InnoDB | Relacional viável, mas sem benefício concreto que justifique preferi-lo | Alternativa só se houver restrição operacional comprovada |
| MongoDB | Tem transações; o modelo documental traz menos vantagem diante das relações e validações necessárias | Não adotar como banco principal |
| SQLite | Adequado a uso local e simples; API, workers e revisão concorrentes pedem um servidor central | Não usar nem como substituto nos testes de integração |
| Banco vetorial dedicado | A similaridade é uma etapa do produto, não o centro da persistência | Adiar; medir primeiro a busca textual. Se `pg_trgm` não bastar, testar `pgvector` no próprio PostgreSQL |
| Redis, microsserviços de dados, treinamento de modelo | Complexidade sem necessidade no MVP | Fora do MVP |

## Consequências

**Destrava:**

- Isolamento em duas camadas: a aplicação autoriza e o RLS restringe as linhas. O RLS é forçado, com `USING` e `WITH CHECK`, e o contexto vai por transação com `SET LOCAL`.
- Revogação com a sessão aberta: a reatribuição trava o cliente, encerra o vínculo, cria o novo e incrementa `versao_acesso`.
- Deduplicação: SHA-256 no arquivo e unicidade por identificador externo do OFX. PDFs sem identificador mantêm as ocorrências e recebem alerta.
- Exportação reproduzível por fotografia e hash. Baixar de novo entrega o mesmo arquivo.
- Aprendizado só com decisão humana, versionado e reversível.

**Custa:**

- Toda tabela de negócio carrega `escritorio_id` e `cliente_id`, e as chaves estrangeiras repetem esse escopo.
- É preciso testar a negação de acesso em consultas indiretas, agregações e tabelas de ligação.
- Testes de integração usam PostgreSQL real (Testcontainers). Nada de SQLite.
- Backup diário e restauração testada antes do piloto: RPO de até 24 h e RTO de até 4 h (metas propostas).

## Pendências ligadas

| Pendência | Encaminhamento do estudo |
|---|---|
| D-01, D-02, D-04 | Leitores extensíveis, regra de adquirente desativada, terceiro banco parametrizado |
| D-03, D-06 | Pseudonimizar nomes por padrão; propor 7 dias e 20 MiB e medir no piloto |
| D-05 | Layout provisório; o banco guarda versões sem inventar colunas definitivas do Domínio |
| D-07, D-09 | Carteira individual; vários vínculos no modelo, um responsável ativo no início |
| D-08 e precedência (RF-CLA-09 [definir]) | Calibrar com o gabarito; registrar e testar a precedência proposta |
| Retenção (sem ID) | Proposta de 90 dias para originais e 30 dias para logs técnicos, até acordo com os pilotos |
| Provedor do piloto (sem ID) | Escolher pelo backup verificável e pela região; não há dados para fixar valor mensal |

Detalhes do modelo em [Arquitetura · Dados](/lastro-lancamentos/arquitetura/dados/).

**Fonte:** Banco de dados para o Lastro, v1.0 (10/11/2026).
