# Módulo `web`: front-end SPA (WEB-01)

React 19 + TypeScript strict + Vite, em `web/`. Gerenciador de pacotes: pnpm (lockfile versionado).
Tudo roda no contêiner `dev`; não é preciso instalar Node na máquina.

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `web/src/api/` | `client.ts` (cliente `openapi-fetch`) e `schema.d.ts` (gerado; não edite) |
| `web/src/copy/` | todo texto de tela, em JSON: `general`, `manager`, `accountant`, `client`; `index.ts` os reúne |
| `web/src/pages/` | `SignIn`, `Invitation`, `NotFound`, `Home`; por papel: `manager/`, `accountant/`, `client/` |
| `web/src/components/` | componentes compartilhados (vazio por enquanto) |
| `web/src/router.tsx` | TanStack Router em código; `createAppRouter({ history, apiClient })` |
| `web/tests/` | testes de componente (Vitest + Testing Library) |

Rotas: `/`, `/entrar`, `/convite/$token`, `/chefe`, `/contador`, `/enviar/$token`; o resto cai em
`NotFound`. As telas ainda são provisórias (sem login, sem validar token, sem guarda de papel).

## Como rodar

Na raiz do repositório, sempre com `--user` (o contêiner não pode criar arquivos do root na pasta):

```
docker compose run --rm --user $(id -u):$(id -g) dev sh -c 'cd web && pnpm install --frozen-lockfile && pnpm run lint && pnpm run test && pnpm run build'
```

Servidor de desenvolvimento: acrescente `-p 5173:5173` e troque o último comando por
`pnpm exec vite --host`. Para falar com a API local, passe `-e VITE_API_URL=http://localhost:8000`
(vazio = caminho relativo `/api/v1`).

## Textos de tela

- Todo texto vem de `web/src/copy/*.json`; nada de texto literal em JSX (nem em `aria-label`,
  `title`, `alt`, `placeholder`). O teste do c5 varre `pages/` e `components/`.
- Todo texto de `copy/` também entra em `docs/design/microcopy.md`, igual, na seção do papel.
- Mensagem ao usuário: o que aconteceu + o que fazer, em português simples (RF-AVI-02).

## Cliente da API

- Os tipos vêm do OpenAPI do backend. Depois de mudar uma rota da API, rode no contêiner:
  `cd web && pnpm run gerar:api`. Ele exporta `docs/api/openapi.json` (módulo
  `lastro.api.export_openapi`, sem subir servidor) e gera `web/src/api/schema.d.ts`. Versione os
  dois arquivos. Rodar de novo não muda nenhum byte.
- Os caminhos gerados já trazem `/api/v1`; por isso o endereço base do cliente é só `VITE_API_URL`.
- Nunca escreva à mão um tipo da API.

## Armadilhas

- **Arquivos do root:** rodar `docker compose run` sem `--user` cria `web/dist/`, `.ruff_cache/` etc.
  como root, e o `hx verify` (que roda com o seu usuário) passa a falhar com "Permission denied".
  Conserto: `docker compose run --rm dev rm -rf web/dist .ruff_cache .pytest_cache`.
- **TypeScript na série 5:** o `openapi-typescript` não funciona com o TypeScript 7.
- **Versões:** Node em três lugares iguais (`Dockerfile`, `web/package.json` em `engines`,
  `web/.nvmrc`); o teste do c1 confere.
- **`git worktree`:** os testes de c1 e c3 usam `git ls-files` dentro do contêiner e falham em um
  worktree, porque o `.git` do worktree aponta para fora da pasta montada. Revise em um clone comum.
- **Aviso do pnpm** ("packages awaiting approval", `@tanstack/react-router`): um script de
  instalação do pacote não foi aprovado. Build e testes passam sem ele; não aprove sem ler o que faz.
- **Formatação:** o Biome usa largura de linha 120 (uma linha do teste `home.test.tsx` passa de 100).
