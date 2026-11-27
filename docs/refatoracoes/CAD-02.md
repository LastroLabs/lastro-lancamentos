# CAD-02 · refazer o leitor em TXT (antes do merge)

**Dona:** marrathomaz · **Branch:** a que já existe, `feat/CAD-02-ler-a-planilha-do-plano-de-contas-e-apon` · **Decisão:** `DECISIONS.md` §11 (T1 a T5, T11, T12).

A branch tem o leitor `.xlsx` em `passing`, mas nunca entrou na `developer`. Ela é refeita no lugar, sem ficha nova. A regra completa, as mensagens e o contrato estão em `docs/modulos/registry.md` ("Leitura do plano de contas em TXT"). Este arquivo só diz **a ordem** e **onde a simulação tropeçou**.

## Ordem

1. **Atualizar a branch com a `developer` antes de tudo** (depois que o PR de docs entrar). A simulação deu conflito em 3 arquivos:
   - `src/lastro/registry/service.py` e `contracts.py`: a CAD-03 entrou depois. Fique com a versão da `developer` e acrescente só a função e os tipos do plano.
   - `ARCHITECTURE.md`: fique com a da `developer`.
   - `docs/modules/registry.md`: o PR de docs apagou a pasta. Aceite a remoção; a seção nova já está em `docs/modulos/registry.md`.
   
   Rode o `pytest` e confirme que está verde antes de seguir.
2. **Ficha e plano novos:** troque o título, os `criterios` e a `verificacao` de `features/CAD-02.json` pelo arquivo deste pacote. **Não mexa em `estado` nem `evidencia`.** Rode `/planejar CAD-02`: o plano antigo é do `.xlsx` (as decisões D1 a D6 ficam no histórico do git) e o novo precisa de aprovação. Commit da ficha e do plano.
3. **Commit só de testes:**
   - apague `tests/registry/test_planilha_plano.py` (autorizado, T12);
   - crie `tests/registry/test_plano_txt.py` com os 10 testes da ficha.
   
   Anote o hash: ele vai no template do PR.
4. `hx feature verify CAD-02`: falha nos 10 e o harness grava `regressed`. Faça commit da ficha.
5. **Implementação, sem tocar em `tests/`:**
   - `chart_txt.py` (novo), `contracts.py` (`ChartAccountEntry`, `ChartOfAccountsResult`) e `service.py` (`read_chart_of_accounts`);
   - apague `chart_spreadsheet.py`, `read_chart_of_accounts_spreadsheet` e `ChartSpreadsheetResult`;
   - tire o `openpyxl` do `pyproject.toml` e rode `uv lock`.
6. `hx verify` e `hx feature verify CAD-02`: `passing`. Commit da ficha. Confira que `git diff <hash> -- tests/` está vazio.

## Pontos que a simulação confirmou

- O leitor aceita os dois planos reais (294 contas, 217 analíticas, 1 aviso) em UTF-8, Windows-1252 e LF/CRLF.
- Em 1.200 embaralhamentos das linhas, com até 3 erros injetados, aceitar ou recusar não mudou nenhuma vez.
- Nenhum outro teste nem código importa o leitor `.xlsx`. Só `test_plano_txt.py` e a remoção de `test_planilha_plano.py` mudam em `tests/`.

## Armadilhas

- **Fatie depois de decodificar**, nunca os bytes.
- **Use `split("\n")` e `rstrip("\r")`**, não `splitlines`.
- O **erro próprio** de cada linha segue a ordem da tabela do `registry.md`: as causas (E1, E8, E3, E5) vêm antes dos toleráveis (E2, E4). Se o reduzido inválido vier antes do tipo inválido, a mensagem aponta o reduzido e a contadora reenvia para só então ver o tipo.
- As **repetições** (E6, E7) são conferidas em toda linha, inclusive nas que já têm erro. É o que torna o resultado independente da ordem das linhas.
- A **hierarquia** roda em todas as linhas com classificação legível, não só nas aceitas. Senão, uma analítica com filha passa quando a filha tem erro tolerável.
- Os testes usam **nomes inventados** (regra 1). Os planos reais não entram no repositório.

## Pronto quando

A ficha está `passing` pelo `hx`, o `pytest` completo está verde, `openpyxl` não aparece em `pyproject.toml` nem em `uv.lock`, e o PR cita `DECISIONS.md` §11 T12.

Referência (não é para copiar sem revisar): `referencia_simulacao/CAD-02_1_testes.patch` e `CAD-02_2_implementacao.patch`.
