"""DB-01: executable schema contract using only deterministic synthetic records.

The six Portuguese entry points are fixed by the feature card. Extra cases use
English names. Missing product modules are checked inside tests, never at collection.
No xfail, skip, SQLite, ORM create_all or substitute migration is used.
"""

import importlib
import os
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from uuid import UUID

import psycopg
import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic.script import ScriptDirectory
from psycopg import sql

_INFRA = sys.modules["_lastro_db01_core_fixtures"]
APP_ROLE = _INFRA.APP_ROLE
OWNER_ROLE = _INFRA.OWNER_ROLE
REPO_ROOT = _INFRA.REPO_ROOT
connect = _INFRA.connect

NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)
LATER = NOW + timedelta(hours=48)
TABLES = (
    "escritorio",
    "usuario",
    "membro",
    "cliente",
    "sessao",
    "convite",
    "atribuicao",
)
PKS = {
    "escritorio": ("id",),
    "usuario": ("id",),
    "membro": ("escritorio_id", "id"),
    "cliente": ("escritorio_id", "id"),
    "sessao": ("escritorio_id", "id"),
    "convite": ("escritorio_id", "id"),
    "atribuicao": ("escritorio_id", "cliente_id", "id"),
}
# Column tuples are (PostgreSQL type, nullable, server default).
COLUMNS = {
    "escritorio": {
        "id": ("uuid", False, "gen_random_uuid()"),
        "nome": ("text", False, None),
        "ativo": ("boolean", False, "true"),
    },
    "usuario": {
        "id": ("uuid", False, "gen_random_uuid()"),
        "identificador_login": ("text", False, None),
        "nome": ("text", False, None),
        "ativo": ("boolean", False, "true"),
        "credencial_hash": ("text", True, None),
    },
    "membro": {
        "escritorio_id": ("uuid", False, None),
        "id": ("uuid", False, "gen_random_uuid()"),
        "usuario_id": ("uuid", False, None),
        "papel": ("text", False, None),
        "ativo": ("boolean", False, "true"),
    },
    "cliente": {
        "escritorio_id": ("uuid", False, None),
        "id": ("uuid", False, "gen_random_uuid()"),
        "nome": ("text", False, None),
        "cnpj_normalizado": ("text", False, None),
        "ativo": ("boolean", False, "true"),
        "versao_acesso": ("bigint", False, "0"),
    },
    "sessao": {
        "escritorio_id": ("uuid", False, None),
        "id": ("uuid", False, "gen_random_uuid()"),
        "membro_id": ("uuid", False, None),
        "hash_token": ("text", False, None),
        "criada_em": ("timestamp with time zone", False, None),
        "expira_em": ("timestamp with time zone", False, None),
        "encerrada_em": ("timestamp with time zone", True, None),
    },
    "convite": {
        "escritorio_id": ("uuid", False, None),
        "id": ("uuid", False, "gen_random_uuid()"),
        "membro_id": ("uuid", False, None),
        "hash_token": ("text", False, None),
        "criado_por": ("uuid", False, None),
        "criado_em": ("timestamp with time zone", False, "now()"),
        "expira_em": ("timestamp with time zone", False, None),
        "usado_em": ("timestamp with time zone", True, None),
        "revogado_em": ("timestamp with time zone", True, None),
    },
    "atribuicao": {
        "escritorio_id": ("uuid", False, None),
        "cliente_id": ("uuid", False, None),
        "id": ("uuid", False, "gen_random_uuid()"),
        "membro_id": ("uuid", False, None),
        "atribuido_por": ("uuid", False, None),
        "inicio": ("timestamp with time zone", False, None),
        "fim": ("timestamp with time zone", True, None),
    },
}
FKS = {
    "escritorio": set(),
    "usuario": set(),
    "membro": {
        (("escritorio_id",), "escritorio", ("id",)),
        (("usuario_id",), "usuario", ("id",)),
    },
    "cliente": {(("escritorio_id",), "escritorio", ("id",))},
    "sessao": {(("escritorio_id", "membro_id"), "membro", ("escritorio_id", "id"))},
    "convite": {
        (("escritorio_id", "membro_id"), "membro", ("escritorio_id", "id")),
        (("escritorio_id", "criado_por"), "membro", ("escritorio_id", "id")),
    },
    "atribuicao": {
        (("escritorio_id", "cliente_id"), "cliente", ("escritorio_id", "id")),
        (("escritorio_id", "membro_id"), "membro", ("escritorio_id", "id")),
        (("escritorio_id", "atribuido_por"), "membro", ("escritorio_id", "id")),
    },
}
UNIQUES = {
    "usuario": {("identificador_login",)},
    "membro": {("escritorio_id", "usuario_id")},
    "cliente": {("escritorio_id", "cnpj_normalizado")},
    "sessao": {("hash_token",)},
    "convite": {("hash_token",)},
}
AUXILIARY = {
    "membro": {("usuario_id",)},
    "sessao": {("escritorio_id", "membro_id")},
    "convite": {("escritorio_id", "membro_id"), ("escritorio_id", "criado_por")},
    "atribuicao": {("escritorio_id", "membro_id"), ("escritorio_id", "atribuido_por")},
}
PARTIALS = {
    "atribuicao": (("escritorio_id", "cliente_id"), "fimisnull"),
    "convite": (("escritorio_id", "membro_id"), "usado_emisnullandrevogado_emisnull"),
}
CHECKS = {
    "membro": ("papel", "chefe", "contador"),
    "sessao": ("expira_em>criada_em",),
    "cliente": ("versao_acesso>=0",),
    "atribuicao": ("fimisnullorfim>inicio",),
    "convite": (
        "hash_token~",
        "^[0-9a-f]{64}$",
        "expira_em>criado_em",
        "usado_emisnullorrevogado_emisnull",
    ),
}


