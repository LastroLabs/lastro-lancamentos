---
title: Segurança e LGPD
description: Ameaças e controles, LGPD em três pontos e as regras do repositório público.
---

:::note[Status]
Aprovada em 18/11/2026 com a arquitetura e o banco (ARQ e BD, conforme `docs/decisoes/DECISIONS.md`). Complementa o `docs/SECURITY.md` do repositório, que prevalece em caso de divergência.
:::

O Lastro guarda extrato bancário de terceiros. O padrão de segurança é o de um sistema financeiro, desde o primeiro commit.

## Ameaças e controles

| Ameaça | Controle |
|---|---|
| Contador vê cliente de outro (ou de outro escritório) | Autorização no serviço e RLS forçado (`FORCE ROW LEVEL SECURITY`) em toda tabela de negócio. O papel da aplicação não é dono das tabelas nem `BYPASSRLS`. Teste automatizado de negação por endereço direto |
| Link do cliente vazado ou adivinhado | Token de 32 bytes aleatórios, só o hash no banco, validade e revogação (RF-SEG-01); limite de requisições por IP e por token; token fora dos logs e do cabeçalho Referer (`Referrer-Policy: no-referrer`) |
| Arquivo malicioso no upload | Tipo verificado pelo conteúdo, não pela extensão; limite de tamanho; quarentena; PDF lido sem executar nada embutido |
| Dado pessoal enviado ao LLM | `anonimizar()` remove CPF, CNPJ (numérico e alfanumérico), agência e conta (RF-SEG-03) e troca todo nome de contraparte por pseudônimo (D-03, aprovada em 18/11); teste que falha se algum desses padrões sair na requisição (fichas IA-01 e IA-02, em revisão) |
| Sessão roubada | Cookie `HttpOnly`, `Secure`, `SameSite=Lax`; rotação no login; expiração por inatividade; proteção CSRF nas rotas que alteram dados |
| Segredo no repositório público | `hx check-clean` local e no `pr.yml` a cada push e PR; chaves só em secrets |
| Perda de dados | Backup diário e restauração testada antes do piloto (RPO 24 h, RTO 4 h, proposta do estudo de banco) |

## Isolamento em duas camadas

1. **A aplicação autoriza a operação.** O servidor confere a atribuição vigente em toda requisição.
2. **O RLS restringe as linhas no banco.** O backend autenticado define o contexto de usuário e escritório por transação, com `SET LOCAL`, nunca por parâmetro vindo do navegador.

O RLS não substitui a segurança da API nem protege o armazenamento de objetos. Downloads passam sempre pela autorização do backend.

### O que a API responde quando recusa

Decisão P-01, aprovada em 18/11/2026 (`docs/decisoes/DECISIONS.md`, seção 4):

| Situação | Status |
|---|---|
| Sem sessão, ou com sessão encerrada | 401 |
| Com sessão, mas o papel não permite | 403 |
| Recurso de outra carteira, de outro escritório ou inexistente | 404, com corpo idêntico ao de um recurso inexistente, inclusive em rotas que alteram dados |

Assim ninguém descobre, pela resposta, que um cliente de outro escritório existe. A recusa por dado inválido (400 ou 422) ainda está pendente (P-13). Detalhes em [Decisão: acesso e cadastro](/lastro-lancamentos/decisoes/acesso-e-cadastro/).

| Quem | O que acessa |
|---|---|
| Chefe | Gere usuários, clientes e atribuições; é o único que cadastra cliente (P-02); vê todos os clientes do próprio escritório (D-09). Se o chefe edita cadastro e gera link sem estar atribuído ainda está pendente (P-09) |
| Contador | Só clientes com atribuição vigente; carteira individual, um responsável ativo por cliente (D-07 e D-09) |
| Cliente por link | Só envio e perguntas da competência autorizada |
| Worker | Tarefas com escopo de escritório e cliente; sem papel administrativo no banco |

## LGPD em três pontos

- **Papéis:** o escritório contábil é o controlador dos dados dos seus clientes e o Lastro atua como operador. Isso precisa estar no termo de uso com os escritórios-piloto antes de qualquer dado real.
- **Transferência internacional:** os provedores de LLM avaliados processam fora do Brasil. A Resolução CD/ANPD nº 19/2024 regula isso. Mesmo anonimizando, a recomendação é tratar como transferência e registrar a base no termo. O documento pede validar com quem orienta o projeto: o time não é de advogados.
- **Minimização e retenção:** ao LLM vai só a descrição anonimizada, o valor e as contas candidatas. Originais ficam 90 dias e logs técnicos 30 dias (proposta), até acordo com os pilotos.

## Repositório público

Nenhum extrato, CNPJ, CPF, nome de cliente ou de escritório entra no git.

- As fixtures são sintéticas.
- CPF e CNPJ de teste em arquivo versionado têm dígito verificador inválido. O `hx check-clean` trata número com dígito válido como possível dado real (`docs/SECURITY.md`).
- O CNPJ alfanumérico (padrão da Receita a partir de julho/2026) também precisa ser tratado: hoje o `hx check-clean` só reconhece CNPJ numérico.
- Os rótulos reais da contadora ficam em pasta privada do grupo, fora do repositório.
- Chamadas a LLM passam somente por `src/lastro/ia/`, depois de `anonimizar()`.
- Rodar `hx check-clean` antes do PR. Com `LASTRO_NOMES_PROIBIDOS` definida, ele também procura os nomes da lista.
- Recebeu um extrato real? Não entra no repositório. Descreva só a estrutura e gere uma fixture sintética equivalente.

:::note[Planejado]
- **Gerador de fixtures:** `hx fixtures build` ainda não existe. Vem da ficha **HAR-03** (em revisão), que gera CNPJs válidos só em tempo de execução, nunca em arquivo versionado.
- **CNPJ alfanumérico no `check-clean`:** vem da ficha **HAR-04** (em revisão).
- **Pasta `docs/bancos/`:** ainda não existe no repositório; nasce com a primeira ficha de leitura de banco.
:::

Fontes: Lastro — Arquitetura do Sistema, seção 8; Banco de dados para o Lastro v1.0, p. 6; Lastro: guia do harness v0.1; Fluxo de desenvolvimento do Lastro.
