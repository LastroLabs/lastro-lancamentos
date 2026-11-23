"""WEB-01 c1 to c5: the front-end environment, routes, generated API client and texts.

The tests run inside the verification container (`docker compose run --rm dev pytest ...`) and
call `pnpm` there. c2 and c4 run the component tests of `web/tests/` (Vitest + Testing Library)
through `pnpm run test` and read the JSON report, so a test that did not run fails here.
Function names follow features/WEB-01.json. Only invented data (the token `abc123`).
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WEB = REPO_ROOT / "web"
SRC = WEB / "src"
COPY_DIR = SRC / "copy"
MICROCOPY = REPO_ROOT / "docs" / "design" / "microcopy.md"
OPENAPI_JSON = REPO_ROOT / "docs" / "api" / "openapi.json"
SCHEMA_TS = SRC / "api" / "schema.d.ts"

INSTALL_TIMEOUT = 900
COMMAND_TIMEOUT = 600

PAGE_TEXTS = (
    "Entrar",
    "Criar sua senha",
    "Área do chefe",
    "Área do contador",
    "Envio do extrato",
    "Página não encontrada. Confira o endereço ou volte ao início.",
)
HEALTH_TEXTS = (
    "Sistema no ar.",
    "O sistema está fora do ar. Tente de novo em alguns minutos.",
)
ROUTE_PATHS = (
    "/entrar",
    "/convite/abc123",
    "/chefe",
    "/contador",
    "/enviar/abc123",
    "/qualquer-coisa",
)
HEALTH_CASES = ("200", "503", "network")
MICROCOPY_SECTIONS = ("chefe", "contador", "cliente", "geral")

# Literal text in JSX: between tags (`>text<`, `>text{`, `}text<`), `{"text"}` and attributes.
JSX_TEXT = re.compile(r"[>}]([^<>{}]*[A-Za-zÀ-ÿ][^<>{}]*)(?=[<{])")
JSX_STRING_EXPRESSION = re.compile(r">\s*\{\s*[\"'`][^\"'`]*[A-Za-zÀ-ÿ]")
TEXT_ATTRIBUTE = re.compile(
    r"\b(?:aria-label|aria-description|title|alt|placeholder)\s*=\s*"
    r"(?:\"[^\"]*[A-Za-zÀ-ÿ][^\"]*\"|\{\s*[\"'`][^\"'`]*[A-Za-zÀ-ÿ])"
)
NOT_TEXT = re.compile(
    r"[=;()]|&&|\|\||\b(?:const|let|var|return|function|import|export|if|else|for|type)\b"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(command, *, cwd=WEB, timeout=COMMAND_TIMEOUT):
    """Run a command; a missing program or a timeout fails the test with a clear message."""
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        pytest.fail(
            f"Program not found: {command[0]!r} (cwd={cwd}). Is it in the dev image?"
        )
    except NotADirectoryError:
        pytest.fail(f"Folder not found: {cwd}")
    except subprocess.TimeoutExpired:
        pytest.fail(f"Timeout of {timeout}s: {' '.join(command)}")


def _require_ok(result, label):
    tail = "\n".join((result.stdout + "\n" + result.stderr).strip().splitlines()[-30:])
    assert result.returncode == 0, f"{label} exited with {result.returncode}:\n{tail}"


def _git_files(*paths):
    result = _run(
        ["git", "-c", "safe.directory=*", "ls-files", "--", *(str(p) for p in paths)],
        cwd=REPO_ROOT,
    )
    _require_ok(result, "git ls-files")
    return [line for line in result.stdout.splitlines() if line]


def _read_json(path):
    assert path.is_file(), f"Missing file: {path.relative_to(REPO_ROOT)}"
    return json.loads(path.read_text(encoding="utf-8"))


def _install():
    """Install the front dependencies from the lockfile (idempotent)."""
    assert (WEB / "package.json").is_file(), "web/package.json does not exist"
    result = _run(["pnpm", "install", "--frozen-lockfile"], timeout=INSTALL_TIMEOUT)
    _require_ok(result, "pnpm install --frozen-lockfile")


def _run_component_tests(test_file, report_dir):
    """Run one Vitest file through `pnpm run test`; return the report entries of its tests."""
    report = report_dir / "vitest-report.json"
    result = _run(
        [
            "pnpm",
            "run",
            "test",
            f"tests/{test_file}",
            "--reporter=json",
            f"--outputFile={report}",
        ]
    )
    assert report.is_file(), (
        f"Vitest wrote no report for tests/{test_file} (does the file exist?):\n"
        f"{result.stdout[-1500:]}\n{result.stderr[-1500:]}"
    )
    data = json.loads(report.read_text(encoding="utf-8"))
    files = [f for f in data["testResults"] if f["name"].endswith(f"tests/{test_file}")]
    assert len(files) == 1, f"tests/{test_file} did not run"
    tests = files[0]["assertionResults"]
    failed = [t["fullName"] for t in tests if t["status"] != "passed"]
    assert not failed, f"Component tests not passing in tests/{test_file}: {failed}"
    assert files[0]["status"] == "passed", f"tests/{test_file} did not pass as a file"
    assert result.returncode == 0, f"pnpm run test exited with {result.returncode}"
    return tests


def _flatten(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _flatten(item)
    elif isinstance(value, list):
        for item in value:
            yield from _flatten(item)


def _copy_texts():
    files = sorted(COPY_DIR.glob("*.json"))
    assert files, "web/src/copy/ has no *.json file with the texts"
    texts = []
    for file in files:
        texts.extend(_flatten(_read_json(file)))
    return texts


def _literal_texts(source):
    """Literal screen texts found in one JSX source (between tags, in expressions, attributes)."""
    found = [m.group(1).strip() for m in JSX_TEXT.finditer(source)]
    found = [text for text in found if text and not NOT_TEXT.search(text)]
    found += [m.group(0).strip() for m in JSX_STRING_EXPRESSION.finditer(source)]
    found += [m.group(0).strip() for m in TEXT_ATTRIBUTE.finditer(source)]
    return found


# ---------------------------------------------------------------------------
# c1: installs, lints, tests and builds in the container
# ---------------------------------------------------------------------------


def test_web01_front_instala_lint_testes_e_build_no_conteiner():
    package_path = WEB / "package.json"
    assert package_path.is_file(), "web/package.json does not exist"
    package = _read_json(package_path)

    # Pinned toolchain: Node in the container = engines = .nvmrc; the lockfile is versioned.
    node = _run(["node", "--version"])
    _require_ok(node, "node --version")
    node_version = node.stdout.strip().lstrip("v")
    engines_node = package.get("engines", {}).get("node", "").strip().lstrip("v")
    nvmrc = WEB / ".nvmrc"
    assert nvmrc.is_file(), "web/.nvmrc does not exist"
    nvmrc_version = nvmrc.read_text(encoding="utf-8").strip().lstrip("v")
    assert engines_node, "web/package.json has no engines.node"
    assert node_version == engines_node == nvmrc_version, (
        f"Node versions differ: container={node_version}, engines={engines_node}, "
        f".nvmrc={nvmrc_version}"
    )
    assert package.get("packageManager", "").startswith("pnpm@"), (
        "packageManager must be pnpm@x"
    )
    assert (WEB / "pnpm-lock.yaml").is_file(), "web/pnpm-lock.yaml does not exist"
    assert "web/pnpm-lock.yaml" in _git_files(WEB / "pnpm-lock.yaml"), (
        "lockfile not versioned"
    )

    # Stack of the sheet: React 19, TypeScript strict, Vite, Biome, Vitest.
    dependencies = {
        **package.get("dependencies", {}),
        **package.get("devDependencies", {}),
    }
    for name in ("react", "typescript", "vite", "@biomejs/biome", "vitest"):
        assert name in dependencies, f"web/package.json lacks {name}"
    assert "19" in dependencies["react"], (
        f"React must be 19, got {dependencies['react']}"
    )
    scripts = package.get("scripts", {})
    assert "biome" in scripts.get("lint", ""), "script lint must run Biome"
    assert "vitest" in scripts.get("test", ""), "script test must run Vitest"
    assert "vite" in scripts.get("build", ""), "script build must run Vite"
    tsconfigs = list(WEB.glob("tsconfig*.json"))
    assert any(
        re.search(r'"strict"\s*:\s*true', t.read_text("utf-8")) for t in tsconfigs
    ), 'TypeScript must be strict (tsconfig with "strict": true)'

    # The four commands of the sheet.
    _install()
    shutil.rmtree(WEB / "dist", ignore_errors=True)
    for script in ("lint", "test", "build"):
        _require_ok(_run(["pnpm", "run", script]), f"pnpm run {script}")
    assert (WEB / "dist" / "index.html").is_file(), (
        "the build did not create web/dist/index.html"
    )

    # Nothing generated is versioned.
    assert _git_files(WEB / "dist", WEB / "node_modules") == []


# ---------------------------------------------------------------------------
# c2: structure and routes
# ---------------------------------------------------------------------------


def test_web01_rotas_dos_tres_papeis_e_pagina_nao_encontrada(tmp_path):
    _install()
    folders = (
        "api",
        "components",
        "copy",
        "pages/manager",
        "pages/accountant",
        "pages/client",
    )
    missing = [f"web/src/{f}" for f in folders if not (SRC / f).is_dir()]
    assert not missing, f"Missing folders: {missing}"
    package = _read_json(WEB / "package.json")
    assert "@tanstack/react-router" in package.get("dependencies", {}), (
        "routes need TanStack Router"
    )

    tests = _run_component_tests("routes.test.tsx", tmp_path)
    names = " ".join(t["fullName"] for t in tests)
    for path in ROUTE_PATHS:
        assert path in names, f"No component test opened the route {path}"


# ---------------------------------------------------------------------------
# c3: API client generated from the OpenAPI, and stable
# ---------------------------------------------------------------------------


def test_web01_cliente_da_api_gerado_do_openapi_e_estavel():
    _install()
    script = _read_json(WEB / "package.json").get("scripts", {}).get("gerar:api", "")
    assert script, "web/package.json has no script gerar:api"
    assert "openapi-typescript" in script, "gerar:api must run openapi-typescript"

    _require_ok(_run(["pnpm", "run", "gerar:api"]), "pnpm run gerar:api (1st)")
    first = {path: path.read_bytes() for path in (OPENAPI_JSON, SCHEMA_TS)}
    _require_ok(_run(["pnpm", "run", "gerar:api"]), "pnpm run gerar:api (2nd)")
    for path, content in first.items():
        assert path.read_bytes() == content, (
            f"2nd run changed {path.relative_to(REPO_ROOT)}"
        )

    # Both files are versioned and equal to what the command generates.
    for path in first:
        relative = str(path.relative_to(REPO_ROOT))
        assert _git_files(path) == [relative], f"{relative} is not versioned"
        diff = _run(
            ["git", "-c", "safe.directory=*", "diff", "--exit-code", "--", relative],
            cwd=REPO_ROOT,
        )
        assert diff.returncode == 0, (
            f"{relative} differs from the versioned file:\n{diff.stdout}"
        )

    openapi = json.loads(OPENAPI_JSON.read_text(encoding="utf-8"))
    assert "/api/v1/health" in openapi["paths"], "openapi.json lacks /api/v1/health"
    schema = SCHEMA_TS.read_text(encoding="utf-8")
    assert "/api/v1/health" in schema, "schema.d.ts lacks /api/v1/health"
    assert "openapi-typescript" in schema.splitlines()[0] + schema[:300], (
        "schema.d.ts not generated"
    )

    # The HTTP client uses openapi-fetch with the generated types and the configured base URL.
    sources = [p for p in (SRC / "api").glob("*.ts*") if p.name != "schema.d.ts"]
    assert sources, "web/src/api/ has no client besides schema.d.ts"
    text = "\n".join(p.read_text(encoding="utf-8") for p in sources)
    assert "openapi-fetch" in text, "the client must use openapi-fetch"
    assert "schema" in text, "the client must use the types of schema.d.ts"
    assert "/api/v1" in text, "the client must use the /api/v1 prefix"
    assert "VITE_API_URL" in text, "the base address must come from VITE_API_URL"
    handwritten = re.findall(r"^\s*(?:export\s+)?interface\s+\w+", text, re.MULTILINE)
    assert not handwritten, f"API types must not be written by hand: {handwritten}"
    package = _read_json(WEB / "package.json")
    for name in ("openapi-fetch", "openapi-typescript"):
        assert name in {
            **package.get("dependencies", {}),
            **package.get("devDependencies", {}),
        }


# ---------------------------------------------------------------------------
# c4: home page shows the API health
# ---------------------------------------------------------------------------


def test_web01_pagina_inicial_mostra_saude_da_api(tmp_path):
    _install()
    tests = _run_component_tests("home.test.tsx", tmp_path)
    names = " ".join(t["fullName"] for t in tests)
    for case in HEALTH_CASES:
        assert case in names, f"No component test covers the health case {case!r}"


# ---------------------------------------------------------------------------
# c5: all screen texts come from copy/ and are listed in the microcopy
# ---------------------------------------------------------------------------


def test_web01_textos_de_tela_centralizados_no_microcopy():
    assert (COPY_DIR / "index.ts").is_file(), "web/src/copy/index.ts does not exist"
    texts = _copy_texts()
    assert texts, "web/src/copy/ has no text"
    for required in (*PAGE_TEXTS, *HEALTH_TEXTS):
        assert required in texts, (
            f"Text of c2/c4 missing in web/src/copy/: {required!r}"
        )

    assert MICROCOPY.is_file(), "docs/design/microcopy.md does not exist"
    microcopy = MICROCOPY.read_text(encoding="utf-8")
    headings = [
        line.lstrip("#").strip().lower()
        for line in microcopy.splitlines()
        if line.startswith("#")
    ]
    for section in MICROCOPY_SECTIONS:
        assert any(section in heading for heading in headings), (
            f"microcopy.md lacks the section {section!r}"
        )
    not_listed = [text for text in texts if text not in microcopy]
    assert not not_listed, (
        f"Texts in copy/ missing (or different) in microcopy.md: {not_listed}"
    )

    # No literal text in the components and pages.
    sources = [
        path
        for folder in ("pages", "components")
        for path in sorted((SRC / folder).rglob("*.tsx"))
    ]
    assert any((SRC / "pages").rglob("*.tsx")), "web/src/pages/ has no page yet"
    offenders = {
        str(path.relative_to(REPO_ROOT)): _literal_texts(
            path.read_text(encoding="utf-8")
        )
        for path in sources
    }
    offenders = {path: found for path, found in offenders.items() if found}
    assert not offenders, f"Literal text in JSX (use web/src/copy/): {offenders}"