def _normalize(expression):
    return re.sub(r"[\s()\"]", "", str(expression).lower()).replace("::text", "")


def _tables(conn):
    return {
        row[0]
        for row in conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
    }


def _require_schema(conn):
    missing = set(TABLES) - _tables(conn)
    assert not missing, f"DB-01 schema absent: {sorted(missing)}"


def _insert(conn, table, **values):
    statement = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING *").format(
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, values)),
        sql.SQL(", ").join(sql.Placeholder() for _ in values),
    )
    cursor = conn.execute(statement, list(values.values()))
    row = dict(
        zip(
            (column.name for column in cursor.description),
            cursor.fetchone(),
            strict=True,
        )
    )
    assert isinstance(row["id"], UUID) and row["id"].version == 4
    return row


def _seed(conn):
    """Generate fictitious firms, users and clients; CNPJ has deliberately invalid DV."""
    a = _insert(conn, "escritorio", nome="ESCRITORIO_TESTE_A")["id"]
    b = _insert(conn, "escritorio", nome="ESCRITORIO_TESTE_B")["id"]
    state = {"a": a, "b": b}
    for key, firm, role in (
        ("chief", a, "chefe"),
        ("first", a, "contador"),
        ("second", a, "contador"),
        ("foreign", b, "contador"),
    ):
        user = _insert(
            conn,
            "usuario",
            identificador_login=f"USUARIO_TESTE_{key}",
            nome=f"PESSOA_TESTE_{key}",
        )
        assert user["credencial_hash"] is None and user["ativo"] is True
        state[f"user_{key}"] = user["id"]
        state[key] = _insert(
            conn, "membro", escritorio_id=firm, usuario_id=user["id"], papel=role
        )["id"]
    for key, firm, cnpj in (
        ("client", a, "11122233000100"),
        ("other_client", a, "11122233000200"),
        ("foreign_client", b, "11122233000100"),
    ):
        client = _insert(
            conn,
            "cliente",
            escritorio_id=firm,
            nome=f"CLIENTE_TESTE_{key}",
            cnpj_normalizado=cnpj,
        )
        assert client["ativo"] is True and client["versao_acesso"] == 0
        state[key] = client["id"]
    return state


