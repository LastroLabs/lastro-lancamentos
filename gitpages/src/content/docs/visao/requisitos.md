---
title: Requisitos v0.2
description: Requisitos funcionais do Lastro por prioridade (MoSCoW), versão 0.2 de 07/11/2026.
---

Fonte: **Requisitos funcionais v0.2, 07/11/2026**. É a fonte de verdade do escopo. Esta página reproduz o documento; qualquer mudança começa nele.

- **Selos:** NOVO e AJUSTADO marcam o que mudou na v0.2.
- **Origem:** v2 (proposta v2), Esc.1 e Esc.2 (escritórios-piloto), Ata, Proposta e Equipe, como estão no documento.
- **[definir]:** valor ainda aberto. A lista está em [Escopo do MVP](/lastro-lancamentos/visao/escopo-mvp/#valores-a-definir).
- **Decisões em aberto:** D-01 a D-09 estão no [índice de decisões](/lastro-lancamentos/decisoes/).

| Prioridade | Significado | Quantidade |
|---|---|---|
| Must | Sem isso o MVP não funciona | 56 |
| Should | Importante, com contorno manual | 11 |
| Could | Só se sobrar tempo | 6 |
| Won't | Fora desta versão | 12 |

## Must

### Acesso e segurança

| ID | Requisito | Critério de aceitação | Origem |
|---|---|---|---|
| RF-AUT-01 | O sistema deve permitir que cada contador acesse com login individual. | Dois contadores do mesmo escritório entram com credenciais diferentes e o sistema identifica quem fez cada ação. | v2, Esc.1 |
| RF-AUT-02 (AJUSTADO) | O sistema deve mostrar a cada contador apenas os clientes atribuídos a ele, e ao chefe todos os clientes do escritório, aplicando essa regra no servidor em toda requisição. | O contador A não vê, nem por endereço direto, clientes atribuídos só ao contador B. O chefe vê todos os clientes do escritório e nenhum de outro escritório. | v2, Equipe |
| RF-AUT-03 (NOVO) | O sistema deve ter o papel de chefe, que cadastra contadores e clientes e atribui clientes a contadores. | Um usuário chefe cria um contador, cria um cliente e atribui o cliente a esse contador. Um contador sem o papel de chefe não vê essas ações. | Equipe |
| RF-AUT-04 (NOVO) | O sistema deve encerrar o acesso do contador anterior e conceder o acesso ao novo, imediatamente, quando o chefe reatribuir um cliente. | Depois de trocar as empresas 1 e 2 entre os contadores A e B, A recebe "sem acesso" ao abrir a empresa 1, mesmo com sessão aberta e por endereço direto, e B abre a empresa 1 sem novo login. Dados e aprendizado do cliente permanecem com o cliente. | Equipe |
| RF-SEG-01 | O sistema deve gerar o link do cliente com um código imprevisível e com validade, e permitir que o contador o invalide. | Link expirado ou invalidado mostra mensagem de link inválido e não dá acesso a nenhum dado. O prazo de validade fica em configuração [definir]. | Proposta, v2 |
| RF-SEG-02 | O sistema deve isolar os dados de cada escritório. | Um usuário de um escritório não consegue ler dados de outro escritório por nenhuma tela nem endereço. | Proposta |
| RF-SEG-03 | O sistema deve remover CPF, CNPJ e números de agência e conta das descrições antes de enviá-las a um serviço externo de IA. | Teste com extratos que contêm esses dados: a requisição enviada ao serviço de IA não contém nenhum deles. Ver decisão D-03 sobre nomes. | v2 (riscos, regras do harness) |

### Cadastro

| ID | Requisito | Critério de aceitação | Origem |
|---|---|---|---|
| RF-CAD-01 | O contador deve poder cadastrar um cliente com nome e CNPJ. | O cliente aparece na carteira do contador depois de salvo. | v2 (F04) |
| RF-CAD-02 | O contador deve poder informar os bancos (e as contas) do cliente. | O cliente guarda uma ou mais contas, cada uma com banco e apelido. | v2 (passo 1) |
| RF-CAD-03 | O contador deve poder carregar o plano de contas do cliente por planilha. | O plano de contas do piloto é carregado com código e nome de cada conta. Linha inválida é rejeitada com a linha indicada. | Esc.1, v2 |
| RF-CAD-04 | O contador deve poder indicar qual conta do plano é a conta transitória do cliente. | A conta escolhida precisa existir no plano. Sem ela, o sistema não permite exportar. | Esc.1, Esc.2, v2 |
| RF-CAD-06 (NOVO) | O contador deve poder cadastrar os sócios do cliente (nome). | Os sócios aparecem na ficha do cliente e são usados pela regra RF-CLA-02c. | Esc.2 (retirada de lucro), Proposta |

### Envio e coleta

| ID | Requisito | Critério de aceitação | Origem |
|---|---|---|---|
| RF-ENV-01 | O contador deve poder gerar um link de envio para um cliente e um mês. | O link abre uma página de envio, no celular, sem pedir login, ligada ao cliente e ao mês escolhidos. | v2 (passo 2), Ata |
| RF-ENV-02 | O cliente deve poder enviar um ou mais arquivos PDF ou OFX pelo link. | Dois PDFs escolhidos no celular são aceitos numa única ação. Arquivo de outro tipo é recusado com mensagem. Tamanho máximo [definir]. | v2 (passo 3), Esc.1 |
| RF-ENV-03 | O sistema deve mostrar ao contador, por cliente e mês, se o extrato foi enviado (não enviado, parcial, enviado). | Antes do envio o status é "não enviado". Depois do primeiro arquivo, "parcial" ou "enviado", conforme a conferência de cobertura do mês. | Esc.2 (cobra cerca de 3 vezes), v2 |
| RF-ENV-04 | O cliente deve poder enviar um arquivo complementar quando o sistema avisar que falta algo, e o sistema deve refazer a conferência. | Após o envio de um arquivo que cobre o trecho faltante, o aviso desaparece e o status muda. | Proposta |

### Leitura

| ID | Requisito | Critério de aceitação | Origem |
|---|---|---|---|
| RF-LEI-01 | O sistema deve detectar sozinho o formato do arquivo (OFX ou PDF digital), sem o usuário escolher configuração. | Os arquivos do gabarito são reconhecidos sem nenhuma seleção manual. Formato não suportado gera aviso (ver RF-AVI-02). | v2, Esc.2 |
| RF-LEI-02 | O sistema deve ler OFX de qualquer banco, sem cadastro prévio por banco. | Em cada OFX do gabarito, o número de movimentações lidas é igual ao número de transações do arquivo e data, valor e descrição de cada uma batem. | v2, Esc.2 (reclama do cadastro por OFX) |
| RF-LEI-03 | O sistema deve ler PDF digital de extrato do Inter e do Banco do Brasil. | Em cada PDF do gabarito, as movimentações lidas (data, descrição, valor) coincidem 100% com o gabarito. Ver decisão D-04 sobre o terceiro banco. | v2, Esc.1, Esc.2 |
| RF-LEI-04 | O sistema deve identificar o banco e o período coberto por cada arquivo lido. | O período identificado (primeira e última data) aparece na tela e é usado pela conferência de cobertura (RF-VAL-04). | Proposta |
| RF-LEI-05 | O sistema deve evitar movimentações duplicadas quando o mesmo período é enviado mais de uma vez. | Reenviar o mesmo extrato não duplica linhas quando a transação tem identificador. Sem identificador, linhas idênticas no mesmo dia não são removidas e o sistema avisa o contador. | Proposta |

### Conferência de valores

| ID | Requisito | Critério de aceitação | Origem |
|---|---|---|---|
| RF-VAL-01 | O sistema deve conferir se saldo inicial mais a soma das movimentações é igual ao saldo final, por cálculo em código, sem usar IA. | Um extrato íntegro passa. O mesmo extrato com uma linha removida, um valor alterado ou um sinal invertido falha. | v2, Esc.1 (erro só aparece no fechamento) |
| RF-VAL-02 | O sistema deve conferir o saldo no nível mais fino que o extrato permitir (linha a linha, senão dia a dia). | Em extrato com saldo por linha, a linha onde o saldo deixa de fechar é indicada. Em extrato só com saldo diário, o dia é indicado. | Proposta |
| RF-VAL-03 | O sistema deve conferir se o saldo inicial do mês é igual ao saldo final do mês anterior da mesma conta, quando o mês anterior já estiver no sistema. | Mês que começa com saldo diferente do final do anterior gera aviso com os dois valores. | v2 (passo 4) |
| RF-VAL-04 | O sistema deve avisar quando o período do extrato não vai até o último dia do mês. | Extrato que termina antes do último dia do mês gera aviso indicando a última data presente. | Esc.2 (falta o último dia) |
| RF-VAL-05 | O sistema não deve incluir na exportação as movimentações de um extrato reprovado na conferência sem confirmação explícita do contador. | Extrato reprovado fica bloqueado para exportação. O contador pode liberar escolhendo uma ação que fica registrada. | Proposta, v2 |

### Avisos

| ID | Requisito | Critério de aceitação | Origem |
|---|---|---|---|
| RF-AVI-01 | O sistema deve avisar o cliente, no momento do envio, quando a conferência falhar ou faltar período, dizendo o que falta. | Após enviar um extrato com saldo inicial diferente do final anterior, a tela mostra os dois valores e o que fazer (exemplo: "Outubro começa em R$ 7.900, mas setembro terminou em R$ 8.200. Falta alguma coisa."). | v2 (passo 4) |
| RF-AVI-02 | O sistema deve escrever todas as mensagens de erro e aviso em português simples, sem termos técnicos. | Uma contadora lê a lista completa de mensagens e não encontra termo que não entenda. Cada mensagem diz o que aconteceu e o que fazer. | v2 |

### Classificação

| ID | Requisito | Critério de aceitação | Origem |
|---|---|---|---|
| RF-CLA-01 | O sistema deve sugerir, para cada movimentação, apenas uma conta existente no plano de contas do cliente, ou "não sei". | Em teste com todo o gabarito, nenhuma sugestão fica fora do plano de contas. | v2 (passo 5) |
| RF-CLA-02a (NOVO) | O sistema deve classificar por palavra-chave as movimentações de tarifa bancária, IOF, impostos e encargos (DAS, DARF, GPS, FGTS) e aplicação ou resgate, usando a conta de destino configurada para o cliente. | Cada tipo tem uma lista de palavras-chave e uma conta de destino por cliente. Movimentação que casa recebe a conta e a origem "regra". Cobertura das palavras-chave validada no gabarito. | Esc.1, Esc.2, Proposta |
| RF-CLA-02b (NOVO) | O sistema deve classificar como transferência entre contas próprias a movimentação que corresponde a uma conta cadastrada do mesmo cliente. | Uma saída e uma entrada de mesmo valor e mesma data entre duas contas do cliente são marcadas como transferência interna, sem contar como receita nem despesa. Pix para terceiro não é marcado. | Proposta |
| RF-CLA-02c (NOVO) | O sistema deve classificar como movimento de sócio a movimentação cuja contraparte coincide, inclusive por prefixo do nome, com um sócio cadastrado, distinguindo saída de entrada. | Nome truncado no extrato casa com o sócio cadastrado. Saída recebe a conta padrão de retiradas e entrada recebe a conta padrão de aporte ou empréstimo de sócio, ambas configuráveis e marcadas "a confirmar pelo contador". Entrada de sócio nunca entra como receita. | Esc.2 (retirada de lucro), Proposta |
| RF-CLA-03 | O sistema deve usar o histórico do cliente: uma contraparte já classificada antes recebe a mesma conta. | Movimentação cuja contraparte (texto normalizado) já foi aceita pelo contador antes sai com a mesma conta e a origem "histórico". | v2 (passo 5) |
| RF-CLA-04 | O sistema deve sugerir conta com base em movimentações parecidas do mesmo cliente quando não houver correspondência exata. | Em teste com descrições do gabarito que variam (números, datas), a sugestão aponta para a conta das parecidas e a origem é "parecidas". | v2 |
| RF-CLA-05 | O sistema deve usar IA para sugerir conta apenas nas movimentações que as regras, o histórico e as parecidas não resolveram. | O registro de cada extrato mostra que nenhuma movimentação já resolvida por regra ou histórico foi enviada à IA. | v2, Proposta |
| RF-CLA-06 | O sistema deve registrar e mostrar, em cada sugestão, o motivo (origem) e o nível de confiança (alta, média, baixa). | Toda sugestão exibe origem e confiança na revisão. Os critérios de cada nível ficam documentados [definir]. | v2, Esc.2 (confia após cerca de 3 meses) |
| RF-CLA-07 | O sistema não deve aplicar sugestão cuja confiança esteja abaixo do limite, e deve transformá-la em pergunta ao cliente. | Movimentação abaixo do limite não recebe conta e aparece nas perguntas. O limite inicial é [definir] com dados do piloto. | v2, Proposta |
| RF-CLA-09 (NOVO) | O sistema deve seguir uma ordem de precedência quando mais de uma regra casar com a mesma movimentação. | Com duas regras que casam, vence a de maior precedência e o motivo mostra qual regra foi usada. A ordem fica documentada [definir]. | Proposta |
| RF-CLA-10 (NOVO) | O sistema deve passar a movimentação para a camada seguinte da classificação quando o tipo for reconhecido mas o cliente não tiver conta configurada para ele. | Movimentação de tipo sem conta configurada segue para histórico, parecidas e IA, e o contador vê um aviso de que falta configurar a conta. | Proposta |

### Maquininha (mínimo)

| ID | Requisito | Critério de aceitação | Origem |
|---|---|---|---|
| RF-MAQ-01 | O sistema deve reconhecer créditos de adquirentes (Cielo, Stone, Getnet, Rede, PagBank, Mercado Pago) e classificá-los como "recebimento de cartão", sem abrir as vendas. | Créditos com o nome de uma adquirente recebem a conta configurada para cartão e não viram pergunta ao cliente. | Proposta (a v2 deixa a maquininha toda fora; ver D-02), Esc.1, Esc.2 |

### Perguntas ao cliente

| ID | Requisito | Critério de aceitação | Origem |
|---|---|---|---|
| RF-PER-01 | O sistema deve agrupar as movimentações sem classificação por contraparte e gerar uma pergunta por grupo. | Sete movimentações com a mesma contraparte geram uma única pergunta que lista as sete. | v2 (passo 6), Proposta |
| RF-PER-02 | O cliente deve poder responder cada pergunta escolhendo uma opção em uma lista, com um toque, ou escrever um texto livre na opção "outro". | Cada pergunta tem opções predefinidas (por exemplo fornecedor, retirada pessoal, funcionário, outro). Escolher uma opção registra a resposta sem passo extra. | v2 (passo 6), Esc.1 (resposta em 1 a 2 dias) |
| RF-PER-03 | O sistema deve mostrar, em cada pergunta, a data, o valor e a descrição de cada movimentação do grupo. | A pergunta exibe todas as linhas do grupo com esses três campos. | v2 |
| RF-PER-04 | O cliente deve poder responder "não sei", e a movimentação deve continuar pendente. | Resposta "não sei" não gera sugestão de conta e mantém a movimentação como pendente. | Proposta |
| RF-PER-05 | O sistema deve transformar a resposta do cliente em uma conta sugerida, marcada como "confirmada pelo cliente", para o contador revisar. | A resposta escolhida é convertida em conta por um mapeamento configurável pelo contador. O resultado aparece na revisão no grupo "confirmadas pelo cliente". | v2 (passos 6 e 8) |

### Aprendizado

| ID | Requisito | Critério de aceitação | Origem |
|---|---|---|---|
| RF-APR-01 | O sistema deve registrar como regra do cliente a resposta do cliente depois que o contador a aceitar. | No mês seguinte, a mesma contraparte vem classificada com a origem "histórico". | v2 (passo 7) |
| RF-APR-02 | O sistema deve registrar como aprendizado a correção feita pelo contador, substituindo a sugestão anterior. | Após o contador trocar a conta de uma contraparte, a próxima ocorrência usa a nova conta. | v2 (passo 8) |
| RF-APR-03 | O sistema deve manter o aprendizado separado por cliente. | Uma regra aprendida num cliente não altera a sugestão de outro cliente nem de outro escritório. | v2, Proposta |

### Revisão

| ID | Requisito | Critério de aceitação | Origem |
|---|---|---|---|
| RF-REV-01 | O sistema deve mostrar ao contador as movimentações do mês em três grupos: prontas, confirmadas pelo cliente e pendentes. | Cada movimentação está em exatamente um grupo, e o total de cada grupo aparece na tela. | v2 (passo 8) |
| RF-REV-02 | O contador deve poder, em cada movimentação, aceitar a sugestão, trocar a conta ou marcá-la como pendente, e aceitar um grupo inteiro de uma vez. | Cada ação muda o estado da movimentação e fica registrada com data e usuário. "Aceitar grupo" afeta apenas o grupo visível. | v2 |
| RF-REV-03 | O sistema deve mostrar na revisão o resultado da conferência de saldo do extrato. | A tela de revisão mostra aprovado ou reprovado e, se reprovado, o motivo (RF-VAL). | Proposta |
| RF-REV-04 | O sistema não deve exportar uma movimentação que não tenha sido revisada pelo contador, exceto as pendentes, que saem na conta transitória. | Movimentação não revisada e não pendente impede a exportação, com aviso de quantas faltam. | v2 ("nada importa sem revisão") |

### Exportação

| ID | Requisito | Critério de aceitação | Origem |
|---|---|---|---|
| RF-EXP-01 | O sistema deve gerar uma planilha Excel no layout de importação do Domínio, com número do documento, fornecedor, valor, data, cliente e a conta. | Uma planilha gerada a partir de um extrato do piloto é importada no Domínio por uma contadora sem erro e sem edição manual. Layout exato em D-05. | Esc.1, Esc.2, v2 |
| RF-EXP-02 | O sistema deve exportar as movimentações pendentes na conta transitória do cliente, identificadas como pendentes. | Toda pendente aparece na planilha na conta transitória e com marca que a diferencia das demais. | Esc.1, Esc.2, v2 |
| RF-EXP-03 | O sistema deve garantir que a planilha concilia com o extrato. | Antes do download, o sistema mostra a quantidade de linhas e o total de entradas e saídas exportados, e eles são iguais aos do extrato. | Esc.2 ("tudo conferindo com o extrato") |
| RF-EXP-04 (AJUSTADO) | O contador deve poder salvar as opções de exportação por cliente, e elas devem permanecer com o cliente quando o responsável mudar. | Uma opção salva (por exemplo conta do banco e conta transitória) é reaplicada na exportação seguinte. Após reatribuir o cliente, o novo contador exporta com as opções já salvas, sem reconfigurar. | v2, Equipe |

## Should

| ID | Requisito | Critério de aceitação | Origem |
|---|---|---|---|
| RF-LEI-06 | O sistema deve ler foto e print de extrato, marcando as movimentações como de baixa confiança e exigindo a conferência de saldo. Sujeito à decisão D-01. | Em fotos do gabarito, o sistema extrai as linhas e a conferência de saldo detecta as leituras com valor errado. Taxa mínima de leitura [definir]. | Esc.2, v2 |
| RF-CAD-05 | O contador deve poder importar lançamentos de meses anteriores do cliente para alimentar a classificação. | Depois de importar os lançamentos de um cliente do piloto, movimentações já conhecidas saem classificadas com origem "histórico" já no primeiro mês. | v2 (passo 1), Esc.2 (confiança leva cerca de 3 meses) |
| RF-PAI-01 | O contador deve poder ver a carteira em uma tela única, com o status de cada cliente (sem envio, parcial, perguntas abertas, em revisão, exportado). | A lista mostra um status por cliente e permite filtrar por status. | Esc.2 (cobra cerca de 3 vezes), v2 |
| RF-PER-06 | O cliente deve poder responder parte das perguntas e continuar depois, pelo mesmo link. | As respostas dadas ficam salvas. Reabrir o link mostra só as perguntas restantes. | Proposta |
| RF-REV-05 | O sistema deve permitir ordenar as movimentações da revisão pela menor confiança. | A lista pode ser ordenada, e as de confiança baixa aparecem primeiro. | Proposta, Esc.2 |
| RF-REG-01 | O contador deve poder ver, editar e desativar as regras aprendidas e criar regras manuais por palavra-chave. | Regra desativada deixa de ser usada na próxima classificação. Regra manual criada é aplicada em seguida. | Proposta |
| RF-DOC-01 | O sistema deve guardar os arquivos originais enviados e listá-los por cliente e mês. | O contador baixa o arquivo original de qualquer envio a partir da lista do cliente. | Ata (bloco 5) |
| RF-OBS-01 | O sistema deve registrar, para cada extrato processado, o formato detectado, o leitor usado, o saldo calculado contra o informado, a confiança e o motivo de cada sugestão, as chamadas à IA e o tempo gasto. | Para um extrato processado, o registro permite reconstruir cada decisão do sistema. | v2 (observabilidade) |
| RF-AUT-05 (NOVO) | O sistema deve guardar o histórico de atribuições de cada cliente (contador responsável, início e fim). | Após duas reatribuições, o histórico lista os três responsáveis com as datas. | Equipe, Proposta |
| RF-CLA-02d (NOVO) | O sistema deve marcar como "possível parcelamento, a confirmar" a movimentação com sinal de parcela (texto como "PARC" ou "n/m") ou com valor igual repetido todo mês para a mesma contraparte. | Em casos do gabarito com parcela recorrente, a movimentação aparece marcada e vira pergunta ao contador ou ao cliente, sem receber conta automática. | Esc.1, Esc.2, Proposta |
| RF-OBS-02 | O sistema deve calcular as métricas do piloto: extratos que fecham saldo sem intervenção, acerto por linha contra o gabarito, parte das sugestões aceitas sem edição, tempo e taxa de resposta dos clientes. | Um relatório lista as quatro métricas por período, a partir dos registros de RF-OBS-01. Metas [definir]. | v2 (como medir) |

## Could

| ID | Requisito | Critério de aceitação | Origem |
|---|---|---|---|
| RF-LEI-07 | O sistema deve ler extrato em CSV. | Um CSV do gabarito é lido com o mesmo critério do RF-LEI-02. | Proposta (nenhum entrevistado citou CSV) |
| RF-ENV-05 | O sistema deve oferecer uma mensagem de cobrança pronta, para o contador copiar e enviar ao cliente. | O texto inclui o link e o mês e pode ser copiado com um clique. | Proposta, Esc.2 |
| RF-CLA-08 | O sistema deve alertar o contador sobre pagamento duplicado e fornecedor novo de valor alto. | Dois pagamentos iguais em poucos dias geram alerta. O limite de "valor alto" é [definir]. | Proposta |
| RF-AVI-03 | O sistema deve avisar o contador, dentro do sistema, quando um cliente enviar arquivo ou responder perguntas. | Ao concluir um envio, o contador vê um indicador na carteira. | Proposta |
| RF-REV-06 | O sistema deve mostrar, em cada sugestão, as movimentações parecidas que a embasaram. | Para uma sugestão de origem "parecidas", a tela lista os exemplos usados. | Proposta, Esc.2 |
| RF-EXP-05 | O sistema deve exportar também em CSV genérico. | O arquivo traz as mesmas colunas do RF-EXP-01. | Proposta |

## Won't (fora desta versão)

| ID | Requisito | Motivo | Origem |
|---|---|---|---|
| RF-MAQ-02 | Importar o relatório da maquininha e lançar venda bruta e tarifa. | Próximo módulo prioritário. Cada adquirente tem um relatório diferente. | v2, Esc.1, Esc.2 |
| RF-MAQ-03 | Conciliar vendas, taxa e recebido até zerar a operação. | Depende de RF-MAQ-02. | Esc.2, v2 |
| RF-AVI-04 | Enviar lembretes automáticos por WhatsApp e e-mail. | Adição futura. | Ata, v2 |
| RF-REL-01 | Resumo ou dashboard mensal para o cliente. | O Esc.2 disse que o cliente não leria. Só voltaria se outros escritórios pedirem. | v2, Esc.2 |
| RF-EXP-06 | Exportar para outros sistemas contábeis (Questor, Alterdata). | Os dois pilotos usam Domínio. | v2 |
| RF-IMP-01 | Conciliar impostos e parcelamentos (separar principal, juros e multa e baixar o saldo devedor). | Exige conhecimento fiscal que a equipe não tem. | Esc.1, v2 |
| RF-BAN-01 | Conectar direto ao banco do cliente (Open Finance). | Fora do escopo declarado. | v2 |
| RF-CHAT-01 | Chatbot para tirar dúvidas. | A ata cita, a v2 não inclui e nenhum entrevistado pediu. | Ata |
| RF-COB-01 | Cobrança e assinatura dentro do sistema. | O modelo é por faixa de carteira, a cobrança é tratada fora do sistema nesta fase. | v2, Esc.2 |
| RF-CON-01 | Consultoria sobre gastos e análise de movimentações suspeitas. | Ideia futura da ata. | Ata |
| RF-INF-01 | Uso por trabalhadores informais. | Muda o público e não foi validado. | Ata |
| RF-TRI-01 | Decidir ou sugerir tributação, ou tratar a Reforma Tributária. | Fora do produto. O contador decide. | v2 |

## Perguntas para o time avaliar

- **Coerência:** os requisitos descrevem o que o produto deve fazer, sem misturar o como? Algum está repetido ou contradiz outro?
- **Necessidade:** existe algum Must que o piloto dispensa para provar valor? Podemos rebaixá-lo?
- **Lacunas:** falta alguma dor dos escritórios que não aparece em nenhum requisito?
- **Testabilidade:** os critérios de aceitação podem ser verificados por alguém que não programou o item?
- **Prazo:** cada Must tem uma estimativa de esforço, e a soma cabe em 4 semanas e meia?
- **Decisões:** concordamos com as recomendações D-01 a D-09? Alguma muda o escopo?
- **Fonte única:** o fluxo de chefe e troca de responsável veio de um relato só. Vamos confirmar nos pilotos antes de tratá-lo como certo?

**Próximo passo depois da avaliação:** escrever os requisitos não funcionais (segurança em detalhe, desempenho, privacidade, usabilidade no celular) e transformar os Must em histórias de usuário para o `feature_list.json` do harness.
