"""Fixtures shared by every test module.

`synthetic_fixtures_dir` (HAR-03, plan answer 3): the synthetic data that `hx fixtures build`
writes, generated once per test session in a temporary folder. Tests of any module use it
instead of reading `fixtures/` at the repository root, which is not versioned and does not
exist in a clean CI checkout.

Treat the folder as read-only: it is shared by the whole session. A test that needs to change
a file copies it to its own `tmp_path` first.
"""

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
GENERATOR_MODULE = "fixtures_sinteticas"  # tools/fixtures_sinteticas.py (HAR-03, D1)
FIXTURES_FOLDER = "fixtures"  # same name as the root folder, so `hx fixtures build --check` works


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
