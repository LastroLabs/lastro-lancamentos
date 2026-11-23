"""DB-02 schema contract on disposable PostgreSQL with fictional records."""

import importlib
import os
import re
import subprocess
import sys
from datetime import UTC, datetime

import psycopg
import pytest
import sqlalchemy as sa
from psycopg import sql

_INFRA = sys.modules["_lastro_db02_core_fixtures"]
APP_ROLE = _INFRA.APP_ROLE
OWNER_ROLE = _INFRA.OWNER_ROLE
REPO_ROOT = _INFRA.REPO_ROOT
connect = _INFRA.connect

TABLES = ("plano_contas", "conta_contabil", "conta_bancaria", "socio")
CLIENT_COLUMNS = {
    "plano_atual_id",
    "conta_transitoria_id",
    "conta_entrada_socio_id",
    "conta_saida_socio_id",
}
COLUMNS = {
    "plano_contas": {
        "escritorio_id": ("uuid", False, None),
        "cliente_id": ("uuid", False, None),
        "id": ("uuid", False, "gen_random_uuid()"),
        "versao": ("integer", False, None),
        "importado_por": ("uuid", False, None),
        "importado_em": ("timestamp with time zone", False, None),
        "publicado_em": ("timestamp with time zone", True, None),
        "situacao": ("text", False, None),
    },
    "conta_contabil": {
        "escritorio_id": ("uuid", False, None),
        "cliente_id": ("uuid", False, None),
        "id": ("uuid", False, "gen_random_uuid()"),
        "plano_id": ("uuid", False, None),
        "codigo": ("text", False, None),
        "nome": ("text", False, None),
        "pai_id": ("uuid", True, None),
        "ativo": ("boolean", False, "true"),
    },
    "conta_bancaria": {
        "escritorio_id": ("uuid", False, None),
        "cliente_id": ("uuid", False, None),
        "id": ("uuid", False, "gen_random_uuid()"),
        "banco": ("text", False, None),
        "apelido": ("text", False, None),
        "identificacao_protegida": ("text", True, None),
        "moeda": ("text", False, "'BRL'::text"),
        "conta_contabil_id": ("uuid", True, None),
        "cobertura_inicio": ("date", True, None),
        "cobertura_fim": ("date", True, None),
    },
    "socio": {
        "escritorio_id": ("uuid", False, None),
        "cliente_id": ("uuid", False, None),
        "id": ("uuid", False, "gen_random_uuid()"),
        "nome": ("text", False, None),
        "nome_normalizado": ("text", False, None),
        "ativo": ("boolean", False, "true"),
    },
}
FKS = {
    "plano_contas": {
        (("escritorio_id", "cliente_id"), "cliente", ("escritorio_id", "id")),
        (("escritorio_id", "importado_por"), "membro", ("escritorio_id", "id")),
    },
    "conta_contabil": {
        (("escritorio_id", "cliente_id"), "cliente", ("escritorio_id", "id")),
        (
            ("escritorio_id", "cliente_id", "plano_id"),
            "plano_contas",
            ("escritorio_id", "cliente_id", "id"),
        ),
        (
            ("escritorio_id", "cliente_id", "plano_id", "pai_id"),
            "conta_contabil",
            ("escritorio_id", "cliente_id", "plano_id", "id"),
        ),
    },
    "conta_bancaria": {
        (("escritorio_id", "cliente_id"), "cliente", ("escritorio_id", "id")),
        (
            ("escritorio_id", "cliente_id", "conta_contabil_id"),
            "conta_contabil",
            ("escritorio_id", "cliente_id", "id"),
        ),
    },
    "socio": {
        (("escritorio_id", "cliente_id"), "cliente", ("escritorio_id", "id")),
    },
}


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


def _insert(conn, table, **values):
    query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING id").format(
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, values)),
        sql.SQL(", ").join(sql.Placeholder() for _ in values),
    )
    return conn.execute(query, list(values.values())).fetchone()[0]


def _reject(conn, error, statement, params):
    with pytest.raises(error), conn.transaction():
        conn.execute(statement, params)


def _seed(conn):
    firm = _insert(conn, "escritorio", nome="ESCRITORIO_TESTE_DB02")
    user = _insert(
        conn,
        "usuario",
        identificador_login="USUARIO_TESTE_DB02",
        nome="PESSOA_TESTE_DB02",
    )
    member = _insert(
        conn, "membro", escritorio_id=firm, usuario_id=user, papel="contador"
    )
    clients = [
        _insert(
            conn,
            "cliente",
            escritorio_id=firm,
            nome=f"CLIENTE_TESTE_DB02_{number}",
            cnpj_normalizado=f"11122233000{number}00",
        )
        for number in (1, 2)
    ]
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


def _account(conn, firm, client, plan, code, *, parent=None):
    return _insert(
        conn,
        "conta_contabil",
        escritorio_id=firm,
        cliente_id=client,
        plano_id=plan,
        codigo=code,
        nome=f"CONTA_TESTE_{code}",
        pai_id=parent,
    )


