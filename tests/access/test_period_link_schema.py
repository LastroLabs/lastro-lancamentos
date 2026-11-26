"""DB-03: schema contract for competencia and link_cliente on disposable PostgreSQL.

The four Portuguese entry points are fixed by the feature card. Records are transient
and fictional (DB-03/B1): `*_TESTE_DB03` names, CNPJ with invalid check digits, invented
hashes and database-generated UUIDs; nothing is written to `fixtures/`.
Missing schema or models are reported as assertions inside the tests, never at collection.
"""

import importlib
import os
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta

import psycopg
import pytest
from psycopg import sql

_INFRA = sys.modules["_lastro_db01_core_fixtures"]
APP_ROLE = _INFRA.APP_ROLE
OWNER_ROLE = _INFRA.OWNER_ROLE
REPO_ROOT = _INFRA.REPO_ROOT
connect = _INFRA.connect
process_output = _INFRA.process_output

NOW = datetime(2026, 10, 1, 12, tzinfo=UTC)
WEEK = NOW + timedelta(days=7)
# Used only when criado_em comes from the now() default, so expira_em stays later.
FAR_FUTURE = datetime(2999, 1, 1, tzinfo=UTC)
OCTOBER = date(2026, 10, 1)
HASH_A = "a" * 64
HASH_B = "b" * 64

DB03_TABLES = ("competencia", "link_cliente")
DB01_TABLES = (
    "escritorio",
    "usuario",
    "membro",
    "sessao",
    "convite",
    "cliente",
    "atribuicao",
)
DB02_TABLES = ("plano_contas", "conta_contabil", "conta_bancaria", "socio")
DB02_CLIENT_COLUMNS = (
    "plano_atual_id",
    "conta_transitoria_id",
    "conta_entrada_socio_id",
    "conta_saida_socio_id",
)

COLUMNS = {
    "competencia": {
        "escritorio_id": ("uuid", False, None),
        "cliente_id": ("uuid", False, None),
        "id": ("uuid", False, "gen_random_uuid()"),
        "mes": ("date", False, None),
        "versao_conjunto": ("integer", False, "0"),
        "criada_em": ("timestamp with time zone", False, "now()"),
    },
    "link_cliente": {
        "escritorio_id": ("uuid", False, None),
        "cliente_id": ("uuid", False, None),
        "id": ("uuid", False, "gen_random_uuid()"),
        "competencia_id": ("uuid", False, None),
        "hash_token": ("text", False, None),
        "criado_por": ("uuid", False, None),
        "criado_em": ("timestamp with time zone", False, "now()"),
        "expira_em": ("timestamp with time zone", False, None),
        "revogado_em": ("timestamp with time zone", True, None),
    },
}
PK = ("escritorio_id", "cliente_id", "id")
# Name -> (type, columns, referenced table, referenced columns). D2 names; D4 shortens
# only the link -> competencia FK, whose D2 name would have 67 characters.
CONSTRAINTS = {
    "competencia": {
        "pk_competencia": ("p", PK, None, ()),
        "uq_competencia_escritorio_id_cliente_id_mes": (
            "u",
            ("escritorio_id", "cliente_id", "mes"),
            None,
            (),
        ),
        "fk_competencia_escritorio_id_cliente_id_cliente": (
            "f",
            ("escritorio_id", "cliente_id"),
            "cliente",
            ("escritorio_id", "id"),
        ),
    },
    "link_cliente": {
        "pk_link_cliente": ("p", PK, None, ()),
        "uq_link_cliente_hash_token": ("u", ("hash_token",), None, ()),
        "fk_link_cliente_competencia": (
            "f",
            ("escritorio_id", "cliente_id", "competencia_id"),
            "competencia",
            ("escritorio_id", "cliente_id", "id"),
        ),
        "fk_link_cliente_escritorio_id_criado_por_membro": (
            "f",
            ("escritorio_id", "criado_por"),
            "membro",
            ("escritorio_id", "id"),
        ),
    },
}
# D4 does not fix CHECK names: only their prefix and count are part of the contract.
CHECK_COUNT = {"competencia": 2, "link_cliente": 3}
# Name -> (unique, columns). D5: no extra index on hash_token; one auxiliary index per
# foreign key not covered by a primary key prefix.
INDEXES = {
    "competencia": {
        "pk_competencia": (True, PK),
        "uq_competencia_escritorio_id_cliente_id_mes": (
            True,
            ("escritorio_id", "cliente_id", "mes"),
        ),
    },
    "link_cliente": {
        "pk_link_cliente": (True, PK),
        "uq_link_cliente_hash_token": (True, ("hash_token",)),
        "ix_link_cliente_escritorio_id_cliente_id_competencia_id": (
            False,
            ("escritorio_id", "cliente_id", "competencia_id"),
        ),
        "ix_link_cliente_escritorio_id_criado_por": (
            False,
            ("escritorio_id", "criado_por"),
        ),
    },
}

