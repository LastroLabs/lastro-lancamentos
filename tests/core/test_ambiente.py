"""NUC-01 c1, c2 and c6: environment files, API skeleton and verification environment.

c1 is proved statically (plan, answer 9): the test reads docker-compose.yml, Dockerfile and
.env.example; actually bringing the stack up is the manual check of T6. c2 imports the fixed
extension points without opening a connection. c6 checks the Python of the dev container and
the version of the disposable test PostgreSQL. Function names follow features/NUC-01.json.
"""

import importlib
import os
import re
import socket
import subprocess
import sys

import yaml
from conftest import REPO_ROOT, SUPERUSER, FreshDatabase, connect, process_output

COMPOSE = REPO_ROOT / "docker-compose.yml"
DOCKERFILE = REPO_ROOT / "Dockerfile"
ENV_EXAMPLE = REPO_ROOT / ".env.example"
DOCKER_SOCKET = "/var/run/docker.sock"
API_V1 = "/api/v1"
SKELETON_MODULES = ("lastro.core.config", "lastro.core.db", "lastro.api.app")
URL_LITERAL = re.compile(r"postgres(?:ql)?(?:\+\w+)?://", re.IGNORECASE)
# ${VAR} or ${VAR:?message} / ${VAR?message}; a default value (${VAR:-x}) is not accepted.
VARIABLE_REFERENCE = re.compile(r"^\$\{(?P<name>[A-Z_][A-Z0-9_]*)(?::?\?[^}]*)?\}$")
# Passwords the db service receives (official image + roles script, plan D5).
DB_PASSWORD_VARIABLES = ("POSTGRES_PASSWORD", "OWNER_DB_PASSWORD", "APP_DB_PASSWORD")
ENV_EXAMPLE_REQUIRED = (*DB_PASSWORD_VARIABLES, "DATABASE_URL", "MIGRATIONS_DATABASE_URL")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compose():
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


def _environment(service):
    env = service.get("environment") or {}
    if isinstance(env, list):
        return dict(item.split("=", 1) if "=" in item else (item, None) for item in env)
    return {key: (None if value is None else str(value)) for key, value in env.items()}


def _volume_sources(service):
    sources = []
    for volume in service.get("volumes") or []:
        if isinstance(volume, dict):
            sources.append(str(volume.get("source", "")))
        else:
            sources.append(str(volume).split(":", 1)[0])
    return sources


def _env_files(service):
    """env_file as a list of paths (accepts a string, a list or the long syntax)."""
    entries = service.get("env_file") or []
    if isinstance(entries, str):
        entries = [entries]
    return [entry["path"] if isinstance(entry, dict) else str(entry) for entry in entries]


def _depends_on(service):
    deps = service.get("depends_on") or []
    return set(deps if isinstance(deps, list) else deps.keys())


def _dockerfile_stages():
    """Map stage name -> base image (or parent stage) from the FROM lines."""
    stages = {}
    pattern = re.compile(
        r"^\s*FROM\s+(?:--platform=\S+\s+)?(?P<base>\S+)(?:\s+AS\s+(?P<name>\S+))?\s*$",
        re.IGNORECASE,
    )
    for line in DOCKERFILE.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            stages[(match["name"] or f"#{len(stages)}").lower()] = match["base"]
    return stages


def _base_image(stages, stage):
    seen = set()
    current = stage.lower()
    while current in stages and current not in seen:
        seen.add(current)
        current = stages[current].lower()
    return current


def _env_example():
    values = {}
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("'\"")
    return values


# ---------------------------------------------------------------------------
# c1
# ---------------------------------------------------------------------------


