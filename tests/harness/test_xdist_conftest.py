"""Tests of the parallel hooks in tests/conftest.py (issue #93, DECISIONS §12 V2)."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

CONFTEST = Path(__file__).resolve().parents[1] / "conftest.py"


@pytest.fixture(scope="module")
def conftest_module():
    spec = importlib.util.spec_from_file_location("_lastro_root_conftest_under_test", CONFTEST)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _workers(module, monkeypatch, args, cpus=8):
    monkeypatch.setattr(module.os, "cpu_count", lambda: cpus)
    return module.pytest_xdist_auto_num_workers(SimpleNamespace(args=args))


def test_suite_uses_up_to_four_workers(conftest_module, monkeypatch):
    assert _workers(conftest_module, monkeypatch, ["-q"]) == 4
    assert _workers(conftest_module, monkeypatch, ["tests"], cpus=2) == 2


def test_single_cpu_runs_in_series(conftest_module, monkeypatch):
    assert _workers(conftest_module, monkeypatch, [], cpus=1) == 0


@pytest.mark.parametrize("argument", ["tests/x/test_a.py::test_b", "tests/x/test_a.py"])
def test_file_or_test_argument_runs_in_series(conftest_module, monkeypatch, argument):
    assert _workers(conftest_module, monkeypatch, [argument]) == 0


def test_web_tests_get_one_xdist_group(conftest_module):
    web = SimpleNamespace(path=conftest_module.WEB_TESTS_DIR / "test_web.py", markers=[])
    other = SimpleNamespace(path=CONFTEST.parent / "core" / "test_x.py", markers=[])
    for item in (web, other):
        item.add_marker = item.markers.append
    conftest_module.pytest_collection_modifyitems([web, other])
    assert [m.args for m in web.markers] == [(conftest_module.WEB_GROUP,)]
    assert other.markers == []
