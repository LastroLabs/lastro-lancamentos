---
title: Entidades e atributos
description: Responsabilidades, atributos e integridade das 27 entidades propostas para o MVP.
---

As entidades abaixo são uma especificação, não tabelas já implementadas. O identificador técnico é `id`; o escopo se repete conforme o [modelo lógico](/lastro-lancamentos/modelagem/modelo-logico/). Cada entidade possui âncora para referências vindas dos requisitos e das fichas.

Os requisitos associados podem ser consultados no sentido inverso em [rastreabilidade por entidade](/lastro-lancamentos/modelagem/rastreabilidade/). A lista inclui identidade e sessão, mas exclui as tabelas internas da fila Procrastinate.

## Índice

- **Identidade e carteira**: [ESCRITORIO](#escritorio), [USUARIO](#usuario), [MEMBRO](#membro), [SESSAO](#sessao), [CLIENTE](#cliente), [ATRIBUICAO](#atribuicao).
- **Cadastro e plano contábil**: [CONTA_BANCARIA](#conta_bancaria), [SOCIO](#socio), [PLANO_CONTAS](#plano_contas), [CONTA_CONTABIL](#conta_contabil).
- **Envio e conferência**: [COMPETENCIA](#competencia), [LINK_CLIENTE](#link_cliente), [ARQUIVO](#arquivo), [EXTRATO](#extrato), [MOVIMENTACAO](#movimentacao), [ORIGEM_MOVIMENTACAO](#origem_movimentacao), [VALIDACAO](#validacao).
- **Classificação e revisão**: [REGRA_CLASSIFICACAO](#regra_classificacao), [SUGESTAO](#sugestao), [PERGUNTA](#pergunta), [PERGUNTA_ITEM](#pergunta_item), [PERGUNTA_OPCAO](#pergunta_opcao), [RESPOSTA](#resposta), [REVISAO](#revisao).
- **Exportação**: [EXPORTACAO](#exportacao), [EXPORTACAO_ITEM](#exportacao_item), [EXPORTACAO_VALIDACAO](#exportacao_validacao).

## Identidade e carteira

### ESCRITORIO

Organização que atende os clientes e delimita o isolamento dos dados.

**Atributos:** `id; nome; ativo`

**Integridade:** Possui membros e clientes. A chave do escritório é obtida da sessão autenticada, sem confiar em um identificador enviado pelo navegador.

**Relacionamentos:** USUARIO se associa por MEMBRO. CLIENTE pertence a exatamente um escritório.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=escritorio) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#escritorio).

### USUARIO

Identidade individual autenticada, separada do papel exercido no escritório.

**Atributos:** `id; identificador_login; nome; ativo; credencial_hash quando aplicável à autenticação local`

**Integridade:** Login individual identifica a autoria. Segredo de autenticação não é armazenado em texto puro. Separar a identidade não estabelece uma funcionalidade de compartilhamento de carteira.

**Relacionamentos:** MEMBRO relaciona usuário e escritório; as ações de negócio referenciam o membro autorizado.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=usuario) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#usuario).

### MEMBRO

Associação do usuário ao escritório, com papel de chefe ou contador e situação ativa.

**Atributos:** `id; escritorio_id; usuario_id; papel; ativo`

**Integridade:** UNIQUE(escritorio_id, usuario_id). O papel pertence ao vínculo organizacional. Somente chefe cadastra contador, cliente e atribuição. Pela P-09, o chefe pode ser o responsável de um cliente, e acessar o cliente exige ser o responsável ativo, seja chefe ou contador.

**Relacionamentos:** Referencia ESCRITORIO e USUARIO. É referenciado por SESSAO, ATRIBUICAO e pelos eventos de revisão.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=membro) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#membro).

### SESSAO

Registro da sessão no servidor e de sua possibilidade de encerramento.

**Atributos:** `id; escritorio_id; membro_id; hash_token; criada_em; expira_em; encerrada_em`

**Integridade:** Hash único. Sessão encerrada ou expirada não autoriza requisições. O prazo da sessão não foi fixado nesta modelagem. A carteira é consultada a cada operação, sem ser incorporada como autorização permanente ao token.

**Relacionamentos:** Referencia o MEMBRO do mesmo escritório; não é vinculada artificialmente a um cliente.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=sessao) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#sessao).

### CLIENTE

Empresa atendida, com cadastro, plano vigente e configurações que permanecem após troca de contador.

**Atributos:** `id; escritorio_id; nome; cnpj_normalizado; ativo; versao_acesso; plano_atual_id; conta_transitoria_id; conta_entrada_socio_id; conta_saida_socio_id`

**Integridade:** CNPJ é texto e único dentro do escritório. Só o chefe cria o cadastro. As contas configuradas pertencem ao cliente e ao plano vigente. Na nova carga, a ausência da transitória no plano novo deixa o cliente sem transitória, conforme P-11.

**Relacionamentos:** Possui atribuições, contas bancárias, sócios, planos e competências. As referências ao plano e às contas são opcionais antes de sua configuração.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=cliente) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#cliente).

