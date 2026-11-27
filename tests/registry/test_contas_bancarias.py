"""CAD-04: the accountant gives a client's bank accounts: bank, nickname, months of use (RF-CAD-02).

The first eight tests are the ones named in `features/CAD-04.json`; the last ones cover the
answers to questions 4 and 5 of `planos/CAD-04/plan.md` and stay out of `verificacao`.

The API runs with `create_app()` against the Testcontainers PostgreSQL migrated to `head`
(`migrated_database` of `tests/registry/conftest.py`). Firms, members, clients and
assignments are written straight to the database (state of the examples, not under test);
passwords are generated at run time and hashed by `lastro.access.service.hash_password`.
Each person uses its own `TestClient`, so each one keeps its own session cookie. Client CNPJs
are random 14-digit strings made at run time: no CNPJ literal is committed
(`docs/SECURITY.md` §3). Routes and fields follow answer P3 of the plan. No real data.
"""

import csv
import secrets
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path

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
REPO_ROOT = Path(__file__).resolve().parents[2]
BANKS_CSV = REPO_ROOT / "src" / "lastro" / "registry" / "data" / "bancos.csv"

# Plan CAD-04, answers P-13 (422), P4 and P5.
INVALID_DATA_STATUS = 422
MSG_NO_ACCESS = "Você não tem acesso a este cliente."
MSG_NOT_ASSIGNED = "Atribua este cliente a você para fazer isso."
MSG_NO_BANK = "Informe o banco da conta."
MSG_NO_NICKNAME = "Dê um apelido para a conta."
MSG_BANK_FORMAT = "O código do banco tem 3 números. Confira e tente de novo."
MSG_BANK_UNKNOWN = "Não encontramos um banco com este código. Confira o número."
MSG_DUPLICATE = "Já existe uma conta com este apelido neste cliente. Use outro apelido."
MSG_MONTH_FORMAT = "Informe o mês no formato AAAA-MM, por exemplo 2026-10."
MSG_MONTH_ORDER = "O último mês não pode ser antes do primeiro."
MSG_BANK_CHANGE = "O banco de uma conta não pode ser trocado. Cadastre uma nova conta."
MSG_LONG_NICKNAME = "O apelido deve ter no máximo 255 caracteres."
NICKNAME_MAX_LENGTH = 255

ACCOUNT_FIELDS = {
    "id",
    "bank",
    "bank_name",
    "nickname",
    "currency",
    "first_month",
    "last_month",
}
REQUIRED_BANKS = ("001", "033", "077", "104", "237", "260", "341", "748")


# ---------------------------------------------------------------------------
# Firms, people, clients and HTTP clients
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Person:
    member_id: str
    password: str


@dataclass(frozen=True)
class World:
    database: object
    firm_ids: dict
    people: dict


def _connect(database):
    return psycopg.connect(**database.conninfo(SUPERUSER), autocommit=True)


def _add_firm(conn, firm_name: str, people: tuple[tuple[str, str, str], ...]):
    """Insert a firm and its members; `people` holds (login, display name, role)."""
    firm_id = conn.execute(
        "INSERT INTO escritorio (nome) VALUES (%s) RETURNING id", (firm_name,)
    ).fetchone()[0]
    members = {}
    for login, name, role in people:
        password = secrets.token_urlsafe(12)
        user_id = conn.execute(
            "INSERT INTO usuario (identificador_login, nome, credencial_hash)"
            " VALUES (%s, %s, %s) RETURNING id",
            (login, name, hash_password(password)),
        ).fetchone()[0]
        member_id = conn.execute(
            "INSERT INTO membro (escritorio_id, usuario_id, papel)"
            " VALUES (%s, %s, %s) RETURNING id",
            (firm_id, user_id, role),
        ).fetchone()[0]
        members[login] = Person(member_id=str(member_id), password=password)
    return str(firm_id), members


