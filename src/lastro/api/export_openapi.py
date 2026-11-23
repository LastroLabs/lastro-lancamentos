"""Export the OpenAPI document of the app to a file, without starting a server (plan WEB-01, D4).

Usage:
    python -m lastro.api.export_openapi <output.json>

The output is deterministic (sorted keys, 2-space indent, final newline), so exporting again
changes no byte. The database URL is a placeholder: creating the app never connects.
"""

import json
import sys
from pathlib import Path

from lastro.api.app import create_app
from lastro.core.config import Settings

PLACEHOLDER_DATABASE_URL = "postgresql+psycopg://openapi:openapi@localhost:5432/openapi"


def render_openapi() -> str:
    """Build the app and return its OpenAPI document as stable JSON text.

    Returns:
        The JSON text, ending with a newline.
    """
    app = create_app(Settings(database_url=PLACEHOLDER_DATABASE_URL))
    return json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    """Write the OpenAPI document to the path given in `argv[0]`.

    Args:
        argv: command-line arguments, without the program name.

    Returns:
        The exit code: 0 on success, 2 on wrong usage.
    """
    if len(argv) != 1:
        print("Uso: python -m lastro.api.export_openapi <arquivo.json>", file=sys.stderr)
        return 2
    path = Path(argv[0])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_openapi(), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
