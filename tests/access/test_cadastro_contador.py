"""ACE-02: the manager invites accountants and assigns clients (c1 to c11).

The 14 names of `features/ACE-02.json` come first; the extra tests at the end cover the
answers of `planos/ACE-02/plan.md` (questions 4 and 5, D6) and the "does not read the
password hash" promises of c2.

Names of routes and fields follow the plan (section 5, question 1), in English:

    POST   /api/v1/accountants                    {name, username}
    GET    /api/v1/accountants                    -> [{id, name, username, role, status}]
    POST   /api/v1/accountants/{id}/invitation    -> {invitation_code, invitation_path, expires_at, ...}
    DELETE /api/v1/accountants/{id}/invitation    -> 204
    POST   /api/v1/invitations/accept             {invitation_code, username, password}
    POST   /api/v1/clients/{id}/assignment        {member_id}
    GET    /api/v1/clients/{id}/assignment        -> {responsible: null | {id, name, username}}

`{id}` of a person is the id of the member (plan, question 2). The plan fixes the names of the
response fields but not those of the request bodies of `accept` and of the assignment: the
tests assume `invitation_code`, `username`, `password` and `member_id`.

The API runs with `create_app()` against the Testcontainers PostgreSQL migrated to `head`
(`head_database` of `test_login.py`). Firms, people, clients and the states of the examples
(pending, expired, used or revoked invitation; existing assignment) are written straight to the
database as the superuser, so a missing route fails only the step under test. Passwords are
generated at run time. No real data: ESC-1, ESC-2, EMP-n, chefe_1, contador_a, contador_c...
"""

import hashlib
import logging
import re
import secrets
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta

import psycopg
import pytest
from psycopg import errors
from test_login import (  # noqa: F401 (head_database is a fixture, resolved by name)
    REPO_ROOT,
    SESSION_PATH,
    _client,
    _connect,
    _sign_in,
    head_database,
)

from lastro.access.passwords import verify_password
from lastro.access.service import hash_password

APP_ROLE = "lastro_app"
FIRM_SETTING = "app.firm_id"
ACCOUNTANTS_PATH = "/api/v1/accountants"
ACCEPT_PATH = "/api/v1/invitations/accept"
CLIENTS_PATH = "/api/v1/clients"
INVALID_DATA_STATUS = 422  # P-13, decided in the plan (question 6)

MSG_DEAD_INVITE = "Este convite não vale mais. Peça um novo ao chefe do escritório."
MSG_SHORT_PASSWORD = "A senha precisa ter pelo menos 8 caracteres."
MSG_EMPTY_NAME = "Informe o nome do contador."
MSG_EMPTY_USERNAME = "Informe o usuário de entrada do contador."
MSG_USERNAME_TAKEN = "Este usuário já existe. Escolha outro."
MSG_ALREADY_HAS_PASSWORD = "Este contador já criou a senha."
MSG_MANAGER_ONLY = "Só o chefe do escritório pode fazer isso."
MSG_NO_CLIENT = "Você não tem acesso a este cliente."
MSG_NO_RESPONSIBLE = "Responsável não encontrado no seu escritório."
MSG_NO_ACCOUNTANT = "Contador não encontrado no seu escritório."
MSG_HAS_RESPONSIBLE = "Este cliente já tem um responsável. Use a reatribuição."
MSG_PASSWORD_CREATED = "Senha criada. Agora é só entrar."
MSG_SIGN_IN = "Entre para continuar."

NAME_C = "CONTADOR TESTE C"
ROLE_MANAGER = "manager"
ROLE_ACCOUNTANT = "accountant"
FIRM_1 = "ESC-1"
FIRM_2 = "ESC-2"
# Tables whose rows must not change when a request is refused.
STATE_TABLES = ("usuario", "membro", "convite", "cliente", "atribuicao")


# ---------------------------------------------------------------------------
# World: firms, people, clients and the states of the examples
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Person:
    firm: str
    login: str
    name: str
    role: str  # database value: 'chefe' or 'contador'
    user_id: uuid.UUID
    member_id: uuid.UUID
    password: str | None


@dataclass(frozen=True)
class World:
    database: object
    firm_ids: dict
    people: dict  # login -> Person


def _insert_person(conn, firm, firm_id, login, name, role, password) -> Person:
    credential = None if password is None else hash_password(password)
    user_id = conn.execute(
        "INSERT INTO usuario (identificador_login, nome, credencial_hash)"
        " VALUES (%s, %s, %s) RETURNING id",
        (login, name, credential),
    ).fetchone()[0]
    member_id = conn.execute(
        "INSERT INTO membro (escritorio_id, usuario_id, papel) VALUES (%s, %s, %s)"
        " RETURNING id",
        (firm_id, user_id, role),
    ).fetchone()[0]
    return Person(firm, login, name, role, user_id, member_id, password)