def _values(table, state):
    return {
        "membro": {
            "escritorio_id": state["a"],
            "usuario_id": state["user_foreign"],
            "papel": "contador",
        },
        "cliente": {
            "escritorio_id": state["a"],
            "nome": "CLIENTE_TESTE_EXTRA",
            "cnpj_normalizado": "11122233000300",
        },
        "sessao": {
            "escritorio_id": state["a"],
            "membro_id": state["first"],
            "hash_token": "a" * 64,
            "criada_em": NOW,
            "expira_em": LATER,
        },
        "convite": {
            "escritorio_id": state["a"],
            "membro_id": state["first"],
            "hash_token": "b" * 64,
            "criado_por": state["chief"],
            "criado_em": NOW,
            "expira_em": LATER,
        },
        "atribuicao": {
            "escritorio_id": state["a"],
            "cliente_id": state["client"],
            "membro_id": state["first"],
            "atribuido_por": state["chief"],
            "inicio": NOW,
        },
    }[table].copy()


def _reject(conn, table, values, error):
    """A savepoint isolates each refusal and proves no residual row was written."""
    query = sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
    before = conn.execute(query).fetchone()[0]
    with pytest.raises(error), conn.transaction():
        _insert(conn, table, **values)
    assert conn.execute(query).fetchone()[0] == before


def _catalog(database):
    """Inspect migrated DDL independently of live ORM declarations."""
    engine = sa.create_engine(database.migrations_database_url)
    try:
        with engine.connect() as conn:
            inspector = sa.inspect(conn)
            catalog = {
                table: {
                    "columns": inspector.get_columns(table),
                    "pk": inspector.get_pk_constraint(table),
                    "fk": inspector.get_foreign_keys(table),
                    "uq": inspector.get_unique_constraints(table),
                    "ck": inspector.get_check_constraints(table),
                    "ix": inspector.get_indexes(table),
                }
                for table in TABLES
            }
            # Reflected TypeEngine objects compare by identity. Store SQL type names
            # so a downgrade/upgrade compares the DDL, not different Python instances.
            for spec in catalog.values():
                for column in spec["columns"]:
                    column["type"] = str(
                        column["type"].compile(dialect=engine.dialect)
                    ).lower()
            return catalog
    finally:
        engine.dispose()


def _assert_catalog(catalog):
    for table, spec in catalog.items():
        columns = {
            column["name"]: (
                column["type"],
                column["nullable"],
                column["default"],
            )
            for column in spec["columns"]
        }
        assert columns == COLUMNS[table], table
        assert tuple(spec["pk"]["constrained_columns"]) == PKS[table]
        assert spec["pk"]["name"] == f"pk_{table}"
        actual_fks = set()
        for fk in spec["fk"]:
            names = tuple(fk["constrained_columns"])
            actual_fks.add((names, fk["referred_table"], tuple(fk["referred_columns"])))
            assert fk["name"] == f"fk_{table}_{'_'.join(names)}_{fk['referred_table']}"
        assert actual_fks == FKS[table]
        assert {tuple(item["column_names"]) for item in spec["uq"]} == UNIQUES.get(
            table, set()
        )
        for item in spec["uq"]:
            assert item["name"] == f"uq_{table}_{'_'.join(item['column_names'])}"
        checks = " ".join(_normalize(item["sqltext"]) for item in spec["ck"])
        assert len(spec["ck"]) == {
            "membro": 1,
            "sessao": 1,
            "cliente": 1,
            "atribuicao": 1,
            "convite": 3,
        }.get(table, 0)
        for fragment in CHECKS.get(table, ()):
            assert fragment in checks, (table, fragment, checks)
        for item in spec["ck"]:
            assert item["name"].startswith(f"ck_{table}_")
            assert len(item["name"]) > len(f"ck_{table}_")
        indexes = [item for item in spec["ix"] if not item.get("duplicates_constraint")]
        auxiliary = {
            tuple(item["column_names"]) for item in indexes if not item["unique"]
        }
        assert auxiliary == AUXILIARY.get(table, set())
        partials = [item for item in indexes if item["unique"]]
        assert len(partials) == int(table in PARTIALS)
        if table in PARTIALS:
            columns, predicate = PARTIALS[table]
            assert tuple(partials[0]["column_names"]) == columns
            assert (
                _normalize(partials[0]["dialect_options"]["postgresql_where"])
                == predicate
            )
        for item in indexes:
            expected_name = f"ix_{table}_{'_'.join(item['column_names'])}"
            if table == "convite" and item["unique"]:
                expected_name = "uq_convite_escritorio_id_membro_id_pendente"
            assert item["name"] == expected_name
            if not item["unique"]:
                assert not item.get("dialect_options", {}).get("postgresql_where")
        for kind in ("fk", "uq", "ck", "ix"):
            assert all(len(item["name"]) <= 63 for item in spec[kind])


