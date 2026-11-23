"""NUC-01 c3 and c4: GET /api/v1/health with the database up and down.

Contract from the approved plan (answer 12, D4): body {"api": "up", "database": "connected"};
with the database down, 503 in application/problem+json with the message of the ficha in
`detail`. Function names follow features/NUC-01.json. No login, no business data.
"""

import importlib
import secrets
import socket

UNAVAILABLE_MESSAGE = "O banco de dados não está respondendo. Tente de novo em alguns minutos."
HEALTH_PATH = "/api/v1/health"


def _client_for(monkeypatch, database_url, migrations_database_url):
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("MIGRATIONS_DATABASE_URL", migrations_database_url)
    config = importlib.import_module("lastro.core.config")
    app_module = importlib.import_module("lastro.api.app")
    testclient = importlib.import_module("fastapi.testclient")
    settings = config.Settings(
        database_url=database_url, migrations_database_url=migrations_database_url
    )
    return testclient.TestClient(app_module.create_app(settings=settings))


def _closed_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_saude_com_banco_conectado_responde_ok(monkeypatch, migrated_database):
    with _client_for(
        monkeypatch, migrated_database.database_url, migrated_database.migrations_database_url
    ) as client:
        response = client.get(HEALTH_PATH)

    assert response.status_code == 200
    assert response.json() == {"api": "up", "database": "connected"}


def test_saude_sem_banco_responde_indisponivel(monkeypatch):
    port = _closed_port()
    user = "app_inventado"
    password = secrets.token_hex(12)
    url = f"postgresql+psycopg://{user}:{password}@127.0.0.1:{port}/banco_inventado"

    with _client_for(monkeypatch, url, url) as client:
        response = client.get(HEALTH_PATH)

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["detail"] == UNAVAILABLE_MESSAGE
    assert body["status"] == 503
    for leaked in ("127.0.0.1", str(port), user, password, "banco_inventado", "Traceback", "psycopg"):
        assert leaked not in response.text, f"the response leaks '{leaked}'"
