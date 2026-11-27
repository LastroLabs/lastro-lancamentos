# Plan — HAR-05 · Plano de contas sintético em TXT

**Status:** pronto para revisão; testes aguardam aprovação humana
**Branch:** `feat/HAR-05-gerar-o-plano-de-contas-sintetico-em-txt` · **Data:** 27/11/2026 · **Responsável:** RaissaOliveira19
**Tasks:** `planos/HAR-05/tasks.md`

## 1. A decidir (humano)

Não há decisão de produto nova: formato, contrato do cadastro e exceção aos testes antigos foram aprovados em `docs/decisoes/DECISIONS.md` §11 (T1, T8 e T12). Antes de escrever testes, a responsável precisa revisar este plano e confirmar D1–D4. O dono da HAR-03 e o CODEOWNER de `tools/` revisam o PR conforme T12.

Mudanças sugeridas na ficha HAR-05: nenhuma. A ficha HAR-03 muda apenas c1, c6 e `verificacao`, na lista fechada da T12.

## 2. Decisões técnicas propostas

### D1 · Acrescentar grupos ao plano sem alterar as contas analíticas existentes
- **Alternativas:** reconstruir o plano e os gabaritos; inserir os 10 grupos antes das 13 analíticas atuais.
- **Escolhida:** inserir os grupos e preservar os códigos analíticos e `conta_correta` dos gabaritos. Cada item de `plano` ganha `classificacao` (código sem pontos), `reduzido` de 7 dígitos e `tipo` (`S` ou `A`); a transitória continua a analítica `9.9.99`.
- **Motivo:** preserva as movimentações sintéticas existentes e prova a hierarquia exigida por c2.
- **Impacto:** c1, c2; T1, T2.
- [ ] Confirmada pela responsável.

### D2 · Sortear reduzidos com sequência independente
- **Alternativas:** usar o `_Sorteio` atual do modelo; derivar um `_Sorteio` próprio da semente e do cliente.
- **Escolhida:** sorteio próprio com derivação estável da semente e do identificador sintético do cliente, sem usar `hash()` do Python.
- **Motivo:** não deslocar a sequência que já gera OFX, valores e gabaritos; o reduzido fica reproduzível e único no plano de cada cliente.
- **Impacto:** c1–c3; T2, T3.
- [ ] Confirmada pela responsável.

### D3 · Renderizar TXT com 78 colunas e proteção limitada contra documentos
- **Alternativas:** gerar a linha e confiar só na trava D7; verificar cada linha e sortear outro reduzido quando houver achado.
- **Escolhida:** linha UTF-8 com CRLF e campos de largura fixa (`[0:7]`, `[7:27]`, `[27:67]`, `[67]`, dez espaços finais); conferir com `harness.tipos_da_linha(linha, [])`. Em achado, tentar outro reduzido até um limite; esgotado o limite, deixar a trava D7 recusar o build antes da gravação.
- **Motivo:** atende c1/c3 sem laço infinito no teste de segurança da HAR-03.
- **Impacto:** c1, c3; T1, T3.
- [ ] Confirmada pela responsável.

### D4 · Remover somente o caminho XLSX e aplicar a exceção T12
- **Alternativas:** manter os dois formatos; substituir a planilha por TXT e remover os auxiliares XLSX.
- **Escolhida:** substituir o formato e simplificar `_exigir_sem_documentos` para ler os bytes como texto, preservando a checagem D7. Em `tests/harness/test_fixtures.py`, alterar apenas os testes e auxiliares listados na T12, no commit de testes; não tocar em testes depois da implementação.
- **Motivo:** a decisão T1 aceita só TXT e a T12 delimita a alteração de testes já `passing`.
- **Impacto:** c1–c3, HAR-03 c1/c6; T1, T4.
- [ ] Confirmada pela responsável.

## 3. Abordagem

T1 escreve os três testes HAR-05 e adapta os testes HAR-03 autorizados, antes do código. Os novos testes conferem conteúdo e formato do TXT, hierarquia e gabaritos, e 50 sementes sem documentos válidos, sem passar quando nenhum TXT foi gerado. Após revisão humana dos testes, registra-se o commit de testes. A verificação da HAR-03 documenta a regressão esperada. T2 amplia o modelo do plano; T3 gera o TXT e protege cada linha; T4 remove os auxiliares XLSX e atualiza o harness. T5 roda as duas fichas, a suíte completa e `check-clean`, registra o progresso e abre PR.

## 4. Contexto

- **Código relacionado:** `tools/fixtures_sinteticas.py` (`PLANO_BASE`, `gerar_modelo`, `_cadastro`, `_planilha`, `gerar_arquivos`); `tools/harness.py` (`_exigir_sem_documentos`, `cmd_fixtures_build`); `tests/harness/test_fixtures.py`.
- **Dependências:** HAR-03 está `passing`; `synthetic_fixtures_dir` usa `gerar_arquivos`. CAD-02 é o leitor do TXT, em PR separado.
- **Reaproveitar:** `_Sorteio`, `harness.tipos_da_linha` e a trava D7, os modelos de movimentação e os caminhos relativos a `fixtures/`.
- **Não criar:** XLSX novo, dados reais, biblioteca externa, código de produto fora do harness ou mudanças em testes além da T12.
- **Pesquisa externa:** desnecessária; formato e decisões estão em `docs/modulos/registry.md` e `DECISIONS.md` §11.

## 5. Decisões já resolvidas

- 26/11 · T1/T8: plano em TXT de 78 colunas, UTF-8 com CRLF; `cadastro.json` usa `plano_txt` e inclui classificação, reduzido e tipo.
- 26/11 · T12: exceção explícita para os testes HAR-03 enumerados; o restante dos testes permanece intacto.

## 6. Avaliação da ficha

| # | Achado | Tratamento |
|---|---|---|
| 1 | O c3 pode passar sem nenhum TXT se só verificar a ausência de documentos. | Testar ao menos um plano por semente, em 50 sementes. |
| 2 | O reduzido seguido da classificação pode formar CPF/CNPJ válido. | D3 e teste com o detector do `check-clean`. |
| 3 | A HAR-03 fixa a planilha e já está `passing`. | Modificar só a lista T12 antes do código; verificar HAR-03 novamente ao final. |

## 7. Riscos

- Um laço de retentativas sem limite travaria o teste `test_build_aborta_se_linha_tiver_documento_valido`; D3 preserva o aborto seguro.
- Um sorteio adicional no gerador principal mudaria OFX/gabaritos existentes; D2 isola a sequência.
- O código leitor CAD-02 ainda está em PR: a prova integrada será rodada quando a dependência estiver disponível na `developer`.

## 8. Aprovação

- [ ] D1–D4 confirmadas pela responsável.
- [ ] Plan e tasks revisados por Raissa em DD/MM.
- [ ] Revisão dos testes concluída antes da implementação.