### ATRIBUICAO

Histórico de responsabilidades de um membro sobre o cliente.

**Atributos:** `id; escritorio_id; cliente_id; membro_id; atribuido_por; inicio; fim`

**Integridade:** Um responsável ativo por cliente, conforme D-09 provisória. A troca encerra o vínculo anterior e cria o novo em transação. Estrutura preserva vários vínculos históricos, sem habilitar vários responsáveis simultâneos.

**Relacionamentos:** Cliente, responsável e autor da atribuição pertencem ao mesmo escritório.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=atribuicao) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#atribuicao).

## Cadastro e plano contábil

### CONTA_BANCARIA

Conta própria do cliente, utilizada para identificar origem, continuidade de saldo e transferências internas.

**Atributos:** `id; escritorio_id; cliente_id; banco; apelido; identificacao_protegida; moeda; conta_contabil_id; cobertura_inicio; cobertura_fim`

**Integridade:** Conta contábil pertence ao plano vigente do cliente. O intervalo de cobertura indica em quais competências a conta é esperada; não produz lançamentos fictícios em dias sem movimento.

**Relacionamentos:** Pertence ao CLIENTE e é referenciada por EXTRATO, MOVIMENTACAO e VALIDACAO.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=conta_bancaria) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#conta_bancaria).

### SOCIO

Nome do sócio que pode aparecer como contraparte e exigir confirmação contábil.

**Atributos:** `id; escritorio_id; cliente_id; nome; nome_normalizado; ativo`

**Integridade:** Coincidência por prefixo não comprova identidade. Saídas e entradas utilizam configurações distintas e permanecem a confirmar. Entrada não vira receita automática.

**Relacionamentos:** Pertence ao CLIENTE. O reconhecimento gera evidência da SUGESTAO, sem transformar o nome de um terceiro em cadastro de sócio.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=socio) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#socio).

### PLANO_CONTAS

Versão importada do plano de contas do cliente e seu estado de publicação.

**Atributos:** `id; escritorio_id; cliente_id; versao; importado_por; importado_em; publicado_em; situacao`

**Integridade:** UNIQUE por cliente e versão. Publicar nova carga substitui a referência vigente. A anterior permanece somente como evidência histórica; não continua ativa para sugestões novas. Cabeçalho código/nome na linha 1 é suposição de P-10.

**Relacionamentos:** Possui CONTA_CONTABIL. CLIENTE aponta para o plano atual do próprio cliente.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=plano_contas) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#plano_contas).

### CONTA_CONTABIL

Conta identificada por código e nome dentro de uma versão do plano.

**Atributos:** `id; escritorio_id; cliente_id; plano_id; codigo; nome; pai_id; ativo`

**Integridade:** UNIQUE por plano e código. Conta superior pertence ao mesmo plano e cliente. Sugestão, regra ou revisão não podem selecionar conta de outro cliente. Nova operação valida a pertinência ao plano vigente.

