# CAD-05 · carregar o plano por TXT (ficha editada antes de iniciar)

**Dona:** marrathomaz · **Depende de:** CAD-02, HAR-05, DB-04, ACE-02, NUC-02 · **Decisão:** `DECISIONS.md` §11 (T3, T5, T7).

A ficha não começou, então é editada no lugar e não muda teste de ninguém. Ela abre quando as 5 dependências estiverem `passing`. A ACE-02 é o caminho crítico e depende da NUC-03. Por causa do WIP=1, só abre depois que a branch da CAD-02 entrar na `developer`.

## O que a ficha não diz, mas o banco exige

Foi simulado em 26/11 no banco com RLS, como `lastro_app`. O texto completo está em `docs/modulos/registry.md`, "Carga do plano (CAD-05)".

1. **Recusa antes da transação.** Com `refusal` preenchido, 422 com a mensagem do leitor, sem gravar nada. O plano atual e a configuração ficam iguais.
2. **Versão nova, a anterior fica.** `plano_contas` novo com `versao = max + 1` e `situacao = 'publicado'`; o anterior passa a `'substituido'`.
3. **Pais antes dos filhos.** Gere os ids na aplicação e insira em ordem crescente de comprimento da classificação. Na simulação, filhos antes dos pais deu `ForeignKeyViolation`.
4. **Um `UPDATE` só para trocar o plano atual e remapear** `conta_transitoria_id`, `conta_entrada_socio_id` e `conta_saida_socio_id` pela classificação (ou nulo). A FK dessas colunas inclui `plano_atual_id`; em comandos separados o banco recusa.
5. **`conta_bancaria.conta_contabil_id`**, se preenchido, também é remapeado pela classificação.
6. **Tudo numa transação** (passos 2 a 5).

Resultado da simulação com o plano da fixture:
- carga com 23 contas, igual ao cadastro, com os pais certos;
- recusa por grupo sem nome com a configuração intacta;
- recarga do mesmo plano mantendo a transitória e a conta de sócio no plano novo;
- plano com 3 contas limpando a transitória e mantendo a conta de sócio.

## Critérios da ficha (resumo)

| Critério | O quê |
|---|---|
| c1 | fixture `plano_txt` carregada: classificação, reduzido, nome, tipo e conta superior iguais ao cadastro |
| c2 | linha tolerada aparece com o número e o resto entra |
| c3 | arquivo recusado (grupo sem nome, `.xlsx`) → 422 com a mensagem única e o plano atual intacto |
| c4 | isolamento por carteira e escritório (404) |
| c5 | nova carga substitui o plano atual (P-11) |
| c6 | contas de configuração mantidas ou limpas pela classificação (configuração gravada pelo teste direto no banco, porque a CAD-06 ainda não existe) |
| c7 | chefe não atribuído (403) e atribuído (P-09) |

## Armadilhas

- `codigo` no banco é a classificação **sem pontos** (`1101`). O `codigo` com pontos do `cadastro.json` é só da fixture.
- Os exemplos usam P-13 = 422, aprovada.
- A IA ainda vê os grupos (T9). O filtro `tipo = 'A'` não é desta ficha.

Referência: `referencia_simulacao/CAD-05_carga_simulada.py` (operação de banco, sem a rota).
