"""Reuse disposable PostgreSQL fixtures for DB-02 schema tests."""

import importlib.util
import sys
from pathlib import Path

_MODULE_NAME = "_lastro_db02_core_fixtures"
_PATH = Path(__file__).resolve().parents[1] / "core" / "conftest.py"
_SPEC = importlib.util.spec_from_file_location(_MODULE_NAME, _PATH)
assert _SPEC is not None and _SPEC.loader is not None
_CORE = importlib.util.module_from_spec(_SPEC)
sys.modules[_MODULE_NAME] = _CORE
_SPEC.loader.exec_module(_CORE)

APP_ROLE = _CORE.APP_ROLE
OWNER_ROLE = _CORE.OWNER_ROLE
REPO_ROOT = _CORE.REPO_ROOT
connect = _CORE.connect
process_output = _CORE.process_output
postgres_server = _CORE.postgres_server
fresh_database = _CORE.fresh_database
migrated_database = _CORE.migrated_database
