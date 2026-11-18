# Documentação do Lastro

O site usa Astro, Starlight e o tema compartilhado do projeto. A navegação fica em `astro.config.mjs`; as páginas, em `src/content/docs/`.

## Fontes da modelagem

A especificação em Markdown/MDX fica em `src/content/docs/modelagem/`. Ela não é uma migração nem substitui os requisitos. As entidades e o modelo lógico usam o nome físico como âncora: `#cliente`, `#plano_contas`, `#exportacao_item`.

`src/data/modelagem.json` mantém apenas o catálogo de entidades e os vínculos requisito–entidade–regra–decisão. O texto e o critério dos requisitos continuam vindo de `src/data/requisitos.json`. As fichas são as já descritas em `src/data/fichas.ts`, com seu status de revisão preservado.

`scripts/gerar-requisitos.mjs` também extrai o status e a deliberação D-01 a D-09 da tabela em `decisoes/index.md`. Não edite o JSON gerado à mão. Os efeitos das demais decisões são resumidos em `src/data/modelagem.ts`, com link para a respectiva página de origem.

## Manutenção

Ao alterar uma entidade, mantenha coerentes a descrição, as chaves e os diagramas. Ao alterar um vínculo, atualize `modelagem.json` e confira a prioridade do requisito. Vínculo documentado não significa `passing`; as fichas e evidências continuam sob controle do harness. Não copie para a documentação dados ou identificadores reais.

As regras vigentes de 18/11 são tratadas separadamente do esquema proposto. D-08, P-09, P-13 e a precedência das regras não recebem valores inventados. O registro `docs/decisoes/DECISIONS.md` estava vazio no checkout de origem; os status publicados foram obtidos das páginas de decisões do site.

## Comandos

```sh
pnpm install --frozen-lockfile
node scripts/gerar-requisitos.mjs
pnpm check:docs
pnpm build
node scripts/verificar-modelagem.mjs --dist
```

`check:docs` confere cobertura dos Must, referências e âncoras, além das consultas e do comportamento dos filtros com Node 22.20 ou compatível com `stripTypeScriptTypes`. Os filtros são exercitados sem navegador; isso não substitui a revisão visual do build. `prebuild` executa a consistência documental. Após a compilação, `--dist` confere destinos e fragmentos do HTML, incluindo links para os requisitos, histórias e decisões.

A publicação continua usando o workflow existente, a partir da `main`. A base de desenvolvimento é a `developer`; a documentação deve seguir por revisão sem alterar fichas ou decisões do produto por conta própria.
