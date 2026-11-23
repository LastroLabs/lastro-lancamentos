# Lastro

## Ambiente de desenvolvimento

### Pré-requisitos

- **Windows:** Docker Desktop com WSL2 e Python 3.10+.
- **Linux:** Docker Engine com o plugin `docker compose`, usuário no grupo `docker` e Python 3.10+.

### Atalho `hx` no PowerShell (Windows)

```powershell
. .\tools\hx.ps1
```

O ponto inicial é obrigatório: ele carrega a função `hx` na sessão atual. Para não repetir a cada sessão, adicione a linha abaixo ao `$PROFILE` (abra com `notepad $PROFILE`), ajustando o caminho:

```powershell
. C:\caminho\para\LASTRO\tools\hx.ps1
```

Se o PowerShell bloquear scripts, rode uma vez:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### Atalho `hx` no Linux

```sh
./tools/hx --help
```

Ou, no `~/.bashrc`: `alias hx='python3 /caminho/para/LASTRO/tools/harness.py'`

### Subir o ambiente

```sh
cp .env.example .env
docker compose up -d --wait
curl localhost:8000/api/v1/health
```

O `up` sobe só a `api` (Python 3.14) e o `db` (PostgreSQL 18). Na primeira subida, o `db` cria os papéis `lastro_owner` e `lastro_app`, e a `api` aplica as migrações antes de responder. A saúde responde `{"api": "up", "database": "connected"}`. O `.env` não é versionado; troque as senhas de exemplo antes de usar fora da sua máquina. Para apagar o banco local e começar do zero: `docker compose down -v`.

Se a porta 8000 estiver ocupada, libere-a e rode `docker compose down` antes de subir de novo, porque o Compose pode reaproveitar um container que ficou sem rede.

Os testes (`hx verify`) não usam esse banco: o serviço `dev` cria um PostgreSQL 18 descartável pelo Testcontainers, através do serviço `docker-proxy`. Os dois ficam no perfil `dev`; para derrubá-los: `docker compose --profile dev down`.

### Testar o ambiente

```powershell
docker compose --profile dev build
docker compose run --rm dev python --version
docker compose run --rm dev ruff --version
docker compose run --rm dev pytest --version
docker compose run --rm dev ls
```

## Estrutura do repositório

Referência para pessoas e agentes. Vale para a `developer`, que é a branch da verdade (PROC-01). Uma pasta ou um arquivo fora daqui só entra por PR que atualize esta seção.

Fontes: ARQ-01 a ARQ-08 e BD-01 a BD-08 (`docs/decisoes/DECISIONS.md`), a visão geral da arquitetura (`gitpages/src/content/docs/arquitetura/visao-geral.mdx`) e os caminhos que o `tools/harness.py` lê e escreve. Os itens com **PROPOSTA** ainda dependem de decisão. Os marcados com "(a criar)" estão definidos, mas a pasta ainda não existe.

### Árvore

```text
lastro-lancamentos/
├── .claude/
│   └── commands/             # comandos do Claude Code (/planejar)
├── .github/
│   ├── workflows/            # pr.yml (verify + check-clean) e deploy-docs.yml (site)
│   ├── CODEOWNERS            # donos por pasta
│   └── pull_request_template.md
├── .vscode/
│   └── settings.json         # única configuração de editor compartilhada
├── docs/
│   ├── SECURITY.md           # dados, segredos e uso de LLM
│   ├── decisoes/             # DECISIONS.md: D-xx, ARQ-xx, BD-xx, PROC-xx, P-xx
│   ├── requisitos/           # requisitos_lastro.json (RF-xxx)
│   ├── templates/            # modelos de ficha, plan, tasks e progress (o hx lê progress.md)
│   ├── modulos/              # <modulo>.md, um por módulo (a criar)
│   ├── bancos/               # <banco>.md, só a estrutura do extrato (a criar)
│   ├── ia/                   # boas práticas de LLM (a criar)
│   ├── design/               # DESIGN.md e microcopy.md (a criar)
│   ├── harness/              # PROPOSTA: fluxo e storytelling do harness
│   ├── qualidade.md
│   └── rubrica-revisao.md
├── features/                 # <SIGLA>-nn.json: fichas (o estado só muda pelo hx)
├── fixtures/                 # GERADO por hx fixtures build; fora do Git
├── gitpages/                 # site Astro + Starlight (regra de sincronização abaixo)
├── layouts/
│   └── dominio.yaml          # layout do Domínio, PROVISORIO (D-05) (a criar)
├── migrations/               # migrações versionadas do PostgreSQL 18, Alembic (a criar)
│   └── versions/             # uma migração por PR que muda o esquema
├── planos/
│   └── <ID>/                 # plan.md e tasks.md gerados pelo /planejar
├── progress/                 # <ID>.md: diário da feature (nasce no hx feature start)
├── src/
│   └── lastro/               # backend Python: os 14 módulos (abaixo)
├── tests/
│   ├── <modulo>/             # test_<alvo>.py, um diretório por módulo da ficha
│   ├── harness/              # testes do hx (módulo "harness" das fichas)
│   └── ci/                   # testes dos workflows (módulo "ci")
├── tools/
│   ├── harness.py            # o hx
│   ├── hx                    # atalho POSIX
│   └── hx.ps1                # atalho PowerShell
└── web/                      # front React + Vite, SPA estática (a criar)
    ├── src/                  # código do front (cliente gerado em src/api/gerado/)
    └── public/               # arquivos estáticos
```

