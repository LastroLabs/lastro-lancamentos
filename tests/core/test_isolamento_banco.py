"""NUC-03: the database hides the rows of other firms (c1 to c8).

The seed is written as the container superuser, which ignores row level security. Every
check of the criteria runs as `lastro_app`, the role the API uses, inside a transaction
that names the firm the way the server does (plan D1):

    SELECT set_config('app.firm_id', '<firm uuid>', true)      -- same as SET LOCAL

The setting name `app.firm_id` and the five lookup functions come from `planos/NUC-03/plan.md`
(D1, D3, D4, D6, answers 1 and 5). The functions are read by column position (the order of the ficha),
so the tests do not invent column names. Firms, people, clients and hashes are invented
(ESC-1, ESC-2, EMP-1, EMP-2, EMP-9, contador_a, contador_x); passwords are random at run time.
No real data.
"""

import hashlib
import re
import secrets
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

import psycopg
import pytest
from conftest import APP_ROLE, OWNER_ROLE, SUPERUSER, connect
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy import event

from lastro.access.service import hash_password
from lastro.api.app import create_app
from lastro.core.config import Settings

FIRM_SETTING = "app.firm_id"
SESSION_PATH = "/api/v1/session"
BASE_URL = "https://testserver"
SESSION_ENDED = "Sua sessão terminou. Entre de novo."

# c5 of the ficha: the six DB-01 tables that belong to a firm.
FICHA_TABLES = ("escritorio", "membro", "sessao", "convite", "cliente", "atribuicao")
# Plan answer 2: the tables of DB-02 and DB-03 that belong to a firm get the same rule.
EXTRA_TABLES = (
    "plano_contas",
    "conta_contabil",
    "conta_bancaria",
    "socio",
    "competencia",
    "link_cliente",
)
RLS_TABLES = FICHA_TABLES + EXTRA_TABLES

# The three lookups of c6 and the fourth of plan answer 1.
SESSION_LOOKUP = "buscar_sessao_por_hash"
MEMBERSHIP_LOOKUP = "buscar_vinculos_do_usuario"
INVITE_LOOKUP = "buscar_convite_por_hash"
LOGIN_LOOKUP = "buscar_usuario_por_login"
LOOKUPS = (SESSION_LOOKUP, MEMBERSHIP_LOOKUP, INVITE_LOOKUP, LOGIN_LOOKUP)
# c8 and plan D6: the lookup of the client link, kept apart so c6 does not change.
LINK_LOOKUP = "buscar_link_por_hash"

_cnpj_counter = iter(range(1, 10_000))


# ---------------------------------------------------------------------------
# seed (superuser) and helpers (application role)
# ---------------------------------------------------------------------------


@dataclass
class Firm:
    id: UUID
    chief_user: UUID
    chief_member: UUID
    accountant_user: UUID
    accountant_member: UUID
    clients: dict
    session_hash: str
    invite_id: UUID
    invite_hash: str
    passwords: dict = field(default_factory=dict)


@dataclass
class World:
    database: object
    esc1: Firm
    esc2: Firm


def _sha256(label):
    return hashlib.sha256(f"{label}-{secrets.token_hex(8)}".encode()).hexdigest()


def _fake_cnpj():
    return f"{next(_cnpj_counter):014d}"


