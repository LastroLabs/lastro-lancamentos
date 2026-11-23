# Tasks — WEB-01 · Criar o ambiente do front-end: SPA React com rotas dos três papéis, cliente da API gerado e textos centralizados

**Plan:** planos/WEB-01/plan.md · **Ficha:** features/WEB-01.json
**Ordem:** T1 → revisão humana dos testes → commit só-de-testes (anotar o hash) → T2 em diante (sessão nova, sem editar `tests/` nem `web/tests/`)
**Antes de começar:** a pergunta 1 do plan (rota `/health`) precisa estar resolvida na ficha.

---

## [ ] T1 · Escrever os testes dos critérios
- **Critérios da ficha:** c1 a c5
- **Regra de negócio:** o front só está pronto se instala, passa no lint, nos testes e no build, mostra as telas certas, usa tipos gerados e tira todo texto de um lugar só.
- **Critérios de aceite:**
  - [ ] Existe um teste para cada nome de `verificacao`: `test_web01_front_instala_lint_testes_e_build_no_conteiner`, `test_web01_rotas_dos_tres_papeis_e_pagina_nao_encontrada`, `test_web01_cliente_da_api_gerado_do_openapi_e_estavel`, `test_web01_pagina_inicial_mostra_saude_da_api`, `test_web01_textos_de_tela_centralizados_no_microcopy`
  - [ ] Os de c2 e c4 chamam `pnpm run test` (Vitest) e conferem que os testes de componente rodaram e passaram; os componentes ficam em `web/tests/`
  - [ ] c1 confere: Node do contêiner = `engines` = `web/.nvmrc`; `web/dist/index.html` existe; nada de `dist/` ou `node_modules/` versionado (`git ls-files`)
  - [ ] c3 roda `gerar:api` duas vezes, compara bytes e compara com o arquivo versionado
  - [ ] c5 confere cada texto de `copy/` no `microcopy.md` e varre `pages/` e `components/` (plan, item 5)
  - [ ] Todos falham hoje pelo motivo certo; só dados inventados
- **Exemplos:** `/convite/abc123` → "Criar sua senha"; `/qualquer-coisa` → "Página não encontrada. Confira o endereço ou volte ao início."; saúde 200 → "Sistema no ar."; 503 ou falha de rede → "O sistema está fora do ar. Tente de novo em alguns minutos."
- **Arquivos:** `tests/web/test_web_foundation.py`, `web/tests/*.test.tsx` (sem `__init__.py` novo se o pytest não exigir)
- **Fora do escopo:** código de produção
- **Pronto quando:** `docker compose run --rm dev pytest tests/web/test_web_foundation.py -q` mostra só falhas esperadas

## [ ] T2 · Ambiente: Node e pnpm no `dev` e esqueleto do projeto `web/`
- **Critérios da ficha:** c1
- **Regra de negócio:** quem clona o repositório e roda `hx verify` deve ter o front conferido sem instalar nada na máquina.
- **Critérios de aceite:**
  - [ ] `Dockerfile` (estágio `dev`) traz Node e pnpm em versões fixas (D1); o estágio `runtime` não muda
  - [ ] `web/package.json` (`engines`, `packageManager`, scripts `lint`, `test`, `build`), `web/.nvmrc`, `pnpm-lock.yaml`, TypeScript strict, Biome, Vitest configurados
  - [ ] `pnpm install --frozen-lockfile` funciona com `--user uid:gid` (cache do pnpm em pasta gravável, sem configuração manual)
  - [ ] `.gitignore` cobre `web/node_modules/`, `web/dist/` e o cache do pnpm
- **Exemplos:** os 4 comandos da ficha terminam com código 0; sem o lock atualizado, `--frozen-lockfile` falha
- **Arquivos:** `Dockerfile`, `docker-compose.yml` (só variáveis do `dev`, se preciso), `.gitignore`, `web/*`
- **Reaproveitar:** padrão de versão por digest do uv · **Não criar:** `.nvmrc` na raiz
- **Fora do escopo:** rotas, telas, `tools/`
- **Decisões relacionadas:** D1, D6
- **Pronto quando:** `docker compose run --rm dev pytest tests/web/test_web_foundation.py::test_web01_front_instala_lint_testes_e_build_no_conteiner -q` passa

## [ ] T3 · Rotas dos papéis, páginas provisórias e textos em `copy/`
- **Critérios da ficha:** c2
- **Regra de negócio:** cada papel tem sua área e o cliente entra por link; endereço errado não deixa a pessoa perdida.
- **Critérios de aceite:**
  - [ ] Rotas `/entrar`, `/convite/$token`, `/chefe`, `/contador`, `/enviar/$token` mostram os títulos da ficha; `/qualquer-coisa` mostra a mensagem de 404
  - [ ] Páginas em `web/src/pages/manager/`, `accountant/`, `client/`; as demais (entrar, convite, 404) em `web/src/pages/`
  - [ ] Os textos vêm de `web/src/copy/*.json` (D3); nenhum texto literal em JSX
