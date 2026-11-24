# Tasks — IA-01 · Anonimizar descrições: remover CPF, CNPJ, agência e conta, e proteger nomes por nível, preservando palavras de operação e de atividade

**Plan:** planos/IA-01/plan.md · **Ficha:** features/IA-01.json
**Ordem:** T1 → revisão humana dos testes → commit só-de-testes (anotar o hash) → T2 em diante (sessão nova, sem editar `tests/`)

Dados de referência (inventados, iguais aos da ficha): sócio `SOCIO TESTE A`; contrapartes `MARIA TESTE SOUZA`, `JOAO TESTE LIMA`, `ROSA TESTE CAMPOS`, `PADARIA TESTE LTDA`, `POSTO TESTE SAO JORGE LTDA`, `FARMACIA TESTE CENTRO`. CPF e CNPJ gerados na hora pelo teste.

---

## [x] T1 · Escrever os testes dos critérios
- **Critérios da ficha:** c1 a c8
- **Regra de negócio (em linguagem simples):** antes de mandar uma descrição de extrato para a IA, o sistema esconde o que identifica alguém (documento, agência, conta e nome) e deixa o que ajuda a classificar (PIX, TARIFA, valor, data). Cada teste reproduz um exemplo da ficha.
- **Critérios de aceite:**
  - [x] `tests/ai/test_anonimizar.py` com as 11 funções citadas em `verificacao`
  - [x] CPF e CNPJ (numérico e alfanumérico, DV certo e errado) gerados na hora; nenhum documento fixo no arquivo
  - [x] c8 com o corpo de 200 nomes gerado por fixture do próprio teste (plan, D9) e a regra de "pedaço" da D8
  - [x] c4 prova a recusa ao criar o app (`create_app`) com o nível `medio`, com a mensagem exata da ficha
  - [x] Todos falham hoje por falta de `lastro.ai` (ImportError ou equivalente), não por erro no teste
- **Exemplos:** `PIX ENVIADO <CPF>` → `PIX ENVIADO [CPF]`; `TED AG 1234 C/C 56789-0` → `TED [AGENCIA] [CONTA]`
- **Arquivos:** `tests/ai/test_anonimizar.py`
- **Fora do escopo:** código de produção; `conftest.py` compartilhado
- **Pronto quando:** `docker compose run --rm dev pytest tests/ai/test_anonimizar.py -q` mostra só falhas esperadas

## [x] T2 · Contratos e CPF/CNPJ
- **Critérios da ficha:** c1, c5
- **Regra de negócio (em linguagem simples):** CPF e CNPJ saem do texto em qualquer formato que um banco imprime (com ou sem pontos, com dígito certo ou errado, CNPJ com letras), e no lugar fica um aviso do tipo. O resto da frase não muda.
- **Critérios de aceite:**
  - [x] `NameProtectionLevel` e `InvalidNameProtectionLevelError` em `ai/contracts.py`; `anonymize()` em `ai/service.py`
  - [x] CPF com máscara, sem máscara e com máscara parcial (`***.123.456-**`) → `[CPF]`
  - [x] CNPJ numérico e alfanumérico, maiúsculo ou minúsculo, com e sem máscara → `[CNPJ]`
  - [x] Texto sem documento sai idêntico (c5)
- **Exemplos:** `TED RECEBIDA <14 dígitos>` → `TED RECEBIDA [CNPJ]`; `IOF 15/10/2026` → igual
- **Arquivos:** `src/lastro/ai/contracts.py`, `src/lastro/ai/service.py`, `src/lastro/ai/anonymization.py`
- **Reaproveitar:** regra do DV alfanumérico (`ord(c) - 48`) · **Não criar:** import de `tools/`
- **Fora do escopo:** nomes; configuração
- **Decisões relacionadas:** D1, D2, D3
- **Pronto quando:** `pytest tests/ai/test_anonimizar.py::test_cpf_e_cnpj_numericos_removidos tests/ai/test_anonimizar.py::test_cnpj_alfanumerico_removido -q` passa

## [x] T3 · Agência e conta
- **Critérios da ficha:** c2
- **Regra de negócio (em linguagem simples):** número de agência e de conta identifica a pessoa no banco; sai junto com a palavra que o anuncia (`AG`, `AGENCIA`, `C/C`, `CC`, `CONTA`, `CTA`), com ou sem `:`, com ou sem dígito depois do traço.
- **Critérios de aceite:**
  - [x] `AG 1234`, `AGENCIA 0001`, `AG:4321` → `[AGENCIA]`
  - [x] `C/C 56789-0`, `CONTA 9876543-2`, `CC:11223-4` → `[CONTA]`
  - [x] `CONTA` sem número depois fica como está
- **Exemplos:** `DOC AG:4321 CC:11223-4` → `DOC [AGENCIA] [CONTA]`
- **Arquivos:** `src/lastro/ai/anonymization.py`
- **Fora do escopo:** número solto sem palavra-chave
- **Decisões relacionadas:** D2
- **Pronto quando:** `pytest tests/ai/test_anonimizar.py::test_agencia_e_conta_removidas -q` passa

