"""ACE-01: sign in with an individual login, identify the session and sign out (c1 to c6).

The API runs with `create_app()` against the Testcontainers PostgreSQL of the NUC-01
fixtures, migrated to `head` by a fixture of this file (plan D8; the `migrated_database`
of `tests/access/conftest.py` stays pinned to the DB-01 revision). Users are written
straight to the database with passwords generated at run time and hashed by
`lastro.access.service.hash_password` (plan D4). Each person uses its own `TestClient`,
so each one keeps its own cookie (plan D2). No real data.
"""

import hashlib
import secrets
from dataclasses import dataclass
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from lastro.access.service import hash_password
from lastro.api.app import create_app
from lastro.core.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[2]
SESSION_PATH = "/api/v1/session"
BASE_URL = "https://testserver"
SUPERUSER = "postgres"

WRONG_CREDENTIALS = "Usuário ou senha incorretos."
SESSION_ENDED = "Sua sessão terminou. Entre de novo."
SIGN_IN_REQUIRED = "Entre para continuar."

FIRM_NAME = "ESC-1"
ACCOUNTANT_ROLE = "accountant"
# c6 of the ficha: the password that contador_c, still without a credential, tries.
INVITED_PASSWORD = "senha-teste-123"


@dataclass(frozen=True)
class Person:
    login: str
    name: str
    role: str
    password: str | None


@dataclass(frozen=True)
class Office:
    database: object
    firm_id: str
    passwords: dict


PEOPLE = (
    Person("chefe_1", "Chefe Teste Um", "chefe", secrets.token_urlsafe(12)),
    Person("contador_a", "Contador Teste A", "contador", secrets.token_urlsafe(12)),
    Person("contador_b", "Contador Teste B", "contador", secrets.token_urlsafe(12)),
    # c6: pending invitation, credencial_hash NULL.
    Person("contador_c", "Contador Teste C", "contador", None),
)


@pytest.fixture
def head_database(database_templates):
    """Fresh database with every migration applied: a copy of the `head` template (issue #93)."""
    with database_templates.cloned("head") as database:
        yield database


def _connect(database):
    return psycopg.connect(**database.conninfo(SUPERUSER), autocommit=True)


@pytest.fixture
def office(head_database):
    """ESC-1 with chefe_1, contador_a, contador_b and contador_c (pending invitation)."""
    passwords = {}
    with _connect(head_database) as conn:
        firm_id = conn.execute(
            "INSERT INTO escritorio (nome) VALUES (%s) RETURNING id", (FIRM_NAME,)
        ).fetchone()[0]
        members = {}
        for person in PEOPLE:
            credential = (
                None if person.password is None else hash_password(person.password)
            )
            user_id = conn.execute(
                "INSERT INTO usuario (identificador_login, nome, credencial_hash)"
                " VALUES (%s, %s, %s) RETURNING id",
                (person.login, person.name, credential),
            ).fetchone()[0]
            members[person.login] = conn.execute(
                "INSERT INTO membro (escritorio_id, usuario_id, papel)"
                " VALUES (%s, %s, %s) RETURNING id",
                (firm_id, user_id, person.role),
            ).fetchone()[0]
            passwords[person.login] = person.password
        conn.execute(
            "INSERT INTO convite (escritorio_id, membro_id, hash_token, criado_por, expira_em)"
            " VALUES (%s, %s, %s, %s, now() + interval '48 hours')",
            (
                firm_id,
                members["contador_c"],
                hashlib.sha256(secrets.token_bytes(32)).hexdigest(),
                members["chefe_1"],
            ),
        )
    return Office(database=head_database, firm_id=str(firm_id), passwords=passwords)


def _client(database, cookies=None):
    settings = Settings(
        database_url=database.database_url,
        migrations_database_url=database.migrations_database_url,
    )
    return TestClient(create_app(settings=settings), base_url=BASE_URL, cookies=cookies)


def _sign_in(client, login, password):
    return client.post(SESSION_PATH, json={"username": login, "password": password})


def _session_rows(database):
    with _connect(database) as conn:
        return conn.execute("SELECT hash_token, encerrada_em FROM sessao").fetchall()


def _assert_problem(response, status, detail):
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["status"] == status
    assert body["detail"] == detail


def _assert_no_identity(response, office):
    for leaked in ("contador_a", "contador_b", "contador_c", FIRM_NAME, office.firm_id):
        assert leaked not in response.text, f"the refusal leaks '{leaked}'"


# ---------------------------------------------------------------------------
# c1: own credentials open a session that says who, which role and which firm
# ---------------------------------------------------------------------------


