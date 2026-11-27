"""CAD-03: the manager registers a client with name and CNPJ (RF-CAD-01, RF-AUT-03).

The first five tests are the ones named in `features/CAD-03.json`; the others cover the
answers to questions 3 to 6 of `planos/CAD-03/plan.md` and stay out of `verificacao`.

The API runs with `create_app()` against the Testcontainers PostgreSQL migrated to `head`
(`migrated_database` of `tests/registry/conftest.py`). Firms and members are written straight
to the database, with passwords generated at run time and hashed by
`lastro.access.service.hash_password`. Each person uses its own `TestClient`, so each one keeps
its own session cookie. Valid CNPJs are built at run time from a synthetic 12-character base
by an independent Module 11 helper: no valid CNPJ literal is committed (`docs/SECURITY.md` §3).
No real data.
"""

import secrets
import uuid
from dataclasses import dataclass

import psycopg
import pytest
from fastapi.testclient import TestClient

from lastro.access.service import hash_password
from lastro.api.app import create_app
from lastro.core.config import Settings

BASE_URL = "https://testserver"
SUPERUSER = "postgres"
SESSION_PATH = "/api/v1/session"
CLIENTS_PATH = "/api/v1/clients"
PROBLEM_JSON = "application/problem+json"

# Plan CAD-03, questions 1 and 3 to 6 (answered on 25/11).
INVALID_DATA_STATUS = 422
MSG_EMPTY_NAME = "Informe o nome do cliente."
MSG_LONG_NAME = "O nome do cliente deve ter no máximo 255 caracteres."
MSG_INVALID_CNPJ = "O CNPJ informado não é válido. Confira os números."
MSG_NO_ACCESS = "Você não tem acesso a este cliente."
MSG_SIGN_IN = "Entre para continuar."
MSG_MANAGER_ONLY = "Só o chefe do escritório pode fazer isso."
MSG_NOT_ASSIGNED = "Atribua este cliente a você para fazer isso."
MSG_DUPLICATE_CNPJ = "Este CNPJ já está cadastrado no seu escritório."
NAME_MAX_LENGTH = 255

CLIENT_NAME = "EMPRESA TESTE 1"
SECOND_CLIENT_NAME = "EMPRESA TESTE 2"
# Synthetic 12-character bases; the check digits are computed at run time.
CNPJ_BASE = "112223330001"
OTHER_CNPJ_BASE = "445556660001"

_WEIGHTS_FIRST = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_WEIGHTS_SECOND = (6, *_WEIGHTS_FIRST)


# ---------------------------------------------------------------------------
# Synthetic CNPJ, independent of the production code
# ---------------------------------------------------------------------------


def _check_digit(chars: str, weights: tuple[int, ...]) -> str:
    total = sum(
        (ord(char) - 48) * weight for char, weight in zip(chars, weights, strict=True)
    )
    remainder = total % 11
    return "0" if remainder < 2 else str(11 - remainder)


def _valid_cnpj(base: str = CNPJ_BASE) -> str:
    """14-character valid CNPJ, without mask, built from a 12-character base."""
    first = _check_digit(base, _WEIGHTS_FIRST)
    return f"{base}{first}{_check_digit(base + first, _WEIGHTS_SECOND)}"


def _masked(cnpj: str) -> str:
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


def _wrong_check_digit(cnpj: str) -> str:
    return f"{cnpj[:-1]}{(int(cnpj[-1]) + 1) % 10}"


# ---------------------------------------------------------------------------
# Firms, people and HTTP clients
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Firm:
    firm_id: str
    passwords: dict


@dataclass(frozen=True)
class World:
    database: object
    firms: dict


def _connect(database):
    return psycopg.connect(**database.conninfo(SUPERUSER), autocommit=True)


def _add_firm(conn, firm_name: str, people: tuple[tuple[str, str, str], ...]) -> Firm:
    """Insert a firm and its members; `people` holds (login, display name, role)."""
    firm_id = conn.execute(
        "INSERT INTO escritorio (nome) VALUES (%s) RETURNING id", (firm_name,)
    ).fetchone()[0]
    passwords = {}
    for login, name, role in people:
        password = secrets.token_urlsafe(12)
        user_id = conn.execute(
            "INSERT INTO usuario (identificador_login, nome, credencial_hash)"
            " VALUES (%s, %s, %s) RETURNING id",
            (login, name, hash_password(password)),
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO membro (escritorio_id, usuario_id, papel) VALUES (%s, %s, %s)",
            (firm_id, user_id, role),
        )
        passwords[login] = password
    return Firm(firm_id=str(firm_id), passwords=passwords)


