"""Create DB-01 identity and portfolio constraints.

RLS policies belong to NUC-03 and are required before pilot data may be used.
This revision intentionally depends only on its own historical DDL.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id() -> sa.Column:
    return sa.Column(
        "id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")
    )


def _uuid(name: str) -> sa.Column:
    return sa.Column(name, sa.Uuid(), nullable=False)


def _instant(name: str, *, nullable: bool = False) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=nullable)


def _active() -> sa.Column:
    return sa.Column(
        "ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")
    )


def _fk(
    table: str, columns: list[str], target: str, references: list[str]
) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        columns,
        [f"{target}.{column}" for column in references],
        name=f"fk_{table}_{'_'.join(columns)}_{target}",
        ondelete="NO ACTION",
        onupdate="NO ACTION",
        deferrable=False,
    )


def upgrade() -> None:
    """Create seven empty tables, inheriting the base revision's app privileges."""
    op.create_table(
        "escritorio",
        _id(),
        sa.Column("nome", sa.Text(), nullable=False),
        _active(),
        sa.PrimaryKeyConstraint("id", name="pk_escritorio"),
    )
    op.create_table(
        "usuario",
        _id(),
        sa.Column("identificador_login", sa.Text(), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        _active(),
        sa.Column("credencial_hash", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_usuario"),
        sa.UniqueConstraint(
            "identificador_login", name="uq_usuario_identificador_login"
        ),
    )
    op.create_table(
        "membro",
        _uuid("escritorio_id"),
        _id(),
        _uuid("usuario_id"),
        sa.Column("papel", sa.Text(), nullable=False),
        _active(),
        sa.PrimaryKeyConstraint("escritorio_id", "id", name="pk_membro"),
        _fk("membro", ["escritorio_id"], "escritorio", ["id"]),
        _fk("membro", ["usuario_id"], "usuario", ["id"]),
        sa.UniqueConstraint(
            "escritorio_id", "usuario_id", name="uq_membro_escritorio_id_usuario_id"
        ),
        sa.CheckConstraint("papel IN ('chefe', 'contador')", name="ck_membro_papel"),
    )
    op.create_table(
        "cliente",
        _uuid("escritorio_id"),
        _id(),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("cnpj_normalizado", sa.Text(), nullable=False),
        _active(),
        sa.Column(
            "versao_acesso",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.PrimaryKeyConstraint("escritorio_id", "id", name="pk_cliente"),
        _fk("cliente", ["escritorio_id"], "escritorio", ["id"]),
        sa.UniqueConstraint(
            "escritorio_id",
            "cnpj_normalizado",
            name="uq_cliente_escritorio_id_cnpj_normalizado",
        ),
        sa.CheckConstraint("versao_acesso >= 0", name="ck_cliente_versao_acesso"),
    )
    op.create_table(
        "sessao",
        _uuid("escritorio_id"),
        _id(),
        _uuid("membro_id"),
        sa.Column("hash_token", sa.Text(), nullable=False),
        _instant("criada_em"),
        _instant("expira_em"),
        _instant("encerrada_em", nullable=True),
        sa.PrimaryKeyConstraint("escritorio_id", "id", name="pk_sessao"),
        _fk(
            "sessao", ["escritorio_id", "membro_id"], "membro", ["escritorio_id", "id"]
        ),
        sa.UniqueConstraint("hash_token", name="uq_sessao_hash_token"),
        sa.CheckConstraint("expira_em > criada_em", name="ck_sessao_validade"),
    )
    op.create_table(
        "convite",
        _uuid("escritorio_id"),
        _id(),
        _uuid("membro_id"),
        sa.Column("hash_token", sa.Text(), nullable=False),
        _uuid("criado_por"),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        _instant("expira_em"),
        _instant("usado_em", nullable=True),
        _instant("revogado_em", nullable=True),
        sa.PrimaryKeyConstraint("escritorio_id", "id", name="pk_convite"),
        _fk(
            "convite", ["escritorio_id", "membro_id"], "membro", ["escritorio_id", "id"]
        ),
        _fk(
            "convite",
            ["escritorio_id", "criado_por"],
            "membro",
            ["escritorio_id", "id"],
        ),
        sa.UniqueConstraint("hash_token", name="uq_convite_hash_token"),
        sa.CheckConstraint(
            "hash_token ~ '^[0-9a-f]{64}$'", name="ck_convite_hash_token"
        ),
        sa.CheckConstraint("expira_em > criado_em", name="ck_convite_validade"),
        sa.CheckConstraint(
            "usado_em IS NULL OR revogado_em IS NULL", name="ck_convite_uso_revogacao"
        ),
    )
    op.create_table(
        "atribuicao",
        _uuid("escritorio_id"),
        _uuid("cliente_id"),
        _id(),
        _uuid("membro_id"),
        _uuid("atribuido_por"),
        _instant("inicio"),
        _instant("fim", nullable=True),
        sa.PrimaryKeyConstraint(
            "escritorio_id", "cliente_id", "id", name="pk_atribuicao"
        ),
        _fk(
            "atribuicao",
            ["escritorio_id", "cliente_id"],
            "cliente",
            ["escritorio_id", "id"],
        ),
        _fk(
            "atribuicao",
            ["escritorio_id", "membro_id"],
            "membro",
            ["escritorio_id", "id"],
        ),
        _fk(
            "atribuicao",
            ["escritorio_id", "atribuido_por"],
            "membro",
            ["escritorio_id", "id"],
        ),
        sa.CheckConstraint(
            "fim IS NULL OR fim > inicio", name="ck_atribuicao_intervalo"
        ),
    )
    for table, columns in (
        ("membro", ["usuario_id"]),
        ("sessao", ["escritorio_id", "membro_id"]),
        ("convite", ["escritorio_id", "membro_id"]),
        ("convite", ["escritorio_id", "criado_por"]),
        ("atribuicao", ["escritorio_id", "membro_id"]),
        ("atribuicao", ["escritorio_id", "atribuido_por"]),
    ):
        op.create_index(f"ix_{table}_{'_'.join(columns)}", table, columns)
    op.create_index(
        "ix_atribuicao_escritorio_id_cliente_id",
        "atribuicao",
        ["escritorio_id", "cliente_id"],
        unique=True,
        postgresql_where=sa.text("fim IS NULL"),
    )
    op.create_index(
        "uq_convite_escritorio_id_membro_id_pendente",
        "convite",
        ["escritorio_id", "membro_id"],
        unique=True,
        postgresql_where=sa.text("usado_em IS NULL AND revogado_em IS NULL"),
    )


def downgrade() -> None:
    """Drop only DB-01 tables, dependents first, preserving base privileges."""
    for table in (
        "atribuicao",
        "convite",
        "sessao",
        "cliente",
        "membro",
        "usuario",
        "escritorio",
    ):
        op.drop_table(table)