def test_migracao_db01_cria_tabelas_de_identidade_com_colunas_e_chaves(
    migrated_database,
):
    """c1: exact empty DDL, server defaults, keys and a single child of 0001."""
    with connect(migrated_database.conninfo(OWNER_ROLE)) as conn:
        assert int(conn.execute("SHOW server_version_num").fetchone()[0]) // 10000 == 18
        _require_schema(conn)
        assert _tables(conn) == {*TABLES, "alembic_version"}
        for table in TABLES:
            assert conn.execute(
                sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
            ).fetchone() == (0,)
        actions = conn.execute(
            "SELECT conname, confdeltype, confupdtype, condeferrable, condeferred "
            "FROM pg_constraint WHERE contype = 'f' AND connamespace = 'public'::regnamespace"
        ).fetchall()
        assert len(actions) == sum(map(len, FKS.values()))
        assert all(row[1:] == ("a", "a", False, False) for row in actions)
        state = _seed(conn)
        for table in ("sessao", "convite", "atribuicao"):
            _insert(conn, table, **_values(table, state))
    _assert_catalog(_catalog(migrated_database))
    scripts = ScriptDirectory.from_config(Config(str(REPO_ROOT / "alembic.ini")))
    assert scripts.get_revision("0002").down_revision == "0001"
    assert scripts.get_revision("0001").down_revision is None


FK_CASES = (
    ("atribuicao", "membro_id", "foreign"),
    ("atribuicao", "atribuido_por", "foreign"),
    ("sessao", "membro_id", "foreign"),
    ("convite", "membro_id", "foreign"),
    ("membro", "usuario_id", "missing"),
    ("convite", "criado_por", "foreign"),
    ("membro", "escritorio_id", "missing"),
    ("cliente", "escritorio_id", "missing"),
    ("atribuicao", "cliente_id", "foreign_client"),
)


@pytest.mark.parametrize(("table", "column", "reference"), FK_CASES)
def test_db01_fk_de_outro_escritorio_recusada(
    migrated_database, table, column, reference
):
    """c2: eight card cases plus a client belonging to another firm."""
    with connect(migrated_database.conninfo(APP_ROLE)) as conn:
        _require_schema(conn)
        state = _seed(conn)
        values = _values(table, state)
        values[column] = UUID(int=999) if reference == "missing" else state[reference]
        _reject(conn, table, values, psycopg.errors.ForeignKeyViolation)


def test_db01_um_responsavel_ativo_por_cliente(migrated_database):
    """c3: reject a second open assignment; atomically change it without losing history."""
    with connect(migrated_database.conninfo(APP_ROLE)) as conn:
        _require_schema(conn)
        state = _seed(conn)
        values = _values("atribuicao", state)
        first = _insert(conn, "atribuicao", **values)
        replacement = {**values, "membro_id": state["second"], "inicio": LATER}
        _reject(conn, "atribuicao", replacement, psycopg.errors.UniqueViolation)
        with conn.transaction():
            conn.execute(
                "UPDATE atribuicao SET fim = %s WHERE escritorio_id = %s AND id = %s",
                [LATER, state["a"], first["id"]],
            )
            second = _insert(conn, "atribuicao", **replacement)
        rows = conn.execute(
            "SELECT id, membro_id, fim FROM atribuicao "
            "WHERE escritorio_id = %s AND cliente_id = %s ORDER BY inicio",
            [state["a"], state["client"]],
        ).fetchall()
        assert rows == [
            (first["id"], state["first"], LATER),
            (second["id"], state["second"], None),
        ]
        _insert(
            conn,
            "atribuicao",
            **{
                **values,
                "cliente_id": state["other_client"],
                "membro_id": state["chief"],
            },
        )