_CONSTRAINT_SQL = """
SELECT c.conname::text,
       c.contype::text,
       ARRAY(SELECT a.attname::text
               FROM unnest(c.conkey) WITH ORDINALITY AS k(num, ord)
               JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.num
              ORDER BY k.ord),
       CASE WHEN c.contype = 'f' THEN c.confrelid::regclass::text END,
       ARRAY(SELECT a.attname::text
               FROM unnest(c.confkey) WITH ORDINALITY AS k(num, ord)
               JOIN pg_attribute a ON a.attrelid = c.confrelid AND a.attnum = k.num
              ORDER BY k.ord),
       c.confupdtype::text,
       c.confdeltype::text,
       c.condeferrable,
       c.condeferred
  FROM pg_constraint c
 WHERE c.conrelid = to_regclass(%s) AND c.contype IN ('p', 'u', 'f', 'c')
"""
_INDEX_SQL = """
SELECT i.relname::text,
       x.indisunique,
       ARRAY(SELECT a.attname::text
               FROM unnest(x.indkey::int2[]) WITH ORDINALITY AS k(num, ord)
               JOIN pg_attribute a ON a.attrelid = x.indrelid AND a.attnum = k.num
              ORDER BY k.ord),
       pg_get_expr(x.indpred, x.indrelid)
  FROM pg_index x
  JOIN pg_class i ON i.oid = x.indexrelid
 WHERE x.indrelid = to_regclass(%s)
"""


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
    assert result.returncode == 0, process_output(result)


@pytest.fixture
def head_database(fresh_database):
    """Fresh database at `alembic upgrade head`; the shared fixture stays at 0002."""
    _run_alembic(fresh_database, "upgrade", "head")
    return fresh_database


def _insert(conn, table, **values):
    statement = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING *").format(
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, values)),
        sql.SQL(", ").join(sql.Placeholder() for _ in values),
    )
    cursor = conn.execute(statement, list(values.values()))
    names = [column.name for column in cursor.description]
    return dict(zip(names, cursor.fetchone(), strict=True))


def _count(conn, table):
    query = sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
    return conn.execute(query).fetchone()[0]


def _reject(conn, error, table, values):
    """A savepoint isolates each refusal and proves no row was written."""
    before = _count(conn, table)
    with pytest.raises(error), conn.transaction():
        _insert(conn, table, **values)
    assert _count(conn, table) == before


def _require_schema(conn):
    missing = [
        table
        for table in DB03_TABLES
        if conn.execute("SELECT to_regclass(%s)", (f"public.{table}",)).fetchone()[0]
        is None
    ]
    assert not missing, f"DB-03 schema absent: {missing}"


def _columns(conn, table):
    rows = conn.execute(
        "SELECT column_name, data_type, is_nullable = 'YES', column_default "
        "FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %s",
        (table,),
    )
    return {name: (kind, nullable, default) for name, kind, nullable, default in rows}


def _constraints(conn, table):
    return {
        row[0]: {
            "type": row[1],
            "columns": tuple(row[2]),
            "target": row[3],
            "target_columns": tuple(row[4]),
            "on_update": row[5],
            "on_delete": row[6],
            "deferrable": row[7],
            "deferred": row[8],
        }
        for row in conn.execute(_CONSTRAINT_SQL, (f"public.{table}",))
    }


def _indexes(conn, table):
    return {
        name: (unique, tuple(columns), predicate)
        for name, unique, columns, predicate in conn.execute(
            _INDEX_SQL, (f"public.{table}",)
        )
    }