**Os 14 módulos de `src/lastro/`** (nomes exatos da arquitetura):

```text
src/lastro/
├── nucleo/           # config, sessão, permissões, contexto RLS, dinheiro em centavos
├── acesso/           # escritório, usuário, papel, atribuição, link do cliente
├── cadastro/         # cliente, contas bancárias, sócios, plano de contas, configuração
├── envio/            # upload, quarentena, status por cliente e mês
├── leitura/          # detecção de formato, leitores OFX e PDF por banco
├── validacao/        # saldo, continuidade, cobertura do mês (só código, nunca IA)
├── classificacao/    # regras, histórico, parecidas (pg_trgm), chamada à IA
├── perguntas/        # agrupamento, página do cliente, respostas
├── revisao/          # três grupos, aceitar/trocar/pendente, aprendizado
├── exportacao/       # fotografia, planilha do Domínio, conciliação
├── ia/               # único lugar que chama LLM: anonimizar(), schemas, custo
├── observabilidade/  # registro de decisões e métricas do piloto
├── api/              # rotas FastAPI finas: autorização e chamada ao serviço
└── worker/           # tarefas Procrastinate
```

**Padrão interno de um módulo:**

```text
src/lastro/<modulo>/
├── __init__.py
├── servico.py        # interface pública: é o que api/, worker/ e outros módulos chamam (arquitetura)
├── contratos.py      # dataclasses imutáveis trocadas entre módulos (arquitetura)
└── modelos.py        # PROPOSTA: tabelas SQLAlchemy; internas, nenhum outro módulo importa
```

- Regras de dependência da arquitetura: as setas só descem; `api/` e `worker/` chamam serviços e nunca tocam tabela; um módulo chama outro só por `servico.py` e `contratos.py`; só `ia/` importa SDK de LLM; só `envio/` e `exportacao/` falam com o armazenamento de arquivos; `validacao/` não importa `ia/`.
- `api/` e `worker/` não seguem o padrão acima. **PROPOSTA:** um arquivo por módulo atendido (`api/<modulo>.py` com as rotas e `worker/<modulo>.py` com as tarefas).

**Padrão interno do front (`web/`), PROPOSTA** (a arquitetura define só a stack):

```text
web/
├── package.json, lockfile, vite.config.ts, tsconfig.json   # configuração do front fica aqui, nunca na raiz
└── src/
    ├── api/gerado/   # GERADO do OpenAPI (openapi-typescript); não edite à mão (ARQ-05)
    ├── api/          # cliente openapi-fetch configurado à mão
    ├── contador/     # área do contador e do chefe (desktop primeiro)
    └── cliente/      # página /enviar/:token (celular primeiro)
```

### Para que serve cada pasta

