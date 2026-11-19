---
title: Modelo físico e operações
description: Tipos, índices, concorrência, isolamento e operações transacionais previstos para o MVP.
---

A implementação deve seguir [BD-01 a BD-08](/lastro-lancamentos/decisoes/banco-de-dados/) e a [arquitetura aprovada](/lastro-lancamentos/decisoes/arquitetura/). Esta página especifica controles esperados; não contém migração executada nem resultado de teste de integração.

## Tipos e escopo

Identificadores técnicos e referências usam **UUID**. Valores e saldos usam **BIGINT em centavos com sinal**: entrada positiva e saída negativa. Datas bancárias usam `DATE`; os instantes de envio, revisão e revogação usam `TIMESTAMPTZ`. O mês da competência é representado pelo primeiro dia. CNPJ, códigos contábeis e identificadores bancários são texto; não devem ser convertidos em números.

A ficha CAD-01 em revisão prevê CNPJ numérico e alfanumérico. O modelo armazena o identificador como texto normalizado e não inventa regra de validação além da ficha. O status HTTP de dado inválido permanece em P-13.

Colunas centrais de valores, contas, estados e relacionamentos são tipadas. `JSONB` fica restrito a evidências variáveis, metadados sanitizados e fotografias validadas. A confiança pode usar categoria e pontuação limitada; a pontuação não é uma probabilidade calibrada por presunção. O limite continua pendente em D-08.

O [modelo lógico](/lastro-lancamentos/modelagem/modelo-logico/) repete `escritorio_id` e `cliente_id` nas FKs das tabelas subordinadas. Identidade, associação ao escritório e sessão possuem seu escopo próprio; não recebem um cliente fictício para satisfazer essa convenção.

## Restrições e índices

As PKs e FKs impedem referências cruzadas entre escritórios e clientes. Declarar `NOT NULL` para os vínculos obrigatórios e `CHECK` para estados válidos, intervalos temporais, mês no primeiro dia e contagens não negativas. Os campos de conta candidata e conta final permanecem opcionais onde “não sei” e pendência são resultados válidos.

Usar índices parciais para limitar a um vínculo de responsável vigente por cliente, uma sugestão atual por movimentação e uma versão ativa de cada regra histórica. Preservar unicidade de código por versão do plano, de competência por cliente/mês e de posição do item por exportação. Indexar as FKs e os filtros por cliente, competência, conta, data e estado. O `pg_trgm` aprovado em BD-06 consulta exclusivamente o histórico do próprio cliente.

O hash reconhece conteúdo reenviado, mas não autoriza apagar pagamentos legítimos. Para identificador externo estável, a unicidade considera escritório, cliente, conta, origem e identificador. Identificador repetido com data ou valor divergente gera conflito. Sem identificador, duas linhas iguais são preservadas e sinalizadas.

## Sessão, autorização e reatribuição

A sessão no servidor referencia o membro do escritório, tem validade e pode ser encerrada. Não guarda uma carteira fixa que continue autorizando acesso após a reatribuição. A aplicação confere o papel e os vínculos vigentes em toda requisição; RLS reforça o escopo de leitura e escrita, sob papel de banco diferente do proprietário das tabelas.

P-01 prevê **401** sem sessão válida, **403** quando o papel não permite a ação e **404 idêntico ao de inexistente** para recurso de outro escritório ou carteira. Só o chefe cadastra o cliente. A visão de todos os clientes do escritório não implica autorização automática para revisar, exportar, editar cadastros ou emitir links sem atribuição; aplicar a definição disponível e manter P-09 pendente.

A reatribuição bloqueia o cliente, encerra o vínculo anterior, cria o novo e incrementa a versão de acesso na mesma transação. Downloads mediados pelo backend revalidam a permissão. O histórico e as configurações continuam ligados ao cliente.

## Importação e substituição do plano

A leitura da planilha valida código e nome, identificando a linha inválida. Cabeçalhos na primeira linha são uma suposição de P-10, a confirmar. A publicação do novo `PLANO_CONTAS` e a troca da referência vigente do cliente ocorrem em transação. A versão anterior pode permanecer como evidência histórica, mas deixa de fornecer contas candidatas às novas operações.

Conforme P-11, se a conta transitória não estiver no novo plano, o cliente fica **sem transitória**. Não conservar silenciosamente uma FK para uma conta inativa. Validar também contas de banco, de sócio, regras e mapeamentos: referências antigas não se tornam válidas no plano novo por coincidência de UUID. A estratégia de correspondência e a autorização para reaplicar configurações precisam ser explícitas na implementação; não presumir migração automática. Uma exportação já congelada conserva a fotografia original.

## Recebimento, processamento e publicação

