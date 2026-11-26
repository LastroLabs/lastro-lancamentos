"""Create DB-03 competencia and link_cliente tables.

The link stores only the hash of its code. RLS policies belong to NUC-03 and must
precede pilot data; the hash lookup without a firm in context is NUC-03's concern.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uuid(name: str, *, nullable: bool = False) -> sa.Column:
    return sa.Column(name, sa.Uuid(), nullable=nullable)


def _id() -> sa.Column:
    return sa.Column(
        "id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")
    )


def _fk(
    name: str, columns: list[str], references: list[str]
) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        columns,
        references,
        name=name,
        ondelete="NO ACTION",
        onupdate="NO ACTION",
        deferrable=False,
    )


def _pk(table: str) -> sa.PrimaryKeyConstraint:
    return sa.PrimaryKeyConstraint(
        "escritorio_id", "cliente_id", "id", name=f"pk_{table}"
    )


def upgrade() -> None:
    """Add the monthly period per client and its hashed upload link."""
    op.create_table(
        "competencia",
        _uuid("escritorio_id"),
        _uuid("cliente_id"),
        _id(),
        sa.Column("mes", sa.Date(), nullable=False),
        sa.Column(
            "versao_conjunto",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "criada_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        _pk("competencia"),
        _fk(
            "fk_competencia_escritorio_id_cliente_id_cliente",
            ["escritorio_id", "cliente_id"],
            ["cliente.escritorio_id", "cliente.id"],
        ),
        sa.UniqueConstraint(
            "escritorio_id",
            "cliente_id",
            "mes",
            name="uq_competencia_escritorio_id_cliente_id_mes",
        ),
        # D3: explicit timestamp cast keeps the rule independent of the TimeZone.
        sa.CheckConstraint(
            "mes = date_trunc('month', mes::timestamp)",
            name="ck_competencia_primeiro_dia",
        ),
        sa.CheckConstraint(
            "versao_conjunto >= 0", name="ck_competencia_versao_conjunto"
        ),
    )
    op.create_table(
        "link_cliente",
        _uuid("escritorio_id"),
        _uuid("cliente_id"),
        _id(),
        _uuid("competencia_id"),
        sa.Column("hash_token", sa.Text(), nullable=False),
        _uuid("criado_por"),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revogado_em", sa.DateTime(timezone=True), nullable=True),
        _pk("link_cliente"),
        # D4: the D2 name would have 67 characters.
        _fk(
            "fk_link_cliente_competencia",
            ["escritorio_id", "cliente_id", "competencia_id"],
            [
                "competencia.escritorio_id",
                "competencia.cliente_id",
                "competencia.id",
            ],
        ),
        _fk(
            "fk_link_cliente_escritorio_id_criado_por_membro",
            ["escritorio_id", "criado_por"],
            ["membro.escritorio_id", "membro.id"],
        ),
        sa.UniqueConstraint("hash_token", name="uq_link_cliente_hash_token"),
        sa.CheckConstraint(
            "hash_token ~ '^[0-9a-f]{64}$'", name="ck_link_cliente_hash_token"
        ),
        sa.CheckConstraint("expira_em > criado_em", name="ck_link_cliente_validade"),
        sa.CheckConstraint(
            "revogado_em IS NULL OR revogado_em >= criado_em",
            name="ck_link_cliente_revogacao",
        ),
    )
    op.create_index(
        "ix_link_cliente_escritorio_id_cliente_id_competencia_id",
        "link_cliente",
        ["escritorio_id", "cliente_id", "competencia_id"],
    )
    op.create_index(
        "ix_link_cliente_escritorio_id_criado_por",
        "link_cliente",
        ["escritorio_id", "criado_por"],
    )


def downgrade() -> None:
    """Remove only DB-03 tables, preserving DB-01 and DB-02 rows."""
    op.drop_table("link_cliente")
    op.drop_table("competencia")
