# HAR-05 · plano de contas sintético em TXT (refatora a HAR-03)

**Dono:** camposs04 · **Depende de:** HAR-03 · **Decisão:** `DECISIONS.md` §11 (T8, T12) · **Revisão extra:** dono do harness (`tools/` tem CODEOWNERS).

A fixture troca `planos/<cliente>.xlsx` por `planos/<cliente>.txt` e o plano ganha grupos. É a única ficha desta mudança que mexe em testes de outra ficha `passing` (a HAR-03), e só nos da lista T12.

## O que muda

| Arquivo | Mudança |
|---|---|
| `tools/fixtures_sinteticas.py` | `PLANO_BASE` vira `(código com pontos, nome, tipo)` com 10 grupos e 13 analíticas, com os grupos antes das contas abaixo deles (`1`, `1.1`, `1.1.01`…; a transitória `9.9.99` fica abaixo de `9` e `9.9`). Cada conta do `cadastro.json` ganha `classificacao`, `reduzido` e `tipo`; `plano_planilha` vira `plano_txt`. Sai todo o código do `.xlsx` (`zipfile`, XML, `membros_xlsx`). Entra o TXT de 78 colunas em UTF-8 com CRLF |
| `tools/harness.py` | `_exigir_sem_documentos(arquivos)` perde o parâmetro `membros_xlsx` e o ramo `.xlsx`; a chamada em `cmd_fixtures_build` acompanha. Sem isso, o build quebra com `AttributeError` |
| `tests/harness/test_fixtures_plano_txt.py` | novo, com os 3 testes da ficha |
| `tests/harness/test_fixtures.py` | só o que está na T12 |
| `features/HAR-03.json` | c1, c6 e `verificacao`, pelo arquivo deste pacote |

## Ordem

1. `hx feature start HAR-05`, com a árvore limpa. O `start` recusa árvore suja, então ele vem **antes** de escrever os testes. Commit de `progress/HAR-05.md` e da ficha.
2. **Commit só de testes:** o arquivo novo, as mudanças da T12 em `test_fixtures.py` e a edição da `features/HAR-03.json` (só conteúdo). Anote o hash.
3. `hx feature verify HAR-03`: falha (c3 e c6) e grava `regressed`. **Faça commit da ficha antes do próximo verify**: o `hx` recusa árvore suja.
4. `hx feature verify HAR-05`: falha nos 3 e a ficha continua `in_progress`.
5. Implementação, sem tocar em `tests/`.
6. `hx feature verify HAR-05` e depois `hx feature verify HAR-03`, com commit de cada ficha entre um e outro: as duas ficam `passing`.
7. `hx fixtures build` e `hx check-clean`: 0 achados.

## Armadilhas que a simulação encontrou

- **Laço infinito.** O teste da HAR-03 `test_build_aborta_se_linha_tiver_documento_valido` troca o detector por um que acusa **toda linha com dígito**. Um gerador que refaz o reduzido "até sair limpo" nunca termina. Ponha um limite (a simulação usou 20 tentativas) e, se esgotar, deixe a linha como está: a trava D7 aborta o build e o teste passa. Esse teste **não** está na lista T12 e não pode mudar.
- **Teste que passa vazio.** Um teste que só confere "nenhum `.txt` tem documento" passa antes da implementação, porque ainda não existe `.txt`. O c3 exige também ao menos 50 planos conferidos.
- **Sequência de dígitos.** Na linha, o reduzido (7 dígitos) encosta na classificação (`00071921101`). Analítica com classificação de 4 dígitos gera exatamente 11 dígitos, que é candidata a CPF. Com o `\b` do `check-clean`, só sequências de exatamente 11 ou 14 dígitos contam (cerca de 1% vira documento). O gerador confere com `harness.tipos_da_linha(linha, [])` e passa ao reduzido seguinte.
- **Não mude a sequência dos OFX.** Sorteie os reduzidos num `_Sorteio` separado, derivado da semente e do cliente. Assim os OFX e os gabaritos da semente 1 continuam iguais.
- **Nome de teste em uma só ficha.** Os testes novos têm nomes próprios. Se a HAR-05 listar um nome que já está na HAR-03, todo comando do `hx` falha ao carregar as fichas.

## Pronto quando

HAR-05 e HAR-03 estão `passing` pelo `hx`, o `pytest` completo está verde (IA-02, CAD-02 e DB-02 inclusos), `hx check-clean` dá 0 achados e `git diff <hash> -- tests/` está vazio. O leitor da CAD-02 lê os 3 `.txt` gerados sem erro e com os mesmos campos do cadastro (conferido na simulação: 23 contas por cliente).

Referência: `referencia_simulacao/HAR-05_1_testes.patch` e `HAR-05_2_implementacao.patch`.