def test_db01_unicidades_de_cadastro(migrated_database):
    """c4: global login, firm-scoped CNPJ and membership, and the two allowed roles."""
    with connect(migrated_database.conninfo(APP_ROLE)) as conn:
        _require_schema(conn)
        state = _seed(conn)
        _reject(
            conn,
            "cliente",
            {**_values("cliente", state), "cnpj_normalizado": "11122233000100"},
            psycopg.errors.UniqueViolation,
        )
        # _seed already inserted this same CNPJ in A and B successfully.
        assert conn.execute(
            "SELECT count(*) FROM cliente WHERE cnpj_normalizado = %s",
            ["11122233000100"],
        ).fetchone() == (2,)
        _reject(
            conn,
            "usuario",
            {
                "nome": "PESSOA_TESTE_DUPLICADA",
                "identificador_login": "USUARIO_TESTE_chief",
            },
            psycopg.errors.UniqueViolation,
        )
        member = {**_values("membro", state), "usuario_id": state["user_chief"]}
        _reject(conn, "membro", member, psycopg.errors.UniqueViolation)
        _insert(conn, "membro", **{**member, "escritorio_id": state["b"]})
        _reject(
            conn,
            "membro",
            {**_values("membro", state), "papel": "gerente"},
            psycopg.errors.CheckViolation,
        )


def test_db01_convite_guarda_so_o_hash_e_um_pendente_por_membro(migrated_database):
    """c5: pending means unused and unrevoked, including already expired invitations."""
    with connect(migrated_database.conninfo(APP_ROLE)) as conn:
        _require_schema(conn)
        state = _seed(conn)
        columns = {
            row[0]
            for row in conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'convite'"
            )
        }
        assert columns == set(COLUMNS["convite"])
        assert {name for name in columns if "token" in name or "codigo" in name} == {
            "hash_token"
        }
        values = _values("convite", state)
        first = _insert(conn, "convite", **values)
        assert first["hash_token"] == "b" * 64
        _reject(
            conn,
            "convite",
            {**values, "hash_token": "c" * 64},
            psycopg.errors.UniqueViolation,
        )
        with conn.transaction():
            conn.execute(
                "UPDATE convite SET revogado_em = %s WHERE id = %s AND escritorio_id = %s",
                [LATER, first["id"], state["a"]],
            )
            _insert(conn, "convite", **{**values, "hash_token": "c" * 64})
        expired = {
            **values,
            "membro_id": state["second"],
            "hash_token": "d" * 64,
            "criado_em": NOW - timedelta(days=10),
            "expira_em": NOW - timedelta(days=9),
        }
        old = _insert(conn, "convite", **expired)
        renewed = {**values, "membro_id": state["second"], "hash_token": "e" * 64}
        _reject(conn, "convite", renewed, psycopg.errors.UniqueViolation)
        with conn.transaction():
            conn.execute(
                "UPDATE convite SET revogado_em = %s WHERE id = %s AND escritorio_id = %s",
                [NOW, old["id"], state["a"]],
            )
            _insert(conn, "convite", **renewed)
        assert conn.execute("SELECT count(*) FROM convite").fetchone() == (4,)


@pytest.mark.parametrize(
    ("table", "changes"),
    [
        ("atribuicao", {"fim": NOW}),
        ("atribuicao", {"fim": NOW - timedelta(seconds=1)}),
        ("sessao", {"expira_em": NOW}),
        ("sessao", {"expira_em": NOW - timedelta(seconds=1)}),
        ("cliente", {"versao_acesso": -1}),
        ("convite", {"expira_em": NOW}),
        ("convite", {"expira_em": NOW - timedelta(seconds=1)}),
        ("convite", {"usado_em": LATER, "revogado_em": LATER}),
        *[
            ("convite", {"hash_token": value})
            for value in ("abc", "g" * 64, "A" * 64, "a" * 63, "a" * 65)
        ],
    ],
)
def test_db01_invalid_checks_leave_no_rows(migrated_database, table, changes):
    """CHECK failures must be precise and leave the next case usable."""
    with connect(migrated_database.conninfo(APP_ROLE)) as conn:
        _require_schema(conn)
        state = _seed(conn)
        _reject(
            conn,
            table,
            {**_values(table, state), **changes},
            psycopg.errors.CheckViolation,
        )