@pytest.fixture
def world(migrated_database):
    """ESC-1 (chefe_1, contador_a) and ESC-2 (chefe_2), with no client."""
    with _connect(migrated_database) as conn:
        firms = {
            "ESC-1": _add_firm(
                conn,
                "ESC-1",
                (
                    ("chefe_1", "Chefe Teste Um", "chefe"),
                    ("contador_a", "Contador Teste A", "contador"),
                ),
            ),
            "ESC-2": _add_firm(
                conn, "ESC-2", (("chefe_2", "Chefe Teste Dois", "chefe"),)
            ),
        }
    return World(database=migrated_database, firms=firms)


def _client(database) -> TestClient:
    settings = Settings(
        database_url=database.database_url,
        migrations_database_url=database.migrations_database_url,
    )
    return TestClient(create_app(settings=settings), base_url=BASE_URL)


def _signed_in(world: World, firm: str, login: str) -> TestClient:
    client = _client(world.database)
    response = client.post(
        SESSION_PATH,
        json={"username": login, "password": world.firms[firm].passwords[login]},
    )
    assert response.status_code == 200, f"sign-in of {login} failed: {response.text}"
    return client


def _register(client: TestClient, name: str, cnpj: str):
    return client.post(CLIENTS_PATH, json={"name": name, "cnpj": cnpj})


def _insert_client(world: World, firm: str, name: str, cnpj: str) -> str:
    """Write a client straight to the database (state of the examples, not under test)."""
    with _connect(world.database) as conn:
        return str(
            conn.execute(
                "INSERT INTO cliente (escritorio_id, nome, cnpj_normalizado)"
                " VALUES (%s, %s, %s) RETURNING id",
                (world.firms[firm].firm_id, name, cnpj),
            ).fetchone()[0]
        )


def _stored_clients(world: World, firm: str) -> list[tuple]:
    with _connect(world.database) as conn:
        return conn.execute(
            "SELECT nome, cnpj_normalizado FROM cliente WHERE escritorio_id = %s",
            (world.firms[firm].firm_id,),
        ).fetchall()


def _assert_problem(response, status: int, detail: str) -> dict:
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith(PROBLEM_JSON), response.headers
    body = response.json()
    assert body["status"] == status
    assert body["detail"] == detail
    return body


def _list_ids(client: TestClient) -> list[str]:
    response = client.get(CLIENTS_PATH)
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()]


# ---------------------------------------------------------------------------
# c1: the manager registers a client and it shows up in the firm's list
# ---------------------------------------------------------------------------


def test_chefe_cadastra_cliente_que_aparece_na_lista(world):
    cnpj = _valid_cnpj()

    with _signed_in(world, "ESC-1", "chefe_1") as chefe_1:
        created = _register(chefe_1, CLIENT_NAME, _masked(cnpj))
        listed = chefe_1.get(CLIENTS_PATH)

    assert created.status_code == 201, created.text
    body = created.json()
    assert set(body) == {"id", "name", "cnpj"}
    uuid.UUID(body["id"])
    assert body["name"] == CLIENT_NAME
    assert body["cnpj"] == cnpj

    assert listed.status_code == 200, listed.text
    items = listed.json()
    assert [item["id"] for item in items] == [body["id"]]
    assert items[0]["name"] == CLIENT_NAME
    assert items[0]["cnpj"] == cnpj
    assert _stored_clients(world, "ESC-1") == [(CLIENT_NAME, cnpj)]


# ---------------------------------------------------------------------------
# c2: empty name or invalid CNPJ is refused with a message that says what to fix
# ---------------------------------------------------------------------------


def test_cliente_sem_nome_recusado(world):
    with _signed_in(world, "ESC-1", "chefe_1") as chefe_1:
        refused = _register(chefe_1, "", _valid_cnpj())
        _assert_problem(refused, INVALID_DATA_STATUS, MSG_EMPTY_NAME)
        assert _list_ids(chefe_1) == []

    assert _stored_clients(world, "ESC-1") == []


def test_cliente_com_cnpj_invalido_recusado(world):
    with _signed_in(world, "ESC-1", "chefe_1") as chefe_1:
        refused = _register(
            chefe_1, SECOND_CLIENT_NAME, _wrong_check_digit(_valid_cnpj())
        )
        _assert_problem(refused, INVALID_DATA_STATUS, MSG_INVALID_CNPJ)
        assert _list_ids(chefe_1) == []

    assert _stored_clients(world, "ESC-1") == []


# ---------------------------------------------------------------------------
# c3: a client of one firm is invisible to another, even by direct address
# ---------------------------------------------------------------------------


