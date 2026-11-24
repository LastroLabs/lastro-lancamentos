# CAD-01 · Validar CNPJ numérico e alfanumérico do cliente

- Responsável: marrathomaz · Branch: `feat/CAD-01-validar-cnpj-numerico-e-alfanumerico-do` · Início: 23/11/2026
- Ficha: `features/CAD-01.json` (estado e critérios ficam lá; não repita aqui)

<!--
Como preencher (agente, ao encerrar a sessão):
- REESCREVA as seções do topo: Objetivo, Próxima ação, Bloqueios e perguntas.
- ACRESCENTE, sem apagar o que já existe, em Feito, Rodei, Falhou e Decisões.
  Cada linha começa com a data (DD/MM) e a sessão, ex.: "- 14/11 · S2 · ...".
- Registre só o que realmente rodou. Sem dado real, nome de cliente ou segredo.
- Não escreva estado (passing etc.) aqui: ele fica na ficha, gravado pelo script.
-->

## Objetivo
Validação e normalização pura de CNPJ numérico e alfanumérico (padrão julho/2026, IN RFB nº 2.229/2024) no módulo `registry` (sem banco nem HTTP), devolvendo 14 caracteres maiúsculos sem máscara ou mensagem de erro em português simples (RF-CAD-01).

## Próxima ação
Alinhar a descrição do PR #56 quanto à checagem de nomes (ou rodar `hx check-clean` com `LASTRO_NOMES_PROIBIDOS` definida), rodar `sh tools/hx verify` com Docker ativo se quiser reconfirmar localmente, e fazer `git push` da branch `feat/CAD-01-validar-cnpj-numerico-e-alfanumerico-do`.

## Bloqueios e perguntas
- (nenhum)

## Feito
- 23/11 · S1 · Feature iniciada (commit `3f3aff2`), plano e tasks aprovados em `planos/CAD-01/` (commit `fc9b44e`).
- 23/11 · S1 · Testes dos critérios c1 a c4 escritos em `tests/registry/test_cnpj.py` com geração dinâmica de CNPJ válido em runtime (commit só de testes `2c31a61`).
- 24/11 · S1 · Mensagem ajustada para `'Confira os caracteres.'` (commit `ffdac94`); implementados `src/lastro/registry/contracts.py`, `src/lastro/registry/service.py` e `src/lastro/registry/cnpj.py` (commit `7ee296c`), sem editar `tests/`.
- 24/11 · S2 · Alinhadas as mensagens de exemplo em c3 e c4 de `features/CAD-01.json` (`'Confira os caracteres.'`) e preenchido `progress/CAD-01.md`.
- 24/11 · S3 · Documentado o contrato v0 (`CnpjValidationResult` e `validate_cnpj`) na seção 6 do `ARCHITECTURE.md` e criada a página `docs/modulos/registry.md` (campos, mensagens oficiais, aviso à responsável da `CAD-03` e impactos em `CAD-03`, `DB-01`, `P-13` e `tools/harness.py`).
- 24/11 · S3 · Atualizado o status de `planos/CAD-01/plan.md` para aprovado e corrigidas 4 ocorrências residuais de `'Confira os números.'` e checkboxes em `planos/CAD-01/tasks.md`.

## Rodei
- 24/11 · S1 · `hx feature verify CAD-01` → c1 a c4 ok; evidência registrada no commit `c0c3cd7` (sobre o commit `7ee296c2f0d3`).
- 24/11 · S2 · `git diff 2c31a61 -- tests/` → vazio (testes intactos desde o commit só de testes).
- 24/11 · S2 · `sh tools/hx verify` → `[1/2] ruff check . OK`, `[2/2] pytest -q OK`, Arquitetura e E2E pulados; `RESULTADO: OK`.
- 24/11 · S2 · `sh tools/hx check-clean` → `0 achado(s)`, `RESULTADO: OK` (aviso: `LASTRO_NOMES_PROIBIDOS` não definida neste ambiente).
- 24/11 · S3 · `sh tools/hx check-clean` → `0 achado(s)`, `RESULTADO: OK` (aviso: `LASTRO_NOMES_PROIBIDOS` não definida neste ambiente).
- 24/11 · S3 · `git diff 2c31a61 -- tests/` → vazio (testes intactos).
- 24/11 · S3 · Execução direta em Python dos 5 testes de `tests/registry/test_cnpj.py` (`PYTHONPATH=src python3 ...`) → 5/5 OK (nenhum arquivo `.py` alterado na S3).

## Falhou
- 24/11 · S2 · Nenhuma falha de código ou teste; apenas aviso de `LASTRO_NOMES_PROIBIDOS` não definida ao rodar `hx check-clean` sem a variável no ambiente.
- 24/11 · S3 · `sh tools/hx verify` não pôde rodar nesta sessão porque o daemon Docker estava indisponível neste ambiente (`docker info` falhou); apenas arquivos Markdown foram alterados na S3.

## Decisões
- 23/11 · S1 · Implementação própria em Python puro sem lib externa (D1); regra pura em `registry/` sem banco/HTTP (D2); retorno estruturado `CnpjValidationResult` sem exceção (D3); regex ASCII estrita, rejeição de 14 caracteres iguais e Módulo 11 com `ord(c) - 48` (D4); contrato v0 em `lastro.registry.contracts`/`service` (D5); geração dinâmica de CNPJs válidos nos testes para não commitar literais válidos (D6); aceitação de `A–Z` completo e mensagem padronizada com `'Confira os caracteres.'` (perguntas 1 a 5). Detalhes em `planos/CAD-01/plan.md`.

## Fim de sessão
- [x] `hx verify` verde, ou a falha está descrita em "Falhou"
- [x] Nada quebrado nem pela metade na branch; commit feito
- [x] "Próxima ação" atualizada
- [x] Nenhum dado real nem segredo nas anotações
