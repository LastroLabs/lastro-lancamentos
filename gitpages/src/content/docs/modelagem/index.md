---
title: Modelagem de dados
description: Modelo do MVP alinhado aos requisitos, às decisões de 18/11 e às fichas da developer.
---

O modelo organiza os dados necessários para receber extratos, conferir saldos, sugerir contas, registrar respostas e decisões do contador e produzir a exportação para o Domínio. A documentação foi elaborada a partir da **branch `developer`**, dos requisitos vigentes e das decisões registradas no Pages em 18/11/2026.

## Organização

- [Entidades e atributos](/lastro-lancamentos/modelagem/entidades/): responsabilidades e dados de cada entidade.
- [Diagramas](/lastro-lancamentos/modelagem/diagramas/): relacionamentos organizados por fluxo.
- [Modelo lógico](/lastro-lancamentos/modelagem/modelo-logico/): chaves, escopo e integridade referencial.
- [Modelo físico e operações](/lastro-lancamentos/modelagem/modelo-fisico/): tipos, índices, transações e verificações.
- [Premissas e decisões](/lastro-lancamentos/modelagem/decisoes/): o que está aprovado, provisório ou pendente e seu impacto nos dados.
- [Rastreabilidade](/lastro-lancamentos/modelagem/rastreabilidade/): requisito, prioridade, critério de aceitação, entidades, regra e fichas relacionadas.

## Status e limites

A escolha do **PostgreSQL 18**, do isolamento com RLS, dos valores em centavos e do histórico auditável está **aprovada**, conforme [BD-01 a BD-08](/lastro-lancamentos/decisoes/banco-de-dados/). Sessão no servidor e fila no PostgreSQL com Procrastinate também estão aprovadas pela [arquitetura](/lastro-lancamentos/decisoes/arquitetura/).

O **esquema detalhado desta seção é uma proposta de implementação** dessas decisões. Os nomes e as restrições das tabelas ainda precisam ser transformados em migrações e validados. No checkout analisado, `src/lastro/` contém apenas `__init__.py`; não foram encontradas entidades persistidas ou migrações de produto. As fichas S1 apresentadas no site estão em revisão e não representam funcionalidades concluídas.

O modelo propõe **27 tabelas de domínio e acesso**. A separação de `USUARIO`, `MEMBRO` e `SESSAO` preserva identidade, papel no escritório e revogação; `PLANO_CONTAS` explicita a publicação e a substituição do plano. As tabelas internas do Procrastinate são infraestrutura e não integram essa contagem. Não se propõe uma segunda fila baseada em `ARQUIVO`.

## Escopo e prioridades

Os [56 Must](/lastro-lancamentos/modelagem/rastreabilidade/?prioridade=Must) têm vínculo documental individual com entidades ou com uma regra da aplicação. Os requisitos Should e Could continuam complementares. Apoio estrutural não altera sua prioridade nem comprova entrega. Os Won’t permanecem fora do modelo do MVP.

As prioridades, o texto e os critérios de aceitação vêm do [catálogo de requisitos](/lastro-lancamentos/visao/requisitos/). A [rastreabilidade geral](/lastro-lancamentos/requisitos/rastreabilidade/) mantém a origem, as dores, as frentes e as fichas; o [backlog](/lastro-lancamentos/requisitos/backlog/) reúne os épicos e as histórias de usuário.

## Regras incorporadas de 18/11

O **chefe cadastra clientes**, conforme P-02/P-02a. A conta entra na carteira do contador após a atribuição. A nova carga do plano **substitui a versão vigente** e deixa o cliente sem transitória se a conta não estiver no novo plano, conforme P-11, assumida. Pela P-09, o chefe vê a lista do escritório e só edita cadastros ou gera links dos clientes atribuídos a ele; pode se atribuir um cliente.

Pelos padrões atuais, o link tem validade de **7 dias**, o arquivo tem limite de **20 MiB**, a carteira é individual e há **um responsável ativo por cliente**. Esses padrões são configuráveis e provisórios. A pseudonimização de todos os nomes de contrapartes decorre da D-03 aprovada. A regra mínima de adquirentes permanece desligada até confirmação; o layout do Domínio continua provisório até homologação real.

Os detalhes e os links das fontes estão em [Premissas e decisões](/lastro-lancamentos/modelagem/decisoes/).

## Base documental

Foram considerados a modelagem de referência apresentada em PDF, o [escopo](/lastro-lancamentos/visao/escopo-mvp/), os [requisitos](/lastro-lancamentos/visao/requisitos/), a [arquitetura de dados](/lastro-lancamentos/arquitetura/dados/), as decisões de [arquitetura](/lastro-lancamentos/decisoes/arquitetura/), [banco](/lastro-lancamentos/decisoes/banco-de-dados/), [acesso e cadastro](/lastro-lancamentos/decisoes/acesso-e-cadastro/) e [processo](/lastro-lancamentos/decisoes/processo/), além dos metadados das fichas publicados no Pages.

:::note[Lacuna do registro de decisões]
`docs/decisoes/DECISIONS.md` está vazio no checkout analisado. Os status acima reproduzem as páginas de decisões existentes no Pages; não representam uma leitura de conteúdo desse arquivo. A reposição do registro central precisa ser conferida pelo projeto. `AGENTS.md` e `docs/SECURITY.md` também contêm referências anteriores às aprovações de 18/11. Essa divergência não altera o código nem autoriza novas decisões nesta modelagem.
:::