@pytest.fixture
def world(head_database):  # noqa: F811
    """ESC-1 (chefe_1, contador_a) and ESC-2 (chefe_2, contador_x), all with a password."""
    seed = {
        FIRM_1: (
            ("chefe_1", "Chefe Teste Um", "chefe"),
            ("contador_a", "Contador Teste A", "contador"),
        ),
        FIRM_2: (
            ("chefe_2", "Chefe Teste Dois", "chefe"),
            ("contador_x", "Contador Teste X", "contador"),
        ),
    }
    firm_ids, people = {}, {}
    with _connect(head_database) as conn:
        for firm, members in seed.items():
            firm_ids[firm] = conn.execute(
                "INSERT INTO escritorio (nome) VALUES (%s) RETURNING id", (firm,)
            ).fetchone()[0]
            for login, name, role in members:
                people[login] = _insert_person(
                    conn,
                    firm,
                    firm_ids[firm],
                    login,
                    name,
                    role,
                    secrets.token_urlsafe(12),
                )
    return World(database=head_database, firm_ids=firm_ids, people=people)


def _hash_of(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _add_accountant(world, login, name=None, state="pending", firm=FIRM_1):
    """A contador without password and an invitation in `state`; returns (person, code).

    States: pending, expired (ended 1 second ago by the database clock), used, revoked, none.
    """
    name = name or f"Contador Teste {login[-1].upper()}"
    firm_id = world.firm_ids[firm]
    chefe = world.people["chefe_1" if firm == FIRM_1 else "chefe_2"]
    code = secrets.token_urlsafe(32)
    columns = {
        "pending": ("now() + interval '48 hours'", "NULL", "NULL", "now()"),
        "expired": (
            "now() - interval '1 second'",
            "NULL",
            "NULL",
            "now() - interval '2 days'",
        ),
        "used": ("now() + interval '48 hours'", "now()", "NULL", "now()"),
        "revoked": ("now() + interval '48 hours'", "NULL", "now()", "now()"),
    }
    with _connect(world.database) as conn:
        person = _insert_person(conn, firm, firm_id, login, name, "contador", None)
        if state != "none":
            expires, used, revoked, created = columns[state]
            conn.execute(
                "INSERT INTO convite (escritorio_id, membro_id, hash_token, criado_por,"
                " criado_em, expira_em, usado_em, revogado_em)"
                f" VALUES (%s, %s, %s, %s, {created}, {expires}, {used}, {revoked})",
                (firm_id, person.member_id, _hash_of(code), chefe.member_id),
            )
    return person, code


def _add_client(world, name, firm=FIRM_1) -> str:
    """A client straight in the database (a synthetic 14-digit CNPJ, unique per call)."""
    cnpj = f"{secrets.randbelow(10**14):014d}"
    with _connect(world.database) as conn:
        return str(
            conn.execute(
                "INSERT INTO cliente (escritorio_id, nome, cnpj_normalizado)"
                " VALUES (%s, %s, %s) RETURNING id",
                (world.firm_ids[firm], name, cnpj),
            ).fetchone()[0]
        )


def _assign_in_database(world, client_id, person, assigned_by="chefe_1"):
    with _connect(world.database) as conn:
        conn.execute(
            "INSERT INTO atribuicao (escritorio_id, cliente_id, membro_id, atribuido_por,"
            " inicio) VALUES (%s, %s, %s, %s, now())",
            (
                world.firm_ids[FIRM_1],
                client_id,
                person.member_id,
                world.people[assigned_by].member_id,
            ),
        )


def _snapshot(world) -> dict:
    """Every row of the state tables, as text, to prove that a refusal changed nothing."""
    with _connect(world.database) as conn:
        return {
            table: sorted(
                row[0]
                for row in conn.execute(f"SELECT row_to_json(t)::text FROM {table} t")
            )
            for table in STATE_TABLES
        }


def _count(world, table, where="true", params=()) -> int:
    with _connect(world.database) as conn:
        return conn.execute(
            f"SELECT count(*) FROM {table} WHERE {where}",
            params,
        ).fetchone()[0]


def _invites_of(world, person):
    """(hash_token, usado_em, revogado_em) of every invitation of the member."""
    with _connect(world.database) as conn:
        return conn.execute(
            "SELECT hash_token, usado_em, revogado_em FROM convite WHERE membro_id = %s",
            (person.member_id,),
        ).fetchall()


def _pending_count(world, person) -> int:
    return _count(
        world,
        "convite",
        "membro_id = %s AND usado_em IS NULL AND revogado_em IS NULL",
        (person.member_id,),
    )


def _stored_credential(world, person):
    with _connect(world.database) as conn:
        return conn.execute(
            "SELECT credencial_hash FROM usuario WHERE id = %s", (person.user_id,)
        ).fetchone()[0]


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _signed_in(world, login):
    client = _client(world.database)
    person = world.people[login]
    response = _sign_in(client, login, person.password)
    assert response.status_code == 200, f"sign-in of {login} failed: {response.text}"
    return client


def _register(client, name, username):
    return client.post(ACCOUNTANTS_PATH, json={"name": name, "username": username})


def _new_invitation(client, person):
    return client.post(f"{ACCOUNTANTS_PATH}/{person.member_id}/invitation")


def _cancel_invitation(client, person):
    return client.delete(f"{ACCOUNTANTS_PATH}/{person.member_id}/invitation")


def _accept(client, code, username, password):
    return client.post(
        ACCEPT_PATH,
        json={"invitation_code": code, "username": username, "password": password},
    )


def _assign(client, client_id, member_id):
    return client.post(
        f"{CLIENTS_PATH}/{client_id}/assignment", json={"member_id": str(member_id)}
    )


def _responsible(client, client_id):
    return client.get(f"{CLIENTS_PATH}/{client_id}/assignment")


def _statuses(client) -> dict:
    """username -> status of every person in the manager's list."""
    response = client.get(ACCOUNTANTS_PATH)
    assert response.status_code == 200, response.text
    return {item["username"]: item["status"] for item in response.json()}


def _assert_problem(response, status, detail) -> dict:
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["status"] == status
    assert body["detail"] == detail
    return body


def _assert_no_leak(response, *leaked):
    for text in leaked:
        assert str(text) not in response.text, f"the refusal leaks '{text}'"


def _can_sign_in(world, login, password) -> bool:
    with _client(world.database) as client:
        return _sign_in(client, login, password).status_code == 200


# ---------------------------------------------------------------------------
# c1: the manager registers an accountant and gets the invitation once
# ---------------------------------------------------------------------------


def test_chefe_cadastra_contador_e_recebe_convite(world, caplog):
    chefe_1 = world.people["chefe_1"]
    before_users = _count(world, "usuario")

    with caplog.at_level(logging.DEBUG), _signed_in(world, "chefe_1") as client:
        created = _register(client, NAME_C, "contador_c")
        listed = client.get(ACCOUNTANTS_PATH)

    assert created.status_code == 201, created.text
    body = created.json()
    assert body["name"] == NAME_C
    assert body["username"] == "contador_c"
    assert body["role"] == ROLE_ACCOUNTANT
    assert body["status"] == "convite_pendente"
    uuid.UUID(body["id"])
    code = body["invitation_code"]
    assert len(code) >= 43
    assert re.fullmatch(r"[A-Za-z0-9_-]+", code), "the code is not URL-safe"
    assert body["invitation_path"] == f"/convite/{code}"
    expires_at = datetime.fromisoformat(body["expires_at"])

    # In the database: 1 new user without password, 1 active accountant member, 1 pending invite.
    assert _count(world, "usuario") == before_users + 1
    with _connect(world.database) as conn:
        user_id, credential = conn.execute(
            "SELECT id, credencial_hash FROM usuario WHERE identificador_login = %s",
            ("contador_c",),
        ).fetchone()
        member = conn.execute(
            "SELECT id, escritorio_id, papel, ativo FROM membro WHERE usuario_id = %s",
            (user_id,),
        ).fetchall()
        invites = conn.execute(
            "SELECT membro_id, hash_token, criado_por, criado_em, expira_em, usado_em,"
            " revogado_em FROM convite WHERE membro_id = %s",
            (member[0][0],),
        ).fetchall()
        leaked_in = [
            table
            for table in ("usuario", "membro", "convite", "atribuicao", "sessao")
            if conn.execute(
                f"SELECT count(*) FROM {table} t WHERE t::text LIKE %s",
                (f"%{code}%",),
            ).fetchone()[0]
        ]
    assert credential is None
    assert len(member) == 1
    member_id, firm_id, role, active = member[0]
    assert (firm_id, role, active) == (world.firm_ids[FIRM_1], "contador", True)
    assert str(member_id) == body["id"]
    assert len(invites) == 1
    _, hash_token, created_by, created_at, expires_in_db, used_at, revoked_at = invites[
        0
    ]
    assert hash_token == _hash_of(code)
    assert created_by == chefe_1.member_id
    assert (used_at, revoked_at) == (None, None)
    assert expires_in_db - created_at == timedelta(hours=48)
    assert abs(expires_at - expires_in_db) < timedelta(seconds=1)

    # The code is stored nowhere and logged nowhere.
    assert leaked_in == [], f"the code is stored in {leaked_in}"
    assert code not in caplog.text

    # The list: 3 people, the manager included, with no code and no hash.
    assert listed.status_code == 200, listed.text
    items = listed.json()
    assert len(items) == 3
    by_login = {item["username"]: item for item in items}
    assert set(by_login) == {"chefe_1", "contador_a", "contador_c"}
    assert (by_login["chefe_1"]["role"], by_login["chefe_1"]["status"]) == (
        ROLE_MANAGER,
        "ativo",
    )
    assert by_login["contador_a"]["status"] == "ativo"
    assert by_login["contador_c"]["status"] == "convite_pendente"
    assert code not in listed.text
    for item in items:
        assert "invitation_code" not in item
        assert "invitation_path" not in item
    for forbidden in (hash_token, "credencial", "hash_token"):
        assert forbidden not in listed.text


# ---------------------------------------------------------------------------
# c2: the accountant accepts the invitation, creates the password and signs in
# ---------------------------------------------------------------------------


def test_contador_aceita_convite_cria_senha_e_entra(world):
    contador_c, code = _add_accountant(world, "contador_c", NAME_C)
    password = secrets.token_urlsafe(12)
    other_password = secrets.token_urlsafe(12)

    with _client(world.database) as anonymous:
        accepted = _accept(anonymous, code, "contador_c", password)
        second = _accept(anonymous, code, "contador_c", other_password)
    with _client(world.database) as sign_in_client:
        signed_in = _sign_in(sign_in_client, "contador_c", password)
        identity = sign_in_client.get(SESSION_PATH)

    assert accepted.status_code == 200, accepted.text
    assert MSG_PASSWORD_CREATED in accepted.text
    assert password not in accepted.text
    ((_, used_at, revoked_at),) = _invites_of(world, contador_c)
    assert used_at is not None
    assert revoked_at is None
    stored = _stored_credential(world, contador_c)
    assert stored is not None
    assert stored.startswith("$argon2"), "the hash does not come from hash_password"
    assert verify_password(stored, password)

    assert signed_in.status_code == 200, signed_in.text
    assert identity.status_code == 200, identity.text
    body = identity.json()
    assert (body["username"], body["role"], body["firm_name"]) == (
        "contador_c",
        ROLE_ACCOUNTANT,
        FIRM_1,
    )
    assert body["firm_id"] == str(world.firm_ids[FIRM_1])

    with _signed_in(world, "chefe_1") as chefe_1:
        listed = chefe_1.get(ACCOUNTANTS_PATH)
        assert _statuses(chefe_1)["contador_c"] == "ativo"
    for secret in (password, other_password, stored):
        assert secret not in listed.text, "the manager sees the password or its hash"

    _assert_problem(second, 404, MSG_DEAD_INVITE)
    assert verify_password(_stored_credential(world, contador_c), password)
    assert not verify_password(_stored_credential(world, contador_c), other_password)


# ---------------------------------------------------------------------------
# c3: every dead invitation gets the same refusal; a short password spends nothing
# ---------------------------------------------------------------------------


def test_convite_invalido_recebe_a_mesma_recusa(world):
    contador_c, code_k = _add_accountant(world, "contador_c", NAME_C)
    expired, code_expired = _add_accountant(world, "contador_d", state="expired")
    used, code_used = _add_accountant(world, "contador_e", state="used")
    revoked, code_revoked = _add_accountant(world, "contador_f", state="revoked")
    attempts = (
        ("(a) unknown code", secrets.token_urlsafe(32), "contador_c"),
        ("(b) expired by the database clock", code_expired, "contador_d"),
        ("(c) already used", code_used, "contador_e"),
        ("(d) cancelled", code_revoked, "contador_f"),
        ("(e) username that does not match", code_k, "contador_x"),
    )
    before = _snapshot(world)

    with _client(world.database) as anonymous:
        responses = [
            (label, _accept(anonymous, code, username, secrets.token_urlsafe(12)))
            for label, code, username in attempts
        ]

    bodies = []
    for label, response in responses:
        bodies.append(_assert_problem(response, 404, MSG_DEAD_INVITE))
        _assert_no_leak(
            response,
            "contador_c",
            "contador_d",
            "contador_x",
            NAME_C,
            FIRM_1,
            FIRM_2,
            world.firm_ids[FIRM_1],
        )
    assert all(body == bodies[0] for body in bodies), "the five refusals differ"
    assert _snapshot(world) == before, "a refusal changed the database"
    for person in (contador_c, expired, used, revoked):
        assert _stored_credential(world, person) is None


def test_senha_curta_nao_gasta_o_convite(world):
    contador_c, code = _add_accountant(world, "contador_c", NAME_C)
    before = _snapshot(world)
    password = secrets.token_urlsafe(12)

    with _client(world.database) as anonymous:
        short = _accept(anonymous, code, "contador_c", "curta")
        assert _snapshot(world) == before
        assert _pending_count(world, contador_c) == 1
        later = _accept(anonymous, code, "contador_c", password)

    _assert_problem(short, INVALID_DATA_STATUS, MSG_SHORT_PASSWORD)
    assert later.status_code == 200, later.text
    assert verify_password(_stored_credential(world, contador_c), password)
    assert _can_sign_in(world, "contador_c", password)


# ---------------------------------------------------------------------------
# c4: empty or repeated name/username creates nothing
# ---------------------------------------------------------------------------


def test_cadastro_de_contador_invalido_ou_duplicado_recusado(world):
    before = _snapshot(world)

    with _signed_in(world, "chefe_1") as chefe_1:
        empty_name = _register(chefe_1, "", "contador_c")
        empty_username = _register(chefe_1, NAME_C, "")
        same_firm = _register(chefe_1, NAME_C, "contador_a")
        other_firm = _register(chefe_1, NAME_C, "contador_x")

    _assert_problem(empty_name, INVALID_DATA_STATUS, MSG_EMPTY_NAME)
    _assert_problem(empty_username, INVALID_DATA_STATUS, MSG_EMPTY_USERNAME)
    same_body = _assert_problem(same_firm, 409, MSG_USERNAME_TAKEN)
    other_body = _assert_problem(other_firm, 409, MSG_USERNAME_TAKEN)
    assert same_body == other_body, "the refusal tells which firm owns the username"
    _assert_no_leak(other_firm, FIRM_2, "chefe_2", world.firm_ids[FIRM_2])
    assert _snapshot(world) == before, "a refused registration created something"


# ---------------------------------------------------------------------------
# c5: new invitation, cancellation, and no invitation for who already has a password
# ---------------------------------------------------------------------------


def test_chefe_gera_novo_convite_ou_cancela(world):
    contador_a = world.people["contador_a"]
    contador_c, code_1 = _add_accountant(world, "contador_c", NAME_C)

    with _signed_in(world, "chefe_1") as chefe_1, _client(world.database) as anonymous:
        # (1) a new invitation replaces the pending one
        renewed = _new_invitation(chefe_1, contador_c)
        assert renewed.status_code == 201, renewed.text
        body = renewed.json()
        code_2 = body["invitation_code"]
        assert code_2 != code_1 and len(code_2) >= 43
        assert body["invitation_path"] == f"/convite/{code_2}"
        datetime.fromisoformat(body["expires_at"])
        rows = {row[0]: row for row in _invites_of(world, contador_c)}
        assert rows[_hash_of(code_1)][2] is not None, "K1 was not revoked"
        assert rows[_hash_of(code_2)][1:] == (None, None)
        assert _pending_count(world, contador_c) == 1
        assert _statuses(chefe_1)["contador_c"] == "convite_pendente"

        # (2) the old code is dead at once
        old = _accept(anonymous, code_1, "contador_c", secrets.token_urlsafe(12))
        _assert_problem(old, 404, MSG_DEAD_INVITE)

        # (3) cancelling leaves no pending invitation
        cancelled = _cancel_invitation(chefe_1, contador_c)
        assert cancelled.status_code == 204, cancelled.text
        assert _pending_count(world, contador_c) == 0
        assert _statuses(chefe_1)["contador_c"] == "sem_convite"

        # (4) the cancelled code is dead too; the accountant still has no password
        cancelled_use = _accept(
            anonymous, code_2, "contador_c", secrets.token_urlsafe(12)
        )
        _assert_problem(cancelled_use, 404, MSG_DEAD_INVITE)

        # (5) who already created the password gets no invitation
        refused = _new_invitation(chefe_1, contador_a)
        _assert_problem(refused, 409, MSG_ALREADY_HAS_PASSWORD)

    assert _stored_credential(world, contador_c) is None
    assert not _can_sign_in(world, "contador_c", secrets.token_urlsafe(12))
    assert _pending_count(world, contador_a) == 0


# ---------------------------------------------------------------------------
# c6: the manager assigns a client without a responsible to an active member
# ---------------------------------------------------------------------------


def test_chefe_atribui_cliente_com_um_responsavel_ativo(world):
    contador_c, _ = _add_accountant(
        world, "contador_c", NAME_C
    )  # invitation still pending
    emp_1 = _add_client(world, "EMP-1")

    with _signed_in(world, "chefe_1") as chefe_1:
        assigned = _assign(chefe_1, emp_1, contador_c.member_id)
        consulted = _responsible(chefe_1, emp_1)

    assert assigned.status_code == 201, assigned.text
    assert consulted.status_code == 200, consulted.text
    assert consulted.json()["responsible"] == {
        "id": str(contador_c.member_id),
        "name": NAME_C,
        "username": "contador_c",
    }
    with _connect(world.database) as conn:
        rows = conn.execute(
            "SELECT membro_id, atribuido_por, fim FROM atribuicao WHERE cliente_id = %s",
            (emp_1,),
        ).fetchall()
    assert rows == [(contador_c.member_id, world.people["chefe_1"].member_id, None)]


def test_chefe_atribui_cliente_a_si_mesmo(world):
    chefe_1 = world.people["chefe_1"]
    emp_2 = _add_client(world, "EMP-2")

    with _signed_in(world, "chefe_1") as client:
        assigned = _assign(client, emp_2, chefe_1.member_id)
        consulted = _responsible(client, emp_2)

    assert assigned.status_code == 201, assigned.text
    assert consulted.status_code == 200, consulted.text
    assert consulted.json()["responsible"]["id"] == str(chefe_1.member_id)
    assert consulted.json()["responsible"]["username"] == "chefe_1"
    with _connect(world.database) as conn:
        rows = conn.execute(
            "SELECT membro_id, atribuido_por, fim FROM atribuicao WHERE cliente_id = %s",
            (emp_2,),
        ).fetchall()
    assert rows == [(chefe_1.member_id, chefe_1.member_id, None)]


# ---------------------------------------------------------------------------
# c7: a client that already has a responsible is not assigned again here
# ---------------------------------------------------------------------------


def test_cliente_com_responsavel_nao_e_atribuido_de_novo(world):
    contador_a = world.people["contador_a"]
    contador_c, _ = _add_accountant(world, "contador_c", NAME_C)
    emp_1 = _add_client(world, "EMP-1")
    _assign_in_database(world, emp_1, contador_a)

    with _signed_in(world, "chefe_1") as chefe_1:
        refused = _assign(chefe_1, emp_1, contador_c.member_id)
        consulted = _responsible(chefe_1, emp_1)

    _assert_problem(refused, 409, MSG_HAS_RESPONSIBLE)
    assert consulted.json()["responsible"]["id"] == str(contador_a.member_id)
    assert _count(world, "atribuicao", "cliente_id = %s", (emp_1,)) == 1


# ---------------------------------------------------------------------------
# c8: an accountant is refused every manager action
# ---------------------------------------------------------------------------


def test_contador_sem_papel_de_chefe_recusado(world):
    contador_c, _ = _add_accountant(world, "contador_c", NAME_C)
    emp_1 = _add_client(world, "EMP-1")
    contador_a = world.people["contador_a"]
    before = _snapshot(world)

    with _signed_in(world, "contador_a") as client:
        refusals = (
            _register(client, "CONTADOR TESTE D", "contador_d"),
            _new_invitation(client, contador_c),
            _cancel_invitation(client, contador_c),
            client.post(CLIENTS_PATH, json={"name": "EMP-5", "cnpj": "00000000000191"}),
            _assign(client, emp_1, contador_a.member_id),
        )

    for refusal in refusals:
        _assert_problem(refusal, 403, MSG_MANAGER_ONLY)
    assert _snapshot(world) == before
    assert _count(world, "atribuicao", "cliente_id = %s", (emp_1,)) == 0


# ---------------------------------------------------------------------------
# c9: another firm's manager sees nothing: same refusal as a missing record
# ---------------------------------------------------------------------------


def test_chefe_de_outro_escritorio_nao_atribui_cliente(world):
    contador_x = world.people["contador_x"]
    contador_c, _ = _add_accountant(world, "contador_c", NAME_C)
    emp_1 = _add_client(world, "EMP-1")
    before = _snapshot(world)
    leaked = (emp_1, "EMP-1", "contador_a", "contador_c", NAME_C, FIRM_1)

    with _signed_in(world, "chefe_2") as chefe_2:
        of_other_firm = _assign(chefe_2, emp_1, contador_x.member_id)
        nonexistent = _assign(chefe_2, uuid.uuid4(), contador_x.member_id)
        invitation = _new_invitation(chefe_2, contador_c)

    body_a = _assert_problem(of_other_firm, 404, MSG_NO_CLIENT)
    body_b = _assert_problem(nonexistent, 404, MSG_NO_CLIENT)
    assert body_a == body_b
    _assert_problem(invitation, 404, MSG_NO_ACCOUNTANT)
    for response in (of_other_firm, nonexistent, invitation):
        _assert_no_leak(response, *leaked)
    assert _snapshot(world) == before


def test_atribuir_a_contador_de_outro_escritorio_recusado(world):
    contador_a = world.people["contador_a"]
    emp_9 = _add_client(world, "EMP-9", firm=FIRM_2)
    before = _snapshot(world)

    with _signed_in(world, "chefe_2") as chefe_2:
        of_other_firm = _assign(chefe_2, emp_9, contador_a.member_id)
        nonexistent = _assign(chefe_2, emp_9, uuid.uuid4())

    body_c = _assert_problem(of_other_firm, 404, MSG_NO_RESPONSIBLE)
    body_d = _assert_problem(nonexistent, 404, MSG_NO_RESPONSIBLE)
    assert body_c == body_d
    _assert_no_leak(of_other_firm, contador_a.member_id, "contador_a", FIRM_1)
    assert _snapshot(world) == before
    assert _count(world, "atribuicao") == 0


# ---------------------------------------------------------------------------
# c10: "has this person created the password?" comes from a restricted function
# ---------------------------------------------------------------------------


def _app_connection(world):
    return psycopg.connect(**world.database.conninfo(APP_ROLE), autocommit=True)


def _run_in_firm(conn, firm_id, query, params=()):
    with conn.transaction():
        if firm_id is not None:
            conn.execute(
                "SELECT set_config(%s, %s, true)", (FIRM_SETTING, str(firm_id))
            )
        return conn.execute(query, params).fetchall()


def test_senha_criada_por_funcao_restrita(world):
    chefe_1, contador_a, contador_x = (
        world.people[login] for login in ("chefe_1", "contador_a", "contador_x")
    )
    contador_c, _ = _add_accountant(world, "contador_c", NAME_C)
    firm_1 = world.firm_ids[FIRM_1]
    ids = [
        chefe_1.user_id,
        contador_a.user_id,
        contador_c.user_id,
        contador_x.user_id,
        uuid.uuid4(),
    ]
    lookup = "SELECT usuario_id, tem_senha FROM usuarios_com_senha(%s::uuid[])"

    with _app_connection(world) as conn:
        # (1) the application user cannot read the column directly
        with pytest.raises(errors.InsufficientPrivilege):
            _run_in_firm(
                conn,
                firm_1,
                "SELECT credencial_hash FROM usuario WHERE id = %s",
                (contador_c.user_id,),
            )
        # (2) in the name of ESC-1: only the firm's people, with yes or no
        rows = _run_in_firm(conn, firm_1, lookup, (ids,))
        assert sorted(rows) == sorted(
            [
                (chefe_1.user_id, True),
                (contador_a.user_id, True),
                (contador_c.user_id, False),
            ]
        )
        # (3) without a firm in the transaction: 0 rows, no error
        assert _run_in_firm(conn, None, lookup, (ids,)) == []
        # (4) the application user cannot change or drop the function
        for statement in (
            "ALTER FUNCTION usuarios_com_senha(uuid[]) SECURITY INVOKER",
            "DROP FUNCTION usuarios_com_senha(uuid[])",
            (
                "CREATE OR REPLACE FUNCTION usuarios_com_senha(uuid[])"
                " RETURNS TABLE (usuario_id uuid, tem_senha boolean)"
                " LANGUAGE sql AS $$ SELECT NULL::uuid, true WHERE false $$"
            ),
        ):
            with pytest.raises(errors.InsufficientPrivilege):
                _run_in_firm(conn, firm_1, statement)

    # Shape of the function, read as the superuser.
    with _connect(world.database) as conn:
        found = conn.execute(
            "SELECT p.prosecdef, pg_get_userbyid(p.proowner), p.proconfig,"
            " pg_get_function_result(p.oid), p.proacl::text[]"
            " FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace"
            " WHERE n.nspname = 'public' AND p.proname = 'usuarios_com_senha'"
        ).fetchall()
        version = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    assert len(found) == 1, "usuarios_com_senha does not exist"
    secdef, owner, config, result, acl = found[0]
    assert secdef is True
    assert owner == "lastro_owner"
    assert any(setting.startswith("search_path=") for setting in config or [])
    assert "usuario_id" in result and "tem_senha" in result
    assert "credencial" not in result
    grantees = {entry.split("=")[0] for entry in acl or []}
    assert "lastro_app" in grantees
    assert "" not in grantees, "PUBLIC can execute the function"
    assert all(
        entry.split("=")[1].split("/")[0] == "X"
        for entry in acl
        if entry.startswith("lastro_app=")
    ), "lastro_app has more than EXECUTE"
    # Its own migration, the one after 0006 of NUC-03.
    migrations = sorted((REPO_ROOT / "migrations" / "versions").glob("0007_*.py"))
    assert len(migrations) == 1, "expected one migration 0007 of ACE-02"
    assert version >= "0007"

    # The list (c1, c2, c5) and the refusal of c5 (5) go through that function: they say
    # `ativo` for who has a password and `convite_pendente` for who does not.
    with _signed_in(world, "chefe_1") as chefe:
        statuses = _statuses(chefe)
        refused = _new_invitation(chefe, contador_a)
    assert statuses["contador_a"] == "ativo"
    assert statuses["contador_c"] == "convite_pendente"
    _assert_problem(refused, 409, MSG_ALREADY_HAS_PASSWORD)


# ---------------------------------------------------------------------------
# c11: two simultaneous acceptances of the same invitation: only one wins
# ---------------------------------------------------------------------------


def test_dois_aceites_simultaneos_so_um_vale(world):
    contador_c, code = _add_accountant(world, "contador_c", NAME_C)
    passwords = {
        "primeira": secrets.token_urlsafe(12),
        "segunda": secrets.token_urlsafe(12),
    }
    barrier = threading.Barrier(2)

    def accept(password):
        # Own app, own engine, own database connection.
        with _client(world.database) as anonymous:
            barrier.wait(timeout=30)
            return _accept(anonymous, code, "contador_c", password)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {name: pool.submit(accept, pw) for name, pw in passwords.items()}
        responses = {
            name: future.result(timeout=60) for name, future in futures.items()
        }

    codes = sorted(response.status_code for response in responses.values())
    assert codes == [200, 404], [response.text for response in responses.values()]
    winner = next(
        name for name, response in responses.items() if response.status_code == 200
    )
    loser = "segunda" if winner == "primeira" else "primeira"
    _assert_problem(responses[loser], 404, MSG_DEAD_INVITE)

    ((_, used_at, revoked_at),) = _invites_of(world, contador_c)
    assert used_at is not None and revoked_at is None
    stored = _stored_credential(world, contador_c)
    assert verify_password(stored, passwords[winner])
    assert not verify_password(stored, passwords[loser])
    assert _can_sign_in(world, "contador_c", passwords[winner])
    assert not _can_sign_in(world, "contador_c", passwords[loser])


# ---------------------------------------------------------------------------
# Extra tests (plan: questions 4 and 5, D6, c2 promises), outside `verificacao`
# ---------------------------------------------------------------------------


def test_cancelar_sem_convite_pendente_devolve_204(world):
    """Question 4: DELETE without a pending invitation is 204; 404 only if the person is missing."""
    contador_a = world.people["contador_a"]

    with _signed_in(world, "chefe_1") as chefe_1:
        without_invite = _cancel_invitation(chefe_1, contador_a)
        missing = chefe_1.delete(f"{ACCOUNTANTS_PATH}/{uuid.uuid4()}/invitation")

    assert without_invite.status_code == 204, without_invite.text
    _assert_problem(missing, 404, MSG_NO_ACCOUNTANT)


def test_consulta_de_cliente_sem_responsavel_devolve_nulo(world):
    """Question 5: GET without a responsible is 200 with `responsible: null`."""
    emp_1 = _add_client(world, "EMP-1")

    with _signed_in(world, "chefe_1") as chefe_1:
        consulted = _responsible(chefe_1, emp_1)

    assert consulted.status_code == 200, consulted.text
    assert consulted.json() == {"responsible": None}


def test_convite_vencido_aparece_na_lista_e_novo_convite_substitui(world):
    """D6: an expired invitation is `convite_vencido`; a new one revokes it first."""
    contador_c, code_old = _add_accountant(world, "contador_c", NAME_C, state="expired")

    with _signed_in(world, "chefe_1") as chefe_1:
        assert _statuses(chefe_1)["contador_c"] == "convite_vencido"
        renewed = _new_invitation(chefe_1, contador_c)
        assert renewed.status_code == 201, renewed.text
        assert _statuses(chefe_1)["contador_c"] == "convite_pendente"

    rows = {row[0]: row for row in _invites_of(world, contador_c)}
    assert rows[_hash_of(code_old)][2] is not None, (
        "the expired invitation was not revoked"
    )
    assert _pending_count(world, contador_c) == 1
    with _client(world.database) as anonymous:
        accepted = _accept(
            anonymous,
            renewed.json()["invitation_code"],
            "contador_c",
            secrets.token_urlsafe(12),
        )
    assert accepted.status_code == 200, accepted.text


def test_rotas_de_convite_pedem_sessao_exceto_o_aceite(world):
    """Without a session the manager routes answer 401; the acceptance needs none (c2)."""
    contador_a = world.people["contador_a"]
    emp_1 = _add_client(world, "EMP-1")

    with _client(world.database) as anonymous:
        refusals = (
            _register(anonymous, NAME_C, "contador_c"),
            anonymous.get(ACCOUNTANTS_PATH),
            _new_invitation(anonymous, contador_a),
            _cancel_invitation(anonymous, contador_a),
            _assign(anonymous, emp_1, contador_a.member_id),
            _responsible(anonymous, emp_1),
        )
        unknown_code = _accept(
            anonymous, secrets.token_urlsafe(32), "contador_c", "x" * 12
        )

    for refusal in refusals:
        _assert_problem(refusal, 401, MSG_SIGN_IN)
    assert unknown_code.status_code == 404, "the acceptance must not ask for a session"


def test_aceite_usa_funcao_de_busca_e_nao_le_a_credencial():
    """c2: found by `buscar_convite_por_hash`; no query of the user or of the invite by hash."""
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((REPO_ROOT / "src" / "lastro" / "access").glob("*.py"))
    )
    assert "buscar_convite_por_hash" in source
    assert not re.search(r"\.hash_token\s*==", source), "invite looked up by hash_token"
    assert not re.search(r"select\(\s*User\s*\)", source), (
        "whole user loaded (reads the hash)"
    )
    assert "usuarios_com_senha" in source