- **Exemplos:** `/enviar/abc123` → "Envio do extrato"; `/chefe` → "Área do chefe"; rota sem texto → 404
- **Arquivos:** `web/src/main.tsx`, `web/src/router.tsx`, `web/src/pages/**`, `web/src/copy/*`
- **Fora do escopo:** login real, validação do token, guarda de papel (outras fichas)
- **Decisões relacionadas:** D2, D3
- **Pronto quando:** `docker compose run --rm dev pytest tests/web/test_web_foundation.py::test_web01_rotas_dos_tres_papeis_e_pagina_nao_encontrada -q` passa

## [ ] T4 · Exportar o OpenAPI e gerar o cliente
- **Critérios da ficha:** c3
- **Regra de negócio:** o front nunca escreve tipo da API à mão; mudou o backend, o contrato versionado muda e o front acusa.
- **Critérios de aceite:**
  - [ ] `pnpm run gerar:api` grava `docs/api/openapi.json` (sem subir servidor) e `web/src/api/schema.d.ts`
  - [ ] Segunda execução não muda nenhum byte; `schema.d.ts` contém `/api/v1/health`
  - [ ] Cliente em `web/src/api/` com `openapi-fetch`, prefixo `/api/v1` e base de `VITE_API_URL` (com `.env.example` do web, sem segredo)
- **Exemplos:** `VITE_API_URL` vazia → caminho relativo `/api/v1`; rota nova na API → o arquivo muda ao gerar de novo
- **Arquivos:** `src/lastro/api/export_openapi.py`, `docs/api/openapi.json`, `web/src/api/*`, `web/package.json`
- **Reaproveitar:** `lastro.api.app.create_app`, `API_V1_PREFIX` · **Não criar:** tipos escritos à mão; script em `tools/`
- **Fora do escopo:** mudar rotas da API; avisar o dono da NUC-01 (regra 11)
- **Decisões relacionadas:** D4
- **Pronto quando:** `docker compose run --rm dev pytest tests/web/test_web_foundation.py::test_web01_cliente_da_api_gerado_do_openapi_e_estavel -q` passa

## [ ] T5 · Página inicial com a saúde da API
- **Critérios da ficha:** c4
- **Regra de negócio:** quem abre o sistema vê se ele está no ar, sem termo técnico.
- **Critérios de aceite:**
  - [ ] `/` consulta `/health` pelo cliente gerado
  - [ ] 200 com `up`/`connected` → "Sistema no ar."; 503, falha de rede ou corpo inesperado → "O sistema está fora do ar. Tente de novo em alguns minutos."
  - [ ] A tela não mostra código de status, rota nem termo técnico
- **Exemplos:** 200 → "Sistema no ar."; 503 → mensagem de fora do ar; rede caída → a mesma
- **Arquivos:** `web/src/pages/Home.tsx` (nome livre), `web/src/copy/*`
- **Reaproveitar:** cliente da T4 · **Não criar:** biblioteca de simulação de rede
- **Fora do escopo:** nova tentativa automática, indicador de carregamento elaborado
- **Decisões relacionadas:** D5
- **Pronto quando:** `docker compose run --rm dev pytest tests/web/test_web_foundation.py::test_web01_pagina_inicial_mostra_saude_da_api -q` passa

## [ ] T6 · Microcopy e conferência dos textos
- **Critérios da ficha:** c5
- **Regra de negócio:** uma contadora lê todos os textos de uma vez e confere se entende (RF-AVI-02).
- **Critérios de aceite:**
  - [ ] `docs/design/microcopy.md` com seções chefe, contador, cliente e geral
  - [ ] Cada texto de `copy/` aparece igual; os de c2 e c4 estão entre eles
  - [ ] Nenhum texto literal em `pages/` nem `components/`
  - [ ] Tempo do `hx verify` completo registrado em `progress/WEB-01.md`
- **Arquivos:** `docs/design/microcopy.md`, `web/src/copy/*`
- **Fora do escopo:** `DESIGN.md`, identidade visual
- **Pronto quando:** `docker compose run --rm dev pytest tests/web/test_web_foundation.py::test_web01_textos_de_tela_centralizados_no_microcopy -q` passa

## [ ] T7 · Verificação final
- **Critérios de aceite:**
  - [ ] `git diff <hash-dos-testes> -- tests/ web/tests/` vazio
  - [ ] `ruff check .` limpo
  - [ ] `hx check-clean` e `hx verify` em OK
  - [ ] `hx feature verify WEB-01` grava `passing`
- **Pronto quando:** `hx check-clean`, `hx verify` e `hx feature verify WEB-01` terminam com código 0