def _bank(conn, firm, client, account=None, code="001"):
    return _insert(
        conn,
        "conta_bancaria",
        escritorio_id=firm,
        cliente_id=client,
        banco=code,
        apelido="CONTA_MOVIMENTO_TESTE",
        conta_contabil_id=account,
    )


def _fks(inspector, table):
    return {
        (
            tuple(fk["constrained_columns"]),
            fk["referred_table"],
            tuple(fk["referred_columns"]),
        )
        for fk in inspector.get_foreign_keys(table)
    }


def _normalize(value):
    return re.sub(r"[\s()\"]", "", str(value).lower())


def test_migracao_db02_cria_tabelas_de_cadastro_com_colunas_e_chaves(migrated_database):
    """c1: inspect all four tables and their client and plan references."""
    engine = sa.create_engine(migrated_database.migrations_database_url)
    try:
        inspector = sa.inspect(engine)
        assert set(TABLES) <= set(inspector.get_table_names())
        for table in TABLES:
            actual = {
                col["name"]: (str(col["type"]).lower(), col["nullable"], col["default"])
                for col in inspector.get_columns(table)
            }
            assert actual == COLUMNS[table], table
            assert tuple(inspector.get_pk_constraint(table)["constrained_columns"]) == (
                "escritorio_id",
                "cliente_id",
                "id",
            )
            assert _fks(inspector, table) == FKS[table]
        unique = {
            tuple(item["column_names"])
            for item in inspector.get_unique_constraints("conta_contabil")
        }
        assert ("escritorio_id", "cliente_id", "plano_id", "codigo") in unique
        assert ("escritorio_id", "cliente_id", "plano_id", "id") in unique
        assert ("escritorio_id", "cliente_id", "versao") in {
            tuple(item["column_names"])
            for item in inspector.get_unique_constraints("plano_contas")
        }
        client_cols = {col["name"]: col for col in inspector.get_columns("cliente")}
        assert CLIENT_COLUMNS <= client_cols.keys()
        assert all(
            str(client_cols[name]["type"]).lower() == "uuid"
            and client_cols[name]["nullable"]
            for name in CLIENT_COLUMNS
        )
        client_fks = _fks(inspector, "cliente")
        assert (
            ("escritorio_id", "id", "plano_atual_id"),
            "plano_contas",
            ("escritorio_id", "cliente_id", "id"),
        ) in client_fks
        for name in CLIENT_COLUMNS - {"plano_atual_id"}:
            assert (
                ("escritorio_id", "id", "plano_atual_id", name),
                "conta_contabil",
                ("escritorio_id", "cliente_id", "plano_id", "id"),
            ) in client_fks
        checks = {
            table: " ".join(
                _normalize(item["sqltext"])
                for item in inspector.get_check_constraints(table)
            )
            for table in TABLES
        }
        assert "versao>0" in checks["plano_contas"]
        assert all(
            word in checks["plano_contas"]
            for word in ("situacao", "importado", "publicado", "substituido")
        )
        assert "cobertura_fim" in checks["conta_bancaria"]
        registry = importlib.import_module("lastro.registry.models")
        assert {
            model.__tablename__
            for model in (
                registry.BankAccount,
                registry.Partner,
                registry.ChartOfAccounts,
                registry.LedgerAccount,
            )
        } == set(TABLES)
    finally:
        engine.dispose()


def test_db02_conta_contabil_nao_cruza_cliente_nem_plano(migrated_database):
    """c2: compound foreign keys reject cross-client and cross-plan references."""
    with connect(migrated_database.conninfo(APP_ROLE)) as conn:
        firm, member, (first, second) = _seed(conn)
        first_plan = _plan(conn, firm, first, member, 1)
        second_plan = _plan(conn, firm, second, member, 1)
        second_account = _account(conn, firm, second, second_plan, "9.9.99")
        first_account = _account(conn, firm, first, first_plan, "1.1.01")
        _reject(
            conn,
            psycopg.errors.ForeignKeyViolation,
            "INSERT INTO conta_contabil (escritorio_id, cliente_id, plano_id, codigo, nome) VALUES (%s, %s, %s, 'X', 'CONTA_TESTE')",
            (firm, first, second_plan),
        )
        _reject(
            conn,
            psycopg.errors.ForeignKeyViolation,
            "INSERT INTO conta_contabil (escritorio_id, cliente_id, plano_id, codigo, nome, pai_id) VALUES (%s, %s, %s, '1.1.01.001', 'CONTA_TESTE', %s)",
            (firm, first, first_plan, second_account),
        )
        _reject(
            conn,
            psycopg.errors.ForeignKeyViolation,
            "INSERT INTO conta_bancaria (escritorio_id, cliente_id, banco, apelido, conta_contabil_id) VALUES (%s, %s, '001', 'CONTA_TESTE', %s)",
            (firm, first, second_account),
        )
        _reject(
            conn,
            psycopg.errors.UniqueViolation,
            "INSERT INTO conta_contabil (escritorio_id, cliente_id, plano_id, codigo, nome) VALUES (%s, %s, %s, '1.1.01', 'REPETIDA_TESTE')",
            (firm, first, first_plan),
        )
        second_version = _plan(conn, firm, first, member, 2)
        later_account = _account(conn, firm, first, second_version, "1.1.01")
        assert later_account != first_account
        _reject(
            conn,
            psycopg.errors.ForeignKeyViolation,
            "INSERT INTO conta_contabil (escritorio_id, cliente_id, plano_id, codigo, nome, pai_id) VALUES (%s, %s, %s, '1.1.01.002', 'CONTA_TESTE', %s)",
            (firm, first, first_plan, later_account),
        )