O link é validado por hash, competência, expiração e revogação. O padrão de D-06 é 7 dias e 20 MiB por arquivo, configuráveis. A validação do tipo considera o conteúdo, não apenas a extensão. Os objetos ficam privados. A fila utiliza **Procrastinate no PostgreSQL**, conforme ARQ-04; `ARQUIVO` registra o estado do documento, sem atuar como uma segunda fila.

O consumidor é idempotente: uma retentativa não duplica a publicação. O resultado de cada leitura preserva sua versão; só o conjunto publicado participa da revisão. Novo envio complementar ou novo resultado vigente incrementa a versão do conjunto e invalida as conferências e liberações afetadas.

RF-AVI-01 exige mostrar a falha e o que falta **no fluxo de envio**. Colocar o documento na fila não atende sozinho ao critério: a página precisa acompanhar a conclusão da conferência e mostrar uma mensagem em português simples. O mecanismo de acompanhamento pertence à aplicação.

## Conferência e bloqueio

O cálculo é determinístico: saldo inicial mais a soma dos valores com sinal deve coincidir com o saldo final. Havendo saldo por linha, apontar a primeira divergência; caso contrário, usar o dia ou a menor granularidade disponível. Registrar os valores esperado, calculado e a diferença. Sem mês anterior, a continuidade fica “não verificada”. Período declarado e datas de movimentações são evidências distintas para a cobertura.

A regra 4 do `AGENTS.md` impede que um extrato com saldo divergente avance à **classificação ou às perguntas**. RF-VAL-05 permite uma liberação explícita para exportação, registrada com usuário, instante, motivo e versão; essa exceção não aprova o saldo nem libera automaticamente as etapas anteriores. A abrangência da exceção deve ser confirmada pelo projeto antes de alterar esse bloqueio.

## Classificação, respostas e aprendizado

Aplicar regras, histórico aprovado, parecidas e, por último, IA. Se o tipo for reconhecido sem conta configurada, continuar para a camada seguinte e avisar o contador. Registrar a regra vencedora, origem e confiança. A precedência e D-08 ainda exigem definição; o modelo não fixa um limiar arbitrário.

Transferência interna exige contas do mesmo cliente e correspondência de entrada/saída, sem receita ou despesa. Coincidência por prefixo de sócio é indício e continua “a confirmar”; entrada de sócio não vira receita. A regra de adquirentes permanece desativada conforme D-02 provisória.

Cada chamada externa passa pelo gateway aprovado. Remover CPF, CNPJ, agência e conta e pseudonimizar **todo nome de contraparte**, pessoa ou empresa, conforme D-03. Registrar apenas metadados sanitizados. O resultado deve indicar conta do plano vigente ou ausência de conta. As equivalências de pseudônimos, quando necessárias, ficam restritas e não integram logs públicos.

A opção e a resposta pertencem à pergunta da mesma competência do link. “Outro” aceita texto; “não sei” mantém a pendência. A resposta gera sugestão para revisão, sem aprendizado automático. Aceite ou correção do contador publica a regra do cliente, preservando a decisão que a fundamentou. Uma correção encerra a versão anterior para ocorrências futuras.

## Revisão e exportação

Cada decisão de revisão guarda usuário, data e versão esperada. Se o movimento mudou, a operação exige nova leitura. Aceite em grupo usa apenas os itens e versões do grupo visível. Prontas, confirmadas pelo cliente e pendentes são grupos exclusivos de apresentação; o grupo não substitui o evento de revisão.

Em transação, a exportação verifica acesso, plano e configuração vigentes, conta transitória, conjunto publicado, revisão ou pendência e conferências/liberações vigentes. Congela itens, layout, configurações e evidências. A planilha é gerada dessa fotografia, e a entrega confere quantidade, total de entradas e total de saídas em centavos. Não omitir linhas para forçar a conciliação.

Pendentes usam a transitória e uma marca explícita. As demais precisam de revisão. Baixar o mesmo lote devolve o mesmo conteúdo e hash; uma correção posterior gera novo lote. O layout de D-05 continua marcado como provisório até a importação real no Domínio sem edição manual.

## Verificação antes da implementação concluída

Os testes devem cobrir isolamento e 404 indistinguível; reatribuição com sessão aberta; revogação de link; troca de plano com perda da transitória; reenvio e linhas iguais legítimas; saldo divergente bloqueando classificação; complemento de período; regra sem conta; nome de sócio truncado; resposta “não sei”; aprendizado após revisão; concorrência; fotografia e totais da exportação; e sanitização do conteúdo efetivamente enviado à IA.

Os critérios de aceitação estão na [rastreabilidade](/lastro-lancamentos/modelagem/rastreabilidade/). As fichas e evidências seguem a [orquestração](/lastro-lancamentos/fluxo/orquestracao/), a [DoR e DoD](/lastro-lancamentos/requisitos/dor-dod/) e as regras de [segurança](/lastro-lancamentos/arquitetura/seguranca/). Nenhum desses cenários é apresentado aqui como teste já executado.