**Relacionamentos:** Referencia PLANO_CONTAS e opcionalmente outra CONTA_CONTABIL da mesma versão. É destino de configurações, sugestões e revisões.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=conta_contabil) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#conta_contabil).

## Envio e conferência

### COMPETENCIA

Agrupa os dados do cliente em um mês e identifica a versão publicada do conjunto.

**Atributos:** `id; escritorio_id; cliente_id; mes; versao_conjunto; criada_em`

**Integridade:** Uma competência por cliente/mês. O mês usa o primeiro dia. Status de envio e revisão são calculados com base em arquivos, validações, perguntas e decisões, sem criar estados contraditórios.

**Relacionamentos:** Possui links, arquivos, movimentações, validações, perguntas e exportações.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=competencia) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#competencia).

### LINK_CLIENTE

Autorização sem login para envio e respostas de um cliente e mês.

**Atributos:** `id; escritorio_id; cliente_id; competencia_id; hash_token; criado_por; criado_em; expira_em; revogado_em`

**Integridade:** Token imprevisível; armazenar apenas hash. Padrão atual de 7 dias, configurável. Revalidar revogação e competência no envio e na resposta. Só o responsável ativo emite e invalida o link; o chefe não atribuído recebe 403 (P-09).

**Relacionamentos:** Referencia COMPETENCIA e MEMBRO emissor. ARQUIVO e RESPOSTA referenciam o link autorizador.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=link_cliente) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#link_cliente).

### ARQUIVO

Documento recebido, com metadados privados, grupo de envio e estado do documento.

**Atributos:** `id; escritorio_id; cliente_id; competencia_id; link_id; grupo_envio; chave_objeto; sha256; tamanho_bytes; tipo_detectado; estado_documento; recebido_em`

**Integridade:** O grupo associa vários arquivos enviados juntos. Limite atual de 20 MiB por arquivo, configurável. Objetos ficam privados. O estado não substitui a fila: tarefas são controladas pelo Procrastinate aprovado.

**Relacionamentos:** Referencia o link da mesma COMPETENCIA. Pode originar interpretações versionadas em EXTRATO.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=arquivo) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#arquivo).

### EXTRATO

Interpretação versionada do arquivo para uma conta e período.

**Atributos:** `id; escritorio_id; cliente_id; competencia_id; arquivo_id; conta_bancaria_id; leitor; versao_leitor; execucao_chave; periodo_inicio; periodo_fim; saldo_inicial_centavos; saldo_final_centavos; vigente`

**Integridade:** Resultados de reprocessamento preservam a versão e só um conjunto publicado participa da competência. Período declarado é separado das datas das movimentações. OFX não depende de cadastro de banco; PDFs obrigatórios são BB e Inter.

**Relacionamentos:** Referencia ARQUIVO e CONTA_BANCARIA. Dá origem às ocorrências e às validações documentais.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=extrato) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#extrato).

### MOVIMENTACAO

Fato bancário canônico usado pela classificação, revisão e exportação.

**Atributos:** `id; escritorio_id; cliente_id; competencia_id; conta_bancaria_id; data; descricao; contraparte_normalizada; versao_normalizacao; valor_centavos; origem_identificador; identificador_externo; estado; versao`

**Integridade:** Valor inteiro em centavos com sinal. ID externo estável impede duplicação por conta e origem. Sem ID, linhas iguais permanecem preservadas com alerta. Cada movimentação publicada possui ocorrência de origem.

**Relacionamentos:** Referencia competência e conta; possui ocorrências, sugestões e revisões. Pode participar de perguntas e exportações.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=movimentacao) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#movimentacao).

### ORIGEM_MOVIMENTACAO

Ocorrência que explica em qual extrato, linha ou página a movimentação foi lida.

**Atributos:** `id; escritorio_id; cliente_id; competencia_id; conta_bancaria_id; movimentacao_id; extrato_id; ordem; pagina; saldo_informado_centavos; granularidade_saldo`

**Integridade:** Extrato e movimento compartilham cliente, conta e competência. A ordem identifica a ocorrência no extrato. Preserva os saldos por linha ou dia que fundamentam a conferência.

