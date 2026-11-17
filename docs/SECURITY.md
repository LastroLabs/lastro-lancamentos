# Lastro — SECURITY.md (v0.1, 13/11/2026)

Dados, segredos e uso de LLM. Leia antes de mexer em fixtures, em `ia/` ou em qualquer workflow da CI.

> **Premissa:** o repositório é **público** (decisão provável, ainda sem confirmação). Tudo o que for commitado, comentado em PR ou anexado a uma issue deve poder ser lido por qualquer pessoa. Se a decisão mudar para privado, a seção 1 muda; as demais continuam valendo.
>
> Pontos com **[definir]** não têm decisão ainda. Não preencha por conta própria: registre em `docs/decisoes/DECISIONS.md`.
>
> Este documento é regra de engenharia, não parecer jurídico. Base legal da LGPD e contrato com os escritórios precisam de revisão de quem entende do assunto.

## 1. Princípio

Extrato bancário tem dados de terceiros (LGPD). O que não está no repositório não vaza pelo repositório. Por isso:

- Nenhum dado real entra, em lugar nenhum: arquivo, teste, log, mensagem de commit, descrição de PR, comentário, issue, captura de tela.
- Só dados **sintéticos** (seção 3).
- O código pode ser público; os **dados nunca**.

## 2. Proibido no repositório e em qualquer texto público

| Proibido | Exemplos |
|---|---|
| Extrato real, inteiro ou recortado | PDF, OFX, CSV, texto copiado, print |
| Nomes reais | cliente, escritório-piloto, contador, chefe, pessoa, empresa (contraparte de lançamento) |
| Identificadores | CPF, CNPJ, agência, conta, chave Pix, número de documento |
| Segredos | chave de API, token, senha, `.env`, certificado, string de conexão |
| Dumps | banco de dados real, backup, log de produção |

Vale também para **issues, PRs e comentários**: não cole trecho de extrato real para "mostrar o bug". Descreva a estrutura ou reproduza com dado sintético.

## 3. Dados de teste

- Tudo vem de `hx fixtures build` (razão sintético que gera OFX/PDF e o gabarito). Não escreva fixture à mão com dado que pareça real.
- **CPF e CNPJ de teste com dígito verificador inválido.** O `hx check-clean` trata número com DV válido como possível dado real; DV inválido passa como sintético. Exemplo: `111.222.333-00`.
- Nomes de contrapartes inventados e identificáveis como falsos: `CONTRAPARTE_001`, `CLIENTE_TESTE`.
- Valores, datas e descrições são inventados. Não adapte um extrato real "trocando só os nomes": a estrutura de valores e datas também identifica.
- Fixture nova que reproduza um formato de banco: registre a **estrutura** em `docs/bancos/<banco>.md` e gere um equivalente sintético.

## 4. Dados reais dos pilotos (fora do repositório)

Qualquer uso de extrato real, mesmo anonimizado, fica **fora do Git**. Só a estrutura aprendida vai para `docs/bancos/`.

- Onde ficam os arquivos: **[definir]** (pasta local fora do clone, ou armazenamento privado do time).
- Quem tem acesso: **[definir]**.
- Guardião de dados (quem confere e responde por este documento): **[definir]**. Sugestão: pessoa diferente do líder de produto.
- Prazo de guarda e descarte: **[definir]**.
- Anonimização mínima antes de qualquer compartilhamento interno: remover CPF, CNPJ, agência, conta e nomes (substituir por pseudônimos).

## 5. Uso de LLM

- **Só `src/lastro/ia/` fala com o provedor de LLM.** Nenhum outro módulo importa o SDK. A checagem de arquitetura deve acusar o contrário.
- **Antes de qualquer envio, `anonimizar()`** remove CPF, CNPJ, agência e conta.
- **Nomes de contrapartes: proibido enviar** até a decisão D-03.
- O LLM nunca recebe o extrato inteiro se a tarefa pede uma linha. Enviar o mínimo.
- **Nos testes, provedor falso:** sem rede, sem custo e sem dado saindo da máquina. Teste que chama o provedor real é proibido na CI de PR.
- Provedor, contrato de uso e política de retenção dos dados enviados: **[definir]** (decisão de provedor em aberto).
- Registro em log do que foi enviado: pode conter o texto **já anonimizado**, nunca o original.

## 6. Segredos