@pytest.mark.parametrize("table", ("sessao", "convite"))
def test_db01_hash_is_globally_unique(migrated_database, table):
    """Different firms cannot reuse a session/invitation hash."""
    with connect(migrated_database.conninfo(APP_ROLE)) as conn:
        _require_schema(conn)
        state = _seed(conn)
        values = _values(table, state)
        _insert(conn, table, **values)
        other = {**values, "escritorio_id": state["b"], "membro_id": state["foreign"]}
        if table == "convite":
            other["criado_por"] = state["foreign"]
        _reject(conn, table, other, psycopg.errors.UniqueViolation)


def test_db01_partial_uniqueness_is_scoped_to_firm_and_client(migrated_database):
    """Composite identities may repeat across firms without a global id constraint."""
    with connect(migrated_database.conninfo(APP_ROLE)) as conn:
        _require_schema(conn)
        state = _seed(conn)
        # Repeat both client and member ids in B, using valid B references.
        _insert(
            conn,
            "cliente",
            **{
                **_values("cliente", state),
                "escritorio_id": state["b"],
                "id": state["client"],
            },
        )
        _insert(
            conn,
            "membro",
            escritorio_id=state["b"],
            id=state["first"],
            usuario_id=state["user_first"],
            papel="contador",
        )
        assignment = _values("atribuicao", state)
        _insert(conn, "atribuicao", **assignment)
        _insert(
            conn,
            "atribuicao",
            **{
                **assignment,
                "escritorio_id": state["b"],
                "atribuido_por": state["foreign"],
            },
        )
        invitation = _values("convite", state)
        _insert(conn, "convite", **invitation)
        _insert(
            conn,
            "convite",
            **{
                **invitation,
                "escritorio_id": state["b"],
                "criado_por": state["foreign"],
                "hash_token": "f" * 64,
            },
        )


def test_db01_used_invitation_allows_reissue_and_no_fixed_duration(migrated_database):
    """Used invitations leave the partial index; 48 hours is only an example."""
    with connect(migrated_database.conninfo(APP_ROLE)) as conn:
        _require_schema(conn)
        state = _seed(conn)
        values = _values("convite", state)
        _insert(
            conn,
            "convite",
            **{
                **values,
                "usado_em": NOW + timedelta(minutes=1),
                "expira_em": NOW + timedelta(minutes=2),
            },
        )
        _insert(
            conn,
            "convite",
            **{**values, "hash_token": "f" * 64, "expira_em": NOW + timedelta(days=5)},
        )
        assert conn.execute("SELECT count(*) FROM convite").fetchone() == (2,)


@pytest.mark.parametrize(
    ("table", "column"),
    [
        (table, column)
        for table, columns in COLUMNS.items()
        for column, (_, nullable, _) in columns.items()
        if not nullable
    ],
)
def test_db01_required_columns_reject_null(migrated_database, table, column):
    """All approved NOT NULL constraints are enforced by direct SQL, including PKs."""
    with connect(migrated_database.conninfo(APP_ROLE)) as conn:
        _require_schema(conn)
        state = _seed(conn)
        if table == "escritorio":
            values = {"nome": "ESCRITORIO_TESTE_EXTRA", "ativo": True}
        elif table == "usuario":
            values = {
                "nome": "PESSOA_TESTE_EXTRA",
                "identificador_login": "USUARIO_TESTE_EXTRA",
                "ativo": True,
            }
        else:
            values = _values(table, state)
            if "ativo" in COLUMNS[table]:
                values["ativo"] = True
            if table == "cliente":
                values["versao_acesso"] = 0
        _reject(conn, table, {**values, column: None}, psycopg.errors.NotNullViolation)


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


def _base_snapshot(conn):
    return conn.execute(
        "SELECT 'defaults', defaclrole::regrole::text || ':' || defaclobjtype::text || ':' "
        "|| coalesce(defaclnamespace::regnamespace::text, '') || ':' || defaclacl::text "
        "FROM pg_default_acl UNION ALL SELECT 'schema', nspname || ':' || nspacl::text "
        "FROM pg_namespace WHERE nspname = 'public' ORDER BY 1, 2"
    ).fetchall()


