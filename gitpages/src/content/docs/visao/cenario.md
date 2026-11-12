---
title: Cenário e dor dos contadores
description: O que o mercado mostra e o que os dois escritórios-piloto relataram.
---

A dor central é o **fechamento mensal**. O contador:

- gasta horas transformando extratos desorganizados em lançamentos;
- cobra o cliente várias vezes;
- só descobre o erro no fim.

A pesquisa de mercado e as duas entrevistas apontam para o mesmo lugar.

## O que o mercado mostra

| Evidência | Fonte | O que significa para o Lastro |
|---|---|---|
| 529.505 profissionais registrados e 97.836 organizações contábeis no país | CFC, abr/2025 | Mercado grande e pulverizado |
| 69% dos respondentes trabalham em escritórios com até 9 colaboradores e 15% são autônomos; 53% atendem até 50 CNPJs | Cora/Hibou, Radar Contábil, 641 respostas, set/2026 | O usuário típico é um escritório pequeno, sem equipe de TI: o produto precisa funcionar sem implantação |
| 86% têm MEIs e microempresas do Simples entre os principais clientes | Cora/Hibou, idem | Clientes com pouca organização financeira e extratos de bancos variados |
| A maior causa de retrabalho é a desorganização dos documentos enviados pelos clientes, seguida de mudanças na legislação | Martins e Sonaglio, Univali, 251 escritórios de SC | A coleta e a conferência do extrato doem mais que a classificação em si |
| 60% dos contadores não se sentem preparados para a Reforma Tributária; falta de tempo por processos manuais é o principal motivo para não ser consultivo | Omie, jul/2026 | O argumento de venda é o tempo liberado da conciliação |

A pesquisa da Omie é de um fornecedor de software e a da Univali é regional. Entram como sinal, não como medida exata.

## Os dois escritórios-piloto

As entrevistas de validação foram feitas em 02/11/2026 com um contador de cada escritório-piloto. Por regra do repositório público, os escritórios aparecem só como **Esc.1** e **Esc.2**, a mesma notação da coluna "Origem" dos requisitos.

O Banco de dados para o Lastro observa que a correspondência entre os participantes e "Esc.1/Esc.2" não é inteiramente consistente entre os arquivos de origem. Esta página segue a correspondência da Arquitetura do Sistema.

### Esc.1

- Fecha o mês dos clientes e importa os lançamentos no Domínio.
- Recebe extratos em PDF do Inter e do Banco do Brasil e lança tudo no plano de contas de cada cliente, mantido em planilha.
- O que não consegue identificar vai para uma conta transitória até o cliente explicar.
- Quando o extrato vem incompleto, o erro só aparece no fechamento, quando o saldo não bate.
- O cliente costuma responder às perguntas em 1 a 2 dias. Com opções prontas para tocar, esse prazo cai.
- Não espera de uma ferramenta o trabalho fiscal de parcelamentos e impostos (principal, juros e multa).

### Esc.2

- Também importa os lançamentos no Domínio.
- Cobra o mesmo cliente cerca de 3 vezes por mês até o extrato chegar. Muitas vezes o extrato chega sem o último dia do mês.
- Recebe foto e print do celular, não só PDF.
- Já desistiu de ferramentas que exigem cadastrar um layout de OFX por banco.
- A retirada de lucro dos sócios aparece no extrato como Pix com nome truncado e confunde a classificação.
- Só confia numa sugestão automática depois de cerca de 3 meses vendo-a acertar e exige que a planilha final "feche com o extrato".
- Disse que o cliente não leria um resumo mensal. Por isso o RF-REL-01 está em Won't.

### Em comum

Os dois relatam de 2 a 4 horas por fechamento de um cliente. Um deles estima que 65% das movimentações chegam sem identificação. São relatos de dois profissionais, não uma amostra: orientam o MVP, não prometem ganho.

## Da dor ao requisito

| Dor | Quem relatou | Resposta no Lastro |
|---|---|---|
| Extrato incompleto descoberto só no fechamento | Esc.1, Esc.2 | Conferência de saldo e de cobertura no envio (RF-VAL-01 a 04, RF-AVI-01) |
| Cobrar o cliente várias vezes | Esc.2 | Link de envio por cliente e mês e status na carteira (RF-ENV-01, RF-ENV-03, RF-PAI-01) |
| Cadastro de layout por banco | Esc.2 | Detecção automática de formato e OFX de qualquer banco (RF-LEI-01, RF-LEI-02) |
| Perguntas repetidas ao cliente | Esc.1 | Aprendizado por cliente e perguntas agrupadas, respondidas com um toque (RF-APR, RF-PER) |
| Desconfiança da automação | Esc.2 | Origem e confiança em cada sugestão; nada é exportado sem revisão (RF-CLA-06, RF-REV-04) |
| Retirada de sócio confundida com despesa | Esc.2 | Regra de sócio por prefixo de nome, marcada "a confirmar" (RF-CLA-02c) |
| Digitação no Domínio | Esc.1, Esc.2 | Planilha no layout de importação, conciliada com o extrato (RF-EXP-01, RF-EXP-03) |

Fonte: Lastro — Arquitetura do Sistema, seção 2.
