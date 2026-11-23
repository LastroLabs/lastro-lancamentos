---
title: Modelo físico e operações
description: Tipos, índices, concorrência, isolamento e operações transacionais previstos para o MVP.
---

A implementação deve seguir [BD-01 a BD-08](/lastro-lancamentos/decisoes/banco-de-dados/) e a [arquitetura aprovada](/lastro-lancamentos/decisoes/arquitetura/). Esta página especifica controles esperados; não contém migração executada nem resultado de teste de integração.

## Tipos e escopo

Identificadores técnicos e referências usam **UUID**. Valores e saldos usam **BIGINT em centavos com sinal**: entrada positiva e saída negativa. Datas bancárias usam `DATE`; os instantes de envio, revisão e revogação usam `TIMESTAMPTZ`. O mês da competência é representado pelo primeiro dia. CNPJ, códigos contábeis e identificadores bancários são texto; não devem ser convertidos em números.

## Recorte físico da DB-01

Referência: `features/DB-01.json`, c1–c6; decisões do responsável em 23/11/2026 registradas em `docs/decisoes/DECISIONS.md`, seção 5. Esta seção reúne critérios explícitos e complementos F1–F5/D1–D3 confirmados pelo responsável e incorporados a c1/c2/c5/c6 com autorização em 23/11/2026 (R1 do plano). Não apresenta migração executada.

**Divisão aprovada:** nomes físicos portugueses singulares da ficha, como exceção ao CODING_STANDARDS.md; esquema e restrições na DB-01, políticas RLS na NUC-03. A NUC-03 precisa estar concluída antes do uso com dados de piloto. Não criar políticas permissivas de contorno. FKs não substituem isolamento de acesso.

**Leitura da tabela:** `NN` significa `NOT NULL`; PK também implica não nulabilidade. Todo `id` é UUID v4 gerado pelo banco com `gen_random_uuid()` (D1). Referências são UUID. Nulabilidade incorpora F1 confirmado; defaults temporais permanecem somente os explicitados na ficha (F2).

| Tabela | Colunas do recorte confirmado |
|---|---|
| `escritorio` | `id uuid PK`; `nome text NN`; `ativo boolean NN DEFAULT true` |
| `usuario` | `id uuid PK`; `identificador_login text NN UNIQUE`; `nome text NN`; `ativo boolean NN DEFAULT true`; `credencial_hash text NULL` |
| `membro` | `escritorio_id uuid`; `id uuid`; `usuario_id uuid NN`; `papel text NN`; `ativo boolean NN DEFAULT true`; PK `(escritorio_id, id)`; UNIQUE `(escritorio_id, usuario_id)` |
| `sessao` | `escritorio_id uuid`; `id uuid`; `membro_id uuid NN`; `hash_token text NN UNIQUE`; `criada_em timestamptz NN`; `expira_em timestamptz NN`; `encerrada_em timestamptz NULL`; PK `(escritorio_id, id)` |
| `convite` | `escritorio_id uuid`; `id uuid`; `membro_id uuid NN`; `hash_token text NN UNIQUE`; `criado_por uuid NN`; `criado_em timestamptz NN DEFAULT now()`; `expira_em timestamptz NN`; `usado_em timestamptz NULL`; `revogado_em timestamptz NULL`; PK `(escritorio_id, id)` |
| `cliente` | `escritorio_id uuid`; `id uuid`; `nome text NN`; `cnpj_normalizado text NN`; `ativo boolean NN DEFAULT true`; `versao_acesso bigint NN DEFAULT 0`; PK `(escritorio_id, id)`; UNIQUE `(escritorio_id, cnpj_normalizado)` |
| `atribuicao` | `escritorio_id uuid`; `cliente_id uuid`; `id uuid`; `membro_id uuid NN`; `atribuido_por uuid NN`; `inicio timestamptz NN`; `fim timestamptz NULL`; PK `(escritorio_id, cliente_id, id)` |

Nenhuma coluna de plano ou conta contábil em `cliente` nesta migração; entram na DB-02. `credencial_hash` é nulo enquanto o convite não foi aceito; não se cria trigger nem fluxo de aceite por inferência. Não guardar código/token de convite em claro.

### Chaves estrangeiras (c2 e F3/F4 confirmados)