def test_compose_define_api_e_banco_com_versoes_decididas():
    services = _compose()["services"]
    missing = {"api", "db", "dev", "docker-proxy"} - set(services)
    assert not missing, f"docker-compose.yml is missing the services {sorted(missing)}"

    without_profile = {name for name, service in services.items() if not service.get("profiles")}
    assert without_profile == {"api", "db"}, "plain 'docker compose up' must start only api and db"
    for name in ("dev", "docker-proxy"):
        assert "dev" in services[name]["profiles"], f"'{name}' must be in the 'dev' profile"

    stages = _dockerfile_stages()
    api_build, dev_build = services["api"]["build"], services["dev"]["build"]
    assert isinstance(api_build, dict) and api_build.get("target") == "runtime"
    assert isinstance(dev_build, dict) and dev_build.get("target") == "dev"
    for target in ("runtime", "dev"):
        assert target in stages, f"Dockerfile has no stage '{target}'"
        assert _base_image(stages, target).startswith("python:3.14"), target

    assert str(services["db"]["image"]).startswith("postgres:18")

    compose_text = COMPOSE.read_text(encoding="utf-8")
    assert not URL_LITERAL.search(compose_text), "no database URL may be written in the Compose"
    api_env = _environment(services["api"])
    if "DATABASE_URL" in api_env:
        match = VARIABLE_REFERENCE.match(api_env["DATABASE_URL"] or "")
        assert match and match["name"] == "DATABASE_URL", "api gets DATABASE_URL only from env"
    else:
        assert _env_files(services["api"]) == [".env"], "api must receive DATABASE_URL from .env"
    db_env = _environment(services["db"])
    missing = [key for key in DB_PASSWORD_VARIABLES if key not in db_env]
    assert not missing, f"db.environment is missing {missing} (plan D5)"
    for key in DB_PASSWORD_VARIABLES:
        match = VARIABLE_REFERENCE.match(db_env[key] or "")
        assert match and match["name"] == key, f"db.{key} must be ${{{key}}}, got {db_env[key]!r}"
    secret_keys = [
        (name, key, value)
        for name, service in services.items()
        for key, value in _environment(service).items()
        if re.search("PASSWORD|SECRET", key)
    ]
    assert len(secret_keys) >= len(DB_PASSWORD_VARIABLES)
    for name, key, value in secret_keys:
        assert value and VARIABLE_REFERENCE.match(value), f"{name}.{key} must be ${{VAR}}"

    mounting_socket = {n for n, s in services.items() if DOCKER_SOCKET in _volume_sources(s)}
    assert mounting_socket == {"docker-proxy"}, "only docker-proxy may mount the Docker socket"
    assert not services["docker-proxy"].get("ports"), "docker-proxy must not publish ports"
    assert _environment(services["dev"]).get("DOCKER_HOST") == "tcp://docker-proxy:2375"
    assert "docker-proxy" in _depends_on(services["dev"])

    assert ENV_EXAMPLE.is_file(), "missing .env.example"
    example = _env_example()
    missing = [key for key in ENV_EXAMPLE_REQUIRED if key not in example]
    assert not missing, f".env.example is missing {missing}"
    for key in ("DATABASE_URL", "MIGRATIONS_DATABASE_URL"):
        assert URL_LITERAL.match(example[key]), f".env.example: {key} must be a PostgreSQL URL"
    checked = [
        key
        for key, value in example.items()
        if re.search("PASSWORD|SECRET", key) or URL_LITERAL.match(value)
    ]
    assert set(ENV_EXAMPLE_REQUIRED) <= set(checked)
    for key in checked:
        assert "exemplo" in example[key], f".env.example: {key} must hold an example value"
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in gitignore


# ---------------------------------------------------------------------------
# c2
# ---------------------------------------------------------------------------


def test_esqueleto_da_api_tem_pontos_de_extensao_fixos(monkeypatch):
    for relative in ("src/lastro/core/config.py", "src/lastro/core/db.py", "src/lastro/api/app.py"):
        assert (REPO_ROOT / relative).is_file(), f"missing {relative}"

    # Importing without DATABASE_URL must work: so importing cannot connect.
    clean_env = {k: v for k, v in os.environ.items() if not k.endswith("DATABASE_URL")}
    clean_env["PYTHONPATH"] = str(REPO_ROOT / "src")
    imported = subprocess.run(
        [sys.executable, "-c", "; ".join(f"import {m}" for m in SKELETON_MODULES)],
        env=clean_env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert imported.returncode == 0, (
        f"import without DATABASE_URL failed:\n{process_output(imported)}"
    )

    # A listening socket as a trap: the URL points to it, and no connection may arrive
    # while importing, creating the app and calling a route that does not use the database.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as trap:
        trap.bind(("127.0.0.1", 0))
        trap.listen(8)
        trap.setblocking(False)
        url = f"postgresql+psycopg://inventado:inventado@127.0.0.1:{trap.getsockname()[1]}/x"
        monkeypatch.setenv("DATABASE_URL", url)
        monkeypatch.setenv("MIGRATIONS_DATABASE_URL", url)
        for module in SKELETON_MODULES:
            monkeypatch.delitem(sys.modules, module, raising=False)

        config = importlib.import_module("lastro.core.config")
        importlib.import_module("lastro.core.db")
        app_module = importlib.import_module("lastro.api.app")
        fastapi = importlib.import_module("fastapi")
        testclient = importlib.import_module("fastapi.testclient")

        assert config.get_settings().database_url == url
        assert app_module.API_V1_PREFIX == API_V1

        app = app_module.create_app(settings=config.Settings())
        router = fastapi.APIRouter()

        @router.get("/test-echo")
        def echo():
            return {"echo": "ok"}

        app.include_router(router, prefix=app_module.API_V1_PREFIX)
        with testclient.TestClient(app) as client:
            response = client.get(f"{API_V1}/test-echo")

        try:
            trap.accept()
            connected = True
        except BlockingIOError:
            connected = False

    assert response.status_code == 200
    assert response.json() == {"echo": "ok"}
    assert not connected, "importing or creating the app opened a database connection"
    health_paths = [route.path for route in app.routes if route.path.endswith("/health")]
    assert health_paths == [f"{API_V1}/health"]


# ---------------------------------------------------------------------------
# c6
# ---------------------------------------------------------------------------


def test_ambiente_de_verificacao_tem_python_e_banco_decididos(request):
    assert sys.version_info[:2] == (3, 14), f"dev container runs Python {sys.version.split()[0]}"

    # Requested only after the Python check, so a missing Testcontainers does not hide it.
    postgres_server = request.getfixturevalue("postgres_server")
    admin = FreshDatabase(server=postgres_server, name="postgres").conninfo(SUPERUSER)
    with connect(admin) as conn:
        version_num = int(conn.execute("SHOW server_version_num").fetchone()[0])
    assert version_num // 10000 == 18, f"test database answers as PostgreSQL {version_num}"