@pytest.fixture
def world(migrated_database):
    """ESC-1 (chefe_1, contador_a, contador_b) and ESC-2 (chefe_2), with no client."""
    with _connect(migrated_database) as conn:
        esc_1, members_1 = _add_firm(
            conn,
            "ESC-1",
            (
                ("chefe_1", "Chefe Teste Um", "chefe"),
                ("contador_a", "Contador Teste A", "contador"),
                ("contador_b", "Contador Teste B", "contador"),
            ),
        )
        esc_2, members_2 = _add_firm(
            conn, "ESC-2", (("chefe_2", "Chefe Teste Dois", "chefe"),)
        )
    return World(
        database=migrated_database,
        firm_ids={"ESC-1": esc_1, "ESC-2": esc_2},
        people={"ESC-1": members_1, "ESC-2": members_2},
    )


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
        json={"username": login, "password": world.people[firm][login].password},
    )
    assert response.status_code == 200, f"sign-in of {login} failed: {response.text}"
    return client


def _insert_client(world: World, name: str, responsible: str | None) -> str:
    """A client of ESC-1 straight in the database, assigned to `responsible` if given."""
    cnpj = f"{secrets.randbelow(10**14):014d}"
    firm_id = world.firm_ids["ESC-1"]
    with _connect(world.database) as conn:
        client_id = conn.execute(
            "INSERT INTO cliente (escritorio_id, nome, cnpj_normalizado)"
            " VALUES (%s, %s, %s) RETURNING id",
            (firm_id, name, cnpj),
        ).fetchone()[0]
        if responsible is not None:
            conn.execute(
                "INSERT INTO atribuicao (escritorio_id, cliente_id, membro_id,"
                " atribuido_por, inicio) VALUES (%s, %s, %s, %s, now())",
                (
                    firm_id,
                    client_id,
                    world.people["ESC-1"][responsible].member_id,
                    world.people["ESC-1"]["chefe_1"].member_id,
                ),
            )
    return str(client_id)


def _accounts_path(client_id: str) -> str:
    return f"{CLIENTS_PATH}/{client_id}/bank-accounts"


def _inform(client: TestClient, client_id: str, **body):
    """POST one account; keyword names are the API fields (bank, nickname, ...)."""
    return client.post(_accounts_path(client_id), json=body)


def _list(client: TestClient, client_id: str) -> list[dict]:
    response = client.get(_accounts_path(client_id))
    assert response.status_code == 200, response.text
    return response.json()


def _row_count(world: World) -> int:
    with _connect(world.database) as conn:
        return conn.execute("SELECT count(*) FROM conta_bancaria").fetchone()[0]


def _stored(world: World, client_id: str) -> dict:
    """Rows of the client's accounts, keyed by nickname: (bank, coverage start, end)."""
    with _connect(world.database) as conn:
        rows = conn.execute(
            "SELECT apelido, banco, cobertura_inicio, cobertura_fim"
            " FROM conta_bancaria WHERE cliente_id = %s",
            (client_id,),
        ).fetchall()
    return {nickname: (bank, start, end) for nickname, bank, start, end in rows}


def _assert_problem(response, status: int, detail: str) -> dict:
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith(PROBLEM_JSON), response.headers
    body = response.json()
    assert body["status"] == status
    assert body["detail"] == detail
    return body


def _bank_names() -> dict:
    with BANKS_CSV.open(encoding="utf-8", newline="") as handle:
        return {row["codigo"]: row["nome"] for row in csv.DictReader(handle)}


def _state_c1(world: World, contador_a: TestClient) -> str:
    """EMP-1 of contador_a with the two accounts of c1; returns the client id."""
    emp_1 = _insert_client(world, "EMP-1", "contador_a")
    first = _inform(contador_a, emp_1, bank="001", nickname="Conta movimento")
    second = _inform(contador_a, emp_1, bank="077", nickname="Conta digital")
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    return emp_1


# ---------------------------------------------------------------------------
# c1: the accountant gives one or more accounts, each with bank and nickname
# ---------------------------------------------------------------------------


def test_contador_informa_contas_com_banco_e_apelido(world):
    emp_1 = _insert_client(world, "EMP-1", "contador_a")

    with _signed_in(world, "ESC-1", "contador_a") as contador_a:
        first = _inform(contador_a, emp_1, bank="001", nickname="Conta movimento")
        second = _inform(contador_a, emp_1, bank="077", nickname="Conta digital")
        listed = _list(contador_a, emp_1)

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert set(first.json()) == ACCOUNT_FIELDS
    uuid.UUID(first.json()["id"])
    assert [(item["bank"], item["nickname"]) for item in listed] == [
        ("001", "Conta movimento"),
        ("077", "Conta digital"),
    ]
    assert [item["id"] for item in listed] == [first.json()["id"], second.json()["id"]]
    assert _row_count(world) == 2


