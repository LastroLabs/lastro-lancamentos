# ruff: noqa: F811  (the imported fixture is used by name as a test argument)
"""ADM-01: create a firm and its manager by command, for the first access (c1 to c4).

The command runs as a real process (`python -m lastro.access.admin criar-escritorio`)
against the Testcontainers PostgreSQL of the NUC-01 fixtures, migrated to `head`. Sign-in
and identification use the ACE-01 route `/api/v1/session`. Names, logins and passwords are
invented. No real data.
"""

import os
import subprocess
import sys

import psycopg
from test_login import (  # noqa: F401 (fixtures, resolved by name below)
    REPO_ROOT,
    SESSION_PATH,
    _client,
    _connect,
    _sign_in,
    head_database,
)

from lastro.access.passwords import verify_password
from lastro.access.service import hash_password

PASSWORD_VARIABLE = "LASTRO_SENHA_CHEFE"
PASSWORD_1 = "senha-teste-123"
PASSWORD_2 = "outra-senha"
PASSWORD_3 = "terceira-senha-teste"

FIRM_1 = "ESCRITORIO TESTE 1"
FIRM_2 = "ESCRITORIO TESTE 2"
MANAGER_1 = "chefe_1"
MANAGER_2 = "chefe_2"
NAME_1 = "CHEFE TESTE 1"
NAME_2 = "CHEFE TESTE 2"

MSG_FIRM_MISSING = "Informe o nome do escritório."
MSG_USER_MISSING = "Informe o usuário do chefe."
MSG_NAME_MISSING = "Informe o nome do chefe."
MSG_PASSWORD_MISSING = "Defina a senha do chefe na variável LASTRO_SENHA_CHEFE."
MSG_PASSWORD_ARGUMENT = (
    "Não escreva a senha no comando. Use a variável LASTRO_SENHA_CHEFE."
)
MSG_PASSWORD_SHORT = "A senha do chefe deve ter pelo menos 8 caracteres."

EXIT_OK = 0
EXIT_TAKEN = 1
EXIT_USAGE = 2


def _created(firm, username):
    return f"Escritório {firm} criado. O chefe {username} já pode entrar."


def _taken(username):
    return f"O usuário {username} já existe. Nada foi alterado."


def _run(database, *, firm, username, name, password=None, extra=()):
    """Run the command as a process; the password goes only through the variable."""
    env = {
        **os.environ,
        "PYTHONPATH": str(REPO_ROOT / "src"),
        "DATABASE_URL": database.database_url,
        "MIGRATIONS_DATABASE_URL": database.migrations_database_url,
    }
    env.pop(PASSWORD_VARIABLE, None)
    if password is not None:
        env[PASSWORD_VARIABLE] = password
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "lastro.access.admin",
            "criar-escritorio",
            "--escritorio",
            firm,
            "--usuario",
            username,
            "--nome",
            name,
            *extra,
        ],
        cwd=REPO_ROOT,
        env=env,
        stdin=subprocess.DEVNULL,  # no interactive terminal
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _output(result):
    return result.stdout + result.stderr


def _counts(database):
    with _connect(database) as conn:
        return tuple(
            conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ("escritorio", "usuario", "membro")
        )


def _assert_nothing_written(database):
    assert _counts(database) == (0, 0, 0)


def _assert_no_password_in_text_columns(database, password):
    """No text column of any table holds the password (only its hash may be stored)."""
    with _connect(database) as conn:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT table_name FROM information_schema.tables"
                " WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            ).fetchall()
        ]
        for table in tables:
            columns = [
                row[0]
                for row in conn.execute(
                    "SELECT column_name FROM information_schema.columns"
                    " WHERE table_schema = 'public' AND table_name = %s"
                    " AND data_type IN ('text', 'character varying', 'character')",
                    (table,),
                ).fetchall()
            ]
            for column in columns:
                found = conn.execute(
                    psycopg.sql.SQL(
                        "SELECT count(*) FROM {table} WHERE position(%s in {column}) > 0"
                    ).format(
                        table=psycopg.sql.Identifier(table),
                        column=psycopg.sql.Identifier(column),
                    ),
                    (password,),
                ).fetchone()[0]
                assert found == 0, f"the password is stored in {table}.{column}"


