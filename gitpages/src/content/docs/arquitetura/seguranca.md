---
title: Segurança e LGPD
description: Ameaças e controles, LGPD em três pontos e as regras do repositório público.
---

:::note[Status]
Recomendada, aguardando aprovação. Complementa o `docs/SECURITY.md` do repositório.
:::

O Lastro guarda extrato bancário de terceiros. O padrão de segurança é o de um sistema financeiro, desde o primeiro commit.

## Ameaças e controles

| Ameaça | Controle |
|---|---|
| Contador vê cliente de outro (ou de outro escritório) | Autorização no serviço e RLS forçado (`FORCE ROW LEVEL SECURITY`) em toda tabela de negócio. O papel da aplicação não é dono das tabelas nem `BYPASSRLS`. Teste automatizado de negação por endereço direto |
| Link do cliente vazado ou adivinhado | Token de 32 bytes aleatórios, só o hash no banco, validade e revogação (RF-SEG-01); limite de requisições por IP e por token; token fora dos logs e do cabeçalho Referer (`Referrer-Policy: no-referrer`) |
| Arquivo malicioso no upload | Tipo verificado pelo conteúdo, não pela extensão; limite de tamanho; quarentena; PDF lido sem executar nada embutido |
| Dado pessoal enviado ao LLM | `anonimizar()` remove CPF, CNPJ, agência e conta (RF-SEG-03) e, até D-03, troca nomes por pseudônimos; teste que falha se algum desses padrões sair na requisição |
| Sessão roubada | Cookie `HttpOnly`, `Secure`, `SameSite=Lax`; rotação no login; expiração por inatividade; proteção CSRF nas rotas que alteram dados |
| Segredo no repositório público | `harness.py check-clean` e varredura de segredos no CI; chaves só em secrets |
| Perda de dados | Backup diário e restauração testada antes do piloto (RPO 24 h, RTO 4 h, proposta do estudo de banco) |

## Isolamento em duas camadas

1. **A aplicação autoriza a operação.** O servidor confere a atribuição vigente em toda requisição.
2. **O RLS restringe as linhas no banco.** O backend autenticado define o contexto de usuário e escritório por transação, com `SET LOCAL`, nunca por parâmetro vindo do navegador.

O RLS não substitui a segurança da API nem protege o armazenamento de objetos. Downloads passam sempre pela autorização do backend.

| Quem | O que acessa |
|---|---|
| Chefe | Gere usuários, clientes e atribuições; vê a carteira do próprio escritório. Até D-09, revisão e exportação exigem atribuição explícita, inclusive para o chefe |
| Contador | Só clientes com atribuição vigente |
| Cliente por link | Só envio e perguntas da competência autorizada |
| Worker | Tarefas com escopo de escritório e cliente; sem papel administrativo no banco |

## LGPD em três pontos

- **Papéis:** o escritório contábil é o controlador dos dados dos seus clientes e o Lastro atua como operador. Isso precisa estar no termo de uso com os escritórios-piloto antes de qualquer dado real.
- **Transferência internacional:** os provedores de LLM avaliados processam fora do Brasil. A Resolução CD/ANPD nº 19/2024 regula isso. Mesmo anonimizando, a recomendação é tratar como transferência e registrar a base no termo. O documento pede validar com quem orienta o projeto: o time não é de advogados.
- **Minimização e retenção:** ao LLM vai só a descrição anonimizada, o valor e as contas candidatas. Originais ficam 90 dias e logs técnicos 30 dias (proposta), até acordo com os pilotos.

## Repositório público

Nenhum extrato, CNPJ, CPF, nome de cliente ou de escritório entra no git.

- As fixtures são sintéticas e geradas com `harness.py fixtures build`.
- Os rótulos reais da contadora ficam em pasta privada do grupo, fora do repositório.
- Chamadas a LLM passam somente por `src/lastro/ia/`, depois de `anonimizar()`.
- Rodar `harness.py check-clean` antes do PR.
- Recebeu um extrato real? Descreva só a estrutura em `docs/bancos/` e gere uma fixture sintética equivalente.

Fontes: Lastro — Arquitetura do Sistema, seção 8; Banco de dados para o Lastro v1.0, p. 6; Lastro: guia do harness v0.1; Fluxo de desenvolvimento do Lastro.