def _seed_firm(conn, name, chief, accountant, clients):
    firm = conn.execute(
        "INSERT INTO escritorio (nome) VALUES (%s) RETURNING id", (name,)
    ).fetchone()[0]
    users, members, passwords = {}, {}, {}
    for login, role in ((chief, "chefe"), (accountant, "contador")):
        passwords[login] = secrets.token_urlsafe(12)
        users[login] = conn.execute(
            "INSERT INTO usuario (identificador_login, nome, credencial_hash)"
            " VALUES (%s, %s, %s) RETURNING id",
            (login, f"Pessoa Teste {login}", hash_password(passwords[login])),
        ).fetchone()[0]
        members[login] = conn.execute(
            "INSERT INTO membro (escritorio_id, usuario_id, papel)"
            " VALUES (%s, %s, %s) RETURNING id",
            (firm, users[login], role),
        ).fetchone()[0]
    client_ids = {
        client_name: conn.execute(
            "INSERT INTO cliente (escritorio_id, nome, cnpj_normalizado)"
            " VALUES (%s, %s, %s) RETURNING id",
            (firm, client_name, _fake_cnpj()),
        ).fetchone()[0]
        for client_name in clients
    }
    first_client = next(iter(client_ids.values()))
    session_hash = _sha256("sessao")
    conn.execute(
        "INSERT INTO sessao (escritorio_id, membro_id, hash_token, criada_em, expira_em)"
        " VALUES (%s, %s, %s, now(), now() + interval '12 hours')",
        (firm, members[accountant], session_hash),
    )
    invite_hash = _sha256("convite")
    invite_id = conn.execute(
        "INSERT INTO convite (escritorio_id, membro_id, hash_token, criado_por, expira_em)"
        " VALUES (%s, %s, %s, %s, now() + interval '48 hours') RETURNING id",
        (firm, members[accountant], invite_hash, members[chief]),
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO atribuicao (escritorio_id, cliente_id, membro_id, atribuido_por, inicio)"
        " VALUES (%s, %s, %s, %s, now())",
        (firm, first_client, members[accountant], members[chief]),
    )
    # Tables of DB-02 and DB-03 (plan answer 2): one row each, all on the first client.
    plan = conn.execute(
        "INSERT INTO plano_contas (escritorio_id, cliente_id, versao, importado_por,"
        " importado_em, situacao) VALUES (%s, %s, 1, %s, now(), 'importado') RETURNING id",
        (firm, first_client, members[chief]),
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO conta_contabil (escritorio_id, cliente_id, plano_id, codigo, nome)"
        " VALUES (%s, %s, %s, '1.1.01', 'CONTA TESTE')",
        (firm, first_client, plan),
    )
    conn.execute(
        "INSERT INTO conta_bancaria (escritorio_id, cliente_id, banco, apelido)"
        " VALUES (%s, %s, '001', 'CONTA MOVIMENTO TESTE')",
        (firm, first_client),
    )
    conn.execute(
        "INSERT INTO socio (escritorio_id, cliente_id, nome, nome_normalizado)"
        " VALUES (%s, %s, 'SOCIO TESTE', 'socio teste')",
        (firm, first_client),
    )
    period = conn.execute(
        "INSERT INTO competencia (escritorio_id, cliente_id, mes)"
        " VALUES (%s, %s, '2026-10-01') RETURNING id",
        (firm, first_client),
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO link_cliente (escritorio_id, cliente_id, competencia_id, hash_token,"
        " criado_por, expira_em) VALUES (%s, %s, %s, %s, %s, now() + interval '7 days')",
        (firm, first_client, period, _sha256("link"), members[chief]),
    )
    return Firm(
        id=firm,
        chief_user=users[chief],
        chief_member=members[chief],
        accountant_user=users[accountant],
        accountant_member=members[accountant],
        clients=client_ids,
        session_hash=session_hash,
        invite_id=invite_id,
        invite_hash=invite_hash,
        passwords=passwords,
    )


def _seed(database, esc1_clients):
    with connect(database.conninfo(SUPERUSER)) as conn:
        esc1 = _seed_firm(conn, "ESC-1", "chefe_1", "contador_a", esc1_clients)
        esc2 = _seed_firm(conn, "ESC-2", "chefe_2", "contador_x", ("EMP-9",))
    return World(database=database, esc1=esc1, esc2=esc2)


@pytest.fixture
def clients_world(migrated_database):
    """c1 to c4: ESC-1 with EMP-1 and EMP-2, ESC-2 with EMP-9."""
    return _seed(migrated_database, ("EMP-1", "EMP-2"))


@pytest.fixture
def world(migrated_database):
    """c5 to c7: ESC-1 with EMP-1 assigned to contador_a, ESC-2 with EMP-9 assigned to contador_x."""
    return _seed(migrated_database, ("EMP-1",))


@contextmanager
def _transaction(conn, firm_id=None):
    """A transaction that names the firm like the server does; no firm when `firm_id` is None."""
    with conn.transaction():
        if firm_id is not None:
            conn.execute(
                "SELECT set_config(%s, %s, true)", (FIRM_SETTING, str(firm_id))
            )
        yield


def _app(database):
    return connect(database.conninfo(APP_ROLE))


def _client_names(conn):
    return [row[0] for row in conn.execute("SELECT nome FROM cliente ORDER BY nome")]


def _count(conn, table):
    return conn.execute(
        sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
    ).fetchone()[0]


def _counts(conn, firm_id=None):
    with _transaction(conn, firm_id):
        return {table: _count(conn, table) for table in RLS_TABLES}


def _function_names_found(database):
    with connect(database.conninfo(SUPERUSER)) as conn:
        return {
            row[0]
            for row in conn.execute(
                "SELECT proname FROM pg_proc WHERE proname = ANY(%s)", (list(LOOKUPS),)
            )
        }


# ---------------------------------------------------------------------------
# c1: a query without filter shows only the firm of the transaction
# ---------------------------------------------------------------------------


def test_consulta_sem_filtro_ve_so_o_proprio_escritorio(clients_world):
    with (
        _app(clients_world.database) as conn,
        _transaction(conn, clients_world.esc1.id),
    ):
        names = _client_names(conn)

    assert names == ["EMP-1", "EMP-2"], "EMP-9 (ESC-2) must not appear for ESC-1"


# ---------------------------------------------------------------------------
# c2: without a firm, nothing is shown and nothing fails
# ---------------------------------------------------------------------------


def test_consulta_sem_escritorio_nao_ve_nada(clients_world):
    with _app(clients_world.database) as conn, _transaction(conn):
        names = _client_names(conn)

    assert names == []


# ---------------------------------------------------------------------------
# c3: in the name of one firm, no write reaches another firm
# ---------------------------------------------------------------------------


def test_gravar_em_outro_escritorio_e_recusado(clients_world):
    esc1, esc2 = clients_world.esc1, clients_world.esc2
    with (
        _app(clients_world.database) as conn,
        pytest.raises(psycopg.errors.InsufficientPrivilege),
        _transaction(conn, esc1.id),
    ):
        conn.execute(
            "INSERT INTO cliente (escritorio_id, nome, cnpj_normalizado)"
            " VALUES (%s, 'EMP-10', %s)",
            (esc2.id, _fake_cnpj()),
        )

    with connect(clients_world.database.conninfo(SUPERUSER)) as conn:
        found = conn.execute(
            "SELECT count(*) FROM cliente WHERE nome = 'EMP-10'"
        ).fetchone()[0]
    assert found == 0, "EMP-10 exists after the refused write"


def test_alterar_cliente_de_outro_escritorio_nao_altera(clients_world):
    esc1, esc2 = clients_world.esc1, clients_world.esc2
    with _app(clients_world.database) as conn:
        with _transaction(conn, esc1.id):
            changed = conn.execute(
                "UPDATE cliente SET nome = 'NOME ALTERADO' WHERE id = %s",
                (esc2.clients["EMP-9"],),
            ).rowcount
        with _transaction(conn, esc2.id):
            names = _client_names(conn)

    assert changed == 0, "ESC-1 changed a client of ESC-2"
    assert names == ["EMP-9"], "the name of EMP-9 changed"


def test_apagar_ou_mover_cliente_para_outro_escritorio_e_recusado(clients_world):
    """Extra to c3: delete finds 0 rows and moving an own client to another firm is refused."""
    esc1, esc2 = clients_world.esc1, clients_world.esc2
    with connect(clients_world.database.conninfo(SUPERUSER)) as conn:
        # A client of ESC-2 with nothing attached, so only RLS can stop its deletion.
        loose_client = conn.execute(
            "INSERT INTO cliente (escritorio_id, nome, cnpj_normalizado)"
            " VALUES (%s, 'EMP-11', %s) RETURNING id",
            (esc2.id, _fake_cnpj()),
        ).fetchone()[0]
    with _app(clients_world.database) as conn:
        with _transaction(conn, esc1.id):
            deleted = conn.execute(
                "DELETE FROM cliente WHERE id = %s", (loose_client,)
            ).rowcount
        with (
            pytest.raises(psycopg.errors.InsufficientPrivilege),
            _transaction(conn, esc1.id),
        ):
            conn.execute(
                "UPDATE cliente SET escritorio_id = %s WHERE id = %s",
                (esc2.id, esc1.clients["EMP-2"]),
            )
        with _transaction(conn, esc2.id):
            esc2_names = _client_names(conn)
        with _transaction(conn, esc1.id):
            esc1_names = _client_names(conn)

    assert deleted == 0, "ESC-1 deleted a client of ESC-2"
    assert esc2_names == ["EMP-11", "EMP-9"], "EMP-11 was deleted"
    assert esc1_names == ["EMP-1", "EMP-2"], "EMP-2 left ESC-1"


# ---------------------------------------------------------------------------
# c4: the firm of one transaction does not leak into the next one
# ---------------------------------------------------------------------------


def test_escritorio_nao_vaza_entre_transacoes(clients_world):
    with _app(clients_world.database) as conn:
        with _transaction(conn, clients_world.esc1.id):
            first = _client_names(conn)
        # Same connection; this transaction names no firm (the setting is now empty text,
        # not NULL, which must still mean "no firm" and not an error).
        with _transaction(conn):
            second = _client_names(conn)

    assert first == ["EMP-1", "EMP-2"]
    assert second == []


# ---------------------------------------------------------------------------
# c5: every table that has a firm is protected, not only cliente
# ---------------------------------------------------------------------------


def _policies(conn):
    return conn.execute(
        "SELECT tablename, policyname, roles::text[], qual, with_check"
        " FROM pg_policies WHERE schemaname = 'public'"
    ).fetchall()


def test_rls_em_todas_as_tabelas_da_db01(world):
    expected_esc1 = {
        "escritorio": 1,
        "membro": 2,
        "sessao": 1,
        "convite": 1,
        "cliente": 1,
        "atribuicao": 1,
        # Plan answer 2: one row of each in the seed.
        **dict.fromkeys(EXTRA_TABLES, 1),
    }
    with _app(world.database) as conn:
        with_firm = _counts(conn, world.esc1.id)
        without_firm = _counts(conn)
    assert with_firm == expected_esc1
    assert without_firm == dict.fromkeys(RLS_TABLES, 0)

    with connect(world.database.conninfo(SUPERUSER)) as conn:
        flags = {
            name: (enabled, forced, owner)
            for name, enabled, forced, owner in conn.execute(
                "SELECT relname, relrowsecurity, relforcerowsecurity,"
                " pg_get_userbyid(relowner) FROM pg_class"
                " WHERE relnamespace = 'public'::regnamespace AND relkind = 'r'"
            )
        }
        policies = _policies(conn)
    for table in RLS_TABLES:
        enabled, forced, owner = flags[table]
        assert enabled and forced, (
            f"{table}: ROW LEVEL SECURITY must be enabled and forced"
        )
        assert owner != APP_ROLE, f"{table} must not belong to the application role"
        app_policies = [p for p in policies if p[0] == table and OWNER_ROLE not in p[2]]
        assert app_policies, f"{table} has no policy for the application role"
        assert all(p[3] and p[4] for p in app_policies), (
            f"{table}: the policy needs USING and WITH CHECK"
        )
    assert flags["usuario"][0] is False, "usuario belongs to no firm and has no RLS"


def test_politica_do_dono_nao_vale_para_a_aplicacao(world):
    """D2: the owner (which runs migrations and the functions) sees all; the app gains nothing."""
    with connect(world.database.conninfo(SUPERUSER)) as conn:
        policies = _policies(conn)
        owner_attributes = conn.execute(
            "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = %s",
            (OWNER_ROLE,),
        ).fetchone()
    assert owner_attributes == (False, False), (
        "the owner must not bypass RLS by attribute"
    )
    open_policies = [
        p for p in policies if p[3] and p[3].strip("() ").lower() == "true"
    ]
    assert open_policies, "no policy lets the owner read the rows of every firm (D2)"
    for table, name, roles, *_ in open_policies:
        assert roles == [OWNER_ROLE], (
            f"{table}.{name} is open to {roles}, not only the owner"
        )

    with connect(world.database.conninfo(OWNER_ROLE)) as conn:
        assert _count(conn, "cliente") == 2, (
            "the owner must see the clients of both firms"
        )


def test_aplicacao_nao_le_credencial_hash_por_consulta_direta(world):
    """Plan answer 1: the app keeps INSERT and UPDATE on usuario, but cannot read the hash."""
    with _app(world.database) as conn:
        for query in (
            "SELECT credencial_hash FROM usuario",
            "SELECT * FROM usuario",
            "SELECT id FROM usuario WHERE credencial_hash IS NOT NULL",
        ):
            with (
                pytest.raises(psycopg.errors.InsufficientPrivilege),
                _transaction(conn, world.esc1.id),
            ):
                conn.execute(query)
        with _transaction(conn, world.esc1.id):
            columns = conn.execute(
                "SELECT id, identificador_login, nome, ativo FROM usuario"
            ).fetchall()
            conn.execute(
                "UPDATE usuario SET credencial_hash = %s WHERE id = %s",
                (hash_password(secrets.token_urlsafe(12)), world.esc1.accountant_user),
            )
            conn.execute(
                "INSERT INTO usuario (identificador_login, nome, credencial_hash)"
                " VALUES ('contador_b', 'Pessoa Teste contador_b', NULL)"
            )
    assert len(columns) == 4, "the other columns of usuario must stay readable"


# ---------------------------------------------------------------------------
# c6: the three lookups made before the firm is known go through database functions
# ---------------------------------------------------------------------------


def _lookup(conn, function, argument):
    """Call a lookup outside any firm; returns (rows, column names)."""
    with _transaction(conn):
        cursor = conn.execute(f"SELECT * FROM {function}(%s)", (argument,))
        return cursor.fetchall(), [column.name for column in cursor.description]


def _assert_minimal(columns, function):
    forbidden = {"nome", "hash_token"}
    if function != LOGIN_LOOKUP:
        forbidden.add("credencial_hash")
    assert not forbidden & set(columns), (
        f"{function} returns {sorted(forbidden & set(columns))}"
    )


def _add_closed_invites(conn, esc1):
    """Expired, used and cancelled invites for one more member of ESC-1; returns their hashes."""
    user = conn.execute(
        "INSERT INTO usuario (identificador_login, nome) VALUES ('contador_b', 'Pessoa Teste B')"
        " RETURNING id"
    ).fetchone()[0]
    member = conn.execute(
        "INSERT INTO membro (escritorio_id, usuario_id, papel) VALUES (%s, %s, 'contador')"
        " RETURNING id",
        (esc1.id, user),
    ).fetchone()[0]
    hashes = {
        "expired": _sha256("vencido"),
        "used": _sha256("usado"),
        "cancelled": _sha256("cancelado"),
    }
    for state, extra_columns, extra_values in (
        ("expired", "", ""),
        ("used", ", usado_em", ", now() - interval '1 day'"),
        ("cancelled", ", revogado_em", ", now() - interval '1 day'"),
    ):
        conn.execute(
            "INSERT INTO convite (escritorio_id, membro_id, hash_token, criado_por,"
            f" criado_em, expira_em{extra_columns}) VALUES (%s, %s, %s, %s,"
            f" now() - interval '3 days', now() - interval '2 days'{extra_values})",
            (esc1.id, member, hashes[state], esc1.chief_member),
        )
    return hashes


def test_buscas_sem_escritorio_por_funcoes_restritas(world):
    esc1 = world.esc1
    with connect(world.database.conninfo(SUPERUSER)) as conn:
        closed = _add_closed_invites(conn, esc1)

    present = _function_names_found(world.database)
    assert {SESSION_LOOKUP, MEMBERSHIP_LOOKUP, INVITE_LOOKUP} <= present, (
        f"missing database functions: {sorted({SESSION_LOOKUP, MEMBERSHIP_LOOKUP, INVITE_LOOKUP} - present)}"
    )

    with _app(world.database) as conn:
        # (1) the tables are closed without a firm.
        with _transaction(conn):
            assert (
                conn.execute(
                    "SELECT count(*) FROM sessao WHERE hash_token = %s",
                    (esc1.session_hash,),
                ).fetchone()[0]
                == 0
            )
            assert (
                conn.execute(
                    "SELECT count(*) FROM convite WHERE hash_token = %s",
                    (esc1.invite_hash,),
                ).fetchone()[0]
                == 0
            )

        # (2a) session of contador_a: firm, member, expira_em, encerrada_em.
        rows, columns = _lookup(conn, SESSION_LOOKUP, esc1.session_hash)
        assert len(rows) == 1 and len(columns) == 4, rows
        firm, member, expires_at, ended_at = rows[0]
        assert (firm, member) == (esc1.id, esc1.accountant_member)
        assert isinstance(expires_at, datetime) and ended_at is None
        _assert_minimal(columns, SESSION_LOOKUP)

        # (2b) active memberships of contador_a: firm, member, role.
        rows, columns = _lookup(conn, MEMBERSHIP_LOOKUP, esc1.accountant_user)
        assert rows == [(esc1.id, esc1.accountant_member, "contador")]
        _assert_minimal(columns, MEMBERSHIP_LOOKUP)

        # (2c) the pending invite of ESC-1: firm, invite, member.
        rows, columns = _lookup(conn, INVITE_LOOKUP, esc1.invite_hash)
        assert rows == [(esc1.id, esc1.invite_id, esc1.accountant_member)]
        _assert_minimal(columns, INVITE_LOOKUP)

        # (2d) hashes that do not exist, and (2e) expired, used and cancelled invites.
        unknown = _sha256("inexistente")
        assert _lookup(conn, SESSION_LOOKUP, unknown)[0] == []
        assert _lookup(conn, INVITE_LOOKUP, unknown)[0] == []
        for state, hash_value in closed.items():
            assert _lookup(conn, INVITE_LOOKUP, hash_value)[0] == [], (
                f"{state} invite found"
            )

    # The functions: SECURITY DEFINER, fixed search_path, owner role, EXECUTE only to the app.
    with connect(world.database.conninfo(SUPERUSER)) as conn:
        details = conn.execute(
            "SELECT proname, prosecdef, proconfig, pg_get_userbyid(proowner),"
            " pg_get_function_identity_arguments(oid),"
            " (SELECT array_agg(DISTINCT CASE WHEN a.grantee = 0 THEN 'PUBLIC'"
            "         ELSE pg_get_userbyid(a.grantee) END)"
            "    FROM aclexplode(coalesce(proacl, acldefault('f', proowner))) a"
            "   WHERE a.privilege_type = 'EXECUTE')"
            " FROM pg_proc WHERE proname = ANY(%s)",
            (list(LOOKUPS),),
        ).fetchall()
    for name, security_definer, config, owner, arguments, executors in details:
        assert security_definer, f"{name} must be SECURITY DEFINER"
        normalized = [re.sub(r"\s", "", setting) for setting in config or []]
        assert "search_path=pg_catalog,public" in normalized, (
            f"{name}: search_path {config}"
        )
        assert owner == OWNER_ROLE, f"{name} belongs to {owner}"
        assert set(executors) == {OWNER_ROLE, APP_ROLE}, (
            f"{name}: EXECUTE for {executors}"
        )

    # (2f) the application role cannot change or drop a function.
    with _app(world.database) as conn:
        for name, _, _, _, arguments, _ in details:
            for statement in (
                f"DROP FUNCTION public.{name}({arguments})",
                f"ALTER FUNCTION public.{name}({arguments}) SECURITY INVOKER",
            ):
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    conn.execute(statement)
    assert _function_names_found(world.database) >= {
        SESSION_LOOKUP,
        MEMBERSHIP_LOOKUP,
        INVITE_LOOKUP,
    }


def test_vinculos_do_usuario_so_ativos_um_por_escritorio(world):
    """Extra to c6 (2b): one row per active membership; inactive ones and other users do not appear."""
    esc1, esc2 = world.esc1, world.esc2
    with connect(world.database.conninfo(SUPERUSER)) as conn:
        conn.execute(
            "INSERT INTO membro (escritorio_id, usuario_id, papel) VALUES (%s, %s, 'chefe')",
            (esc2.id, esc1.accountant_user),
        )
        inactive_user = conn.execute(
            "INSERT INTO usuario (identificador_login, nome) VALUES ('contador_z', 'Pessoa Teste Z')"
            " RETURNING id"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO membro (escritorio_id, usuario_id, papel, ativo)"
            " VALUES (%s, %s, 'contador', false)",
            (esc1.id, inactive_user),
        )

    with _app(world.database) as conn:
        two, _ = _lookup(conn, MEMBERSHIP_LOOKUP, esc1.accountant_user)
        none, _ = _lookup(conn, MEMBERSHIP_LOOKUP, inactive_user)
        nobody, _ = _lookup(conn, MEMBERSHIP_LOOKUP, UUID(int=0))

    assert {row[0] for row in two} == {esc1.id, esc2.id} and len(two) == 2
    assert none == [], "an inactive membership must not be returned"
    assert nobody == []


def test_busca_de_login_devolve_so_o_necessario(world):
    """Plan answer 1: login in lower case gives user id, credential hash and active flag."""
    with _app(world.database) as conn:
        rows, columns = _lookup(conn, LOGIN_LOOKUP, "contador_a")
        missing, _ = _lookup(conn, LOGIN_LOOKUP, "pessoa_inexistente")

    assert len(rows) == 1 and len(columns) == 3, rows
    user_id, credential_hash, active = rows[0]
    assert user_id == world.esc1.accountant_user
    assert credential_hash and credential_hash.startswith("$argon2")
    assert active is True
    _assert_minimal(columns, LOGIN_LOOKUP)
    assert missing == []


# ---------------------------------------------------------------------------
# c7: sign-in and identification still work through the API, using the functions
# ---------------------------------------------------------------------------

# A lookup by token, login or code written straight against the tables of the firm.
_DIRECT_LOOKUP = re.compile(
    r"\bWHERE\b.*\b(hash_token|identificador_login)\b", re.DOTALL | re.IGNORECASE
)


def test_login_continua_funcionando_com_rls(world):
    settings = Settings(
        database_url=world.database.database_url,
        migrations_database_url=world.database.migrations_database_url,
    )
    app = create_app(settings=settings)
    statements = []
    password = world.esc1.passwords["contador_a"]

    with TestClient(app, base_url=BASE_URL) as client:
        event.listen(
            app.state.database.engine.sync_engine,
            "before_cursor_execute",
            lambda conn, cursor, statement, params, context, many: statements.append(
                statement
            ),
        )
        sign_in = client.post(
            SESSION_PATH, json={"username": "contador_a", "password": password}
        )
        identity = client.get(SESSION_PATH)
        same_session = dict(client.cookies)
        sign_out = client.delete(SESSION_PATH)
        replay_client = TestClient(app, base_url=BASE_URL, cookies=same_session)
        replay = replay_client.get(SESSION_PATH)

    assert sign_in.status_code == 200, sign_in.text
    assert identity.status_code == 200, identity.text
    body = identity.json()
    assert body["username"] == "contador_a"
    assert body["role"] == "accountant"  # the API name of the role `contador` (ACE-01)
    assert body["firm_id"] == str(world.esc1.id)
    assert body["firm_name"] == "ESC-1"
    assert sign_out.status_code == 204, sign_out.text
    assert replay.status_code == 401, replay.text
    assert replay.headers["content-type"].startswith("application/problem+json")
    assert replay.json()["detail"] == SESSION_ENDED

    # The lookups before the firm is known are the database functions, never a direct query.
    sql_text = "\n".join(statements)
    for function in (SESSION_LOOKUP, MEMBERSHIP_LOOKUP, LOGIN_LOOKUP):
        assert function in sql_text, f"the API never called {function}"
    direct = [s for s in statements if "buscar_" not in s and _DIRECT_LOOKUP.search(s)]
    assert not direct, f"direct lookup without a firm: {direct[0]}"


# ---------------------------------------------------------------------------
# c8: the client link is found by its code through a restricted function
# ---------------------------------------------------------------------------


def _add_links(conn, firm, client):
    """Links of one client in the seeded period (10/2026); returns {label: (id, hash)}.

    `open` is within its term, `expired` passed it, `revoked` was invalidated within it.
    """
    period = conn.execute(
        "SELECT id FROM competencia WHERE escritorio_id = %s AND cliente_id = %s"
        " AND mes = '2026-10-01'",
        (firm.id, client),
    ).fetchone()[0]
    links = {}
    for label, created, expires, revoked in (
        ("open", "now() - interval '1 day'", "now() + interval '6 days'", "NULL"),
        ("expired", "now() - interval '8 days'", "now() - interval '1 day'", "NULL"),
        (
            "revoked",
            "now() - interval '1 day'",
            "now() + interval '6 days'",
            "now() - interval '1 hour'",
        ),
    ):
        hash_value = _sha256(f"link-{label}")
        link_id = conn.execute(
            "INSERT INTO link_cliente (escritorio_id, cliente_id, competencia_id,"
            " hash_token, criado_por, criado_em, expira_em, revogado_em)"
            f" VALUES (%s, %s, %s, %s, %s, {created}, {expires}, {revoked}) RETURNING id",
            (firm.id, client, period, hash_value, firm.accountant_member),
        ).fetchone()[0]
        links[label] = (link_id, hash_value)
    return period, links


def test_busca_do_link_sem_escritorio_por_funcao_restrita(world):
    esc1, esc2 = world.esc1, world.esc2
    emp1, emp9 = esc1.clients["EMP-1"], esc2.clients["EMP-9"]
    with connect(world.database.conninfo(SUPERUSER)) as conn:
        period1, links1 = _add_links(conn, esc1, emp1)
        period9, links9 = _add_links(conn, esc2, emp9)
        found = conn.execute(
            "SELECT count(*) FROM pg_proc WHERE proname = %s", (LINK_LOOKUP,)
        ).fetchone()[0]
    assert found == 1, f"missing database function: {LINK_LOOKUP}"
    l1_id, l1_hash = links1["open"]
    l2_id, l2_hash = links1["expired"]
    _, l3_hash = links1["revoked"]
    l9_id, l9_hash = links9["open"]

    with _app(world.database) as conn:
        # (1) the table is closed without a firm.
        with _transaction(conn):
            assert (
                conn.execute(
                    "SELECT count(*) FROM link_cliente WHERE hash_token = %s",
                    (l1_hash,),
                ).fetchone()[0]
                == 0
            )

        # (2a) L1: firm, link, client, period and expira_em, in this order.
        rows, columns = _lookup(conn, LINK_LOOKUP, l1_hash)
        assert len(rows) == 1 and len(columns) == 5, rows
        firm, link, client, period, expires_at = rows[0]
        assert (firm, link, client, period) == (esc1.id, l1_id, emp1, period1)
        assert isinstance(expires_at, datetime) and expires_at > datetime.now(UTC)
        _assert_minimal(columns, LINK_LOOKUP)
        assert "cnpj_normalizado" not in columns, f"{LINK_LOOKUP} returns the CNPJ"

        # (2b) a code never made and (2c) the invalidated L3: nothing, without error.
        assert _lookup(conn, LINK_LOOKUP, _sha256("inexistente"))[0] == []
        assert _lookup(conn, LINK_LOOKUP, l3_hash)[0] == []

        # (2d) the expired L2 is found; the app refuses it by its own clock (plan P5).
        rows, _ = _lookup(conn, LINK_LOOKUP, l2_hash)
        assert len(rows) == 1, rows
        assert rows[0][:2] == (esc1.id, l2_id)
        assert rows[0][4] < datetime.now(UTC)

        # (2e) L9 belongs to ESC-2 and only to it.
        rows, _ = _lookup(conn, LINK_LOOKUP, l9_hash)
        assert [row[:4] for row in rows] == [(esc2.id, l9_id, emp9, period9)]

    # The function: SECURITY DEFINER, fixed search_path, owner role, EXECUTE only to the app.
    with connect(world.database.conninfo(SUPERUSER)) as conn:
        security_definer, config, owner, arguments, executors = conn.execute(
            "SELECT prosecdef, proconfig, pg_get_userbyid(proowner),"
            " pg_get_function_identity_arguments(oid),"
            " (SELECT array_agg(DISTINCT CASE WHEN a.grantee = 0 THEN 'PUBLIC'"
            "         ELSE pg_get_userbyid(a.grantee) END)"
            "    FROM aclexplode(coalesce(proacl, acldefault('f', proowner))) a"
            "   WHERE a.privilege_type = 'EXECUTE')"
            " FROM pg_proc WHERE proname = %s",
            (LINK_LOOKUP,),
        ).fetchone()
    assert security_definer, f"{LINK_LOOKUP} must be SECURITY DEFINER"
    normalized = [re.sub(r"\s", "", setting) for setting in config or []]
    assert "search_path=pg_catalog,public" in normalized, f"search_path {config}"
    assert owner == OWNER_ROLE, f"{LINK_LOOKUP} belongs to {owner}"
    assert set(executors) == {OWNER_ROLE, APP_ROLE}, f"EXECUTE for {executors}"

    # (2f) the application role cannot change or drop the function.
    with _app(world.database) as conn:
        for statement in (
            f"DROP FUNCTION public.{LINK_LOOKUP}({arguments})",
            f"ALTER FUNCTION public.{LINK_LOOKUP}({arguments}) SECURITY INVOKER",
        ):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(statement)
