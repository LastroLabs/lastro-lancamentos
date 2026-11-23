---
title: Modelo lógico
description: Chaves, escopo e relações das tabelas propostas para o MVP.
---

## Convenções

`E` representa `escritorio_id`; `C`, `cliente_id`; `I`, o identificador técnico. ESCRITORIO e USUARIO usam `I` como PK. MEMBRO, SESSAO e CONVITE usam `(E, I)`. CLIENTE usa `(E, I)`. As demais tabelas subordinadas ao cliente usam `(E, C, I)` e FK `(E, C)` para CLIENTE `(E, I)`.

Uma FK que inclui competência, conta, movimento, pergunta ou plano exige uma chave `UNIQUE` com a mesma combinação no destino. Compartilhar o UUID não dispensa preservar o escopo. As referências ao plano atual e às contas de configuração podem ficar nulas até o cadastro estar completo.

F3/F4 confirmados em 23/11/2026: MEMBRO e CLIENTE têm FK direta escritorio_id → escritorio(id), sem duplicar relações garantidas por FKs compostas. Todas as FKs da DB-01 usam ON DELETE/UPDATE NO ACTION e NOT DEFERRABLE, sem cascata.

## Relações por entidade

### ESCRITORIO

USUARIO se associa por MEMBRO. CLIENTE pertence a exatamente um escritório.

Possui membros e clientes. A chave do escritório é obtida da sessão autenticada, sem confiar em um identificador enviado pelo navegador.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#escritorio) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=escritorio).

### USUARIO

MEMBRO relaciona usuário e escritório; as ações de negócio referenciam o membro autorizado.

Login individual identifica a autoria. Segredo de autenticação não é armazenado em texto puro. Separar a identidade não estabelece uma funcionalidade de compartilhamento de carteira.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#usuario) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=usuario).

### MEMBRO

Referencia ESCRITORIO e USUARIO. É referenciado por SESSAO, CONVITE (destinatário e autor), ATRIBUICAO e pelos eventos de revisão.

UNIQUE(escritorio_id, usuario_id). O papel pertence ao vínculo organizacional. Somente chefe cadastra contador, cliente e atribuição. Pela P-09, o chefe pode ser o responsável de um cliente, e acessar o cliente exige ser o responsável ativo, seja chefe ou contador.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#membro) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=membro).

### SESSAO

Referencia o MEMBRO do mesmo escritório; não é vinculada artificialmente a um cliente.

Hash único. Sessão encerrada ou expirada não autoriza requisições. O prazo da sessão não foi fixado nesta modelagem. A carteira é consultada a cada operação, sem ser incorporada como autorização permanente ao token.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#sessao) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=sessao).

### CONVITE

Referencia MEMBRO destinatário e MEMBRO autor pelas FKs `(escritorio_id, membro_id)` e `(escritorio_id, criado_por)`, ambas para `membro(escritorio_id, id)`, conforme DB-01/c2. PK `(escritorio_id, id)`.

