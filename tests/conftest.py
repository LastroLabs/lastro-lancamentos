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

import contextlib
import importlib
import importlib.util
import os
import secrets
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
GENERATOR_MODULE = "fixtures_sinteticas"  # tools/fixtures_sinteticas.py (HAR-03, D1)
FIXTURES_FOLDER = "fixtures"  # same name as the root folder, so `hx fixtures build --check` works

# Parallel runs (issue #93, plan D6, DECISIONS §12 V2): rules for tests in CODING_STANDARDS.md.
MAX_TEST_PROCESSES = 4
WEB_TESTS_DIR = Path(__file__).resolve().parent / "web"
WEB_GROUP = "web"

_CORE_MODULE = "_lastro_core_fixtures"
_CORE_PATH = Path(__file__).resolve().parent / "core" / "conftest.py"
_CORE_SPEC = importlib.util.spec_from_file_location(_CORE_MODULE, _CORE_PATH)
assert _CORE_SPEC is not None and _CORE_SPEC.loader is not None
_CORE = importlib.util.module_from_spec(_CORE_SPEC)
sys.modules[_CORE_MODULE] = _CORE
_CORE_SPEC.loader.exec_module(_CORE)


def pytest_xdist_auto_num_workers(config):
    """Processes for `-n auto` (pyproject addopts): up to 4 for a suite or folder.

    One file or one test (`path.py` or `path.py::name`, as each criterion of
    `hx feature verify`) runs in series: starting workers would cost more than it saves.
    """
    for argument in config.args:
        if "::" in argument or argument.endswith(".py"):
            return 0
    cpus = os.cpu_count() or 1
    return min(MAX_TEST_PROCESSES, cpus) if cpus > 1 else 0


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items):
    """The WEB-01 tests share web/node_modules and web/dist: one group, so one process."""
    for item in items:
        if item.path.is_relative_to(WEB_TESTS_DIR):
            item.add_marker(pytest.mark.xdist_group(WEB_GROUP))


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


class _DatabaseTemplates:
    """One migrated database per Alembic revision, cloned for each test (issue #93, plan D3).

    Running the migrations costs ~5 s per database; `CREATE DATABASE ... TEMPLATE` copies a
    migrated one in a fraction of a second. A template is migrated the first time a revision
    is asked for, by the same `alembic upgrade` the fixtures ran before, then closed to
    connections, because the copy needs it idle. Tests that move between revisions keep using
    `fresh_database` and run Alembic themselves: that is what they prove.
    """

    def __init__(self, server):
        self._server = server
        self._names = {}

    def _database(self, name):
        return _CORE.FreshDatabase(server=self._server, name=name)

    def _execute(self, query):
        with _CORE.connect(self._database("postgres").conninfo(_CORE.SUPERUSER)) as conn:
            conn.execute(query)

    def _template(self, revision):
        if revision in self._names:
            return self._names[revision]
        sql = _CORE._psycopg().sql
        name = f"template_{revision}_{secrets.token_hex(4)}"
        self._execute(
            sql.SQL("CREATE DATABASE {} OWNER {}").format(
                sql.Identifier(name), sql.Identifier(_CORE.OWNER_ROLE)
            )
        )
        result = _alembic_upgrade(self._database(name), revision)
        if result.returncode != 0:
            pytest.fail(
                f"alembic upgrade {revision} failed on the template database:\n"
                f"{_CORE.process_output(result)}"
            )
        self._execute(
            sql.SQL("ALTER DATABASE {} WITH ALLOW_CONNECTIONS false").format(sql.Identifier(name))
        )
        self._names[revision] = name
        return name

    @contextlib.contextmanager
    def cloned(self, revision):
        """New database at `revision`, owned by `lastro_owner`, dropped when the block ends."""
        sql = _CORE._psycopg().sql
        template = self._template(revision)
        name = f"test_{secrets.token_hex(6)}"
        self._execute(
            sql.SQL("CREATE DATABASE {} TEMPLATE {} OWNER {}").format(
                sql.Identifier(name), sql.Identifier(template), sql.Identifier(_CORE.OWNER_ROLE)
            )
        )
        try:
            yield self._database(name)
        finally:
            self._drop(name)

    def _drop(self, name):
        sql = _CORE._psycopg().sql
        self._execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))

    def drop_templates(self):
        for name in self._names.values():
            self._drop(name)
        self._names.clear()


def _alembic_upgrade(database, revision):
    """`alembic upgrade <revision>` as the migration owner, as the fixtures ran it before."""
    return subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", revision],
        cwd=REPO_ROOT,
        env={
            **os.environ,
            "PYTHONPATH": str(REPO_ROOT / "src"),
            "DATABASE_URL": database.database_url,
            "MIGRATIONS_DATABASE_URL": database.migrations_database_url,
        },
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.fixture(scope="session")
def database_templates(postgres_server):
    """Factory of migrated databases: `with database_templates.cloned("head") as db: ...`."""
    templates = _DatabaseTemplates(postgres_server)
    try:
        yield templates
    finally:
        templates.drop_templates()


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