## [x] T4 · Contraparte e pseudônimos no nível estrito
- **Critérios da ficha:** c3, c8 (nível estrito)
- **Regra de negócio (em linguagem simples):** depois das palavras de operação (PIX, TED, BOLETO...) vem quem pagou ou recebeu. Esse nome vira `PESSOA_nnn` ou `EMPRESA_nnn`, sempre o mesmo para o mesmo nome no lote. Sócio cadastrado, mesmo cortado no extrato, recebe o pseudônimo do sócio.
- **Critérios de aceite:**
  - [x] Operação, conector na borda, número, data, valor e marcador ficam; cada sequência do resto vira um pseudônimo
  - [x] Empresa por sufixo societário ou palavra de atividade; `ME`/`MEI`/`EPP`/`EI` não decidem o tipo; nome que aparece sozinho no lote é pessoa em todo o lote
  - [x] Numeração por ordem de aparição, 3 dígitos, contadores separados
  - [x] Sócio casa por prefixo (o mais curto com 6+ caracteres)
- **Exemplos:** `PIX SOCIO TESTE` com sócio `SOCIO TESTE A` → mesmo `PESSOA_nnn` do sócio; `BOLETO PADARIA TESTE LTDA` → `BOLETO EMPRESA_001`
- **Arquivos:** `src/lastro/ai/anonymization.py`
- **Não criar:** lista de nomes próprios
- **Fora do escopo:** nível `pessoas_protegidas` (T5)
- **Decisões relacionadas:** D4, D5, D6
- **Pronto quando:** `pytest tests/ai/test_anonimizar.py -q -k "pseudonimos_estaveis or pseudonimo_de_empresa"` passa

## [x] T5 · Listas versionadas e nível `pessoas_protegidas`
- **Critérios da ficha:** c6, c7, c8
- **Regra de negócio (em linguagem simples):** no nível intermediário, a palavra que diz o ramo (POSTO, FARMACIA) fica visível, porque ajuda a classificar, e o resto do nome vira pseudônimo. As palavras que podem ficar visíveis vêm de uma lista com fonte pública; palavra de ramo que também é prenome (ROSA, MARINA) vai para a lista de conflito e nunca fica visível.
- **Critérios de aceite:**
  - [x] `src/lastro/ai/preservation_lists.yaml` com `operacao` (40+), `atividade` (100+) e `conflito`, cada palavra com `palavra`, `fonte` e `revisado`; sem repetição entre listas
  - [x] Atividade conferida contra a subclasse CNAE citada; conflito = atividade presente nos nomes do Censo 2010 (plan, D7)
  - [x] `pessoas_protegidas`: atividade em claro, resto da contraparte em pseudônimo; o nível estrito não muda
  - [x] `PyYAML` em `dependencies` e `uv.lock` atualizado
- **Exemplos:** `PIX ENVIADO POSTO TESTE SAO JORGE LTDA` → `PIX ENVIADO POSTO EMPRESA_001`; `PIX ROSA TESTE CAMPOS` → `PIX PESSOA_nnn`
- **Arquivos:** `src/lastro/ai/preservation_lists.yaml`, `src/lastro/ai/anonymization.py`, `pyproject.toml`, `uv.lock`
- **Fora do escopo:** script que gera a lista (a conferência fica registrada no plan e no PR)
- **Decisões relacionadas:** D4, D7, D8
- **Pronto quando:** `pytest tests/ai/test_anonimizar.py -q -k "listas or intermediario or nenhum_nome"` passa

## [x] T6 · Nível por configuração e recusa ao iniciar
- **Critérios da ficha:** c4
- **Regra de negócio (em linguagem simples):** o escritório escolhe o nível numa configuração; sem configurar, vale o estrito (D-03). Um valor errado não pode deixar o sistema rodando sem proteção: a aplicação nem sobe e diz o que fazer. Documento, agência e conta somem em todos os níveis.
- **Critérios de aceite:**
  - [x] Variável `NAME_PROTECTION_LEVEL`; ausente → `estrito`
  - [x] Valor desconhecido → `InvalidNameProtectionLevelError` com a mensagem exata da ficha; `create_app()` falha ao ser criado
  - [x] `desligado` deixa o nome em claro e troca documento, agência e conta
  - [x] `.env.example` e `docker-compose.yml` (serviço `api`) passam a variável
- **Exemplos:** `medio` → "Nível de proteção de nomes inválido: medio. Use estrito, pessoas_protegidas ou desligado."
- **Arquivos:** `src/lastro/ai/service.py`, `src/lastro/api/app.py` (1 linha), `.env.example`, `docker-compose.yml`
- **Fora do escopo:** guardar o nível no banco ou por escritório
- **Decisões relacionadas:** D1; pergunta 1
- **Pronto quando:** `pytest tests/ai/test_anonimizar.py -q -k "configuravel or nivel_invalido"` passa

## [x] T7 · Verificação final
- **Critérios de aceite:**
  - [x] `git diff <hash-dos-testes> -- tests/` vazio
  - [x] `ruff check .` limpo
  - [x] `hx check-clean` e `hx verify` em OK
  - [x] `hx feature verify IA-01` grava `passing`
  - [x] `docs/modulos/ai.md` com o uso de `anonymize()` e as armadilhas
- **Pronto quando:** os três comandos do `hx` terminam com código 0