**Relacionamentos:** Resolve a relação N:M entre EXTRATO e MOVIMENTACAO. O fato pode aparecer em arquivos sobrepostos sem perder sua evidência.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=origem_movimentacao) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#origem_movimentacao).

### VALIDACAO

Resultado versionado de saldo, continuidade ou cobertura, inclusive quando não verificável.

**Atributos:** `id; escritorio_id; cliente_id; competencia_id; conta_bancaria_id; extrato_id opcional; tipo; resultado; versao_conjunto; esperado_centavos; calculado_centavos; diferenca_centavos; referencia; motivo; liberado_por; liberado_em; motivo_liberacao`

**Integridade:** Uma falha não se torna aprovação pela liberação. Liberação explícita para exportação conserva autor, motivo e versão; novo conjunto exige nova conferência. Saldo divergente bloqueia classificação e perguntas conforme AGENTS.md.

**Relacionamentos:** Referencia competência, conta e eventualmente extrato; a exportação preserva a validação efetivamente utilizada.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=validacao) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#validacao).

## Classificação e revisão

### REGRA_CLASSIFICACAO

Regra por cliente, incluindo palavra-chave, histórico aprovado e mapeamento das opções de resposta.

**Atributos:** `id; escritorio_id; cliente_id; tipo; chave_ou_padrao; direcao; prioridade; conta_destino_id; revisao_origem_id; versao; ativa; inicio; fim`

**Integridade:** Precedência é registrada, mas sua ordem definitiva ainda precisa ser definida. Sem conta configurada, a classificação continua na próxima camada. Histórico exige revisão aprovadora. A regra de adquirentes existe na especificação e permanece desativada.

**Relacionamentos:** Referencia conta do plano vigente e revisão de origem quando aprendida. Não transfere aprendizado para outro cliente.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=regra_classificacao) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#regra_classificacao).

### SUGESTAO

Conta candidata com origem, confiança e evidência, inclusive tentativa que termina sem conta.

**Atributos:** `id; escritorio_id; cliente_id; movimentacao_id; conta_id opcional; origem; confianca; pontuacao opcional; motivo; evidencias; regra_id opcional; ia_metadados; versao_movimento; atual; criada_em`

**Integridade:** No máximo uma sugestão atual por movimento. Conta deve pertencer ao plano vigente; ausência de conta é resultado válido. Metadados da IA são sanitizados, com versão de prompt/modelo e estado da tentativa; nomes e identificadores removidos não vão para logs.

**Relacionamentos:** Referencia MOVIMENTACAO, conta candidata e regra opcional. RESPOSTA pode produzir sugestão com origem cliente.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=sugestao) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#sugestao).

### PERGUNTA

Agrupamento de dúvidas sobre uma contraparte na competência.

**Atributos:** `id; escritorio_id; cliente_id; competencia_id; chave_agrupamento; versao_normalizacao; enunciado; criada_em`

**Integridade:** Uma pergunta apresenta as movimentações do grupo, com data, valor e descrição. Baixa confiança gera pergunta sem aplicar conta automaticamente; o limiar depende de D-08.

**Relacionamentos:** Possui PERGUNTA_ITEM, PERGUNTA_OPCAO e, no recorte, até uma RESPOSTA registrada.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=pergunta) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#pergunta).

### PERGUNTA_ITEM

Associação entre a pergunta e cada movimentação apresentada ao cliente.

**Atributos:** `id; escritorio_id; cliente_id; competencia_id; pergunta_id; movimentacao_id`

**Integridade:** UNIQUE por pergunta e movimento. Os dois lados pertencem à mesma competência e cliente; não repetir a mesma linha no grupo.

**Relacionamentos:** Referencia PERGUNTA e MOVIMENTACAO e resolve a relação N:M entre elas.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=pergunta_item) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#pergunta_item).

### PERGUNTA_OPCAO

Fotografia de uma opção exibida, incluindo outro e não sei.