| Origem | Colunas | Destino |
|---|---|---|
| `membro` | `usuario_id` | `usuario(id)` |
| `membro` | `escritorio_id` | `escritorio(id)` |
| `cliente` | `escritorio_id` | `escritorio(id)` |
| `sessao` | `(escritorio_id, membro_id)` | `membro(escritorio_id, id)` |
| `convite` | `(escritorio_id, membro_id)` e `(escritorio_id, criado_por)` | `membro(escritorio_id, id)` |
| `atribuicao` | `(escritorio_id, cliente_id)` | `cliente(escritorio_id, id)` |
| `atribuicao` | `(escritorio_id, membro_id)` e `(escritorio_id, atribuido_por)` | `membro(escritorio_id, id)` |

F3 confirma as FKs diretas membro/cliente para escritório, sem FKs diretas redundantes em sessão, convite ou atribuição. Todas as FKs usam ON DELETE/UPDATE NO ACTION e NOT DEFERRABLE, sem cascata (F4). Complementos transcritos na ficha com autorização em R1.

### CHECKs e índices explícitos (c1/c3/c4/c5)

- `membro`: `papel IN ('chefe', 'contador')`.
- `sessao`: `expira_em > criada_em`.
- `cliente`: `versao_acesso >= 0`.
- `atribuicao`: `fim IS NULL OR fim > inicio`; índice único parcial `(escritorio_id, cliente_id) WHERE fim IS NULL`.
- `convite`: `hash_token ~ '^[0-9a-f]{64}$'`; `expira_em > criado_em`; `usado_em IS NULL OR revogado_em IS NULL`; índice único parcial `(escritorio_id, membro_id) WHERE usado_em IS NULL AND revogado_em IS NULL`.

Esse índice mantém um convite expirado na unicidade se não usado nem revogado. A3 exige revogar o convite expirado ainda pendente antes da reemissão; o serviço desse fluxo não faz parte da DB-01. As 48 h do exemplo não são política de validade. O esquema aceita chefe como responsável (c3/P-09) e o mesmo usuário em escritórios distintos (c4).

**Complemento D2/F5, decidido pelo responsável em 23/11/2026:** os dois índices de `convite` nas mesmas colunas têm nomes distintos, sem alterar suas propriedades:

| Nome | Colunas | Único | Predicado |
|---|---|---|---|
| `ix_convite_escritorio_id_membro_id` | `(escritorio_id, membro_id)` | Não | Sem predicado |
| `uq_convite_escritorio_id_membro_id_pendente` | `(escritorio_id, membro_id)` | Sim | `usado_em IS NULL AND revogado_em IS NULL` |

O primeiro integra os seis índices auxiliares de F5; o segundo mantém a restrição de um convite pendente por membro. Este complemento de nomes prevalece sobre a aplicação indistinta de `ix_<table>_<columns>` aos dois índices. Registro: `docs/decisoes/DECISIONS.md`, seção 5, e D2 em `planos/DB-01/plan.md`.

### Migração e permissões explícitas (c1/c6)

Uma revisão Alembic após a base NUC-01 (`0001` no repositório consultado), sem criar dados. Seis modelos em `src/lastro/access/models.py`, cliente em `src/lastro/registry/models.py`. Downgrade remove as sete tabelas e retorna à revisão anterior; reaplicar restaura o mesmo esquema. O papel da aplicação lê/grava sem ser dono e não pode apagar a tabela `escritorio`. A DB-01 não implementa login, aceite de convite, serviço de reatribuição nem políticas RLS.

### Complementos F1–F5 confirmados em 23/11/2026

O responsável confirmou todas as decisões abaixo e autorizou sua inclusão nos critérios, concluída em R1. Isso não constitui aprovação integral do plano.

