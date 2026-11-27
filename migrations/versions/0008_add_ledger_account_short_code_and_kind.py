"""Short code and kind (S or A) on the ledger account (DB-04, DECISIONS T6).

The accounting program gives each account a short code, the code the export uses (D-05),
and says whether it is a group (`S`, synthetic) or receives entries (`A`, analytic). The
short code is unique within one plan version; NULLs never clash, so a plain `UNIQUE` is
enough. Existing accounts become `A`, without a short code.

The format of the short code is checked when the TXT is read (CAD-02), not here (plan D4).
Row-level security and privileges are per table (0001, 0005), so the new columns are
already covered.

Downgrade drops the two columns, and with them every short code and kind stored.

Revision ID: 0008
Revises: 0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "conta_contabil"
CHECK_KIND = "ck_conta_contabil_tipo"
UNIQUE_SHORT_CODE = "uq_conta_contabil_plano_reduzido"


def upgrade() -> None:
    """Add the short code and the kind, with their check and unique key."""
    op.add_column(TABLE, sa.Column("codigo_reduzido", sa.Text(), nullable=True))
    op.add_column(
        TABLE,
        sa.Column("tipo", sa.Text(), nullable=False, server_default=sa.text("'A'")),
    )
    op.create_check_constraint(CHECK_KIND, TABLE, "tipo IN ('S', 'A')")
    op.create_unique_constraint(
        UNIQUE_SHORT_CODE,
        TABLE,
        ["escritorio_id", "cliente_id", "plano_id", "codigo_reduzido"],
    )


def downgrade() -> None:
    """Drop only what the upgrade added."""
    op.drop_constraint(UNIQUE_SHORT_CODE, TABLE, type_="unique")
    op.drop_constraint(CHECK_KIND, TABLE, type_="check")
    op.drop_column(TABLE, "tipo")
    op.drop_column(TABLE, "codigo_reduzido")
