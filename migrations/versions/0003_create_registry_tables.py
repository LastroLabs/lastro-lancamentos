"""Create DB-02 registry tables and client accounting configuration.

RLS policies belong to NUC-03 and must precede pilot data.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uuid(name: str, *, nullable: bool = False) -> sa.Column:
    return sa.Column(name, sa.Uuid(), nullable=nullable)


def _id() -> sa.Column:
    return sa.Column(
        "id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")
    )


def _client_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["escritorio_id", "cliente_id"],
        ["cliente.escritorio_id", "cliente.id"],
        name=f"fk_{table}_cliente",
        ondelete="NO ACTION",
        onupdate="NO ACTION",
        deferrable=False,
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
    """Add four client-owned tables and optional current-plan configuration."""
    op.create_table(
        "plano_contas",
        _uuid("escritorio_id"),
        _uuid("cliente_id"),
        _id(),
        sa.Column("versao", sa.Integer(), nullable=False),
        _uuid("importado_por"),
        sa.Column("importado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("publicado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("situacao", sa.Text(), nullable=False),
        _pk("plano_contas"),
        _client_fk("plano_contas"),
        _fk(
            "fk_plano_contas_importado_por_membro",
            ["escritorio_id", "importado_por"],
            ["membro.escritorio_id", "membro.id"],
        ),
        sa.UniqueConstraint(
            "escritorio_id", "cliente_id", "versao", name="uq_plano_contas_versao"
        ),
        sa.CheckConstraint("versao > 0", name="ck_plano_contas_versao"),
        sa.CheckConstraint(
            "situacao IN ('importado', 'publicado', 'substituido')",
            name="ck_plano_contas_situacao",
        ),
    )
    op.create_table(
        "conta_contabil",
        _uuid("escritorio_id"),
        _uuid("cliente_id"),
        _id(),
        _uuid("plano_id"),
        sa.Column("codigo", sa.Text(), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        _uuid("pai_id", nullable=True),
        sa.Column(
            "ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        _pk("conta_contabil"),
        _client_fk("conta_contabil"),
        _fk(
            "fk_conta_contabil_plano",
            ["escritorio_id", "cliente_id", "plano_id"],
            [
                "plano_contas.escritorio_id",
                "plano_contas.cliente_id",
                "plano_contas.id",
            ],
        ),
        _fk(
            "fk_conta_contabil_pai",
            ["escritorio_id", "cliente_id", "plano_id", "pai_id"],
            [
                "conta_contabil.escritorio_id",
                "conta_contabil.cliente_id",
                "conta_contabil.plano_id",
                "conta_contabil.id",
            ],
        ),
        sa.UniqueConstraint(
            "escritorio_id",
            "cliente_id",
            "plano_id",
            "codigo",
            name="uq_conta_contabil_plano_codigo",
        ),
        sa.UniqueConstraint(
            "escritorio_id",
            "cliente_id",
            "plano_id",
            "id",
            name="uq_conta_contabil_plano_id",
        ),
    )
    op.create_table(
        "conta_bancaria",
        _uuid("escritorio_id"),
        _uuid("cliente_id"),
        _id(),
        sa.Column("banco", sa.Text(), nullable=False),
        sa.Column("apelido", sa.Text(), nullable=False),
        sa.Column("identificacao_protegida", sa.Text(), nullable=True),
        sa.Column("moeda", sa.Text(), nullable=False, server_default=sa.text("'BRL'")),
        _uuid("conta_contabil_id", nullable=True),
        sa.Column("cobertura_inicio", sa.Date(), nullable=True),
        sa.Column("cobertura_fim", sa.Date(), nullable=True),
        _pk("conta_bancaria"),
        _client_fk("conta_bancaria"),
        _fk(
            "fk_conta_bancaria_conta_contabil",
            ["escritorio_id", "cliente_id", "conta_contabil_id"],
            [
                "conta_contabil.escritorio_id",
                "conta_contabil.cliente_id",
                "conta_contabil.id",
            ],
        ),
        sa.CheckConstraint(
            "cobertura_fim IS NULL OR cobertura_inicio IS NULL OR "
            "cobertura_fim >= cobertura_inicio",
            name="ck_conta_bancaria_cobertura",
        ),
    )
    op.create_table(
        "socio",
        _uuid("escritorio_id"),
        _uuid("cliente_id"),
        _id(),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("nome_normalizado", sa.Text(), nullable=False),
        sa.Column(
            "ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        _pk("socio"),
        _client_fk("socio"),
    )
    for column in (
        "plano_atual_id",
        "conta_transitoria_id",
        "conta_entrada_socio_id",
        "conta_saida_socio_id",
    ):
        op.add_column("cliente", _uuid(column, nullable=True))
    op.create_foreign_key(
        "fk_cliente_plano_atual",
        "cliente",
        "plano_contas",
        ["escritorio_id", "id", "plano_atual_id"],
        ["escritorio_id", "cliente_id", "id"],
        ondelete="NO ACTION",
        onupdate="NO ACTION",
        deferrable=False,
    )
    for column in (
        "conta_transitoria_id",
        "conta_entrada_socio_id",
        "conta_saida_socio_id",
    ):
        op.create_foreign_key(
            f"fk_cliente_{column}",
            "cliente",
            "conta_contabil",
            ["escritorio_id", "id", "plano_atual_id", column],
            ["escritorio_id", "cliente_id", "plano_id", "id"],
            ondelete="NO ACTION",
            onupdate="NO ACTION",
            deferrable=False,
        )
        op.create_check_constraint(
            f"ck_cliente_{column}_plano",
            "cliente",
            f"{column} IS NULL OR plano_atual_id IS NOT NULL",
        )


def downgrade() -> None:
    """Remove only DB-02 objects, preserving DB-01 tables and their rows."""
    for column in (
        "conta_saida_socio_id",
        "conta_entrada_socio_id",
        "conta_transitoria_id",
    ):
        op.drop_constraint(f"ck_cliente_{column}_plano", "cliente", type_="check")
        op.drop_constraint(f"fk_cliente_{column}", "cliente", type_="foreignkey")
    op.drop_constraint("fk_cliente_plano_atual", "cliente", type_="foreignkey")
    for column in (
        "conta_saida_socio_id",
        "conta_entrada_socio_id",
        "conta_transitoria_id",
        "plano_atual_id",
    ):
        op.drop_column("cliente", column)
    for table in ("socio", "conta_bancaria", "conta_contabil", "plano_contas"):
        op.drop_table(table)
