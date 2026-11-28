"""Fixtures shared by every test module.

`synthetic_fixtures_dir` (HAR-03, plan answer 3): the synthetic data that `hx fixtures build`
writes, generated once per test session in a temporary folder. Tests of any module use it
instead of reading `fixtures/` at the repository root, which is not versioned and does not
exist in a clean CI checkout.

Treat the folder as read-only: it is shared by the whole session. A test that needs to change
a file copies it to its own `tmp_path` first.

`postgres_server` (NUC-01): the disposable PostgreSQL, defined only here so that every folder
shares one container per test process (issue #93, DECISIONS §12, V1). Its helpers stay in
`tests/core/conftest.py`, loaded below under its own name, as `access` and `registry` do.
"""

import importlib
import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
GENERATOR_MODULE = "fixtures_sinteticas"  # tools/fixtures_sinteticas.py (HAR-03, D1)
FIXTURES_FOLDER = "fixtures"  # same name as the root folder, so `hx fixtures build --check` works

_CORE_MODULE = "_lastro_core_fixtures"
_CORE_PATH = Path(__file__).resolve().parent / "core" / "conftest.py"
_CORE_SPEC = importlib.util.spec_from_file_location(_CORE_MODULE, _CORE_PATH)
assert _CORE_SPEC is not None and _CORE_SPEC.loader is not None
_CORE = importlib.util.module_from_spec(_CORE_SPEC)
sys.modules[_CORE_MODULE] = _CORE
_CORE_SPEC.loader.exec_module(_CORE)


@pytest.fixture(scope="session")
def postgres_server():
    postgres_module = _CORE._require("testcontainers.postgres", "plan D1")
    admin_pw = _CORE._new_pw()
    container = postgres_module.PostgresContainer(
        _CORE.POSTGRES_IMAGE,
        username=_CORE.SUPERUSER,
        password=admin_pw,
        dbname="postgres",
        driver=None,
    )
    # The finally also covers a failed start or wait: with Ryuk disabled (plan D1), nothing
    # else would remove a container that was created but never became ready.
    try:
        try:
            container.start()
        except Exception as error:  # noqa: BLE001 (docker, proxy or timeout: all become one clear failure)
            pytest.fail(
                "Could not start the test PostgreSQL through Testcontainers. Check that Docker is "
                "running and that the 'docker-proxy' service (profile 'dev') is up and allows "
                f"creating containers. Cause: {type(error).__name__}: {error}"
            )
        server = _CORE.PostgresServer(
            host=container.get_container_host_ip(),
            port=int(container.get_exposed_port(5432)),
            superuser_password=admin_pw,
            owner_password=_CORE._new_pw(),
            app_password=_CORE._new_pw(),
        )
        roles_sql = _CORE.CREATE_ROLES_SQL
        if not roles_sql.is_file():
            pytest.fail(f"Missing roles script: {roles_sql.relative_to(REPO_ROOT)} (plan D5)")
        admin = _CORE.FreshDatabase(server=server, name="postgres").conninfo(_CORE.SUPERUSER)
        with _CORE.connect(admin) as conn, conn.cursor() as cursor:
            cursor.execute(roles_sql.read_text(encoding="utf-8"))
            _CORE._set_password(cursor, _CORE.OWNER_ROLE, server.owner_password)
            _CORE._set_password(cursor, _CORE.APP_ROLE, server.app_password)
        yield server
    finally:
        container.stop()


@pytest.fixture(scope="session")
def synthetic_fixtures_dir(tmp_path_factory):
    """Folder with the files of the default seed, the same bytes `hx fixtures build` writes."""
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    # Imported here, not at the top: modules that never ask for the fixture do not load it.
    generator = importlib.import_module(GENERATOR_MODULE)

    folder = tmp_path_factory.mktemp("synthetic") / FIXTURES_FOLDER
    for relative, data in generator.gerar_arquivos().items():
        target = folder / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return folder
