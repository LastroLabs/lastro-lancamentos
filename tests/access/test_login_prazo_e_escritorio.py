"""ACE-01, answers to questions 1 and 2 of the plan (24/11/2026).

Question 1 (D9): a session ends after 2 hours without use; every accepted request moves
`expira_em` to now + 2 h, never past `criada_em` + 12 h. Question 2 (D10): the MVP keeps
one active membership per user. With the right password, a user in two firms gets its own
409 (context for support), without opening a session and without naming the firms; with a
wrong password, the usual 401, so nobody learns the account exists.

Reuses the fixtures and helpers of `test_login.py` (same database, same ESC-1 people).
No real data; passwords generated at run time.
"""

import secrets
from datetime import timedelta

import pytest
from test_login import (  # noqa: F401 (fixtures, resolved by name below)
    FIRM_NAME,
    SESSION_ENDED,
    SESSION_PATH,
    WRONG_CREDENTIALS,
    _assert_problem,
    _client,
    _connect,
    _session_rows,
    _sign_in,
    head_database,
    office,
)

from lastro.access.service import hash_password

MULTIPLE_FIRMS = "Este usuário está em mais de um escritório. Peça ao chefe um usuário para cada escritório."
SECOND_FIRM = "ESC-2"
IDLE = timedelta(hours=2)
MAX_DURATION = timedelta(hours=12)
TOLERANCE = timedelta(minutes=1)


@pytest.fixture
def esc1(request):
    """The ESC-1 of `test_login.py` (fixture `office`), resolved by name."""
    return request.getfixturevalue("office")


@pytest.fixture
def two_firms(esc1):
    """contador_d: accountant in ESC-1 and manager in ESC-2."""
    pw = secrets.token_urlsafe(12)
    with _connect(esc1.database) as conn:
        second = conn.execute(
            "INSERT INTO escritorio (nome) VALUES (%s) RETURNING id", (SECOND_FIRM,)
        ).fetchone()[0]
        user_id = conn.execute(
            "INSERT INTO usuario (identificador_login, nome, credencial_hash)"
            " VALUES ('contador_d', 'Contador Teste D', %s) RETURNING id",
            (hash_password(pw),),
        ).fetchone()[0]
        for firm_id, role in ((esc1.firm_id, "contador"), (second, "chefe")):
            conn.execute(
                "INSERT INTO membro (escritorio_id, usuario_id, papel) VALUES (%s, %s, %s)",
                (firm_id, user_id, role),
            )
    return {"office": esc1, "pw": pw}


def _set_session_times(database, created_ago, expires_in):
    with _connect(database) as conn:
        conn.execute(
            "UPDATE sessao SET criada_em = now() - %s, expira_em = now() + %s",
            (created_ago, expires_in),
        )


def _session_times(database):
    with _connect(database) as conn:
        return conn.execute("SELECT criada_em, expira_em, now() FROM sessao").fetchone()


# ---------------------------------------------------------------------------
# D9: 2 hours without use, 12 hours at most
# ---------------------------------------------------------------------------


def test_pedido_renova_o_prazo_por_duas_horas(esc1):
    with _client(esc1.database) as client:
        assert (
            _sign_in(client, "contador_a", esc1.passwords["contador_a"]).status_code
            == 200
        )
        _created_at, expires_at, now = _session_times(esc1.database)
        assert abs(expires_at - (now + IDLE)) < TOLERANCE, "sign-in must give 2 hours"

        _set_session_times(esc1.database, timedelta(hours=3), timedelta(minutes=5))
        identity = client.get(SESSION_PATH)

    assert identity.status_code == 200, identity.text
    _created_at, expires_at, now = _session_times(esc1.database)
    assert abs(expires_at - (now + IDLE)) < TOLERANCE, (
        "a request must renew to now + 2 h"
    )


def test_renovacao_nao_passa_de_doze_horas(esc1):
    with _client(esc1.database) as client:
        assert (
            _sign_in(client, "contador_a", esc1.passwords["contador_a"]).status_code
            == 200
        )
        _set_session_times(esc1.database, timedelta(hours=11), timedelta(minutes=5))
        identity = client.get(SESSION_PATH)

    assert identity.status_code == 200, identity.text
    created_at, expires_at, _now = _session_times(esc1.database)
    assert abs(expires_at - (created_at + MAX_DURATION)) < TOLERANCE


def test_sessao_parada_por_duas_horas_termina(esc1):
    with _client(esc1.database) as client:
        assert (
            _sign_in(client, "contador_a", esc1.passwords["contador_a"]).status_code
            == 200
        )
        _set_session_times(esc1.database, timedelta(hours=3), -timedelta(minutes=1))
        identity = client.get(SESSION_PATH)

    _assert_problem(identity, 401, SESSION_ENDED)


def test_sessao_com_mais_de_doze_horas_termina(esc1):
    with _client(esc1.database) as client:
        assert (
            _sign_in(client, "contador_a", esc1.passwords["contador_a"]).status_code
            == 200
        )
        _set_session_times(
            esc1.database, MAX_DURATION + timedelta(minutes=1), timedelta(minutes=30)
        )
        identity = client.get(SESSION_PATH)

    _assert_problem(identity, 401, SESSION_ENDED)


# ---------------------------------------------------------------------------
# D10: one active membership per user in the MVP, with its own error
# ---------------------------------------------------------------------------


def test_dois_escritorios_recebe_erro_proprio_so_com_a_senha_certa(two_firms):
    esc1 = two_firms["office"]
    with _client(esc1.database) as client:
        bad_pw = _sign_in(client, "contador_d", secrets.token_urlsafe(12))
        right_pw = _sign_in(client, "contador_d", two_firms["pw"])
        identity = client.get(SESSION_PATH)

    # Wrong password: the usual refusal, nothing says the account exists.
    _assert_problem(bad_pw, 401, WRONG_CREDENTIALS)
    # Right password: its own answer, no session, no firm name.
    _assert_problem(right_pw, 409, MULTIPLE_FIRMS)
    for refusal in (bad_pw, right_pw):
        assert "set-cookie" not in refusal.headers
        for firm in (FIRM_NAME, SECOND_FIRM):
            assert firm not in refusal.text, f"the refusal leaks '{firm}'"
    assert identity.status_code == 401
    assert _session_rows(esc1.database) == []