def test_db01_migracao_reverte_e_usuario_da_aplicacao_nao_e_dono(fresh_database):
    """c6: preserve base objects/ACLs; restore identical DDL; app has DML but no DROP."""
    _run_alembic(fresh_database, "upgrade", "0001")
    with connect(fresh_database.conninfo(OWNER_ROLE)) as conn:
        base_tables = _tables(conn)
        base_acl = _base_snapshot(conn)
        conn.execute("CREATE TABLE db01_base_probe (id integer PRIMARY KEY, note text)")
        conn.execute("INSERT INTO db01_base_probe VALUES (1, 'SYNTHETIC_BASE')")
    _run_alembic(fresh_database, "upgrade", "0002")
    with connect(fresh_database.conninfo(OWNER_ROLE)) as conn:
        _require_schema(conn)
    before = _catalog(fresh_database)
    _run_alembic(fresh_database, "downgrade", "0001")
    with connect(fresh_database.conninfo(OWNER_ROLE)) as conn:
        assert _tables(conn) == base_tables | {"db01_base_probe"}
        assert conn.execute("SELECT version_num FROM alembic_version").fetchall() == [
            ("0001",)
        ]
        assert _base_snapshot(conn) == base_acl
        assert conn.execute("SELECT * FROM db01_base_probe").fetchall() == [
            (1, "SYNTHETIC_BASE")
        ]
    _run_alembic(fresh_database, "upgrade", "0002")
    assert _catalog(fresh_database) == before
    with connect(fresh_database.conninfo(APP_ROLE)) as conn:
        assert conn.execute("SELECT current_user").fetchone() == (APP_ROLE,)
        assert conn.execute(
            "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
        ).fetchone() == (False, False)
        owners = conn.execute(
            "SELECT tablename, tableowner FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename = ANY(%s)",
            [list(TABLES)],
        ).fetchall()
        assert len(owners) == 7 and all(owner == OWNER_ROLE for _, owner in owners)
        for table in TABLES:
            assert conn.execute(
                sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
            ).fetchone() == (0,)
        state = _seed(conn)
        for table in ("sessao", "convite", "atribuicao"):
            _insert(conn, table, **_values(table, state))
        updates = {
            "escritorio": ("nome", "ESCRITORIO_TESTE_ATUALIZADO"),
            "usuario": ("nome", "PESSOA_TESTE_ATUALIZADA"),
            "membro": ("ativo", False),
            "cliente": ("versao_acesso", 1),
            "sessao": ("encerrada_em", LATER),
            "convite": ("usado_em", LATER),
            "atribuicao": ("fim", LATER),
        }
        for table in TABLES:
            assert (
                conn.execute(
                    sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
                ).fetchone()[0]
                > 0
            )
            column, value = updates[table]
            result = conn.execute(
                sql.SQL("UPDATE {} SET {} = %s RETURNING {}").format(
                    sql.Identifier(table),
                    sql.Identifier(column),
                    sql.Identifier(column),
                ),
                [value],
            ).fetchall()
            assert result and all(row == (value,) for row in result)
        with pytest.raises(psycopg.errors.InsufficientPrivilege), conn.transaction():
            conn.execute("DROP TABLE escritorio")
        for table in reversed(TABLES):
            conn.execute(sql.SQL("DELETE FROM {}").format(sql.Identifier(table)))
            assert conn.execute(
                sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
            ).fetchone() == (0,)