def _assert_table_schema(conn, table):
    """Columns, keys, CHECK count and indexes exactly as c1/c2, D4 and D5 describe."""
    assert _columns(conn, table) == COLUMNS[table], table
    constraints = _constraints(conn, table)
    keys = {
        name: (item["type"], item["columns"], item["target"], item["target_columns"])
        for name, item in constraints.items()
        if item["type"] != "c"
    }
    assert keys == CONSTRAINTS[table], table
    checks = [name for name, item in constraints.items() if item["type"] == "c"]
    assert len(checks) == CHECK_COUNT[table], (table, checks)
    assert all(name.startswith(f"ck_{table}_") for name in checks), checks
    indexes = {
        name: (unique, columns)
        for name, (unique, columns, predicate) in _indexes(conn, table).items()
        if predicate is None
    }
    assert indexes == INDEXES[table], table
    assert all(predicate is None for _, _, predicate in _indexes(conn, table).values())


def _model(name, table):
    path = REPO_ROOT / "src" / "lastro" / "access" / "models.py"
    assert path.is_file(), "DB-03 model module absent: lastro.access.models"
    access = importlib.import_module("lastro.access.models")
    model = getattr(access, name, None)
    assert model is not None, f"DB-03 model absent: lastro.access.models.{name}"
    base = importlib.import_module("lastro.core.models").Base
    assert model.metadata is base.metadata
    assert model.__tablename__ == table
    assert set(model.__table__.columns.keys()) == set(COLUMNS[table])
    return model


def _seed(conn):
    """Fictional firms, members and clients (DB-03/B1)."""
    firm = _insert(conn, "escritorio", nome="ESCRITORIO_TESTE_DB03_1")["id"]
    other_firm = _insert(conn, "escritorio", nome="ESCRITORIO_TESTE_DB03_2")["id"]
    state = {"firm": firm, "other_firm": other_firm}
    for key, owner, role in (
        ("chief", firm, "chefe"),
        ("foreign", other_firm, "contador"),
    ):
        user = _insert(
            conn,
            "usuario",
            identificador_login=f"USUARIO_TESTE_DB03_{key}",
            nome=f"PESSOA_TESTE_DB03_{key}",
        )["id"]
        state[key] = _insert(
            conn, "membro", escritorio_id=owner, usuario_id=user, papel=role
        )["id"]
    for key, cnpj in (("client", "11122233000100"), ("other_client", "11122233000200")):
        state[key] = _insert(
            conn,
            "cliente",
            escritorio_id=firm,
            nome=f"CLIENTE_TESTE_DB03_{key}",
            cnpj_normalizado=cnpj,
        )["id"]
    return state


def _period(state, client="client", month=OCTOBER):
    return {"escritorio_id": state["firm"], "cliente_id": state[client], "mes": month}


def _link(state, period, **overrides):
    values = {
        "escritorio_id": state["firm"],
        "cliente_id": state["client"],
        "competencia_id": period,
        "hash_token": HASH_A,
        "criado_por": state["chief"],
        "criado_em": NOW,
        "expira_em": WEEK,
    }
    return {**values, **overrides}


def _set_timezone(conn, zone):
    conn.execute(sql.SQL("SET TimeZone = {}").format(sql.Literal(zone)))


def test_migracao_db03_cria_competencia_unica_por_cliente_e_mes(head_database):
    """c1: one competencia per client and month, always stored on the first day."""
    with connect(head_database.conninfo(APP_ROLE)) as conn:
        _require_schema(conn)
        _assert_table_schema(conn, "competencia")
        state = _seed(conn)
        first = _insert(conn, "competencia", **_period(state))
        assert first["mes"] == OCTOBER
        assert first["versao_conjunto"] == 0
        assert first["criada_em"] is not None
        _reject(conn, psycopg.errors.UniqueViolation, "competencia", _period(state))
        _insert(conn, "competencia", **_period(state, "other_client"))
        _reject(
            conn,
            psycopg.errors.CheckViolation,
            "competencia",
            _period(state, month=date(2026, 10, 15)),
        )
        _reject(
            conn,
            psycopg.errors.CheckViolation,
            "competencia",
            {**_period(state, month=date(2026, 9, 1)), "versao_conjunto": -1},
        )
        _reject(
            conn,
            psycopg.errors.NotNullViolation,
            "competencia",
            _period(state, month=None),
        )
        # D3: the first-day rule must not depend on the session time zone.
        for offset, zone in enumerate(("UTC", "America/Sao_Paulo", "Asia/Tokyo")):
            _set_timezone(conn, zone)
            for day in (date(2026, 10, 15), date(2026, 11, 30), date(2027, 1, 2)):
                _reject(
                    conn,
                    psycopg.errors.CheckViolation,
                    "competencia",
                    _period(state, month=day),
                )
            month = date(2027, 1 + offset, 1)
            row = _insert(conn, "competencia", **_period(state, month=month))
            assert row["mes"] == month, zone
        assert _count(conn, "competencia") == 5
    _model("Period", "competencia")


