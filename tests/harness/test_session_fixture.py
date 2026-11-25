"""HAR-03: session fixture `synthetic_fixtures_dir` (plan, answer 3).

Tests of other modules (CAD-05, IA-02, DB-01) cannot read `fixtures/` at the repository root:
the folder is not versioned and the CI does not run `hx fixtures build`. The fixture in
`tests/conftest.py` calls the generator once per session and writes the files to a temporary
folder. These tests prove that the folder is exactly what `hx fixtures build` would write.

All data is synthetic.
"""

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import harness

FIXTURES_FOLDER = "fixtures"
GENERATOR_MODULE = "fixtures_sinteticas"


def _files_on_disk(folder):
    """Relative paths (with /) of every file under `folder`."""
    return {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}


def test_session_fixture_matches_generator_bytes(synthetic_fixtures_dir):
    expected = importlib.import_module(GENERATOR_MODULE).gerar_arquivos()

    assert _files_on_disk(synthetic_fixtures_dir) == set(expected)
    for relative, data in expected.items():
        assert (synthetic_fixtures_dir / relative).read_bytes() == data, relative


def test_session_fixture_passes_fixtures_check(synthetic_fixtures_dir, capsys):
    assert synthetic_fixtures_dir.name == FIXTURES_FOLDER

    code = harness.main(["fixtures", "build", "--check"], raiz=synthetic_fixtures_dir.parent)

    assert code == 0, capsys.readouterr().err


def test_session_fixture_lives_outside_the_repository(synthetic_fixtures_dir):
    assert not synthetic_fixtures_dir.resolve().is_relative_to(REPO_ROOT.resolve())
