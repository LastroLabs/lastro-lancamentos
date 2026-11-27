"""Lookup "did this person create the password?", without reading the credential (ACE-02, c10).

The manager's list and the refusal of a new invitation need a yes or no per person. The
application role cannot read `usuario.credencial_hash` (migration 0005), so this function,
which runs as `lastro_owner`, answers only `usuario_id` and `tem_senha` and only for people
who are members of the firm named in the transaction (plan D5, DECISIONS ACE-02/F1).

Without a firm in the transaction, it returns no rows and no error.

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "lastro_app"
SIGNATURE = "public.usuarios_com_senha(uuid[])"

CREATE_FUNCTION = """
    CREATE FUNCTION public.usuarios_com_senha(p_usuario_ids uuid[])
    RETURNS TABLE (usuario_id uuid, tem_senha boolean)
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public
    AS $$
        SELECT u.id, u.credencial_hash IS NOT NULL
          FROM public.usuario u
          JOIN public.membro m ON m.usuario_id = u.id
         WHERE u.id = ANY (p_usuario_ids)
           AND m.escritorio_id = NULLIF(current_setting('app.firm_id', true), '')::uuid
    $$
"""


def upgrade() -> None:
    """Add the lookup, executable only by the application role."""
    op.execute(CREATE_FUNCTION)
    op.execute(f"REVOKE ALL ON FUNCTION {SIGNATURE} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {SIGNATURE} TO {APP_ROLE}")


def downgrade() -> None:
    """Drop the lookup."""
    op.execute(f"DROP FUNCTION {SIGNATURE}")