# ---------------------------------------------------------------------------
# c2: an account without bank or without nickname is refused; the list does not change
# ---------------------------------------------------------------------------


def test_conta_sem_banco_ou_apelido_recusada(world):
    with _signed_in(world, "ESC-1", "contador_a") as contador_a:
        emp_1 = _state_c1(world, contador_a)
        before = _list(contador_a, emp_1)

        no_bank = _inform(contador_a, emp_1, nickname="Reserva")
        empty_bank = _inform(contador_a, emp_1, bank="", nickname="Reserva")
        no_nickname = _inform(contador_a, emp_1, bank="001")
        blank_nickname = _inform(contador_a, emp_1, bank="001", nickname="   ")

        after = _list(contador_a, emp_1)

    _assert_problem(no_bank, INVALID_DATA_STATUS, MSG_NO_BANK)
    _assert_problem(empty_bank, INVALID_DATA_STATUS, MSG_NO_BANK)
    _assert_problem(no_nickname, INVALID_DATA_STATUS, MSG_NO_NICKNAME)
    _assert_problem(blank_nickname, INVALID_DATA_STATUS, MSG_NO_NICKNAME)
    assert len(after) == 2
    assert after == before
    assert _row_count(world) == 2


# ---------------------------------------------------------------------------
# c3: another portfolio or another firm neither reads nor gives accounts
# ---------------------------------------------------------------------------


def test_contas_negadas_a_outra_carteira_e_escritorio(world):
    with _signed_in(world, "ESC-1", "contador_a") as contador_a:
        emp_1 = _state_c1(world, contador_a)
        before = _list(contador_a, emp_1)
    missing = str(uuid.uuid4())

    refusals = []
    with _signed_in(world, "ESC-1", "contador_b") as contador_b:
        refusals.append(contador_b.get(_accounts_path(emp_1)))
        refusals.append(_inform(contador_b, emp_1, bank="001", nickname="Outra"))
        refusals.append(contador_b.get(_accounts_path(missing)))
    with _signed_in(world, "ESC-2", "chefe_2") as chefe_2:
        refusals.append(chefe_2.get(_accounts_path(emp_1)))
        refusals.append(_inform(chefe_2, emp_1, bank="001", nickname="Outra"))

    assert len(refusals) == 5
    bodies = {response.content for response in refusals}
    for response in refusals:
        _assert_problem(response, 404, MSG_NO_ACCESS)
        for leaked in (emp_1, "EMP-1", "Conta movimento", "Conta digital", "Outra"):
            assert leaked not in response.text, f"the refusal leaks '{leaked}'"
    assert len(bodies) == 1, "the five 404 bodies must be identical"

    with _signed_in(world, "ESC-1", "contador_a") as contador_a:
        assert _list(contador_a, emp_1) == before
    assert _row_count(world) == 2


# ---------------------------------------------------------------------------
# c4: the bank code has 3 digits and exists in the versioned list
# ---------------------------------------------------------------------------


def test_codigo_de_banco_validado_pela_lista(world):
    with _signed_in(world, "ESC-1", "contador_a") as contador_a:
        emp_1 = _state_c1(world, contador_a)

        not_digits = _inform(contador_a, emp_1, bank="ABC", nickname="Reserva")
        too_short = _inform(contador_a, emp_1, bank="12", nickname="Reserva")

        # The file is read only after the API answered the cases that do not need it.
        names = _bank_names()
        absent = next(f"{n:03d}" for n in range(1000) if f"{n:03d}" not in names)
        unknown = _inform(contador_a, emp_1, bank=absent, nickname="Reserva")
        padded = _inform(contador_a, emp_1, bank=" 341 ", nickname="Reserva")
        listed = _list(contador_a, emp_1)

    _assert_problem(not_digits, INVALID_DATA_STATUS, MSG_BANK_FORMAT)
    _assert_problem(too_short, INVALID_DATA_STATUS, MSG_BANK_FORMAT)
    _assert_problem(unknown, INVALID_DATA_STATUS, MSG_BANK_UNKNOWN)
    assert padded.status_code == 201, padded.text
    assert padded.json()["bank"] == "341"

    assert len(listed) == 3
    for item in listed:
        assert set(item) == ACCOUNT_FIELDS
        assert item["bank_name"] == names[item["bank"]]
        assert item["currency"] == "BRL"
    assert [item["bank"] for item in listed] == ["001", "077", "341"]
    assert listed[0]["bank_name"], "001 must come back with the bank name from the file"

    with BANKS_CSV.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == ["codigo", "nome", "fonte"]
        codes = [row["codigo"] for row in reader]
    for required in REQUIRED_BANKS:
        assert required in codes, f"bancos.csv lacks the bank {required}"
    assert len(codes) == len(set(codes)), "bancos.csv repeats a code"
    for code in codes:
        assert len(code) == 3 and code.isascii() and code.isdigit(), code


