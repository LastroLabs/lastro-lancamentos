"""DB-04: short code and kind (S or A) on conta_contabil, on disposable PostgreSQL.

Every test climbs to the DB-04 revision, not to `head`, so a later migration cannot change
what these tests prove (plan D1, the lesson of DECISIONS T12). Records are fictional and
transient (plan, answer 2): `*_TESTE_DB04` names, CNPJ with an invalid check digit.
"""

import os
import subprocess
import sys
from datetime import UTC, datetime
from uuid import uuid4

import psycopg
import pytest
import sqlalchemy as sa
from psycopg import sql
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from lastro.registry.models import LedgerAccount

_INFRA = sys.modules["_lastro_db02_core_fixtures"]
APP_ROLE = _INFRA.APP_ROLE
OWNER_ROLE = _INFRA.OWNER_ROLE
REPO_ROOT = _INFRA.REPO_ROOT
connect = _INFRA.connect

DB04_REVISION = "0008"
PREVIOUS_REVISION = "0007"
NEW_COLUMNS = {"codigo_reduzido", "tipo"}
# The eight DB-02 columns, unchanged, plus the two DB-04 columns (plan D2).
COLUMNS = {
    "escritorio_id": ("uuid", False, None),
    "cliente_id": ("uuid", False, None),
    "id": ("uuid", False, "gen_random_uuid()"),
    "plano_id": ("uuid", False, None),
    "codigo": ("text", False, None),
    "nome": ("text", False, None),
    "pai_id": ("uuid", True, None),
    "ativo": ("boolean", False, "true"),
    "codigo_reduzido": ("text", True, None),
    "tipo": ("text", False, "'A'::text"),
}
UNIQUE_SHORT_CODE = ("escritorio_id", "cliente_id", "plano_id", "codigo_reduzido")
SHORT_CODE = "0000123"
_OMIT = object()


def _run_alembic(database, *arguments):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=REPO_ROOT,
        env={
            **os.environ,
            "PYTHONPATH": str(REPO_ROOT / "src"),
            "DATABASE_URL": database.database_url,
            "MIGRATIONS_DATABASE_URL": database.migrations_database_url,
        },
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, _INFRA.process_output(result)


@pytest.fixture
def database_at_db04(fresh_database):
    """Fresh database at the DB-04 revision."""
    _run_alembic(fresh_database, "upgrade", DB04_REVISION)
    return fresh_database


def _act_as(conn, firm):
    """Name the firm for the whole session, as the server does per transaction (NUC-03)."""
    conn.execute("SELECT set_config('app.firm_id', %s, false)", (str(firm),))


def _insert(conn, table, **values):
    query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING id").format(
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, values)),
        sql.SQL(", ").join(sql.Placeholder() for _ in values),
    )
    return conn.execute(query, list(values.values())).fetchone()[0]


def _seed(conn):
    """One firm with one member and the clients EMP-1 and EMP-2."""
    firm = uuid4()
    _act_as(conn, firm)
    _insert(conn, "escritorio", id=firm, nome="ESCRITORIO_TESTE_DB04")
    user = _insert(
        conn,
        "usuario",
        identificador_login="USUARIO_TESTE_DB04",
        nome="PESSOA_TESTE_DB04",
    )
    member = _insert(
        conn, "membro", escritorio_id=firm, usuario_id=user, papel="contador"
    )
    clients = {
        name: _insert(
            conn,
            "cliente",
            escritorio_id=firm,
            nome=f"{name}_TESTE_DB04",
            cnpj_normalizado=f"44455566000{number}00",
        )
        for number, name in ((1, "EMP-1"), (2, "EMP-2"))
    }
    return firm, member, clients


def _plan(conn, firm, client, member, version):
    return _insert(
        conn,
        "plano_contas",
        escritorio_id=firm,
        cliente_id=client,
        versao=version,
        importado_por=member,
        importado_em=datetime(2026, 1, 1, tzinfo=UTC),
        situacao="importado",
    )


def _account(conn, firm, client, plan, code, *, short_code=_OMIT, kind=_OMIT):
    """Insert an account; a column left as `_OMIT` is not named in the INSERT."""
    extra = {}
    if short_code is not _OMIT:
        extra["codigo_reduzido"] = short_code
    if kind is not _OMIT:
        extra["tipo"] = kind
    return _insert(
        conn,
        "conta_contabil",
        escritorio_id=firm,
        cliente_id=client,
        plano_id=plan,
        codigo=code,
        nome=f"CONTA_TESTE_DB04_{code}",
        **extra,
    )


def _reject(conn, error, firm, client, plan, code, **columns):
    with pytest.raises(error), conn.transaction():
        _account(conn, firm, client, plan, code, **columns)


def _normalize(value):
    return "".join(str(value).lower().split())


def _column_names(conn):
    return {
        row[0]
        for row in conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'conta_contabil'"
        )
    }


