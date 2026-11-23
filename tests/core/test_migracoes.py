"""NUC-01 c5: Alembic migrations and the two database roles.

Each test gets a new empty database (fixture `fresh_database`) inside the disposable
PostgreSQL 18 of the session. Migrations run as `lastro_owner` through
MIGRATIONS_DATABASE_URL; the application connects as `lastro_app` (plan D5, D7, D8).
Function names follow features/NUC-01.json. Only invented names (probe tables).
"""

import importlib
import secrets

import pytest
from conftest import (
    APP_ROLE,
    OWNER_ROLE,
    REPO_ROOT,
    SUPERUSER,
    connect,
    process_output,
    run_alembic_upgrade,
)

# Snapshot of everything a migration may touch: tables, default privileges, schema ACL
# and the recorded revision. If a re-run "applies nothing", the snapshot does not change.
SNAPSHOT_SQL = """
SELECT 'table', schemaname || '.' || tablename FROM pg_tables
 WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
UNION ALL
SELECT 'default_acl', defaclrole::regrole::text || ':' || defaclobjtype || ':'
       || coalesce(defaclnamespace::regnamespace::text, '') || ':' || defaclacl::text
  FROM pg_default_acl
UNION ALL
SELECT 'schema_acl', nspname || ':' || coalesce(nspacl::text, '') FROM pg_namespace
 WHERE nspname = 'public'
ORDER BY 1, 2
"""


def _head_revision():
    assert (REPO_ROOT / "alembic.ini").is_file(), "missing alembic.ini (T5)"
    alembic_config = importlib.import_module("alembic.config")
    alembic_script = importlib.import_module("alembic.script")
    config = alembic_config.Config(str(REPO_ROOT / "alembic.ini"))
    head = alembic_script.ScriptDirectory.from_config(config).get_current_head()
    assert head is not None, "alembic has no migration (expected 0001_base_privileges, plan D8)"
    return head


def _alembic_version_table_exists(database):
    with connect(database.conninfo(OWNER_ROLE)) as conn:
        return conn.execute("SELECT to_regclass('public.alembic_version')").fetchone()[0] is not None


def _recorded_revisions(database):
    with connect(database.conninfo(OWNER_ROLE)) as conn:
        return [row[0] for row in conn.execute("SELECT version_num FROM alembic_version")]


def _snapshot(database):
    with connect(database.conninfo(SUPERUSER)) as conn:
        return conn.execute(SNAPSHOT_SQL).fetchall()


def _assert_upgrade_ok(result, attempt):
    assert result.returncode == 0, (
        f"alembic upgrade head failed on attempt {attempt}:\n{process_output(result)}"
    )


def test_migracoes_em_banco_vazio_chegam_a_ultima_versao(fresh_database):
    head = _head_revision()
    assert not _alembic_version_table_exists(fresh_database), "the database should start empty"

    _assert_upgrade_ok(run_alembic_upgrade(fresh_database), attempt=1)

    assert _recorded_revisions(fresh_database) == [head]


def test_migracoes_reaplicadas_nao_mudam_nada(fresh_database):
    head = _head_revision()
    _assert_upgrade_ok(run_alembic_upgrade(fresh_database), attempt=1)
    before = _snapshot(fresh_database)
    assert ("table", "public.alembic_version") in before, "snapshot did not see the migrations"

    _assert_upgrade_ok(run_alembic_upgrade(fresh_database), attempt=2)

    assert _recorded_revisions(fresh_database) == [head]
    assert _snapshot(fresh_database) == before


def test_usuario_da_aplicacao_nao_e_superusuario_nem_dono(migrated_database):
    psycopg = importlib.import_module("psycopg")
    sql = psycopg.sql
    probe = f"probe_{secrets.token_hex(4)}"

    with connect(migrated_database.conninfo(SUPERUSER)) as conn:
        roles = {
            row[0]: row[1:]
            for row in conn.execute(
                "SELECT rolname, rolsuper, rolbypassrls, rolcreaterole, rolcreatedb"
                " FROM pg_roles WHERE rolname = ANY(%s)",
                [[OWNER_ROLE, APP_ROLE]],
            )
        }
        db_owner = conn.execute(
            "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = %s",
            [migrated_database.name],
        ).fetchone()[0]
    assert set(roles) == {OWNER_ROLE, APP_ROLE}
    for role, (is_super, bypass_rls, create_role, create_db) in roles.items():
        assert not is_super, f"{role} must not be superuser"
        assert not bypass_rls, f"{role} must not have BYPASSRLS"
        assert not create_role, f"{role} must not have CREATEROLE"
        assert not create_db, f"{role} must not have CREATEDB"
    assert db_owner == OWNER_ROLE

    # A table created by the owner after the migrations (as a future migration would).
    with connect(migrated_database.conninfo(OWNER_ROLE)) as conn:
        conn.execute(
            sql.SQL("CREATE TABLE {} (id integer PRIMARY KEY, note text)").format(
                sql.Identifier(probe)
            )
        )

    with connect(migrated_database.conninfo(APP_ROLE)) as conn:
        assert conn.execute("SELECT current_user").fetchone()[0] == APP_ROLE
        table = sql.Identifier(probe)
        conn.execute(sql.SQL("INSERT INTO {} VALUES (1, 'a')").format(table))
        conn.execute(sql.SQL("UPDATE {} SET note = 'b' WHERE id = 1").format(table))
        assert conn.execute(sql.SQL("SELECT note FROM {}").format(table)).fetchall() == [("b",)]
        conn.execute(sql.SQL("DELETE FROM {} WHERE id = 1").format(table))

        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("CREATE TABLE app_should_not_create (id integer)")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(sql.SQL("DROP TABLE {}").format(table))
