---
title: Equipe
description: Papéis do fluxo de desenvolvimento, frentes da arquitetura e a proposta de quem assume cada um.
---

Sete pessoas, todas escrevendo código. Cada pessoa tem uma **frente** (onde codifica) e algumas têm também um **papel do fluxo** (que tipo de decisão é dela).

## Proposta de equipe

:::caution[Proposta]
Esta divisão é uma proposta e será confirmada no planejamento de segunda. Quem assume cada papel continua como pendência no [índice de decisões](/lastro-lancamentos/decisoes/#pendências-em-aberto-sem-id).
:::

| Nome | Papel no time | Frente | Papel do fluxo | Suplente de | GitHub |
|---|---|---|---|---|---|
| Júlia Santana Campos | Líder e Tech Lead | Coordenação técnica | Líder | F4b IA | [camposs04](https://github.com/camposs04) |
| Caio Nascimento | Vice-líder | Classificação/IA | F4b IA | Líder | |
| Arthur Leite | Desenvolvedor | Plataforma | B Contratos | — | |
| Thomaz Martins | Desenvolvedor | Plataforma | G Gabarito/E2E | B Contratos | |
| Guilherme Pereira | Desenvolvedor | Frontend | Front | — | |
| Raissa Oliveira | Desenvolvedora | Frontend | A Processo | Front | |
| João Sauma | Desenvolvedor | Leitura de bancos | — | A Processo | |

## Os seis papéis do fluxo

Papel não é cargo nem tempo fora do código. É ser **dono de um tipo de decisão**, com cerca de 1,5 a 2 horas por semana além do desenvolvimento. Cada papel tem um suplente.

| Papel | Nome | O que faz | O que decide |
|---|---|---|---|
| Líder | Produto e pilotos | Prioriza o que entra na demo e decide as perguntas de negócio (D-xx) | Guardião de dados: nada real entra no repositório |
| A | Processo | Cuida do `harness.py`, da CI, do `AGENTS.md` e da rotina noturna | As regras do processo |
| B | Contratos | Define e congela as entradas e saídas entre módulos (Pydantic e OpenAPI) | O formato dos dados que circulam |
| G | Gabarito e E2E | Gerador de extratos sintéticos, defeitos plantados e as jornadas J1 a J3 | O que é a resposta certa nos testes |
| Front | Interface | Telas de revisão em três grupos e perguntas ao cliente | A experiência do contador |
| F4b | IA | Classificação com LLM, justificativa e confiança, conjunto de avaliação e a pasta `ia/` | Prompts, modelo e custo |

**Cuidado na escolha:** quem tem só 5 h por semana não deve assumir A, B, G ou Líder. São os papéis que mais travam os outros quando atrasam.

## As frentes da arquitetura

Cada pessoa é dona de módulos. Todo mundo trabalha full stack quando a sua feature precisa de tela.

| Frente | Módulos que possui | Entregas Must principais |
|---|---|---|
| Plataforma e arquitetura | `nucleo`, `acesso`, `cadastro`, `envio`, `revisao` (back), `exportacao`, `migrations/`, infra e CI | Sessão, RLS, reatribuição (RF-AUT, RF-SEG), cadastro (RF-CAD), link e upload (RF-ENV), revisão e exportação Domínio (RF-REV, RF-EXP), Docker, deploy, backups |
| Frontend | `web/` | Uma pessoa na área do contador (carteira, cadastro, revisão, exportação); outra na página do cliente no celular (envio, avisos, perguntas) e no design system (Tailwind + shadcn, fonte Inter) |
| Leitura e conferência (bancos) | `leitura`, `validacao`, `docs/bancos/`, `fixtures/` | Detecção de formato, OFX de qualquer banco, PDF de BB e Inter, conferência de saldo e cobertura (RF-LEI, RF-VAL) |
| Classificação e IA | `classificacao`, `perguntas` (back), `ia` | Regras, histórico, parecidas, gateway de IA com `anonimizar()`, agrupamento de perguntas, aprendizado (RF-CLA, RF-PER, RF-APR) e a avaliação do estudo de LLM |

Não vale a pena ter alguém só para banco de dados: o esquema muda junto com cada módulo. Cada dono escreve a migração do seu módulo e a dupla de plataforma revisa todas.

### Duas versões do tamanho do time

| Fonte | Tamanho | Divisão |
|---|---|---|
| Fluxo de desenvolvimento (estratégia vigente) | 7 pessoas | Seis papéis distribuídos entre as sete, como na proposta acima |
| Lastro — Arquitetura do Sistema | 6 pessoas | 2 em plataforma, 2 no frontend, 1 em leitura de bancos e 1 em classificação/IA. Com 7, a sétima iria para leitura de bancos, que é o maior risco técnico do MVP |

### Papéis que se acumulam, segundo a Arquitetura

| Papel | Quem, segundo a Arquitetura | Carga |
|---|---|---|
| Donos do harness (`AGENTS.md`, `harness.py`, `noturno.yml`) | A dupla de plataforma | Contínua, baixa |
| Líder de produto (fala com os pilotos, fecha as D-xx) | Quem o grupo indicar; sugestão: alguém fora da plataforma | 2 a 3 h por semana |
| Guardião de dados (`SECURITY.md`, `check-clean`) | Um da dupla de plataforma | Revisa PR que toca dado ou IA |
| Revisor de PR | Todos, em rodízio, pela rubrica de 6 itens | Todo PR tem revisor de outra frente |

Na proposta acima, o papel A (Processo) fica com o Frontend, e não com a dupla de plataforma como sugere a Arquitetura. A confirmação é do planejamento de segunda.

Fontes: Fluxo de desenvolvimento do Lastro, seção 02; Lastro — Arquitetura do Sistema, seção 9; proposta de equipe da liderança (12/11/2026).