def _identity(database, username, password):
    with _client(database) as client:
        sign_in = _sign_in(client, username, password)
        identity = client.get(SESSION_PATH)
    return sign_in, identity


# ---------------------------------------------------------------------------
# c1: one command creates firm and manager in one transaction; the manager signs in
# ---------------------------------------------------------------------------


def test_adm01_cria_escritorio_e_chefe_que_consegue_entrar(head_database, caplog):
    result = _run(
        head_database,
        firm=FIRM_1,
        username=MANAGER_1,
        name=NAME_1,
        password=PASSWORD_1,
    )

    assert result.returncode == EXIT_OK, _output(result)
    assert result.stdout.strip() == _created(FIRM_1, MANAGER_1)
    assert PASSWORD_1 not in _output(result)
    assert PASSWORD_1 not in caplog.text
    assert _counts(head_database) == (1, 1, 1)

    with _connect(head_database) as conn:
        member = conn.execute("SELECT papel, ativo FROM membro").fetchall()
        user = conn.execute(
            "SELECT identificador_login, nome, credencial_hash FROM usuario"
        ).fetchall()
    assert member == [("chefe", True)]
    assert len(user) == 1
    login, name, credential_hash = user[0]
    assert (login, name) == (MANAGER_1, NAME_1)
    assert credential_hash and credential_hash != PASSWORD_1
    # Same hashing as ACE-01: a full Argon2 hash that its own check accepts for this
    # password and refuses for any other, and with the same parameters as its output.
    assert credential_hash.startswith("$argon2")
    assert verify_password(credential_hash, PASSWORD_1)
    assert not verify_password(credential_hash, PASSWORD_2)
    assert credential_hash.split("$")[:4] == hash_password(PASSWORD_1).split("$")[:4]
    _assert_no_password_in_text_columns(head_database, PASSWORD_1)

    sign_in, identity = _identity(head_database, MANAGER_1, PASSWORD_1)
    assert sign_in.status_code == 200, sign_in.text
    assert identity.status_code == 200, identity.text
    body = identity.json()
    assert body["username"] == MANAGER_1
    # The API names the role in English ("manager"); the database keeps "chefe".
    assert body["role"] == "manager"
    assert body["firm_name"] == FIRM_1
    assert PASSWORD_1 not in sign_in.text + identity.text


# ---------------------------------------------------------------------------
# c2: an existing user is refused, nothing changes, no firm is created
# ---------------------------------------------------------------------------


def test_adm01_usuario_existente_recusado_sem_alterar(head_database):
    first = _run(
        head_database,
        firm=FIRM_1,
        username=MANAGER_1,
        name=NAME_1,
        password=PASSWORD_1,
    )
    assert first.returncode == EXIT_OK, _output(first)
    with _connect(head_database) as conn:
        before = conn.execute("SELECT id, credencial_hash FROM usuario").fetchall()

    second = _run(
        head_database,
        firm=FIRM_2,
        username=MANAGER_1,
        name=NAME_1,
        password=PASSWORD_2,
    )

    assert second.returncode == EXIT_TAKEN, _output(second)
    assert second.stderr.strip() == _taken(MANAGER_1)
    assert PASSWORD_2 not in _output(second)
    assert _counts(head_database) == (1, 1, 1)
    with _connect(head_database) as conn:
        assert conn.execute("SELECT nome FROM escritorio").fetchall() == [(FIRM_1,)]
        assert (
            conn.execute("SELECT id, credencial_hash FROM usuario").fetchall() == before
        )

    old_login, _ = _identity(head_database, MANAGER_1, PASSWORD_1)
    new_login, _ = _identity(head_database, MANAGER_1, PASSWORD_2)
    assert old_login.status_code == 200, old_login.text
    assert new_login.status_code == 401


def test_adm01_login_so_com_caixa_diferente_conta_como_existente(head_database):
    first = _run(
        head_database,
        firm=FIRM_1,
        username=MANAGER_1,
        name=NAME_1,
        password=PASSWORD_1,
    )
    assert first.returncode == EXIT_OK, _output(first)

    second = _run(
        head_database,
        firm=FIRM_2,
        username="Chefe_1",
        name=NAME_1,
        password=PASSWORD_2,
    )

    assert second.returncode == EXIT_TAKEN, _output(second)
    assert second.stderr.strip() == _taken("Chefe_1")
    assert _counts(head_database) == (1, 1, 1)