# ---------------------------------------------------------------------------
# c5: two equal nicknames in the same client are refused; in another client, accepted
# ---------------------------------------------------------------------------


def test_apelido_repetido_no_mesmo_cliente_recusado(world):
    with _signed_in(world, "ESC-1", "contador_a") as contador_a:
        emp_1 = _state_c1(world, contador_a)
        emp_2 = _insert_client(world, "EMP-2", "contador_a")

        spaces_and_case = _inform(
            contador_a, emp_1, bank="341", nickname="conta  MOVIMENTO"
        )
        accent = _inform(contador_a, emp_1, bank="341", nickname="Conta Movimênto")
        emp_1_list = _list(contador_a, emp_1)

        other_client = _inform(contador_a, emp_2, bank="001", nickname="Conta movimento")
        emp_2_list = _list(contador_a, emp_2)

    _assert_problem(spaces_and_case, 409, MSG_DUPLICATE)
    _assert_problem(accent, 409, MSG_DUPLICATE)
    assert len(emp_1_list) == 2

    assert other_client.status_code == 201, other_client.text
    assert [item["nickname"] for item in emp_2_list] == ["Conta movimento"]
    assert _row_count(world) == 3


# ---------------------------------------------------------------------------
# c6: first and last month of use are optional, validated, stored as day 1
# ---------------------------------------------------------------------------


def test_meses_de_uso_da_conta_validados(world):
    with _signed_in(world, "ESC-1", "contador_a") as contador_a:
        emp_1 = _state_c1(world, contador_a)

        old = _inform(
            contador_a,
            emp_1,
            bank="341",
            nickname="Conta antiga",
            first_month="2026-01",
            last_month="2026-09",
        )
        new = _inform(
            contador_a, emp_1, bank="260", nickname="Conta nova", first_month="2026-10"
        )
        reversed_months = _inform(
            contador_a,
            emp_1,
            bank="104",
            nickname="Erro 1",
            first_month="2026-10",
            last_month="2026-09",
        )
        slashed = _inform(
            contador_a, emp_1, bank="104", nickname="Erro 2", first_month="10/2026"
        )
        month_13 = _inform(
            contador_a, emp_1, bank="104", nickname="Erro 3", first_month="2026-13"
        )
        listed = _list(contador_a, emp_1)

    assert old.status_code == 201, old.text
    assert new.status_code == 201, new.text
    assert (old.json()["first_month"], old.json()["last_month"]) == ("2026-01", "2026-09")
    assert (new.json()["first_month"], new.json()["last_month"]) == ("2026-10", None)

    stored = _stored(world, emp_1)
    assert stored["Conta antiga"] == ("341", date(2026, 1, 1), date(2026, 9, 1))
    assert stored["Conta nova"] == ("260", date(2026, 10, 1), None)
    assert stored["Conta movimento"][1:] == (None, None)
    assert stored["Conta digital"][1:] == (None, None)

    by_nickname = {item["nickname"]: item for item in listed}
    assert by_nickname["Conta antiga"]["first_month"] == "2026-01"
    assert by_nickname["Conta antiga"]["last_month"] == "2026-09"
    assert by_nickname["Conta nova"]["first_month"] == "2026-10"
    assert by_nickname["Conta nova"]["last_month"] is None
    for plain in ("Conta movimento", "Conta digital"):
        assert by_nickname[plain]["first_month"] is None
        assert by_nickname[plain]["last_month"] is None

    _assert_problem(reversed_months, INVALID_DATA_STATUS, MSG_MONTH_ORDER)
    _assert_problem(slashed, INVALID_DATA_STATUS, MSG_MONTH_FORMAT)
    _assert_problem(month_13, INVALID_DATA_STATUS, MSG_MONTH_FORMAT)
    assert len(listed) == 4


