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

### Testar o ambiente

```powershell
docker compose build
docker compose run --rm dev python --version
docker compose run --rm dev ruff --version
docker compose run --rm dev pytest --version
docker compose run --rm dev ls
```