Hash globalmente único; índice único parcial `(escritorio_id, membro_id)` onde `usado_em IS NULL AND revogado_em IS NULL`, conforme c5. Expiração não integra esse predicado; A3 exige revogar o convite expirado pendente antes de reemitir. CHECKs exigem expiração posterior à criação e impedem uso e revogação simultâneos. Tipos/defaults e complementos F1–F5 confirmados: [recorte DB-01](/lastro-lancamentos/modelagem/modelo-fisico/#recorte-físico-da-db-01).

### CLIENTE

Possui atribuições, contas bancárias, sócios, planos e competências. As referências ao plano e às contas são opcionais antes de sua configuração.

CNPJ é texto e único dentro do escritório. Só o chefe cria o cadastro. As contas configuradas pertencem ao cliente e ao plano vigente. Na nova carga, a ausência da transitória no plano novo deixa o cliente sem transitória, conforme P-11.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#cliente) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=cliente).

### ATRIBUICAO

Cliente, responsável e autor da atribuição pertencem ao mesmo escritório.

Um responsável ativo por cliente, conforme D-09 provisória. A troca encerra o vínculo anterior e cria o novo em transação. Estrutura preserva vários vínculos históricos, sem habilitar vários responsáveis simultâneos.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#atribuicao) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=atribuicao).

### CONTA_BANCARIA

Pertence ao CLIENTE e é referenciada por EXTRATO, MOVIMENTACAO e VALIDACAO.

Conta contábil pertence ao plano vigente do cliente. O intervalo de cobertura indica em quais competências a conta é esperada; não produz lançamentos fictícios em dias sem movimento.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#conta_bancaria) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=conta_bancaria).

### SOCIO

Pertence ao CLIENTE. O reconhecimento gera evidência da SUGESTAO, sem transformar o nome de um terceiro em cadastro de sócio.

Coincidência por prefixo não comprova identidade. Saídas e entradas utilizam configurações distintas e permanecem a confirmar. Entrada não vira receita automática.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#socio) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=socio).

### PLANO_CONTAS

Possui CONTA_CONTABIL. CLIENTE aponta para o plano atual do próprio cliente.

UNIQUE por cliente e versão. Publicar nova carga substitui a referência vigente. A anterior permanece somente como evidência histórica; não continua ativa para sugestões novas. Cabeçalho código/nome na linha 1 é suposição de P-10.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#plano_contas) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=plano_contas).

### CONTA_CONTABIL

Referencia PLANO_CONTAS e opcionalmente outra CONTA_CONTABIL da mesma versão. É destino de configurações, sugestões e revisões.

UNIQUE por plano e código. Conta superior pertence ao mesmo plano e cliente. Sugestão, regra ou revisão não podem selecionar conta de outro cliente. Nova operação valida a pertinência ao plano vigente.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#conta_contabil) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=conta_contabil).

### COMPETENCIA

Possui links, arquivos, movimentações, validações, perguntas e exportações.

Uma competência por cliente/mês. O mês usa o primeiro dia. Status de envio e revisão são calculados com base em arquivos, validações, perguntas e decisões, sem criar estados contraditórios.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#competencia) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=competencia).

### LINK_CLIENTE

Referencia COMPETENCIA e MEMBRO emissor. ARQUIVO e RESPOSTA referenciam o link autorizador.

Token imprevisível; armazenar apenas hash. Padrão atual de 7 dias, configurável. Revalidar revogação e competência no envio e na resposta. Só o responsável ativo emite e invalida o link; o chefe não atribuído recebe 403 (P-09).

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#link_cliente) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=link_cliente).

### ARQUIVO

Referencia o link da mesma COMPETENCIA. Pode originar interpretações versionadas em EXTRATO.

O grupo associa vários arquivos enviados juntos. Limite atual de 20 MiB por arquivo, configurável. Objetos ficam privados. O estado não substitui a fila: tarefas são controladas pelo Procrastinate aprovado.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#arquivo) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=arquivo).

### EXTRATO

Referencia ARQUIVO e CONTA_BANCARIA. Dá origem às ocorrências e às validações documentais.

Resultados de reprocessamento preservam a versão e só um conjunto publicado participa da competência. Período declarado é separado das datas das movimentações. OFX não depende de cadastro de banco; PDFs obrigatórios são BB e Inter.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#extrato) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=extrato).

### MOVIMENTACAO

Referencia competência e conta; possui ocorrências, sugestões e revisões. Pode participar de perguntas e exportações.

Valor inteiro em centavos com sinal. ID externo estável impede duplicação por conta e origem. Sem ID, linhas iguais permanecem preservadas com alerta. Cada movimentação publicada possui ocorrência de origem.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#movimentacao) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=movimentacao).

### ORIGEM_MOVIMENTACAO

Resolve a relação N:M entre EXTRATO e MOVIMENTACAO. O fato pode aparecer em arquivos sobrepostos sem perder sua evidência.

Extrato e movimento compartilham cliente, conta e competência. A ordem identifica a ocorrência no extrato. Preserva os saldos por linha ou dia que fundamentam a conferência.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#origem_movimentacao) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=origem_movimentacao).

### VALIDACAO

Referencia competência, conta e eventualmente extrato; a exportação preserva a validação efetivamente utilizada.

Uma falha não se torna aprovação pela liberação. Liberação explícita para exportação conserva autor, motivo e versão; novo conjunto exige nova conferência. Saldo divergente bloqueia classificação e perguntas conforme AGENTS.md.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#validacao) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=validacao).

### REGRA_CLASSIFICACAO

Referencia conta do plano vigente e revisão de origem quando aprendida. Não transfere aprendizado para outro cliente.

Precedência é registrada, mas sua ordem definitiva ainda precisa ser definida. Sem conta configurada, a classificação continua na próxima camada. Histórico exige revisão aprovadora. A regra de adquirentes existe na especificação e permanece desativada.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#regra_classificacao) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=regra_classificacao).

### SUGESTAO

Referencia MOVIMENTACAO, conta candidata e regra opcional. RESPOSTA pode produzir sugestão com origem cliente.

No máximo uma sugestão atual por movimento. Conta deve pertencer ao plano vigente; ausência de conta é resultado válido. Metadados da IA são sanitizados, com versão de prompt/modelo e estado da tentativa; nomes e identificadores removidos não vão para logs.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#sugestao) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=sugestao).

### PERGUNTA

Possui PERGUNTA_ITEM, PERGUNTA_OPCAO e, no recorte, até uma RESPOSTA registrada.

Uma pergunta apresenta as movimentações do grupo, com data, valor e descrição. Baixa confiança gera pergunta sem aplicar conta automaticamente; o limiar depende de D-08.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#pergunta) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=pergunta).

### PERGUNTA_ITEM

Referencia PERGUNTA e MOVIMENTACAO e resolve a relação N:M entre elas.

UNIQUE por pergunta e movimento. Os dois lados pertencem à mesma competência e cliente; não repetir a mesma linha no grupo.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#pergunta_item) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=pergunta_item).

### PERGUNTA_OPCAO

Pertence à PERGUNTA. RESPOSTA deve selecionar uma opção daquela mesma pergunta.

Código único por pergunta. Uma opção do tipo conta referencia conta válida do cliente no momento de sua publicação; respostas antigas preservam o que foi apresentado.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#pergunta_opcao) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=pergunta_opcao).

### RESPOSTA

Pergunta, opção e link são consistentes entre si e pertencem ao mesmo cliente/mês.

Até uma resposta por pergunta no recorte. Outro permite texto livre. Não sei mantém a pendência. A resposta sugere conta para revisão; não publica aprendizado por conta própria.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#resposta) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=resposta).

### REVISAO

Referencia MOVIMENTACAO, membro autorizado, sugestão e conta final opcionais. Pode fundamentar uma regra histórica.

Aceite ou correção exige conta válida; pendência pode ficar sem conta final. A sugestão analisada pertence ao próprio movimento. Concorrência usa a versão esperada. Aceite de grupo afeta somente itens e versões visíveis.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#revisao) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=revisao).

### EXPORTACAO

Possui EXPORTACAO_ITEM e EXPORTACAO_VALIDACAO da mesma competência.

Layout atual é provisório e precisa de importação real no Domínio. Conferir acesso, revisão/pendência, transitória, validações e totais antes de liberar o download. Reentrega conserva o arquivo; correção cria outro lote.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#exportacao) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=exportacao).

### EXPORTACAO_ITEM

Lote e movimento compartilham competência. Revisão, quando presente, pertence ao movimento exportado.

Ordem e movimento não se repetem no lote. Não pendente exige revisão válida do próprio movimento; pendente usa transitória e marca explícita. Preservar documento, fornecedor, cliente, data, valor e conta usados no layout sem fixar colunas não homologadas.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#exportacao_item) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=exportacao_item).

### EXPORTACAO_VALIDACAO

Referencia EXPORTACAO e VALIDACAO da mesma competência.

Uma validação aparece no máximo uma vez por lote. Preservar o resultado e a autorização utilizados, sem converter reprovação em aprovação nem reutilizar liberação de outro conjunto.

[Descrição e atributos](/lastro-lancamentos/modelagem/entidades/#exportacao_validacao) · [Requisitos vinculados](/lastro-lancamentos/modelagem/rastreabilidade/?entidade=exportacao_validacao).

## FKs com identidade ampliada

- `CLIENTE.plano_atual_id` referencia um PLANO_CONTAS do próprio cliente. Configurações referenciam contas do mesmo cliente e são validadas contra esse plano vigente.
- `CONTA_CONTABIL.pai_id` inclui o plano do registro na FK; a conta superior pertence à mesma versão.
- `ARQUIVO.link_id` inclui a competência; o arquivo não usa link de outro mês.
- `EXTRATO.arquivo_id` preserva a competência do arquivo e a conta do cliente.
- `ORIGEM_MOVIMENTACAO` inclui competência e conta nas FKs para extrato e movimentação.
- `PERGUNTA_ITEM` inclui competência nas FKs para pergunta e movimento.
- `RESPOSTA.opcao_id` inclui a pergunta; pergunta e link incluem a mesma competência.
- `REVISAO.sugestao_id` inclui a movimentação, impedindo aceitar sugestão de outra linha.
- `EXPORTACAO_ITEM` inclui competência nas referências a lote e movimento; a revisão referenciada pertence ao mesmo movimento.
- `EXPORTACAO_VALIDACAO` inclui competência nas referências ao lote e à validação.

## Unicidades de negócio

CNPJ é único por escritório; membro, por escritório e usuário; competência, por cliente e mês; versão do plano, por cliente; código de conta, por plano. Pergunta não repete o movimento associado e possui opções com código próprio. No recorte há no máximo uma resposta por pergunta. Ordem e movimentação são únicas dentro do lote exportado; uma validação não é repetida no mesmo lote.

Os índices parciais limitam responsável vigente, sugestão atual e regra histórica ativa. O identificador bancário estável tem unicidade por conta/origem quando presente. Não criar unicidade para a combinação descrição/data/valor sem identificador externo.

## Regras que não cabem apenas em FKs

Plano vigente, carteira atual, expiração do link, publicação do conjunto, precedência e portas da exportação dependem de transações e autorização na aplicação. FKs garantem pertencimento; não substituem essas verificações. O [modelo físico](/lastro-lancamentos/modelagem/modelo-fisico/) detalha as operações e os critérios de validação.
