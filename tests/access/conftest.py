"""Reuse NUC-01 fixtures under an unambiguous module name, without a second bootstrap."""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

_MODULE_NAME = "_lastro_db01_core_fixtures"
_PATH = Path(__file__).resolve().parents[1] / "core" / "conftest.py"
_SPEC = importlib.util.spec_from_file_location(_MODULE_NAME, _PATH)
assert _SPEC is not None and _SPEC.loader is not None
_CORE = importlib.util.module_from_spec(_SPEC)
sys.modules[_MODULE_NAME] = _CORE
_SPEC.loader.exec_module(_CORE)

# Keep public helpers available even when legacy core tests resolve this conftest.
APP_ROLE = _CORE.APP_ROLE
OWNER_ROLE = _CORE.OWNER_ROLE
SUPERUSER = _CORE.SUPERUSER
REPO_ROOT = _CORE.REPO_ROOT
PostgresServer = _CORE.PostgresServer
FreshDatabase = _CORE.FreshDatabase
connect = _CORE.connect
process_output = _CORE.process_output
run_alembic_upgrade = _CORE.run_alembic_upgrade
postgres_server = _CORE.postgres_server
fresh_database = _CORE.fresh_database


@pytest.fixture
def migrated_database(fresh_database):
    """Keep DB-01 checks pinned to revision 0002 as later features add tables."""
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "0002"],
        cwd=REPO_ROOT,
        env={
            **os.environ,
            "PYTHONPATH": str(REPO_ROOT / "src"),
            "DATABASE_URL": fresh_database.database_url,
            "MIGRATIONS_DATABASE_URL": fresh_database.migrations_database_url,
        },
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, process_output(result)
    return fresh_database