- Chaves e tokens só em variável de ambiente ou no cofre de segredos do GitHub. Nunca em código, `.env` versionado, exemplo, teste ou log.
- `.env` está no `.gitignore`. Para documentar variáveis, use `.env.example` com valores falsos.
- **Lista de nomes proibidos fora do repositório:** a variável `LASTRO_NOMES_PROIBIDOS` (nomes separados por `;`) existe só na máquina de cada dev e como segredo da CI. A própria lista revelaria os nomes dos pilotos se estivesse no Git.
- Segredo vazou? Considere comprometido: **revogue e troque** antes de qualquer outra ação (seção 9).

## 7. CI e controles automáticos

| Controle | O que faz | O que **não** faz |
|---|---|---|
| `hx check-clean` | Procura CPF/CNPJ com DV válido, prefixos de chave de API (ex.: `sk-`, `AKIA`), linhas `CHAVE=valor` e nomes da lista externa | Não acha nome real fora da lista, nem dado sem padrão. Sem a variável de nomes, essa parte é **pulada** e avisa |
| CI `pr.yml` | Roda `verify` e `check-clean` em todo PR | Não revisa o conteúdo semântico |
| Rubrica de revisão | O revisor **bloqueia** o PR com dado real ou segredo | Depende de leitura humana |
| Arquitetura | Falha se outro módulo importar o SDK de LLM | — |

Regras da CI (repositório público):
- Gatilho **`pull_request`**, nunca `pull_request_target`. PR de fork não recebe segredos.
- Permissões do workflow somente de leitura (`contents: read`), salvo necessidade explícita e revisada.
- **Nenhuma chave de LLM** em job de PR; testes usam o provedor falso.
- Comandos em fichas (`features/*.json`) só podem ser `pytest` ou `ruff`. Qualquer outro é recusado pelo `hx feature verify`.
- Mudanças em `.github/`, `tools/` e neste arquivo exigem aprovação do dono (via CODEOWNERS).
- Aceitar PRs só de branches do repositório, se o time optar por não receber contribuição externa: **[definir]**.

O `check-clean` **reduz** o risco, não o elimina. A segunda barreira é a revisão humana.

## 8. Regras do produto que são segurança

Detalhe nos requisitos (RF-SEG) e nas regras do `AGENTS.md`; aqui só o lembrete.

- **Isolamento no servidor, em toda requisição:** escritório não vê outro escritório; contador só vê clientes atribuídos.
- **Link do cliente imprevisível e com expiração.** Cliente final não tem login.
- **Nada é exportado sem revisão do contador.**
- **Dinheiro e dados do cliente em logs:** logs não registram valores, descrições de lançamentos nem identificadores. Política exata de logs e retenção no produto: **[definir]**.
- Retenção e descarte de extratos no produto, e pedido de exclusão pelo titular (LGPD): **[definir]**.

## 9. Se algo vazar

Aja nesta ordem. Não espere para "ver se alguém notou".

1. **Avise o guardião de dados** (ou o líder, enquanto não houver um) e o time, no canal combinado.
2. **Segredo?** Revogue e troque a chave **antes** de limpar o Git. Apagar o arquivo não desfaz: o histórico e os forks guardam cópia.
3. **Dado real?** Pare de usar o commit. Remova do histórico (reescrita de histórico e pedido de limpeza ao GitHub). **[confirmar o procedimento atual no momento do incidente; não foi verificado]**
4. **Registre** o que vazou, quando, quem viu e o que foi feito, em um arquivo **fora do repositório**.
5. **Comunicação** ao escritório-piloto e, se for o caso, ao titular: **[definir]**, com apoio de quem entende de LGPD.
6. **Depois:** o que deixou passar vira regra ou check novo (issue `harness:`).

## 10. Checklist antes de abrir um PR

- [ ] `hx check-clean` verde, com `LASTRO_NOMES_PROIBIDOS` definida na sua máquina
- [ ] Nenhuma fixture escrita à mão; CPF/CNPJ de teste com DV inválido
- [ ] Nada de dado real em descrição, comentário ou captura de tela
- [ ] Chamadas a LLM só por `src/lastro/ia/`, depois de `anonimizar()`
- [ ] Nenhum segredo, `.env` ou chave nos arquivos nem nos logs

## Em aberto neste documento

| Tema | Decisão pendente |
|---|---|
| Repositório | Confirmar público; se privado, revisar seção 1 |
| Guardião de dados | Quem é |
| Dados dos pilotos | Onde ficam, quem acessa, prazo de guarda |
| Provedor de LLM | Qual, contrato e retenção dos dados enviados |
| Nomes de contrapartes | D-03 |
| Logs e retenção no produto | Política e descarte |
| Vazamento | Procedimento de limpeza do histórico e comunicação |
| PRs externos | Aceitar ou não |