**Atributos:** `id; escritorio_id; cliente_id; pergunta_id; codigo; rotulo; tipo; conta_id opcional`

**Integridade:** Código único por pergunta. Uma opção do tipo conta referencia conta válida do cliente no momento de sua publicação; respostas antigas preservam o que foi apresentado.

**Relacionamentos:** Pertence à PERGUNTA. RESPOSTA deve selecionar uma opção daquela mesma pergunta.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=pergunta_opcao) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#pergunta_opcao).

### RESPOSTA

Escolha do cliente autorizada pelo link da competência.

**Atributos:** `id; escritorio_id; cliente_id; competencia_id; pergunta_id; opcao_id; link_id; texto_livre; respondida_em`

**Integridade:** Até uma resposta por pergunta no recorte. Outro permite texto livre. Não sei mantém a pendência. A resposta sugere conta para revisão; não publica aprendizado por conta própria.

**Relacionamentos:** Pergunta, opção e link são consistentes entre si e pertencem ao mesmo cliente/mês.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=resposta) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#resposta).

### REVISAO

Decisão do contador, registrada como evento para aceitar, corrigir ou manter pendente.

**Atributos:** `id; escritorio_id; cliente_id; movimentacao_id; sugestao_id opcional; membro_id; acao; conta_final_id opcional; versao_movimento; criada_em`

**Integridade:** Aceite ou correção exige conta válida; pendência pode ficar sem conta final. A sugestão analisada pertence ao próprio movimento. Concorrência usa a versão esperada. Aceite de grupo afeta somente itens e versões visíveis.

**Relacionamentos:** Referencia MOVIMENTACAO, membro autorizado, sugestão e conta final opcionais. Pode fundamentar uma regra histórica.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=revisao) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#revisao).

## Exportação

### EXPORTACAO

Lote que congela uma versão da competência, configuração e layout usados na geração do Excel.

**Atributos:** `id; escritorio_id; cliente_id; competencia_id; membro_id; versao_conjunto; chave_idempotencia; situacao; tipo; layout_versao; layout_hash; layout_homologado; configuracao_snapshot; qtde_linhas; entradas_centavos; saidas_centavos; chave_objeto; sha256; criada_em`

**Integridade:** Layout atual é provisório e precisa de importação real no Domínio. Conferir acesso, revisão/pendência, transitória, validações e totais antes de liberar o download. Reentrega conserva o arquivo; correção cria outro lote.

**Relacionamentos:** Possui EXPORTACAO_ITEM e EXPORTACAO_VALIDACAO da mesma competência.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=exportacao) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#exportacao).

### EXPORTACAO_ITEM

Cópia imutável dos dados de uma linha efetivamente exportada.

**Atributos:** `id; escritorio_id; cliente_id; competencia_id; exportacao_id; movimentacao_id; revisao_id opcional; ordem; data_movimento; valor_centavos; codigo_contabil; pendente; dados_layout`

**Integridade:** Ordem e movimento não se repetem no lote. Não pendente exige revisão válida do próprio movimento; pendente usa transitória e marca explícita. Preservar documento, fornecedor, cliente, data, valor e conta usados no layout sem fixar colunas não homologadas.

**Relacionamentos:** Lote e movimento compartilham competência. Revisão, quando presente, pertence ao movimento exportado.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=exportacao_item) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#exportacao_item).

### EXPORTACAO_VALIDACAO

Associação do lote às conferências e eventuais liberações utilizadas.

**Atributos:** `id; escritorio_id; cliente_id; competencia_id; exportacao_id; validacao_id; resultado_snapshot; liberacao_snapshot`

**Integridade:** Uma validação aparece no máximo uma vez por lote. Preservar o resultado e a autorização utilizados, sem converter reprovação em aprovação nem reutilizar liberação de outro conjunto.

**Relacionamentos:** Referencia EXPORTACAO e VALIDACAO da mesma competência.

[Requisitos desta entidade](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=exportacao_validacao) · [Chaves e vínculos](/lastro-lancamentos/modelagem/modelo-logico/#exportacao_validacao).