# ---------------------------------------------------------------------------
# c7: the accountant changes nickname and months and closes the account; nothing is deleted
# ---------------------------------------------------------------------------


def test_contador_altera_e_encerra_conta_sem_apagar(world):
    with _signed_in(world, "ESC-1", "contador_a") as contador_a:
        emp_1 = _state_c1(world, contador_a)
        emp_2 = _insert_client(world, "EMP-2", "contador_a")
        for bank, nickname, first, last in (
            ("341", "Conta antiga", "2026-01", "2026-09"),
            ("260", "Conta nova", "2026-10", None),
        ):
            body = {"bank": bank, "nickname": nickname, "first_month": first}
            if last:
                body["last_month"] = last
            assert _inform(contador_a, emp_1, **body).status_code == 201
        foreign = _inform(contador_a, emp_2, bank="001", nickname="Conta de EMP-2")
        assert foreign.status_code == 201, foreign.text
        foreign_id = foreign.json()["id"]

        before = _list(contador_a, emp_1)
        target = next(item for item in before if item["nickname"] == "Conta movimento")
        path = f"{_accounts_path(emp_1)}/{target['id']}"
        rows_before = _row_count(world)
        missing = contador_a.get(_accounts_path(str(uuid.uuid4())))

        renamed = contador_a.patch(path, json={"nickname": "Conta principal"})
        closed = contador_a.patch(path, json={"last_month": "2026-11"})
        after_changes = _list(contador_a, emp_1)

        bank_change = contador_a.patch(path, json={"bank": "237"})
        duplicate = contador_a.patch(path, json={"nickname": "Conta digital"})
        reversed_months = contador_a.patch(
            path, json={"first_month": "2026-01", "last_month": "2025-01"}
        )
        other_account = contador_a.patch(
            f"{_accounts_path(emp_1)}/{foreign_id}", json={"nickname": "Invadida"}
        )
        after_refusals = _list(contador_a, emp_1)
        foreign_after = _list(contador_a, emp_2)
        delete = contador_a.delete(path)
        after_delete = _list(contador_a, emp_1)

    with _signed_in(world, "ESC-1", "contador_b") as contador_b:
        other_portfolio = contador_b.patch(path, json={"nickname": "Invadida"})

    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["nickname"] == "Conta principal"
    assert closed.status_code == 200, closed.text
    assert closed.json()["last_month"] == "2026-11"
    assert _stored(world, emp_1)["Conta principal"] == (
        "001",
        None,
        date(2026, 11, 1),
    )

    expected = [dict(item) for item in before]
    for item in expected:
        if item["id"] == target["id"]:
            item["nickname"] = "Conta principal"
            item["last_month"] = "2026-11"
    assert after_changes == expected

    _assert_problem(bank_change, INVALID_DATA_STATUS, MSG_BANK_CHANGE)
    _assert_problem(duplicate, 409, MSG_DUPLICATE)
    _assert_problem(reversed_months, INVALID_DATA_STATUS, MSG_MONTH_ORDER)
    not_found = _assert_problem(missing, 404, MSG_NO_ACCESS)
    assert _assert_problem(other_portfolio, 404, MSG_NO_ACCESS) == not_found
    assert _assert_problem(other_account, 404, MSG_NO_ACCESS) == not_found
    assert other_account.content == missing.content
    assert other_portfolio.content == missing.content
    assert after_refusals == expected
    assert [item["nickname"] for item in foreign_after] == ["Conta de EMP-2"]

    assert delete.status_code in (404, 405), delete.text
    assert after_delete == expected
    assert _row_count(world) == rows_before


# ---------------------------------------------------------------------------
# c8: a manager who is not responsible gets 403; assigned to self, acts as accountant
# ---------------------------------------------------------------------------


