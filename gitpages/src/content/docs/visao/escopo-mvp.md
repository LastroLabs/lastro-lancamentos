---
title: Escopo do MVP
description: O que entra, o que fica fora e o que ainda depende de decisão.
---

O MVP são os **56 requisitos Must** da v0.2. Should entra se houver contorno manual e tempo. Could, só se sobrar tempo. Won't fica fora desta versão. A lista completa está em [Requisitos v0.2](/lastro-lancamentos/visao/requisitos/).

## O que entra

| Bloco | O MVP entrega | Requisitos |
|---|---|---|
| Acesso | Login individual, carteira por contador, papel de chefe, reatribuição com revogação imediata, isolamento por escritório | RF-AUT-01 a 04, RF-SEG-01 a 03 |
| Cadastro | Cliente, contas bancárias, plano de contas por planilha, conta transitória, sócios | RF-CAD-01 a 04, RF-CAD-06 |
| Envio | Link por cliente e mês, envio de PDF e OFX pelo celular, status, complemento | RF-ENV-01 a 04 |
| Leitura | Detecção de formato, OFX de qualquer banco, PDF digital de BB e Inter, período, sem duplicar | RF-LEI-01 a 05 |
| Conferência | Saldo por cálculo, linha a linha ou dia a dia, continuidade, cobertura do mês, bloqueio de reprovado | RF-VAL-01 a 05 |
| Avisos | Aviso ao cliente no envio, mensagens em português simples | RF-AVI-01, 02 |
| Classificação | Regras, transferência interna, sócio, histórico, parecidas, IA nas sobras, origem e confiança, limite, precedência | RF-CLA-01 a 07, 09, 10 |
| Maquininha (mínimo) | Crédito de adquirente como "recebimento de cartão", sem abrir as vendas | RF-MAQ-01 (depende de D-02) |
| Perguntas | Agrupadas por contraparte, resposta com um toque, "não sei", conversão em conta | RF-PER-01 a 05 |
| Aprendizado | Resposta aceita vira regra, correção vira aprendizado, separado por cliente | RF-APR-01 a 03 |
| Revisão | Três grupos, aceitar, trocar ou pendente, resultado da conferência, nada sai sem revisão | RF-REV-01 a 04 |
| Exportação | Planilha no layout do Domínio, pendentes na transitória, conciliação, opções por cliente | RF-EXP-01 a 04 |

## O que fica fora

- **Should:** foto e print (D-01), importação de meses anteriores, carteira em tela única, resposta parcial, ordenação por confiança, edição de regras, arquivos originais, observabilidade, histórico de atribuições, parcelamento, métricas do piloto.
- **Could:** CSV, mensagem de cobrança pronta, alerta de duplicado, aviso interno, parecidas na tela, exportação em CSV.
- **Won't:** relatório e conciliação de maquininha, lembretes automáticos, resumo mensal, outros sistemas contábeis, impostos e parcelamentos, Open Finance, chatbot, cobrança interna, consultoria, informais, tributação.

O estudo de banco de dados resume o mesmo recorte: Must são PDF digital de BB e Inter, OFX, conferência determinística, classificação em camadas, perguntas, revisão e exportação. Foto/OCR é Should, CSV é Could e o terceiro banco fica em D-04.

## O que depende de decisão

| Decisão | Afeta no MVP |
|---|---|
| D-02 | Se a regra mínima de maquininha (RF-MAQ-01) entra |
| D-04 | Qual é o terceiro banco de PDF |
| D-05 | O layout exato da planilha do Domínio; bloqueia a exportação final |
| D-06 | Tamanho máximo de arquivo e validade do link |
| D-03, D-07, D-08, D-09 | Nomes enviados à IA, carteira compartilhada, limite de confiança, papel do chefe |

Detalhes no [índice de decisões](/lastro-lancamentos/decisoes/).

## Valores a definir

Os requisitos marcam com **[definir]** os valores ainda abertos:

| Requisito | O que falta definir |
|---|---|
| RF-SEG-01 | Prazo de validade do link |
| RF-ENV-02 | Tamanho máximo de arquivo |
| RF-CLA-06 | Critérios de cada nível de confiança |
| RF-CLA-07 | Limite inicial de confiança, com dados do piloto |
| RF-CLA-09 | Ordem de precedência das regras |
| RF-LEI-06 (Should) | Taxa mínima de leitura de foto |
| RF-OBS-02 (Should) | Metas das métricas do piloto |
| RF-CLA-08 (Could) | Limite de "valor alto" |

Fontes: Requisitos funcionais v0.2; Banco de dados para o Lastro v1.0, p. 2.