def test_cliente_invisivel_para_outro_escritorio(world):
    cnpj = _valid_cnpj()
    emp_1 = _insert_client(world, "ESC-1", CLIENT_NAME, cnpj)
    missing = str(uuid.uuid4())

    with _signed_in(world, "ESC-2", "chefe_2") as chefe_2:
        listed = chefe_2.get(CLIENTS_PATH)
        direct = chefe_2.get(f"{CLIENTS_PATH}/{emp_1}")
        nonexistent = chefe_2.get(f"{CLIENTS_PATH}/{missing}")

    assert listed.status_code == 200, listed.text
    assert listed.json() == []

    direct_body = _assert_problem(direct, 404, MSG_NO_ACCESS)
    nonexistent_body = _assert_problem(nonexistent, 404, MSG_NO_ACCESS)
    assert direct_body == nonexistent_body
    for leaked in (emp_1, CLIENT_NAME, cnpj, "ESC-1"):
        assert leaked not in direct.text, f"the refusal leaks '{leaked}'"


# ---------------------------------------------------------------------------
# c4: without a session, no client is registered
# ---------------------------------------------------------------------------


def test_cadastro_sem_sessao_recusado(world):
    with _client(world.database) as anonymous:
        refused = _register(anonymous, CLIENT_NAME, _valid_cnpj())

    _assert_problem(refused, 401, MSG_SIGN_IN)
    assert _stored_clients(world, "ESC-1") == []


# ---------------------------------------------------------------------------
# Additional tests (plan CAD-03, questions 3 to 6), outside `verificacao`
# ---------------------------------------------------------------------------


def test_contador_nao_cadastra_cliente(world):
    """Question 4 (P-02): only the manager registers; the accountant gets 403."""
    with _signed_in(world, "ESC-1", "contador_a") as contador_a:
        refused = _register(contador_a, CLIENT_NAME, _valid_cnpj())

    _assert_problem(refused, 403, MSG_MANAGER_ONLY)
    assert _stored_clients(world, "ESC-1") == []


def test_cnpj_repetido_no_mesmo_escritorio_recusado(world):
    """Question 3: 409 in the same firm; the same CNPJ is accepted in another firm."""
    cnpj = _valid_cnpj()

    with _signed_in(world, "ESC-1", "chefe_1") as chefe_1:
        first = _register(chefe_1, CLIENT_NAME, _masked(cnpj))
        repeated = _register(chefe_1, SECOND_CLIENT_NAME, cnpj)
    with _signed_in(world, "ESC-2", "chefe_2") as chefe_2:
        other_firm = _register(chefe_2, CLIENT_NAME, cnpj)

    assert first.status_code == 201, first.text
    body = _assert_problem(repeated, 409, MSG_DUPLICATE_CNPJ)
    assert first.json()["id"] not in str(body)
    assert CLIENT_NAME not in repeated.text
    assert _stored_clients(world, "ESC-1") == [(CLIENT_NAME, cnpj)]
    assert other_firm.status_code == 201, other_firm.text


def test_chefe_nao_abre_cliente_sem_atribuicao(world):
    """Question 5 (P-09): the manager of the same firm, not responsible, gets 403."""
    cnpj = _valid_cnpj()

    with _signed_in(world, "ESC-1", "chefe_1") as chefe_1:
        created = _register(chefe_1, CLIENT_NAME, cnpj)
        assert created.status_code == 201, created.text
        opened = chefe_1.get(f"{CLIENTS_PATH}/{created.json()['id']}")

    _assert_problem(opened, 403, MSG_NOT_ASSIGNED)
    assert CLIENT_NAME not in opened.text
    assert cnpj not in opened.text


def test_nome_aparado_e_limitado_a_255_caracteres(world):
    """Question 6: name is stripped; blank counts as empty; at most 255 characters."""
    longest = "N" * NAME_MAX_LENGTH

    with _signed_in(world, "ESC-1", "chefe_1") as chefe_1:
        blank = _register(chefe_1, "   ", _valid_cnpj())
        too_long = _register(chefe_1, longest + "N", _valid_cnpj())
        trimmed = _register(chefe_1, f"  {CLIENT_NAME}  ", _valid_cnpj())
        at_limit = _register(chefe_1, longest, _valid_cnpj(OTHER_CNPJ_BASE))

    _assert_problem(blank, INVALID_DATA_STATUS, MSG_EMPTY_NAME)
    _assert_problem(too_long, INVALID_DATA_STATUS, MSG_LONG_NAME)
    assert trimmed.status_code == 201, trimmed.text
    assert trimmed.json()["name"] == CLIENT_NAME
    assert at_limit.status_code == 201, at_limit.text
    assert at_limit.json()["name"] == longest