def test_contas_chefe_nao_atribuido_403_e_atribuido_informa(world):
    with _signed_in(world, "ESC-1", "contador_a") as contador_a:
        emp_1 = _state_c1(world, contador_a)
        before = _list(contador_a, emp_1)
    emp_4 = _insert_client(world, "EMP-4", "chefe_1")

    with _signed_in(world, "ESC-1", "chefe_1") as chefe_1:
        read = chefe_1.get(_accounts_path(emp_1))
        inform = _inform(chefe_1, emp_1, bank="341", nickname="Outra")
        no_bank = _inform(chefe_1, emp_1, nickname="Sem banco")

        own = _inform(chefe_1, emp_4, bank="001", nickname="Conta movimento")
        own_list = _list(chefe_1, emp_4)

    refusals = [read, inform, no_bank]
    bodies = {response.content for response in refusals}
    for response in refusals:
        _assert_problem(response, 403, MSG_NOT_ASSIGNED)
        for leaked in (emp_1, "EMP-1", "Conta movimento", "Conta digital", "Outra"):
            assert leaked not in response.text, f"the refusal leaks '{leaked}'"
    assert len(bodies) == 1, "the three 403 bodies must be identical"

    with _signed_in(world, "ESC-1", "contador_a") as contador_a:
        assert _list(contador_a, emp_1) == before

    assert own.status_code == 201, own.text
    assert [(item["bank"], item["nickname"]) for item in own_list] == [
        ("001", "Conta movimento")
    ]
    assert _row_count(world) == 3


# ---------------------------------------------------------------------------
# Additional tests (plan CAD-04, answers P4 and P5), outside `verificacao`
# ---------------------------------------------------------------------------


def test_apelido_aparado_e_limitado_a_255_caracteres(world):
    """P5: the nickname is stored without spaces at the ends; at most 255 characters."""
    longest = "A" * NICKNAME_MAX_LENGTH
    emp_1 = _insert_client(world, "EMP-1", "contador_a")

    with _signed_in(world, "ESC-1", "contador_a") as contador_a:
        trimmed = _inform(contador_a, emp_1, bank="001", nickname="  Conta nova  ")
        too_long = _inform(contador_a, emp_1, bank="001", nickname=longest + "A")
        at_limit = _inform(contador_a, emp_1, bank="001", nickname=longest)

    assert trimmed.status_code == 201, trimmed.text
    assert trimmed.json()["nickname"] == "Conta nova"
    _assert_problem(too_long, INVALID_DATA_STATUS, MSG_LONG_NICKNAME)
    assert at_limit.status_code == 201, at_limit.text
    assert at_limit.json()["nickname"] == longest


def test_dado_invalido_vem_antes_do_apelido_repetido(world):
    """P5: every 422 is checked before the 409 for a repeated nickname."""
    with _signed_in(world, "ESC-1", "contador_a") as contador_a:
        emp_1 = _state_c1(world, contador_a)
        refused = _inform(contador_a, emp_1, bank="12", nickname="Conta movimento")

    _assert_problem(refused, INVALID_DATA_STATUS, MSG_BANK_FORMAT)


def test_patch_omitido_nao_muda_e_nulo_limpa_os_meses(world):
    """P4: omitted field keeps the value; null months clear; null or empty nickname is 422."""
    emp_1 = _insert_client(world, "EMP-1", "contador_a")

    with _signed_in(world, "ESC-1", "contador_a") as contador_a:
        created = _inform(
            contador_a,
            emp_1,
            bank="341",
            nickname="Conta antiga",
            first_month="2026-01",
            last_month="2026-09",
        )
        assert created.status_code == 201, created.text
        path = f"{_accounts_path(emp_1)}/{created.json()['id']}"

        nothing = contador_a.patch(path, json={})
        same_bank = contador_a.patch(path, json={"bank": "341"})
        cleared = contador_a.patch(path, json={"last_month": None})
        null_nickname = contador_a.patch(path, json={"nickname": None})
        empty_nickname = contador_a.patch(path, json={"nickname": ""})

    assert nothing.status_code == 200, nothing.text
    assert nothing.json() == created.json()
    assert same_bank.status_code == 200, same_bank.text
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["first_month"] == "2026-01"
    assert cleared.json()["last_month"] is None
    _assert_problem(null_nickname, INVALID_DATA_STATUS, MSG_NO_NICKNAME)
    _assert_problem(empty_nickname, INVALID_DATA_STATUS, MSG_NO_NICKNAME)
