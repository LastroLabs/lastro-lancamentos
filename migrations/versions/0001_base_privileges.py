"""Base privileges of the application role (plan NUC-01, D8).

Every table and sequence that lastro_owner creates in the public schema from now on is
readable and writable by lastro_app, which keeps no right to create, alter or drop objects.
No business table here.

Revision ID: 0001
Revises:
Create Date: 2026-11-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Grant lastro_app the use of the schema and default row privileges."""
    op.execute("GRANT USAGE ON SCHEMA public TO lastro_app")
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE lastro_owner IN SCHEMA public"
        " GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO lastro_app"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE lastro_owner IN SCHEMA public"
        " GRANT USAGE ON SEQUENCES TO lastro_app"
    )


def downgrade() -> None:
    """Revoke what upgrade() granted."""
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE lastro_owner IN SCHEMA public"
        " REVOKE USAGE ON SEQUENCES FROM lastro_app"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE lastro_owner IN SCHEMA public"
        " REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM lastro_app"
    )
    op.execute("REVOKE USAGE ON SCHEMA public FROM lastro_app")
