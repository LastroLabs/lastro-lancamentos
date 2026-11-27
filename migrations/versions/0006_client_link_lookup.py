"""Lookup of the client link by its code, before the firm is known (NUC-03, c8).

The client opens the link without signing in, so the API must learn the firm from the code
itself. `link_cliente` is under forced row level security (migration 0005), so a direct
query without a firm finds nothing. This function, like the four lookups of 0005, runs as
`lastro_owner`, makes one exact search by hash and returns only what the API needs to name
the firm and go on under row level security (plan D6).

An invalidated link is filtered here. An expired one is returned with `expira_em`: the API
compares it with its own clock and refuses it the same way as an unknown code (plan P5).

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "lastro_app"
SIGNATURE = "public.buscar_link_por_hash(text)"

CREATE_FUNCTION = """
    CREATE FUNCTION public.buscar_link_por_hash(p_hash text)
    RETURNS TABLE (
        escritorio_id uuid,
        link_id uuid,
        cliente_id uuid,
        competencia_id uuid,
        expira_em timestamptz
    )
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public
    AS $$
        SELECT l.escritorio_id, l.id, l.cliente_id, l.competencia_id, l.expira_em
          FROM public.link_cliente l
         WHERE l.hash_token = p_hash
           AND l.revogado_em IS NULL
    $$
"""


def upgrade() -> None:
    """Add the link lookup, executable only by the application role."""
    op.execute(CREATE_FUNCTION)
    op.execute(f"REVOKE ALL ON FUNCTION {SIGNATURE} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {SIGNATURE} TO {APP_ROLE}")


def downgrade() -> None:
    """Drop the link lookup."""
    op.execute(f"DROP FUNCTION {SIGNATURE}")
