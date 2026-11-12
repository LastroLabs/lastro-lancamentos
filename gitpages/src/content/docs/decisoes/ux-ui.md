---
title: "Decisão: UX/UI"
description: Insights da análise comparativa de interfaces para o design do Lastro.
---

| Status | Data | Fonte |
|---|---|---|
| Recomendada, aguardando aprovação | Sem data no documento | Estudo de UX/UI – Lastro |

## Contexto

O usuário típico é um escritório pequeno, sem equipe de TI, e o cliente responde pelo celular. O estudo analisou a interface de cinco produtos do mercado contábil para tirar lições de legibilidade, clareza e organização.

## Decisão

Síntese de insights do estudo para o Lastro:

- **Tipografia e legibilidade:** manter a fonte Inter como padrão do sistema, pela legibilidade e pelo aspecto profissional.
- **Clareza e simplicidade:** visual limpo, com pouca poluição, evitando a sobrecarga de chamadas para ação.
- **Organização visual:** cards e boxes com bom espaçamento e bordas arredondadas para destacar as funcionalidades.
- **Responsividade e contraste:** contraste acessível e layouts totalmente responsivos no celular e no desktop.

## Alternativas consideradas

O estudo comparou cinco produtos. O que serviu de exemplo e o que evitar:

| Produto analisado | Seguir | Evitar |
|---|---|---|
| Conciliador Contábil | Fonte Inter, disposição limpa, botões fáceis de tocar, bordas arredondadas, navegação simples | Poucos pontos fracos evidentes |
| SS Parisi Software | Estrutura clara da seção de soluções | Falta de responsividade, mensagens sobre imagens de fundo, poluição visual |
| Nibo | Design profissional e boa organização dos blocos | Paleta pouco marcante, excesso de prova social |
| Sistema Domínio | Cards interativos, formulário de contato claro | Sobrecarga de dados, imagens genéricas, textos longos e repetitivos |
| Conta Azul | Seções por funcionalidade, identidade visual coesa, boa tipografia | Excesso de elementos e de chamadas para ação competindo entre si |

## Consequências

**Destrava:**

- o design system do frontend: Tailwind CSS 4 com componentes shadcn/ui e fonte Inter, já adotados na stack recomendada pela Arquitetura;
- as duas entradas do app: área do contador (desktop primeiro) e página do cliente (celular primeiro).

**Custa:**

- O estudo analisa principalmente páginas iniciais e sites institucionais, não telas de trabalho como a revisão.
- A experiência do contador na revisão ainda precisa ser validada com a contadora. O roteiro da Arquitetura prevê ajustes de usabilidade com ela na semana 4,5.

## Pendências ligadas

| Pendência | Relação |
|---|---|
| React ou Vue (sem ID) | O design system depende da biblioteca de UI; a Arquitetura recomenda React |
| RF-AVI-02 | Mensagens em português simples, sem termos técnicos: validar a lista com uma contadora |
| RF-PER-02 | Perguntas respondidas com um toque, no celular |

**Fonte:** Estudo de UX/UI – Lastro (análise comparativa e síntese de insights).
