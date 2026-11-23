# Plan — WEB-01 · Criar o ambiente do front-end: SPA React com rotas dos três papéis, cliente da API gerado e textos centralizados

**Status:** pronto para revisão (falta o PR da ficha, seção 1)
**Branch:** feat/WEB-01-criar-o-ambiente-do-front-end-spa-react · **Data:** 23/11/2026 · **Responsável:** jvsauma
**Tasks:** planos/WEB-01/tasks.md

## 1. A decidir (humano)
Nenhuma pergunta em aberto: as 7 do rascunho foram resolvidas em 23/11 (ver seção 5).

**Pendente para o humano (PR da ficha, antes da T1):** c3 e c4 com `/api/v1/health` e `up`/`connected`; c5 incluindo `components/` e atributos (`aria-label`, `title`, `alt`, `placeholder`); comandos de `verificacao` sem mudança (só `pytest`, como exige o harness).

## 2. Decisões tomadas pelo agente
### D1 · Node 24 e pnpm no estágio `dev` do Dockerfile
- **Alternativas:** A) Node 24 (copiado da imagem oficial `node`, por digest, como o uv) · B) Node 26 · C) Node 22
- **Escolhida:** A — **motivo:** padrão já usado no Dockerfile (uv por digest); mesmo raciocínio da ARQ-08 (versão madura, ecossistema testado). **Contradição de fontes:** nodejs.org lista o 26 como LTS; endoflife.date diz que o 24 saiu de Active LTS em 20/10/2026 (manutenção, segurança até 2028); um quadro antigo do GitHub ainda o lista como Active. Não resolvi: se preferir o 26 (LTS ativo), troca-se um número na T2.
- **pnpm:** `npm install -g pnpm@<versão exata>` no Dockerfile, pois o Corepack deixou de vir com o Node 25+. Pode-se também copiar de `ghcr.io/pnpm/pnpm`. Escolhi o npm: um passo só, versão fixada. `packageManager` no `package.json` repete a versão.
- **Fontes:** https://nodejs.org/about/releases/ · https://endoflife.date/nodejs · https://pnpm.io/docker · https://github.com/nodejs/docker-node/pull/1768 (acesso em 23/11)
- **Impacto:** T2 · c1
- [x] confirmado em 23/11

### D2 · Rotas com TanStack Router em código (sem gerador de arquivos)
- **Alternativas:** A) por código · B) por arquivos (plugin gera `routeTree.gen.ts`) · C) React Router
- **Escolhida:** A — **motivo:** são 7 rotas; o plugin traria arquivo gerado e mais uma ferramenta. A documentação recomenda arquivos para a maioria dos apps; a ficha já fixa TanStack Router e permite migrar depois sem mudar as telas. Testes com `createMemoryHistory` (guia oficial).
- **Fontes:** https://tanstack.com/router/latest/docs/framework/react/routing/code-based-routing · https://tanstack.com/router/latest/docs/framework/react/how-to/setup-testing (acesso em 23/11)
- **Impacto:** T3 · c2
- [x] confirmado em 23/11

### D3 · Textos em JSON (`web/src/copy/*.json`), com `index.ts` tipado
- **Alternativas:** A) JSON por seção (geral, chefe, contador, cliente) · B) objetos `.ts` e o teste Python lê o TS · C) o Vitest confere o microcopy
- **Escolhida:** A — **motivo:** o teste de c5 é `pytest` e lê JSON direto; o TS importa o mesmo arquivo, sem duas fontes. B exigiria analisar TypeScript em Python.
- **Impacto:** T3, T5 · c2, c4, c5
- [x] confirmado em 23/11

### D4 · `gerar:api` exporta o OpenAPI com um módulo Python curto em `src/lastro/api/`
- **Alternativas:** A) `python -m lastro.api.export_openapi` (usa `create_app()` com URL de banco fictícia; o banco é preguiçoso, não conecta) · B) `python -c` dentro do `package.json` · C) script em `tools/` (exige aprovação do dono)
- **Escolhida:** A — **motivo:** testável, sem `tools/`. Saída determinística (chaves ordenadas, indentação fixa, `\n` final). Toca `api/` (dono: NUC-01): avisar o dono (regra 11).
- **Impacto:** T4 · c3
- [x] confirmado em 23/11

### D5 · Sem biblioteca de simulação de rede (MSW); a saúde recebe um `fetch` injetado
- **Alternativas:** A) `createClient({ fetch })` (opção documentada do openapi-fetch) · B) MSW · C) `vi.stubGlobal`
- **Escolhida:** A — **motivo:** zero dependência nova. Resposta 200 fora do formato esperado conta como "fora do ar".
- **Fonte:** https://openapi-ts.dev/openapi-fetch/api (acesso em 23/11)
- **Impacto:** T4, T5 · c3, c4
- [x] confirmado em 23/11