def test_migracao_db03_cria_link_que_guarda_so_o_hash(head_database):
    """c2: the link stores only the hash, with validity and revocation."""
    with connect(head_database.conninfo(APP_ROLE)) as conn:
        _require_schema(conn)
        _assert_table_schema(conn, "link_cliente")
        for table in DB03_TABLES:
            names = set(_columns(conn, table))
            suspicious = {name for name in names if "token" in name or "codigo" in name}
            assert suspicious == ({"hash_token"} if table == "link_cliente" else set())
        # The global UNIQUE index is the only index on hash_token (D5).
        by_hash = {
            name: (unique, columns, predicate)
            for name, (unique, columns, predicate) in _indexes(
                conn, "link_cliente"
            ).items()
            if columns[0] == "hash_token"
        }
        assert by_hash == {"uq_link_cliente_hash_token": (True, ("hash_token",), None)}
        state = _seed(conn)
        period = _insert(conn, "competencia", **_period(state))["id"]
        link = _insert(conn, "link_cliente", **_link(state, period))
        assert link["hash_token"] == HASH_A
        assert link["expira_em"] - link["criado_em"] == timedelta(days=7)
        assert link["revogado_em"] is None
        for bad_hash in ("abc", "A" * 64, "g" * 64, "a" * 63, "a" * 65):
            _reject(
                conn,
                psycopg.errors.CheckViolation,
                "link_cliente",
                _link(state, period, hash_token=bad_hash),
            )
        _reject(
            conn,
            psycopg.errors.CheckViolation,
            "link_cliente",
            _link(
                state, period, hash_token=HASH_B, revogado_em=NOW - timedelta(seconds=1)
            ),
        )
        revoked = _insert(
            conn,
            "link_cliente",
            **_link(
                state, period, hash_token=HASH_B, revogado_em=NOW + timedelta(hours=1)
            ),
        )
        assert revoked["revogado_em"] == NOW + timedelta(hours=1)
        defaulted = _insert(
            conn,
            "link_cliente",
            **{
                key: value
                for key, value in _link(
                    state, period, hash_token="c" * 64, expira_em=FAR_FUTURE
                ).items()
                if key != "criado_em"
            },
        )
        assert defaulted["criado_em"] is not None
        _reject(
            conn,
            psycopg.errors.NotNullViolation,
            "link_cliente",
            _link(state, period, hash_token="d" * 64, expira_em=None),
        )
    _model("ClientLink", "link_cliente")


def test_db03_link_nao_cruza_cliente_nem_escritorio(head_database):
    """c3: compound keys keep the link inside its client, period and firm."""
    with connect(head_database.conninfo(APP_ROLE)) as conn:
        _require_schema(conn)
        for table in DB03_TABLES:
            constraints = _constraints(conn, table)
            for name, item in constraints.items():
                assert len(name) <= 63, name
                if item["type"] == "f":
                    assert (item["on_update"], item["on_delete"]) == ("a", "a"), name
                    assert item["deferrable"] is False and item["deferred"] is False
            assert all(len(name) <= 63 for name in _indexes(conn, table))
        foreign_keys = {
            name: (item["columns"], item["target"], item["target_columns"])
            for name, item in _constraints(conn, "link_cliente").items()
            if item["type"] == "f"
        }
        assert foreign_keys == {
            "fk_link_cliente_competencia": (
                ("escritorio_id", "cliente_id", "competencia_id"),
                "competencia",
                ("escritorio_id", "cliente_id", "id"),
            ),
            "fk_link_cliente_escritorio_id_criado_por_membro": (
                ("escritorio_id", "criado_por"),
                "membro",
                ("escritorio_id", "id"),
            ),
        }
        # D6: no direct link -> cliente FK; the competencia FK already pins the client.
        assert "cliente" not in {target for _, target, _ in foreign_keys.values()}

        state = _seed(conn)
        period = _insert(conn, "competencia", **_period(state))["id"]
        other_period = _insert(conn, "competencia", **_period(state, "other_client"))[
            "id"
        ]
        _insert(conn, "link_cliente", **_link(state, period))
        cases = (
            (
                psycopg.errors.ForeignKeyViolation,
                _link(state, other_period, hash_token=HASH_B),
            ),
            (
                psycopg.errors.ForeignKeyViolation,
                _link(state, period, hash_token=HASH_B, criado_por=state["foreign"]),
            ),
            (psycopg.errors.UniqueViolation, _link(state, period)),
            (
                psycopg.errors.CheckViolation,
                _link(state, period, hash_token=HASH_B, expira_em=NOW),
            ),
        )
        for error, values in cases:
            _reject(conn, error, "link_cliente", values)
        assert _count(conn, "link_cliente") == 1