def test_adm01_falha_no_meio_da_gravacao_nao_deixa_nada(head_database):
    """A failure while writing the membership rolls back firm and user too."""
    with _connect(head_database) as conn:
        conn.execute(
            "CREATE FUNCTION fail_member_insert() RETURNS trigger AS $$"
            " BEGIN RAISE EXCEPTION 'forced failure for the test'; END;"
            " $$ LANGUAGE plpgsql"
        )
        conn.execute(
            "CREATE TRIGGER fail_member BEFORE INSERT ON membro"
            " FOR EACH ROW EXECUTE FUNCTION fail_member_insert()"
        )

    result = _run(
        head_database,
        firm=FIRM_1,
        username=MANAGER_1,
        name=NAME_1,
        password=PASSWORD_1,
    )

    assert result.returncode != EXIT_OK, _output(result)
    assert _created(FIRM_1, MANAGER_1) not in _output(result)
    assert PASSWORD_1 not in _output(result)
    _assert_nothing_written(head_database)

    # Once the failure is gone the same command works: proves the first run was a
    # real attempt that rolled back, not a refusal before touching the database.
    with _connect(head_database) as conn:
        conn.execute("DROP TRIGGER fail_member ON membro")
    retry = _run(
        head_database,
        firm=FIRM_1,
        username=MANAGER_1,
        name=NAME_1,
        password=PASSWORD_1,
    )
    assert retry.returncode == EXIT_OK, _output(retry)
    assert _counts(head_database) == (1, 1, 1)


# ---------------------------------------------------------------------------
# c3: missing data or password on the command line are refused, nothing is written
# ---------------------------------------------------------------------------


def test_adm01_dado_faltando_ou_senha_no_comando_recusados(head_database):
    cases = {
        "a": (
            {"firm": "", "username": MANAGER_1, "name": NAME_1, "password": PASSWORD_1},
            MSG_FIRM_MISSING,
        ),
        "b": (
            {"firm": FIRM_1, "username": "", "name": NAME_1, "password": PASSWORD_1},
            MSG_USER_MISSING,
        ),
        "c": (
            {"firm": FIRM_1, "username": MANAGER_1, "name": NAME_1, "password": None},
            MSG_PASSWORD_MISSING,
        ),
        "d": (
            {"firm": FIRM_1, "username": MANAGER_1, "name": NAME_1, "password": ""},
            MSG_PASSWORD_MISSING,
        ),
        "e": (
            {
                "firm": FIRM_1,
                "username": MANAGER_1,
                "name": NAME_1,
                "password": None,
                "extra": ("--senha", PASSWORD_1),
            },
            MSG_PASSWORD_ARGUMENT,
        ),
    }

    for case, (arguments, message) in cases.items():
        result = _run(head_database, **arguments)
        assert result.returncode == EXIT_USAGE, f"({case}) {_output(result)}"
        assert message in result.stderr, f"({case}) {_output(result)}"
        assert result.stdout.strip() == "", f"({case}) {result.stdout}"
        _assert_nothing_written(head_database)

    # (e): the password typed on the command line must not be echoed back.
    refused = _run(
        head_database,
        firm=FIRM_1,
        username=MANAGER_1,
        name=NAME_1,
        extra=("--senha", PASSWORD_1),
    )
    assert PASSWORD_1 not in _output(refused)
    # Also when the variable is set at the same time as the forbidden argument.
    both = _run(
        head_database,
        firm=FIRM_1,
        username=MANAGER_1,
        name=NAME_1,
        password=PASSWORD_2,
        extra=("--senha", PASSWORD_1),
    )
    assert both.returncode == EXIT_USAGE, _output(both)
    assert PASSWORD_1 not in _output(both)
    _assert_nothing_written(head_database)