| Pasta | Para que serve (o que entra) | O que não entra | Dono (frente) |
|---|---|---|---|
| `.claude/` | `commands/`: comandos do Claude Code usados pelo time | `settings.local.json` (é pessoal e fica fora do Git); prompts com dado real | Harness e CI |
| `.github/` | Workflows, CODEOWNERS e template de PR | Segredos; workflow com `pull_request_target` | Harness e CI |
| `.vscode/` | Só `settings.json`, compartilhado | Outras configurações pessoais do editor | Harness e CI |
| `docs/` | Documentos do projeto em Markdown, mais `requisitos/` em JSON | Extrato, print ou dado de piloto; documentos privados (vão em `referencias/`, fora do Git) | Documentação; `decisoes/` é da Liderança; `SECURITY.md` é do guardião de dados ([definir]) |
| `features/` | Uma ficha por feature, `<SIGLA>-nn.json` (ex.: `CAD-03.json`) | Edição manual do `estado` e da `evidencia` (só o `hx`) | Liderança (cria); Harness e CI (CODEOWNERS) |
| `fixtures/` | Saída do `hx fixtures build`: cadastro, OFX, planilhas e gabarito sintéticos | Qualquer arquivo versionado; fixture escrita à mão | Harness e CI (HAR-03) |
| `gitpages/` | Código-fonte do site de documentação (Astro + Starlight) | `node_modules/`, `dist/`, `.astro/` | Documentação |
| `layouts/` | `dominio.yaml`: colunas e regras do Excel do Domínio | Colunas fixas em código Python | Dono do módulo `exportacao` ([definir]) |
| `migrations/` | Migrações Alembic, uma por PR que muda o esquema | Dump ou dado de banco; mudança de esquema fora de migração | Banco de dados |
| `planos/` | `<ID>/plan.md` e `<ID>/tasks.md` de cada feature | Código; aprovação do plan feita por agente (só humano aprova) | Responsável pela ficha |
| `progress/` | `<ID>.md`: o que foi feito, rodado, o que falhou e a próxima ação | Saída de comando com dado real | Responsável pela ficha |
| `src/lastro/` | Código Python do backend, só nos 14 módulos | Módulo fora da lista; SDK de LLM fora de `ia/`; dinheiro em float | Um dono por módulo, registrado em `docs/modulos/<modulo>.md`; `nucleo` é de Banco de dados; `acesso` e `ia` são de Segurança |
| `tests/` | `tests/<modulo>/test_<alvo>.py` e `conftest.py` | Dado real; provedor real de LLM; edição durante a implementação (AGENTS.md, regra 3) | Quem escreve os testes da ficha; `harness/` e `ci/` são de Harness e CI |
| `tools/` | Harness (`harness.py`, `hx`, `hx.ps1`) e o código do `hx fixtures build` | Código do produto | Harness e CI |
| `web/` | Front React + Vite e o cliente gerado do OpenAPI | Chamada direta a banco, arquivos ou LLM; tipos da API escritos à mão | Front |

### Arquivos permitidos na raiz

Só estes. Qualquer outro arquivo na raiz é proibido: documento vai para `docs/`, configuração do front vai para `web/` e a do site vai para `gitpages/`.

| Arquivo | Para quê |
|---|---|
| `README.md` | Apresentação, ambiente e esta estrutura |
| `AGENTS.md` | Regras para agentes (roteador, até 100 linhas) |
| `CLAUDE.md` | Só `@AGENTS.md` |
| `.gitignore`, `.gitattributes`, `.dockerignore` | Git e Docker |
| `Dockerfile`, `docker-compose.yml` | Ambiente: `api` e `db` no `up`; `dev` (usado pelo `hx`) e `docker-proxy` no perfil `dev` |
| `pyproject.toml` | Projeto Python: dependências (grupo `dev` à parte) e configuração do ruff |
| `uv.lock` | Versões travadas de todas as dependências (gerado pelo `uv lock`; o build falha se estiver desatualizado) |
| `alembic.ini` | Configuração do Alembic, sem URL do banco (as migrações ficam em `migrations/`) |
| `.env.example` | Modelo de variáveis com valores falsos (copie para `.env`) |
| `LICENSE` | **PROPOSTA:** só se o time escolher uma licença |

### O que é gerado e não vai para o Git

