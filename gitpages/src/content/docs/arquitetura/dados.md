---
title: Dados
description: Modelo de dados, centavos, isolamento, duplicidades e exportação reproduzível.
---

:::note[Status]
Recomendada, aguardando aprovação. Ver [Decisão: banco de dados](/lastro-lancamentos/decisoes/banco-de-dados/). Os nomes de tabela abaixo são uma proposta de esquema, não tabelas que já existem.
:::

## Regras de base

| Tema | Regra |
|---|---|
| Dinheiro e saldos | BIGINT com sinal, **em centavos**; moeda inicialmente BRL. No código, `int` em centavos; nunca float |
| Identificadores | UUID como identificador técnico; códigos contábeis, CNPJ e apelidos são campos de negócio |
| Datas | Datas bancárias em DATE; eventos em TIMESTAMPTZ (UTC), exibidos no fuso adequado |
| Confiança | NUMERIC limitado ou categorias, sem confundir pontuação textual com probabilidade calibrada |
| JSONB | Só para metadados variáveis de leitores, parâmetros e saídas técnicas validadas por schema. Valores, contas, estados e vínculos ficam em colunas tipadas |
| Escopo | Toda tabela de negócio ligada a um cliente carrega `escritorio_id` e `cliente_id`; as chaves estrangeiras repetem esse escopo |

Exemplo fictício: um Pix de R$ 1.250,00 enviado é gravado como `valor_centavos = -125000`.

## Identidade e cadastro

| Entidade | Campos e relações essenciais |
|---|---|
| `escritorio` / `usuario` / `membro` | Membro liga usuário a escritório, papel e situação ativa. `UNIQUE(escritorio_id, usuario_id)`. Senha nunca em texto |
| `cliente` | `escritorio_id`, nome, CNPJ normalizado como texto, ativo, `versao_acesso`. `UNIQUE(escritorio_id, cnpj)`, sem unicidade global |
| `atribuicao_cliente` | Cliente, membro responsável, início, fim e autor. Aceita várias atribuições; a política inicial limita a um responsável ativo enquanto D-09 não for confirmada |
| `conta_bancaria` | Cliente, banco, apelido, moeda e identificadores bancários protegidos |
| `socio` | Cliente e nome normalizado. Casar por prefixo gera sinal de confirmação, não prova de identidade |
| `plano_contas` / `conta_contabil` | Versões do plano por cliente. `UNIQUE(plano_id, codigo)`. Importação em área temporária antes da publicação |
| `configuracao_cliente` | Versão, conta transitória, contas de banco, mapa de respostas, contas de regras. Toda referência pertence ao plano do mesmo cliente |
| `competencia` / `competencia_conta` | Uma competência mensal por cliente. `UNIQUE(cliente_id, mes)`, com `mes` no primeiro dia do mês |
| `link_cliente` | Cliente, competência, `hash_token`, `expira_em`, `revogado_em` e escopos. O token original só existe na emissão |

A reatribuição encerra o vínculo anterior e cria o novo. Dados, regras e opções ficam com o cliente. Cadastro referenciado não é apagado, só inativado.

## Movimentação e evidência

| Entidade | Responsabilidade |
|---|---|
| `arquivo` / `envio` | Um envio tem um ou mais arquivos; cada arquivo tem chave privada, SHA-256, tamanho, tipo detectado e data |
| `execucao_processamento` / `extrato` | Execuções versionadas por arquivo; só uma versão publicada por documento integra o conjunto vigente |
| `movimentacao` / `ocorrencia_origem` | A movimentação é o fato canônico; a ocorrência liga o fato ao arquivo, página, linha e identificador bancário |
| `ponto_saldo` / `validacao` | Saldos por linha, dia ou período; resultado com esperado, calculado, diferença, cobertura e motivo. Nunca um único booleano |
| `contraparte` / `sugestao` | Várias sugestões históricas e no máximo uma atual, com conta, origem, evidências, versão e confiança |
| `regra` / `versao_regra` | Prioridade, direção, contraparte ou padrão, conta de destino e evidência de aprovação; uma versão ativa por regra |
| `pergunta` / `item_pergunta` / `resposta` | Pergunta agrupa movimentações por contraparte e competência; opções e mapeamento versionados |
| `revisao` / `estado_movimentacao` | A revisão é um evento (aceitar, corrigir, tornar pendente) com de/para, usuário e versão esperada |
| `exportacao` / `item_exportacao` | Layout e configuração versionados, totais e hash do arquivo; itens com valores e contas exatos usados |
| `chamada_ia` / `evento_auditoria` | Metadados técnicos da IA e trilha das ações relevantes, com retenção própria |
| `tarefa` / `outbox` | Tarefas com estado, tentativas e prazo; eventos pendentes. Consumidores idempotentes |

## Duplicidades

| Situação | Tratamento |
|---|---|
| Mesmo arquivo reenviado | SHA-256 identifica o conteúdo repetido no cliente; a tentativa fica registrada e as movimentações não são recriadas |
| OFX com identificador estável | Unicidade por escritório, conta, origem e identificador externo. Mesmo identificador com valor ou data diferente gera conflito para revisão, nunca sobrescrita silenciosa |
| PDFs sobrepostos sem identificador | Mantém as ocorrências e sinaliza possível duplicidade. Sem `UNIQUE` desses campos: dois pagamentos legítimos podem ser idênticos |
| Nova versão de leitor | Nova execução comparada à anterior; divergência exige reconciliação explícita |
| Envio complementar | Recalcula cobertura e saldos do conjunto vigente da conta |

## Conferência determinística

- Saldo inicial mais a soma dos valores com sinal deve ser igual ao saldo final. Quando houver saldo por linha ou dia, compara no menor intervalo.
- Continuidade com o mês anterior da mesma conta. Sem mês anterior, marca "não verificado", não aprovado.
- Período declarado e datas das movimentações ficam separados. Sem evidência de cobertura até o fim do mês, emite aviso de cobertura não comprovada.
- Liberar uma falha não apaga a falha: o registro guarda usuário, data, motivo e versão. Reprocessar invalida a liberação.

## Exportação reproduzível

| Porta de controle | Regra |
|---|---|
| Acesso e configuração | Contador autorizado; conta transitória existe no plano do cliente |
| Conjunto vigente | Só movimentações publicadas; duplicidade não resolvida bloqueia ou exige liberação auditada |
| Conferência | Extrato aprovado ou liberação vigente; cobertura não comprovada exige decisão registrada |
| Revisão | Toda movimentação não pendente tem aceite ou correção; pendentes saem na transitória |
| Integridade do arquivo | Quantidade, entradas e saídas conferem em centavos. Nunca omitir linhas para a conta fechar |
| Compatibilidade Domínio | Layout versionado e homologado com importação real. Enquanto D-05 estiver aberta, só artefato de teste identificado |

A exportação é uma **fotografia**: em transação, bloqueia a competência, confere as portas e copia os itens. O Excel é gerado fora da transação e o hash é guardado. Baixar de novo entrega o mesmo arquivo; exportar depois de uma correção cria uma nova versão.

## Metas de operação propostas

São metas a validar no piloto, não medições.

| Operação | Meta inicial |
|---|---|
| Uso interativo | p95 de até 500 ms no backend para listagens paginadas e revisões, com 20 usuários concorrentes no cenário sintético |
| Recuperação | RPO de até 24 h e RTO de até 4 h; backup diário e restauração testada |
| Retenção | 90 dias para originais e 30 dias para logs técnicos, até acordo com os pilotos |

**Fonte:** Banco de dados para o Lastro, v1.0 (10/11/2026).
