# Registry — esquema da DB-02

A revisão Alembic `0003` acrescenta `plano_contas`, `conta_contabil`, `conta_bancaria` e `socio`. Cada tabela usa a chave primária `(escritorio_id, cliente_id, id)` e uma FK composta para `cliente`. A coluna `id` recebe UUID gerado pelo banco.

`plano_contas` pertence a um cliente, tem versão positiva e única por cliente, e registra o membro do mesmo escritório que importou o plano. `conta_contabil` pertence a uma versão do plano do mesmo cliente; a conta pai precisa estar na mesma versão. O código contábil é texto e único apenas dentro daquela versão. `conta_bancaria` guarda o código do banco como texto e só referencia uma conta contábil do próprio cliente. `socio` guarda nome e nome normalizado.

`cliente.plano_atual_id` aponta para um plano do próprio cliente. As contas transitória, de entrada de sócio e de saída de sócio só podem apontar para contas desse plano. A troca do plano exige limpar ou trocar uma conta configurada que não exista no plano novo na mesma operação. Uma conta configurada não pode permanecer quando o plano atual é nulo. A DB-02 não implementa a carga de planilha nem a escolha dessas contas pela API.

O downgrade da `0003` remove as quatro colunas de configuração e as quatro tabelas, preservando as tabelas e os registros da DB-01. Ele elimina os dados próprios da DB-02; deve ser executado apenas conforme o procedimento de migração do ambiente.

As políticas RLS serão criadas na NUC-03. A DB-02 garante integridade referencial, mas o uso com dados de piloto depende da conclusão da NUC-03, conforme `docs/SECURITY.md` §8.