def test_adm01_nome_do_chefe_vazio_recusado(head_database):
    result = _run(
        head_database, firm=FIRM_1, username=MANAGER_1, name="", password=PASSWORD_1
    )

    assert result.returncode == EXIT_USAGE, _output(result)
    assert MSG_NAME_MISSING in result.stderr
    _assert_nothing_written(head_database)


def test_adm01_senha_com_7_caracteres_recusada(head_database):
    short = "abcdefg"
    assert len(short) == 7

    result = _run(
        head_database, firm=FIRM_1, username=MANAGER_1, name=NAME_1, password=short
    )

    assert result.returncode == EXIT_USAGE, _output(result)
    assert MSG_PASSWORD_SHORT in result.stderr
    assert short not in result.stderr.replace(MSG_PASSWORD_SHORT, "")
    _assert_nothing_written(head_database)


def test_adm01_senha_com_8_caracteres_aceita(head_database):
    exact = "abcdefgh"
    assert len(exact) == 8

    result = _run(
        head_database, firm=FIRM_1, username=MANAGER_1, name=NAME_1, password=exact
    )

    assert result.returncode == EXIT_OK, _output(result)
    assert _counts(head_database) == (1, 1, 1)
    sign_in, _ = _identity(head_database, MANAGER_1, exact)
    assert sign_in.status_code == 200, sign_in.text


# ---------------------------------------------------------------------------
# c4: two firms created by the command stay apart
# ---------------------------------------------------------------------------


def test_adm01_dois_escritorios_ficam_separados(head_database):
    first = _run(
        head_database,
        firm=FIRM_1,
        username=MANAGER_1,
        name=NAME_1,
        password=PASSWORD_1,
    )
    second = _run(
        head_database,
        firm=FIRM_2,
        username=MANAGER_2,
        name=NAME_2,
        password=PASSWORD_3,
    )
    assert first.returncode == EXIT_OK, _output(first)
    assert second.returncode == EXIT_OK, _output(second)
    assert second.stdout.strip() == _created(FIRM_2, MANAGER_2)

    with _connect(head_database) as conn:
        assert conn.execute("SELECT count(*) FROM escritorio").fetchone()[0] == 2
        per_firm = conn.execute(
            "SELECT e.nome, count(*), min(m.papel), max(m.papel)"
            " FROM escritorio e JOIN membro m ON m.escritorio_id = e.id"
            " GROUP BY e.nome ORDER BY e.nome"
        ).fetchall()
        # The command creates neither accountants nor clients.
        assert conn.execute("SELECT count(*) FROM membro").fetchone()[0] == 2
        assert (
            conn.execute(
                "SELECT count(*) FROM membro WHERE papel <> 'chefe'"
            ).fetchone()[0]
            == 0
        )
    assert per_firm == [(FIRM_1, 1, "chefe", "chefe"), (FIRM_2, 1, "chefe", "chefe")]

    _, identity_1 = _identity(head_database, MANAGER_1, PASSWORD_1)
    _, identity_2 = _identity(head_database, MANAGER_2, PASSWORD_3)
    assert identity_1.status_code == 200, identity_1.text
    assert identity_2.status_code == 200, identity_2.text
    assert identity_1.json()["username"] == MANAGER_1
    assert identity_1.json()["firm_name"] == FIRM_1
    assert identity_2.json()["username"] == MANAGER_2
    assert identity_2.json()["firm_name"] == FIRM_2
    assert identity_1.json()["firm_id"] != identity_2.json()["firm_id"]
    # Each manager's password opens only their own account.
    wrong, _ = _identity(head_database, MANAGER_1, PASSWORD_3)
    assert wrong.status_code == 401


def test_adm01_nome_de_escritorio_repetido_e_permitido(head_database):
    repeated_firm = FIRM_1
    first = _run(
        head_database,
        firm=repeated_firm,
        username=MANAGER_1,
        name=NAME_1,
        password=PASSWORD_1,
    )
    second = _run(
        head_database,
        firm=repeated_firm,
        username=MANAGER_2,
        name=NAME_2,
        password=PASSWORD_3,
    )

    assert first.returncode == EXIT_OK, _output(first)
    assert second.returncode == EXIT_OK, _output(second)
    assert _counts(head_database) == (2, 2, 2)