### D6 · Dependências do `pnpm` cujas versões ficam no lock
- React 19, TypeScript, Vite + `@vitejs/plugin-react`, Biome, Vitest + `jsdom` + Testing Library, `@tanstack/react-router`, `openapi-typescript`, `openapi-fetch`. Versões exatas só no `pnpm-lock.yaml`, escolhidas na T2 (conferir licença MIT e suporte ao Node fixado). Sem TanStack Query e sem biblioteca de UI: não são pedidos.
- [x] confirmado em 23/11

## 3. Resumo e abordagem
Cria o projeto `web/` e o ambiente que o roda dentro do `dev`. Ordem: testes (pytest que chamam o pnpm, mais testes de componente em `web/tests/`) → Node/pnpm no Dockerfile e esqueleto Vite → rotas e textos → exportação do OpenAPI e cliente gerado → página inicial com a saúde → microcopy e verificação final.

## 4. Contexto encontrado
- **Código relacionado:** `web/src/{api,components,copy,pages/*}/.gitkeep` (só pastas); `src/lastro/api/app.py` (`create_app`, `API_V1_PREFIX`); `src/lastro/api/routes.py` (`/health`, `HealthStatus`, `Problem`); `src/lastro/core/config.py` (`Settings`).
- **Dependências:** `NUC-01` (passing) expõe `/api/v1/health` e o serviço `dev` do Compose.
- **Reaproveitar:** estágio `dev` do `Dockerfile` e serviço `dev` do `docker-compose.yml`; `.gitignore` já ignora `web/dist/` e `node_modules/`.
- **Não criar:** `.nvmrc` na raiz (só `web/.nvmrc`); tipos da API à mão; segunda cópia de texto fora de `copy/`.
- **Falta:** `tests/web/` não existe; `docs/design/` não existe; `web/package.json` não existe.
- **Pesquisa externa:** Node, pnpm, openapi-fetch e TanStack Router (fontes em D1, D2, D5).

## 5. Decisões (já resolvidas)
- 23/11 · Ficha corrigida para `/api/v1/health` e `up`/`connected`; o contrato da NUC-01 manda (pergunta 1, por jvsauma)
- 23/11 · Testes Vitest em `web/tests/`; o hash do commit só-de-testes cobre `tests/` e `web/tests/` (pergunta 2)
- 23/11 · `/` é a página inicial: mostra a saúde da API e um link para `/entrar`, provisória (pergunta 3)
- 23/11 · 404 só com o texto da ficha, sem link, nesta feature (pergunta 4)
- 23/11 · O teste de c5 varre também `components/` e os atributos de texto (pergunta 5)
- 23/11 · `hx verify` não muda; o tempo é medido na T6 e registrado no `progress` (pergunta 6)
- 23/11 · Node 24 mantido, com a divergência de fontes registrada em D1; trocar para o 26 é mudar um número na T2 (pergunta 7)
- 23/11 · D1 a D6 confirmadas por jvsauma

## 6. Avaliação da ficha
| # | Achado | Gravidade | Critério |
|---|---|---|---|
| 1 | Rota e valores da saúde contradizem a NUC-01 (resolvido, seção 5; ficha a corrigir em PR) | BLOQUEANTE | c3, c4 |
| 2 | Hoje o `dev` é Python: sem Node/pnpm não há como cumprir c1; o Dockerfile precisa mudar | ATENÇÃO | c1 |
| 3 | c1 precisa de rede e de pasta de cache gravável com `--user uid:gid` (HOME ausente); conferir na T2 | ATENÇÃO | c1 |
| 4 | Local dos testes Vitest (item 2) | ATENÇÃO | c2, c4 |
| 5 | "Página inicial" não definida (item 3) | ATENÇÃO | c4 |
| 6 | Busca de texto em JSX é fraca (item 5) | ATENÇÃO | c5 |
| 7 | 5 critérios, mas de módulos diferentes (Docker, front, api); pode passar de 2 sessões | ATENÇÃO | todos |
| 8 | Sem dado real: textos e `abc123` são inventados | — | — |

## 7. Riscos
- Instalação lenta e rede indisponível no teste de c1 → timeout explícito no teste; falha com mensagem clara, sem `skip`.
- `node_modules` no bind mount (Docker Desktop lento) → medir na T2; se ruim, volume nomeado para `web/node_modules`.
- Saída do OpenAPI muda com versão do FastAPI/Pydantic → versões já presas no `uv.lock`; o teste compara com o arquivo versionado.
- Avanço de versão do Node fora de D1 → `engines`, `.nvmrc` e Dockerfile comparados pelo teste de c1.

## 8. Aprovação
- [x] Pergunta BLOQUEANTE (1) respondida; [ ] ficha corrigida em PR
- [x] Decisões do agente (D1–D6) confirmadas
- [ ] Plan e tasks revisados por <nome> em DD/MM