def test_login_valido_abre_sessao_identificada(office):
    pw = office.passwords["contador_a"]
    with _client(office.database) as client:
        sign_in = _sign_in(client, "contador_a", pw)
        identity = client.get(SESSION_PATH)

    assert sign_in.status_code == 200, sign_in.text
    assert identity.status_code == 200, identity.text
    body = identity.json()
    assert body["username"] == "contador_a"
    assert body["role"] == ACCOUNTANT_ROLE
    assert body["firm_id"] == office.firm_id
    assert body["firm_name"] == FIRM_NAME
    assert sign_in.json() == body

    # Session cookie kept on the server side: the browser script cannot read it (plan D2).
    set_cookie = sign_in.headers.get("set-cookie", "").lower()
    for attribute in ("httponly", "secure", "samesite=lax"):
        assert attribute in set_cookie, f"session cookie without {attribute}"

    rows = _session_rows(office.database)
    assert len(rows) == 1
    stored_hash, ended_at = rows[0]
    assert ended_at is None
    cookie_values = list(sign_in.cookies.values())
    assert cookie_values, "sign-in did not set a session cookie"
    for response in (sign_in, identity):
        for secret in (pw, stored_hash, *cookie_values):
            assert secret not in response.text, (
                "a response carries the password, hash or token"
            )
    # Only a hash of the token is stored.
    assert all(token != stored_hash for token in cookie_values)


# ---------------------------------------------------------------------------
# c2: wrong password and unknown user get the same refusal
# ---------------------------------------------------------------------------


def test_senha_errada_e_usuario_inexistente_mesma_recusa(office):
    with _client(office.database) as client:
        bad_pw = _sign_in(client, "contador_a", secrets.token_urlsafe(12))
        unknown_user = _sign_in(
            client, "usuario_inexistente", secrets.token_urlsafe(12)
        )
        identity = client.get(SESSION_PATH)

    for refusal in (bad_pw, unknown_user):
        _assert_problem(refusal, 401, WRONG_CREDENTIALS)
        assert "set-cookie" not in refusal.headers
        _assert_no_identity(refusal, office)
    assert bad_pw.json() == unknown_user.json()
    _assert_problem(identity, 401, SIGN_IN_REQUIRED)
    assert _session_rows(office.database) == []


# ---------------------------------------------------------------------------
# c3: two accountants of the same firm, each identified by their own session
# ---------------------------------------------------------------------------


def test_sessoes_simultaneas_identificam_cada_contador(office):
    with _client(office.database) as client_a, _client(office.database) as client_b:
        assert (
            _sign_in(client_a, "contador_a", office.passwords["contador_a"]).status_code
            == 200
        )
        assert (
            _sign_in(client_b, "contador_b", office.passwords["contador_b"]).status_code
            == 200
        )

        first = client_a.get(SESSION_PATH)
        second = client_b.get(SESSION_PATH)
        third = client_a.get(SESSION_PATH)

    expected = ("contador_a", "contador_b", "contador_a")
    for response, username in zip((first, second, third), expected, strict=True):
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["username"] == username
        assert body["role"] == ACCOUNTANT_ROLE
        assert body["firm_name"] == FIRM_NAME
        assert body["firm_id"] == office.firm_id
    assert len(_session_rows(office.database)) == 2


# ---------------------------------------------------------------------------
# c4: after signing out, the same session no longer gives access
# ---------------------------------------------------------------------------


def test_sair_encerra_a_sessao(office):
    with _client(office.database) as client:
        assert (
            _sign_in(client, "contador_a", office.passwords["contador_a"]).status_code
            == 200
        )
        assert client.get(SESSION_PATH).status_code == 200
        same_session = dict(client.cookies)
        sign_out = client.delete(SESSION_PATH)

    assert sign_out.status_code == 204, sign_out.text

    # The same session cookie, sent again after signing out.
    with _client(office.database, cookies=same_session) as replay:
        identity = replay.get(SESSION_PATH)

    _assert_problem(identity, 401, SESSION_ENDED)
    _assert_no_identity(identity, office)
    rows = _session_rows(office.database)
    assert len(rows) == 1
    assert rows[0][1] is not None, "sessao.encerrada_em was not filled on sign-out"


# ---------------------------------------------------------------------------
# c5: a protected resource without a session is refused without data
# ---------------------------------------------------------------------------


def test_pedido_sem_sessao_recusado_sem_dado(office):
    with _client(office.database) as client:
        identity = client.get(SESSION_PATH)

    _assert_problem(identity, 401, SIGN_IN_REQUIRED)
    _assert_no_identity(identity, office)


# ---------------------------------------------------------------------------
# c6: a user who has not created the password yet gets the wrong-password refusal
# ---------------------------------------------------------------------------


def test_usuario_sem_senha_recebe_mesma_recusa(office):
    with _client(office.database) as client:
        bad_pw = _sign_in(client, "contador_a", secrets.token_urlsafe(12))
        invited_pw = _sign_in(client, "contador_c", INVITED_PASSWORD)
        empty_pw = _sign_in(client, "contador_c", "")

    for refusal in (invited_pw, empty_pw):
        _assert_problem(refusal, 401, WRONG_CREDENTIALS)
        assert refusal.json() == bad_pw.json()
        assert "set-cookie" not in refusal.headers
        assert "convite" not in refusal.text.lower()
        _assert_no_identity(refusal, office)
    assert _session_rows(office.database) == []