| Caminho | Quem gera | Por que fica fora |
|---|---|---|
| `fixtures/` (cadastro, OFX, planilhas e gabarito) | `hx fixtures build`, com semente fixa | Regra do projeto: o gabarito gerado não é versionado. Os CNPJs válidos existem só em tempo de execução. Gere de novo com o comando |
| `web/dist/` | Build do Vite | Artefato de build |
| `gitpages/dist/`, `gitpages/.astro/` | Build do Astro | O workflow `deploy-docs.yml` gera de novo |
| `node_modules/` (em qualquer pasta) | pnpm ou npm | Dependências instaladas |
| `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `.venv/` | Python e ferramentas | Cache local |
| `.env`, `.env.*` (menos `.env.example`) | Cada dev | Segredos |
| `.claude/settings.local.json` | Claude Code | Configuração pessoal |
| `referencias/` | Cada dev | Documentos privados de referência |

Gerado, mas **versionado**: `web/src/api/gerado/` (**PROPOSTA**: entra no Git e a CI confere se está em dia com o OpenAPI; ver "Decisões em aberto").

### Onde colocar cada coisa

| Preciso de… | Vai em… |
|---|---|
| Nova ficha | `features/<SIGLA>-nn.json`, por PR na `developer` |
| Plano e tasks de uma ficha | `planos/<ID>/plan.md` e `planos/<ID>/tasks.md` (pelo `/planejar <ID>`) |
| Registrar de onde parei | `progress/<ID>.md` |
| Decisão nova | Uma linha em `docs/decisoes/DECISIONS.md`, com ID `D-xx`, `ARQ-xx` ou `BD-xx` |
| Regra de negócio de um módulo | `docs/modulos/<modulo>.md` |
| Estrutura do extrato de um banco | `docs/bancos/<banco>.md` (só estrutura, nunca dado) |
| Lógica de negócio | `src/lastro/<modulo>/servico.py` |
| Dado trocado entre módulos | `src/lastro/<modulo>/contratos.py` (mudou? abra issue `contrato:`) |
| Rota da API | `src/lastro/api/` (**PROPOSTA:** `api/<modulo>.py`), chamando `src/lastro/<modulo>/servico.py` |
| Tarefa assíncrona | `src/lastro/worker/` (**PROPOSTA:** `worker/<modulo>.py`) |
| Chamada a LLM | Só em `src/lastro/ia/`, depois de `anonimizar()` |
| Mudança no esquema do banco | Nova migração em `migrations/versions/` |
| Coluna do Excel do Domínio | `layouts/dominio.yaml` |
| Teste | `tests/<modulo>/test_<alvo>.py`, onde `<modulo>` é o campo `modulo` da ficha |
| Fixture de teste | Gere com `hx fixtures build` (sai em `fixtures/`). Ajuste o gerador em `tools/` (HAR-03), nunca o arquivo gerado. Um dado mínimo e inventado pode ficar dentro do próprio teste |
| Tela do front | `web/src/` (área do contador ou página do cliente) |
| Página do site de documentação | `gitpages/src/content/docs/`, por PR na `developer` |

### Convenções de nome

- Python: `snake_case` em arquivos, funções e variáveis.
- Testes: `tests/<modulo>/test_<alvo>.py` e funções `test_<comportamento>`.
- Fichas: `features/<SIGLA>-nn.json` (ex.: `ACE-01.json`); o campo `id` é igual ao nome do arquivo. A única exceção histórica é `HX-10` (P-08).
- Documentos: `kebab-case.md`. Exceções, que ficam como estão: os nomes fixos `README.md`, `AGENTS.md`, `CLAUDE.md`, `SECURITY.md`, `DECISIONS.md`, `DESIGN.md` e o dado `docs/requisitos/requisitos_lastro.json`.
- Decisões: `D-xx` (negócio), `ARQ-xx` (arquitetura), `BD-xx` (banco), além das séries já em uso `PROC-xx` (processo) e `P-xx` (revisão das fichas).
- Branches: `feat/<ID>-<slug>` para feature e `docs/<assunto>` para documentação, sempre a partir da `origin/developer`.

### Decisões em aberto (PROPOSTA)

1. **`gitpages/` nas duas branches.** Proposta: o código-fonte do site vive na `developer`. Todo PR que mexe em `gitpages/` vai para a `developer`, e a `main` recebe o site só pelo merge de release (`developer` → `main`), que dispara o deploy. Correção feita direto na `main` volta para a `developer` no mesmo dia. *Decisão da líder.*
2. **Lugar do `SECURITY.md`.** Proposta: fica em `docs/SECURITY.md`. *Decisão da líder.*
3. **Protótipos de tela (fora do harness).** Proposta: ficam fora deste repositório. Uma tela aprovada entra em `web/` por ficha. *Decisão da líder.*
4. **Cliente gerado do OpenAPI.** Proposta: é versionado em `web/src/api/gerado/` e a CI falha se ele estiver desatualizado. *Decisão da frente de Front com a de Harness e CI.*
5. **`fixtures/` fora do Git.** Nesse caso, a CI precisa rodar `hx fixtures build` antes do `pytest` (HAR-03). Além disso, o `hx check-clean` local ignora o que está no `.gitignore`, então a pasta precisa ser varrida de forma explícita. *Decisão da líder.*