def _seed_registry(conn, state):
    """Fictional DB-02 rows, including the new client configuration columns."""
    firm, client = state["firm"], state["client"]
    plan = _insert(
        conn,
        "plano_contas",
        escritorio_id=firm,
        cliente_id=client,
        versao=1,
        importado_por=state["chief"],
        importado_em=NOW,
        situacao="importado",
    )["id"]
    account = _insert(
        conn,
        "conta_contabil",
        escritorio_id=firm,
        cliente_id=client,
        plano_id=plan,
        codigo="01.002.0003",
        nome="CONTA_TESTE_DB03",
    )["id"]
    conn.execute(
        "UPDATE cliente SET plano_atual_id = %s, conta_transitoria_id = %s, "
        "conta_entrada_socio_id = %s, conta_saida_socio_id = %s "
        "WHERE escritorio_id = %s AND id = %s",
        (plan, account, account, account, firm, client),
    )
    _insert(
        conn,
        "conta_bancaria",
        escritorio_id=firm,
        cliente_id=client,
        banco="001",
        apelido="CONTA_MOVIMENTO_TESTE_DB03",
        conta_contabil_id=account,
    )
    _insert(
        conn,
        "socio",
        escritorio_id=firm,
        cliente_id=client,
        nome="SOCIO_TESTE_DB03",
        nome_normalizado="socio_teste_db03",
    )


def _snapshot(conn):
    """Every row of the DB-01 and DB-02 tables, in a stable order."""
    return {
        table: sorted(
            conn.execute(
                sql.SQL("SELECT * FROM {}").format(sql.Identifier(table))
            ).fetchall(),
            key=repr,
        )
        for table in (*DB01_TABLES, *DB02_TABLES)
    }


def _schema(conn):
    return {
        table: (_columns(conn, table), _constraints(conn, table), _indexes(conn, table))
        for table in DB03_TABLES
    }


def test_db03_migracao_reversivel(fresh_database):
    """c4: downgrading DB-03 removes only its tables and keeps DB-01/DB-02 data."""
    _run_alembic(fresh_database, "upgrade", "0003")
    with connect(fresh_database.conninfo(APP_ROLE)) as conn:
        state = _seed(conn)
        _seed_registry(conn, state)
    _run_alembic(fresh_database, "upgrade", "head")
    with connect(fresh_database.conninfo(APP_ROLE)) as conn:
        _require_schema(conn)
        period = _insert(conn, "competencia", **_period(state))["id"]
        _insert(conn, "link_cliente", **_link(state, period))
    with connect(fresh_database.conninfo(OWNER_ROLE)) as conn:
        before = _snapshot(conn)
        schema = _schema(conn)
        client = next(
            row
            for row in conn.execute(
                "SELECT " + ", ".join(DB02_CLIENT_COLUMNS) + " FROM cliente "
                "WHERE id = %s",
                (state["client"],),
            )
        )
        assert all(value is not None for value in client)
        assert all(before[table] for table in DB02_TABLES)

    _run_alembic(fresh_database, "downgrade", "0003")
    with connect(fresh_database.conninfo(OWNER_ROLE)) as conn:
        assert conn.execute("SELECT version_num FROM alembic_version").fetchone() == (
            "0003",
        )
        for table in DB03_TABLES:
            assert (
                conn.execute("SELECT to_regclass(%s)", (f"public.{table}",)).fetchone()[
                    0
                ]
                is None
            ), table
        assert _snapshot(conn) == before

    _run_alembic(fresh_database, "upgrade", "head")
    with connect(fresh_database.conninfo(OWNER_ROLE)) as conn:
        _require_schema(conn)
        assert _schema(conn) == schema
        for table in DB03_TABLES:
            _assert_table_schema(conn, table)
            assert _count(conn, table) == 0
        assert _snapshot(conn) == before