def test_migracao_db04_acrescenta_reduzido_e_tipo(database_at_db04):
    """c1: two new columns, the DB-02 columns unchanged, the check, the unique key and the model."""
    engine = sa.create_engine(database_at_db04.migrations_database_url)
    try:
        inspector = sa.inspect(engine)
        actual = {
            col["name"]: (
                str(col["type"].compile(dialect=engine.dialect)).lower(),
                col["nullable"],
                col["default"],
            )
            for col in inspector.get_columns("conta_contabil")
        }
        assert actual == COLUMNS
        checks = {
            item["name"]: _normalize(item["sqltext"])
            for item in inspector.get_check_constraints("conta_contabil")
        }
        assert "ck_conta_contabil_tipo" in checks
        assert all(
            word in checks["ck_conta_contabil_tipo"] for word in ("tipo", "'s'", "'a'")
        )
        unique = {
            item["name"]: tuple(item["column_names"])
            for item in inspector.get_unique_constraints("conta_contabil")
        }
        assert unique["uq_conta_contabil_plano_reduzido"] == UNIQUE_SHORT_CODE
        assert unique["uq_conta_contabil_plano_codigo"] == (
            "escritorio_id",
            "cliente_id",
            "plano_id",
            "codigo",
        )
        assert unique["uq_conta_contabil_plano_id"] == (
            "escritorio_id",
            "cliente_id",
            "plano_id",
            "id",
        )
    finally:
        engine.dispose()

    table = LedgerAccount.__table__
    assert NEW_COLUMNS <= set(table.c.keys())
    assert table.c.codigo_reduzido.nullable is True
    assert table.c.tipo.nullable is False
    assert _normalize(table.c.tipo.server_default.arg) == "'a'"
    ddl = _normalize(CreateTable(table).compile(dialect=postgresql.dialect()))
    assert "constraintck_conta_contabil_tipocheck" in ddl
    assert "constraintuq_conta_contabil_plano_reduzidounique" in ddl


def test_db04_reduzido_unico_por_plano(database_at_db04):
    """c2: the short code repeats in another plan or client, never in the same plan; NULLs never clash."""
    with connect(database_at_db04.conninfo(APP_ROLE)) as conn:
        firm, member, clients = _seed(conn)
        emp1, emp2 = clients["EMP-1"], clients["EMP-2"]
        p1 = _plan(conn, firm, emp1, member, 1)
        p2 = _plan(conn, firm, emp1, member, 2)
        p3 = _plan(conn, firm, emp2, member, 1)

        _account(conn, firm, emp1, p1, "1101", short_code=SHORT_CODE)
        _reject(
            conn,
            psycopg.errors.UniqueViolation,
            firm,
            emp1,
            p1,
            "1102",
            short_code=SHORT_CODE,
        )
        _account(conn, firm, emp1, p2, "1101", short_code=SHORT_CODE)
        _account(conn, firm, emp2, p3, "1101", short_code=SHORT_CODE)
        _account(conn, firm, emp1, p1, "1103", short_code=None)
        _account(conn, firm, emp1, p1, "1104", short_code=None)

        by_plan = dict(
            conn.execute(
                "SELECT plano_id, count(*) FROM conta_contabil "
                "WHERE codigo_reduzido = %s GROUP BY plano_id",
                (SHORT_CODE,),
            ).fetchall()
        )
        assert by_plan == {p1: 1, p2: 1, p3: 1}
        assert conn.execute(
            "SELECT count(*) FROM conta_contabil "
            "WHERE plano_id = %s AND codigo_reduzido IS NULL",
            (p1,),
        ).fetchone() == (2,)


def test_db04_tipo_so_aceita_s_ou_a(database_at_db04):
    """c3: S and A are accepted, anything else or NULL is refused, and the default is A."""
    with connect(database_at_db04.conninfo(APP_ROLE)) as conn:
        firm, member, clients = _seed(conn)
        client = clients["EMP-1"]
        plan = _plan(conn, firm, client, member, 1)

        synthetic = _account(conn, firm, client, plan, "1", kind="S")
        analytic = _account(conn, firm, client, plan, "11", kind="A")
        _reject(conn, psycopg.errors.CheckViolation, firm, client, plan, "12", kind="X")
        _reject(
            conn, psycopg.errors.NotNullViolation, firm, client, plan, "13", kind=None
        )
        default = _account(conn, firm, client, plan, "14")

        kinds = dict(
            conn.execute(
                "SELECT id, tipo FROM conta_contabil WHERE plano_id = %s", (plan,)
            ).fetchall()
        )
        assert kinds == {synthetic: "S", analytic: "A", default: "A"}


def test_db04_migracao_reversivel(fresh_database):
    """c4: one revision down keeps the accounts and drops the columns; up again they come back as A."""
    _run_alembic(fresh_database, "upgrade", DB04_REVISION)
    with connect(fresh_database.conninfo(APP_ROLE)) as conn:
        firm, member, clients = _seed(conn)
        client = clients["EMP-1"]
        plan = _plan(conn, firm, client, member, 1)
        _account(conn, firm, client, plan, "1", short_code="0000010", kind="S")
        _account(conn, firm, client, plan, "11", short_code="0000011", kind="A")

    kept = "SELECT id, plano_id, codigo, nome FROM conta_contabil ORDER BY codigo"
    with connect(fresh_database.conninfo(OWNER_ROLE)) as conn:
        before = conn.execute(kept).fetchall()
    assert len(before) == 2

    _run_alembic(fresh_database, "downgrade", "-1")
    with connect(fresh_database.conninfo(OWNER_ROLE)) as conn:
        assert conn.execute("SELECT version_num FROM alembic_version").fetchone() == (
            PREVIOUS_REVISION,
        )
        assert NEW_COLUMNS.isdisjoint(_column_names(conn))
        assert conn.execute(kept).fetchall() == before

    _run_alembic(fresh_database, "upgrade", DB04_REVISION)
    with connect(fresh_database.conninfo(OWNER_ROLE)) as conn:
        assert NEW_COLUMNS <= _column_names(conn)
        assert conn.execute(kept).fetchall() == before
        assert conn.execute(
            "SELECT tipo, codigo_reduzido FROM conta_contabil ORDER BY codigo"
        ).fetchall() == [("A", None), ("A", None)]
