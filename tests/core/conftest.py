"""NUC-01: shared fixtures for the environment, health and migration tests.

The test database is a disposable PostgreSQL 18 started by Testcontainers (plan D1),
reached through the `docker-proxy` service of the `dev` profile. Ryuk is disabled in
the Compose file, so the session fixture stops and removes the container itself.

Roles come from `migrations/bootstrap/create_roles.sql` (plan D5), run as the container
superuser. The SQL must create `lastro_owner` and `lastro_app` with LOGIN and without
password; the fixture sets passwords generated at run time. Each migration test gets a
new database with a random name owned by `lastro_owner`.

Nothing here is skipped: without Docker, proxy or database the tests fail with a clear
message (plan, evaluation item 5). No real data and no fixed password.
"""

import importlib
import os
import secrets
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CREATE_ROLES_SQL = REPO_ROOT / "migrations" / "bootstrap" / "create_roles.sql"
POSTGRES_IMAGE = "postgres:18"
OWNER_ROLE = "lastro_owner"
APP_ROLE = "lastro_app"
SUPERUSER = "postgres"


@dataclass(frozen=True)
class PostgresServer:
    host: str
    port: int
    superuser_password: str
    owner_password: str
    app_password: str


@dataclass(frozen=True)
class FreshDatabase:
    server: PostgresServer
    name: str

    def conninfo(self, role):
        """Keyword arguments for psycopg.connect() as `role` (superuser, owner or app)."""
        password = {
            SUPERUSER: self.server.superuser_password,
            OWNER_ROLE: self.server.owner_password,
            APP_ROLE: self.server.app_password,
        }[role]
        return {
            "host": self.server.host,
            "port": self.server.port,
            "user": role,
            "password": password,
            "dbname": self.name,
            "connect_timeout": 5,
        }

    def sqlalchemy_url(self, role):
        info = self.conninfo(role)
        return (
            f"postgresql+psycopg://{info['user']}:{info['password']}"
            f"@{info['host']}:{info['port']}/{info['dbname']}"
        )

    @property
    def database_url(self):
        return self.sqlalchemy_url(APP_ROLE)

    @property
    def migrations_database_url(self):
        return self.sqlalchemy_url(OWNER_ROLE)


def _require(module_name, reason):
    try:
        return importlib.import_module(module_name)
    except ImportError as error:
        pytest.fail(f"'{module_name}' is missing from the dev image ({reason}): {error}")


def _psycopg():
    return _require("psycopg", "PostgreSQL driver, plan D3")


def connect(conninfo, autocommit=True):
    return _psycopg().connect(**conninfo, autocommit=autocommit)


def _set_password(cursor, role, password):
    sql = _psycopg().sql
    cursor.execute(
        sql.SQL("ALTER ROLE {} WITH PASSWORD {}").format(sql.Identifier(role), sql.Literal(password))
    )


def _new_pw():
    """Random password generated at run time; no fixed secret in the repository."""
    return secrets.token_hex(16)


@pytest.fixture
def fresh_database(postgres_server):
    """New empty database owned by `lastro_owner`, dropped after the test."""
    sql = _psycopg().sql
    name = f"test_{secrets.token_hex(6)}"
    admin = FreshDatabase(server=postgres_server, name="postgres").conninfo(SUPERUSER)
    with connect(admin) as conn:
        conn.execute(
            sql.SQL("CREATE DATABASE {} OWNER {}").format(
                sql.Identifier(name), sql.Identifier(OWNER_ROLE)
            )
        )
    try:
        yield FreshDatabase(server=postgres_server, name=name)
    finally:
        with connect(admin) as conn:
            conn.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name))
            )


def run_alembic_upgrade(database):
    """Run `alembic upgrade head` from the repo root, as the migration owner (plan D7)."""
    env = {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT / "src"),
        "DATABASE_URL": database.database_url,
        "MIGRATIONS_DATABASE_URL": database.migrations_database_url,
    }
    return subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def process_output(result, limit=2000):
    """stdout and stderr of a finished subprocess, for failure messages (alembic prints to stdout)."""
    return f"stdout:\n{result.stdout[-limit:]}\nstderr:\n{result.stderr[-limit:]}"


@pytest.fixture
def migrated_database(database_templates):
    """Fresh database with every migration applied: a copy of the `head` template (issue #93)."""
    with database_templates.cloned("head") as database:
        yield database