def test_db01_models_share_metadata_and_match_migrated_catalog(migrated_database):
    """Load live models only after reporting missing modules as assertions."""
    paths = ("core", "access", "registry")
    for module in paths:
        path = REPO_ROOT / "src" / "lastro" / module / "models.py"
        assert path.is_file(), f"DB-01 model absent: lastro.{module}.models"
    base = importlib.import_module("lastro.core.models").Base
    access = importlib.import_module("lastro.access.models")
    registry = importlib.import_module("lastro.registry.models")
    classes = (
        access.Firm,
        access.User,
        access.Member,
        access.Session,
        access.Invitation,
        registry.Client,
        access.Assignment,
    )
    assert {model.__tablename__ for model in classes} == set(TABLES)
    catalog = _catalog(migrated_database)
    _assert_catalog(catalog)
    for model in classes:
        assert model.metadata is base.metadata
        assert model.__module__ == (
            "lastro.registry.models"
            if model is registry.Client
            else "lastro.access.models"
        )
        table = model.__table__
        assert set(table.columns.keys()) == set(COLUMNS[table.name])
        assert tuple(column.name for column in table.primary_key) == PKS[table.name]
        for column in table.columns:
            expected_type, nullable, default = COLUMNS[table.name][column.name]
            assert (
                str(
                    column.type.compile(dialect=sa.dialects.postgresql.dialect())
                ).lower()
                == expected_type
            )
            assert column.nullable == nullable
            actual_default = (
                str(column.server_default.arg) if column.server_default else None
            )
            assert _normalize(actual_default) == _normalize(default)
        assert {
            (
                tuple(fk.column_keys),
                fk.referred_table.name,
                tuple(element.column.name for element in fk.elements),
            )
            for fk in table.foreign_key_constraints
        } == FKS[table.name]
        for fk in table.foreign_key_constraints:
            assert fk.ondelete in (None, "NO ACTION")
            assert fk.onupdate in (None, "NO ACTION")
            assert fk.deferrable in (None, False)
            assert fk.initially in (None, "IMMEDIATE")
        expected_constraint_names = {catalog[table.name]["pk"]["name"]}
        for kind in ("fk", "uq", "ck"):
            expected_constraint_names.update(
                item["name"] for item in catalog[table.name][kind]
            )
        assert {item.name for item in table.constraints} == expected_constraint_names
        assert {index.name for index in table.indexes} == {
            item["name"]
            for item in catalog[table.name]["ix"]
            if not item.get("duplicates_constraint")
        }
        assert {
            tuple(c.name for c in item.columns)
            for item in table.constraints
            if isinstance(item, sa.UniqueConstraint)
        } == UNIQUES.get(table.name, set())
        orm_checks = {
            _normalize(str(item.sqltext))
            for item in table.constraints
            if isinstance(item, sa.CheckConstraint)
        }
        db_checks = {_normalize(item["sqltext"]) for item in catalog[table.name]["ck"]}
        # PostgreSQL rewrites IN into ANY; compare the approved semantic fragments above,
        # while other CHECK expressions have a stable normalized representation.
        if table.name != "membro":
            assert orm_checks == db_checks
        else:
            assert len(orm_checks) == 1
            assert all(word in " ".join(orm_checks) for word in CHECKS["membro"])
        actual_indexes = {
            (
                tuple(index.columns.keys()),
                index.unique,
                _normalize(index.dialect_options["postgresql"]["where"]),
            )
            for index in table.indexes
        }
        expected_indexes = {
            (columns, False, "none") for columns in AUXILIARY.get(table.name, set())
        }
        if table.name in PARTIALS:
            columns, predicate = PARTIALS[table.name]
            expected_indexes.add((columns, True, predicate))
        assert actual_indexes == expected_indexes
    assert len(base.metadata.sorted_tables) == 7
    assert {"pk", "fk", "uq", "ck", "ix"} <= base.metadata.naming_convention.keys()


def test_db01_model_import_does_not_connect():
    """A fresh interpreter must import all models without any database connection."""
    for module in ("core", "access", "registry"):
        assert (REPO_ROOT / "src" / "lastro" / module / "models.py").is_file(), (
            f"DB-01 model absent: lastro.{module}.models"
        )
    code = """
import importlib
import socket
import psycopg
import sqlalchemy
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine
def forbidden(*args, **kwargs):
    raise AssertionError("Model import attempted a database/network connection")
socket.socket.connect = forbidden
socket.create_connection = forbidden
psycopg.connect = forbidden
psycopg.Connection.connect = forbidden
psycopg.AsyncConnection.connect = forbidden
Engine.connect = forbidden
AsyncEngine.connect = forbidden
for module in ("lastro.core.models", "lastro.access.models", "lastro.registry.models"):
    importlib.import_module(module)
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, _INFRA.process_output(result)