def test_db02_contas_de_configuracao_sao_do_plano_atual(migrated_database):
    """c3: client configuration must use its current plan and own accounts."""
    with connect(migrated_database.conninfo(APP_ROLE)) as conn:
        firm, member, (first, second) = _seed(conn)
        old_plan = _plan(conn, firm, first, member, 1)
        new_plan = _plan(conn, firm, first, member, 2)
        foreign_plan = _plan(conn, firm, second, member, 1)
        old_account = _account(conn, firm, first, old_plan, "9.9.99")
        new_account = _account(conn, firm, first, new_plan, "1.1.01")
        foreign_account = _account(conn, firm, second, foreign_plan, "2.2.02")
        where = (firm, first)
        _reject(
            conn,
            psycopg.errors.ForeignKeyViolation,
            "UPDATE cliente SET plano_atual_id = %s WHERE escritorio_id = %s AND id = %s",
            (foreign_plan, *where),
        )
        conn.execute(
            "UPDATE cliente SET plano_atual_id = %s, conta_transitoria_id = %s WHERE escritorio_id = %s AND id = %s",
            (old_plan, old_account, *where),
        )
        _reject(
            conn,
            psycopg.errors.ForeignKeyViolation,
            "UPDATE cliente SET plano_atual_id = %s WHERE escritorio_id = %s AND id = %s",
            (new_plan, *where),
        )
        assert conn.execute(
            "SELECT plano_atual_id, conta_transitoria_id FROM cliente WHERE escritorio_id = %s AND id = %s",
            where,
        ).fetchone() == (old_plan, old_account)
        _reject(
            conn,
            psycopg.errors.ForeignKeyViolation,
            "UPDATE cliente SET conta_entrada_socio_id = %s WHERE escritorio_id = %s AND id = %s",
            (foreign_account, *where),
        )
        conn.execute(
            "UPDATE cliente SET plano_atual_id = %s, conta_transitoria_id = NULL, conta_entrada_socio_id = %s, conta_saida_socio_id = %s WHERE escritorio_id = %s AND id = %s",
            (new_plan, new_account, new_account, *where),
        )
        assert conn.execute(
            "SELECT plano_atual_id, conta_transitoria_id FROM cliente WHERE escritorio_id = %s AND id = %s",
            where,
        ).fetchone() == (new_plan, None)
        _reject(
            conn,
            psycopg.errors.CheckViolation,
            "UPDATE cliente SET plano_atual_id = NULL WHERE escritorio_id = %s AND id = %s",
            where,
        )


def test_db02_codigos_em_texto_e_migracao_reversivel(fresh_database):
    """c4: preserve text codes and all DB-01 data across DB-02 downgrade."""
    _run_alembic(fresh_database, "upgrade", "0002")
    with connect(fresh_database.conninfo(APP_ROLE)) as conn:
        firm, member, clients = _seed(conn)
    _run_alembic(fresh_database, "upgrade", "head")
    with connect(fresh_database.conninfo(APP_ROLE)) as conn:
        plan = _plan(conn, firm, clients[0], member, 1)
        account = _account(conn, firm, clients[0], plan, "01.002.0003")
        bank = _bank(conn, firm, clients[0], account, "001")
        assert conn.execute(
            "SELECT codigo FROM conta_contabil WHERE id = %s", (account,)
        ).fetchone() == ("01.002.0003",)
        assert conn.execute(
            "SELECT banco FROM conta_bancaria WHERE id = %s", (bank,)
        ).fetchone() == ("001",)
    _run_alembic(fresh_database, "downgrade", "0002")
    with connect(fresh_database.conninfo(OWNER_ROLE)) as conn:
        assert conn.execute("SELECT version_num FROM alembic_version").fetchone() == (
            "0002",
        )
        assert all(
            conn.execute("SELECT to_regclass(%s)", (f"public.{table}",)).fetchone()[0]
            is None
            for table in TABLES
        )
        assert set(CLIENT_COLUMNS).isdisjoint(
            {
                row[0]
                for row in conn.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'cliente'"
                )
            }
        )
        assert conn.execute("SELECT id FROM escritorio").fetchall() == [(firm,)]
        assert {row[0] for row in conn.execute("SELECT id FROM cliente")} == set(
            clients
        )
        assert conn.execute("SELECT id FROM membro").fetchall() == [(member,)]
    _run_alembic(fresh_database, "upgrade", "head")
    with connect(fresh_database.conninfo(OWNER_ROLE)) as conn:
        assert all(
            conn.execute("SELECT to_regclass(%s)", (f"public.{table}",)).fetchone()[0]
            is not None
            for table in TABLES
        )