| # | Detalhe complementado | Decisão confirmada | Impacto |
|---|---|---|---|
| F1 | Nulabilidade de `membro.usuario_id`, `sessao.membro_id`, `sessao.criada_em`, `sessao.expira_em`, `atribuicao.membro_id`, `atribuicao.atribuido_por`. | `NOT NULL` em todos, conforme confirmação explícita do responsável. PKs já impõem NN às colunas que as compõem. | Evita FK/CHECK contornados por NULL; c1/c2. |
| F2 | Defaults temporais além de `convite.criado_em`. | Exigir preenchimento explícito para `sessao.criada_em`, `sessao.expira_em`, `atribuicao.inicio` e `convite.expira_em`, sem novos defaults; manter só `now()` explicitado. Não fixar duração de sessão/convite nesta feature. | c1/c5; não transformar 48 h em regra. |
| F3 | Lista completa de FKs diretas para escritório. | Acrescentar `membro.escritorio_id` e `cliente.escritorio_id` → `escritorio(id)`; as FKs compostas de sessão/convite/atribuição já asseguram pertencimento indiretamente. Não adicionar FKs diretas redundantes nessas três sem necessidade aprovada. | Completa relação lógica; apresentar complemento de c1/c2 antes de alterar ficha. |
| F4 | `ON DELETE`, `ON UPDATE` e adiamento das FKs. | `NO ACTION` em ambas, `NOT DEFERRABLE`, sem cascata; preservar histórico e rejeitar referências inválidas na escrita. | c2/c3/c6; não introduzir deleção automática. |
| F5 | Índices auxiliares de FK e nomes exatos de constraints/índices. | Criar os seis índices auxiliares não cobertos por prefixo de PK/UNIQUE: `membro(usuario_id)`, `sessao(escritorio_id, membro_id)`, `convite(escritorio_id, membro_id)` e `(escritorio_id, criado_por)`, `atribuicao(escritorio_id, membro_id)` e `(escritorio_id, atribuido_por)`. O índice parcial de convite só cobre pendentes. Lista e convenção D2 confirmadas; sem unicidade global extra de `id`. | c1, manutenção e desempenho; sem requisito de carga inventado. |

D1–D3 confirmados: UUID v4 com gen_random_uuid(), Base/MetaData comum em core/models.py, modelos nos caminhos A1, classes/convenção central D2 e migração explícita independente dos modelos vivos. Prazo de sessão, algoritmo de credencial, normalização/case do login e regras fiscais de CNPJ não são resolvidos pela DB-01; não acrescentar CHECKs, triggers ou normalização a partir dessas lacunas.

### Continuação das convenções gerais

A ficha CAD-01 em revisão prevê CNPJ numérico e alfanumérico. O modelo armazena o identificador como texto normalizado e não inventa regra de validação além da ficha. O status HTTP de dado inválido permanece em P-13.

Colunas centrais de valores, contas, estados e relacionamentos são tipadas. `JSONB` fica restrito a evidências variáveis, metadados sanitizados e fotografias validadas. A confiança pode usar categoria e pontuação limitada; a pontuação não é uma probabilidade calibrada por presunção. O limite continua pendente em D-08.

O [modelo lógico](/lastro-lancamentos/modelagem/modelo-logico/) repete `escritorio_id` e `cliente_id` nas FKs das tabelas subordinadas. Identidade, associação ao escritório e sessão possuem seu escopo próprio; não recebem um cliente fictício para satisfazer essa convenção.

## Restrições e índices

As PKs e FKs impedem referências cruzadas entre escritórios e clientes. Declarar `NOT NULL` para os vínculos obrigatórios e `CHECK` para estados válidos, intervalos temporais, mês no primeiro dia e contagens não negativas. Os campos de conta candidata e conta final permanecem opcionais onde “não sei” e pendência são resultados válidos.

Usar índices parciais para limitar a um vínculo de responsável vigente por cliente, uma sugestão atual por movimentação e uma versão ativa de cada regra histórica. Preservar unicidade de código por versão do plano, de competência por cliente/mês e de posição do item por exportação. Indexar as FKs e os filtros por cliente, competência, conta, data e estado. O `pg_trgm` aprovado em BD-06 consulta exclusivamente o histórico do próprio cliente.

O hash reconhece conteúdo reenviado, mas não autoriza apagar pagamentos legítimos. Para identificador externo estável, a unicidade considera escritório, cliente, conta, origem e identificador. Identificador repetido com data ou valor divergente gera conflito. Sem identificador, duas linhas iguais são preservadas e sinalizadas.

## Sessão, autorização e reatribuição

A sessão no servidor referencia o membro do escritório, tem validade e pode ser encerrada. Não guarda uma carteira fixa que continue autorizando acesso após a reatribuição. A aplicação confere o papel e os vínculos vigentes em toda requisição; RLS reforça o escopo de leitura e escrita, sob papel de banco diferente do proprietário das tabelas.

P-01 prevê **401** sem sessão válida, **403** quando o papel não permite a ação e **404 idêntico ao de inexistente** para recurso de outro escritório ou carteira. Só o chefe cadastra o cliente. A visão de todos os clientes do escritório não implica autorização para revisar, exportar, editar cadastros ou emitir links: pela P-09, o chefe vê só a lista (id, nome, CNPJ e responsável) e acessa só os clientes atribuídos a ele. Chefe do mesmo escritório que não é o responsável recebe **403**; contador de outra carteira continua recebendo o 404. A gestão de atribuição só exige o papel de chefe.

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
