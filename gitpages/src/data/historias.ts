// RASCUNHO para avaliação do time: uma história de usuário por requisito Must.
// Personas das páginas do site: contador, chefe e cliente do escritório.
// O "para" de cada história vem da dor (visao/cenario) ou do critério de aceitação do requisito.
// O critério de aceitação continua sendo o do requisito (src/data/requisitos.json).

export const historias: Record<string, string> = {
	// Acesso e segurança
	'RF-AUT-01': 'Como contador, quero entrar com o meu próprio login, para que o sistema identifique quem fez cada ação.',
	'RF-AUT-02': 'Como contador, quero ver só os clientes atribuídos a mim (e, como chefe, todos os do escritório), para que ninguém acesse a carteira de outra pessoa, nem por endereço direto.',
	'RF-AUT-03': 'Como chefe, quero cadastrar contadores e clientes e atribuir clientes a contadores, para organizar a carteira do escritório.',
	'RF-AUT-04': 'Como chefe, quero que a reatribuição de um cliente valha na hora, para que o contador anterior perca o acesso e o novo assuma sem novo login.',
	'RF-SEG-01': 'Como contador, quero que o link do cliente tenha código imprevisível e validade e possa ser invalidado, para que um link vencido ou invalidado não dê acesso a nenhum dado.',
	'RF-SEG-02': 'Como escritório, quero meus dados isolados dos de outros escritórios, para que nenhum usuário de fora os leia por tela ou endereço.',
	'RF-SEG-03': 'Como escritório, quero que CPF, CNPJ, agência e conta sejam removidos antes de qualquer envio à IA, para que esses dados não cheguem a um serviço externo.',
	// Cadastro
	'RF-CAD-01': 'Como contador, quero cadastrar um cliente com nome e CNPJ, para que ele apareça na minha carteira.',
	'RF-CAD-02': 'Como contador, quero informar os bancos e as contas do cliente, para que cada extrato fique ligado à conta certa.',
	'RF-CAD-03': 'Como contador, quero carregar o plano de contas do cliente por planilha, para não digitar conta por conta.',
	'RF-CAD-04': 'Como contador, quero indicar a conta transitória do cliente, para que as pendentes tenham onde sair na exportação.',
	'RF-CAD-06': 'Como contador, quero cadastrar os sócios do cliente, para que retiradas e aportes sejam reconhecidos pela regra de sócio.',
	// Envio e coleta
	'RF-ENV-01': 'Como contador, quero gerar um link de envio por cliente e mês, para não precisar cobrar o mesmo extrato várias vezes.',
	'RF-ENV-02': 'Como cliente do escritório, quero enviar um ou mais PDFs ou OFX pelo celular, sem login, para entregar o extrato numa única ação.',
	'RF-ENV-03': 'Como contador, quero ver por cliente e mês se o extrato foi enviado, para saber quem ainda falta sem precisar perguntar.',
	'RF-ENV-04': 'Como cliente do escritório, quero enviar um arquivo complementar quando o sistema avisar que falta algo, para completar o mês sem recomeçar o envio.',
	// Leitura
	'RF-LEI-01': 'Como contador, quero que o sistema detecte sozinho o formato do arquivo, para não ter de escolher configuração nenhuma.',
	'RF-LEI-02': 'Como contador, quero que o OFX de qualquer banco seja lido sem cadastro por banco, para não precisar cadastrar layout de OFX.',
	'RF-LEI-03': 'Como contador, quero que os PDFs digitais do Inter e do Banco do Brasil sejam lidos, para não digitar as movimentações desses bancos.',
	'RF-LEI-04': 'Como contador, quero ver o banco e o período de cada arquivo, para que a cobertura do mês possa ser conferida.',
	'RF-LEI-05': 'Como contador, quero que reenviar o mesmo período não duplique movimentações, para não lançar a mesma coisa duas vezes.',
	// Conferência de valores
	'RF-VAL-01': 'Como contador, quero que o sistema confira por cálculo se o saldo fecha, para descobrir extrato incompleto no envio, e não no fechamento.',
	'RF-VAL-02': 'Como contador, quero saber em que linha ou dia o saldo deixa de fechar, para ir direto ao problema.',
	'RF-VAL-03': 'Como contador, quero que o saldo inicial do mês seja comparado com o final do mês anterior, para perceber o que ficou faltando entre os meses.',
	'RF-VAL-04': 'Como contador, quero ser avisado quando o extrato não vai até o último dia do mês, para cobrar só o trecho que falta.',
	'RF-VAL-05': 'Como contador, quero que um extrato reprovado fique fora da exportação até eu liberar, para que nada reprovado chegue ao Domínio sem uma decisão registrada.',
	// Avisos
	'RF-AVI-01': 'Como cliente do escritório, quero saber na hora do envio o que está faltando, para mandar o complemento sem esperar o contador.',
	'RF-AVI-02': 'Como contador ou cliente, quero mensagens em português simples, que digam o que aconteceu e o que fazer, para entender sem termos técnicos.',
	// Classificação
	'RF-CLA-01': 'Como contador, quero que cada sugestão seja uma conta do plano do cliente ou "não sei", para nunca receber uma conta que não existe.',
	'RF-CLA-02a': 'Como contador, quero que tarifas, IOF, impostos e aplicações sejam classificados por palavra-chave, para não revisar à mão o que é sempre igual.',
	'RF-CLA-02b': 'Como contador, quero que transferências entre contas do próprio cliente sejam reconhecidas, para que não contem como receita nem despesa.',
	'RF-CLA-02c': 'Como contador, quero que movimentos de sócio sejam reconhecidos mesmo com o nome truncado, para que retirada de lucro não seja confundida com despesa.',
	'RF-CLA-03': 'Como contador, quero que uma contraparte que já aceitei volte com a mesma conta, para não classificar de novo o que já decidi.',
	'RF-CLA-04': 'Como contador, quero sugestões baseadas em movimentações parecidas do mesmo cliente, para que descrições que variam também sejam resolvidas.',
	'RF-CLA-05': 'Como contador, quero que a IA só receba o que regras, histórico e parecidas não resolveram, para que ela entre apenas no que sobrou.',
	'RF-CLA-06': 'Como contador, quero ver a origem e a confiança de cada sugestão, para decidir quando confiar na automação.',
	'RF-CLA-07': 'Como contador, quero que uma sugestão abaixo do limite de confiança vire pergunta ao cliente em vez de ser aplicada, para não aceitar palpite como conta.',
	'RF-CLA-09': 'Como contador, quero uma ordem de precedência quando duas regras casam, com o motivo mostrando qual regra valeu, para entender o resultado.',
	'RF-CLA-10': 'Como contador, quero que um tipo reconhecido sem conta configurada siga para as próximas camadas e me avise, para saber o que falta configurar.',
	// Maquininha
	'RF-MAQ-01': 'Como contador, quero que créditos de adquirentes sejam classificados como recebimento de cartão, para que não virem perguntas inúteis ao cliente.',
	// Perguntas ao cliente
	'RF-PER-01': 'Como cliente do escritório, quero uma pergunta por contraparte, e não uma por movimentação, para responder menos vezes.',
	'RF-PER-02': 'Como cliente do escritório, quero responder com um toque numa lista (ou com texto livre em "outro"), para responder rápido pelo celular.',
	'RF-PER-03': 'Como cliente do escritório, quero ver a data, o valor e a descrição de cada movimentação da pergunta, para reconhecer do que se trata.',
	'RF-PER-04': 'Como cliente do escritório, quero poder responder "não sei", para não inventar uma resposta; a movimentação continua pendente.',
	'RF-PER-05': 'Como contador, quero que a resposta do cliente vire uma conta sugerida "confirmada pelo cliente", para revisar já com essa informação.',
	// Aprendizado
	'RF-APR-01': 'Como contador, quero que a resposta do cliente, depois de aceita por mim, vire regra do cliente, para não perguntar a mesma coisa no mês seguinte.',
	'RF-APR-02': 'Como contador, quero que a minha correção substitua a sugestão anterior, para que o mesmo erro não se repita.',
	'RF-APR-03': 'Como contador, quero o aprendizado separado por cliente, para que uma regra de um cliente não mude as sugestões de outro.',
	// Revisão
	'RF-REV-01': 'Como contador, quero ver o mês em três grupos (prontas, confirmadas pelo cliente e pendentes), com o total de cada um, para saber onde concentrar a revisão.',
	'RF-REV-02': 'Como contador, quero aceitar, trocar ou marcar como pendente, item a item ou por grupo, com registro de quem fez, para revisar rápido e deixar rastro.',
	'RF-REV-03': 'Como contador, quero ver na revisão se o extrato passou na conferência e, se não passou, o motivo, para não revisar em cima de extrato incompleto.',
	'RF-REV-04': 'Como contador, quero que nada sem revisão seja exportado (exceto as pendentes, na conta transitória), para que só entre no Domínio o que eu revisei.',
	// Exportação
	'RF-EXP-01': 'Como contador, quero uma planilha no layout de importação do Domínio, para importar sem digitar e sem editar à mão.',
	'RF-EXP-02': 'Como contador, quero as pendentes na conta transitória e marcadas, para fechar o mês e tratá-las depois.',
	'RF-EXP-03': 'Como contador, quero ver antes do download que linhas e totais batem com o extrato, para ter a planilha "conferindo com o extrato".',
	'RF-EXP-04': 'Como contador, quero que as opções de exportação fiquem salvas com o cliente, para que um novo responsável exporte sem reconfigurar.',
};
