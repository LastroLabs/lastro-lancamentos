"""Row level security by firm and the lookups made before the firm is known (NUC-03).

Every table that belongs to a firm gets forced row level security: a row is seen and
written only inside a transaction that names its firm with
`set_config('app.firm_id', '<uuid>', true)`. Without a firm, nothing is seen and nothing
fails (plan D3). `lastro_owner`, which runs migrations and owns the SECURITY DEFINER
functions, has its own open policy, because FORCE also binds the owner (plan D2); the
application never connects as that role.

The four functions answer what the API must ask before it knows the firm: whose session,
whose memberships, which invite and which user for a login (plan D4). The application role
loses the right to read `usuario.credencial_hash` and gets it only through the login lookup.
The lookup of the client link stays out; `link_cliente` is closed until ACE-05.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "lastro_app"
OWNER_ROLE = "lastro_owner"

# Tables with a `escritorio_id` column, and `escritorio` itself, which compares its `id`.
FIRM_TABLES = (
    "membro",
    "sessao",
    "convite",
    "cliente",
    "atribuicao",
    "plano_contas",
    "conta_contabil",
    "conta_bancaria",
    "socio",
    "competencia",
    "link_cliente",
)
ALL_TABLES = ("escritorio", *FIRM_TABLES)

# Plan D3: after a SET LOCAL, the next transaction of the same connection reads empty text.
CURRENT_FIRM = "NULLIF(current_setting('app.firm_id', true), '')::uuid"

# Columns of `usuario` the application may still read (everything but the credential).
USER_READABLE_COLUMNS = "id, identificador_login, nome, ativo"

FUNCTIONS = (
    ("buscar_sessao_por_hash", "text"),
    ("buscar_vinculos_do_usuario", "uuid"),
    ("buscar_convite_por_hash", "text"),
    ("buscar_usuario_por_login", "text"),
)

CREATE_FUNCTIONS = (
    """
    CREATE FUNCTION public.buscar_sessao_por_hash(p_hash text)
    RETURNS TABLE (
        escritorio_id uuid, membro_id uuid, expira_em timestamptz, encerrada_em timestamptz
    )
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public
    AS $$
        SELECT s.escritorio_id, s.membro_id, s.expira_em, s.encerrada_em
          FROM public.sessao s
         WHERE s.hash_token = p_hash
    $$
    """,
    """
    CREATE FUNCTION public.buscar_vinculos_do_usuario(p_usuario_id uuid)
    RETURNS TABLE (escritorio_id uuid, membro_id uuid, papel text)
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public
    AS $$
        SELECT m.escritorio_id, m.id, m.papel::text
          FROM public.membro m
          JOIN public.usuario u ON u.id = m.usuario_id
          JOIN public.escritorio e ON e.id = m.escritorio_id
         WHERE m.usuario_id = p_usuario_id AND m.ativo AND u.ativo AND e.ativo
    $$
    """,
    """
    CREATE FUNCTION public.buscar_convite_por_hash(p_hash text)
    RETURNS TABLE (escritorio_id uuid, convite_id uuid, membro_id uuid)
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public
    AS $$
        SELECT c.escritorio_id, c.id, c.membro_id
          FROM public.convite c
         WHERE c.hash_token = p_hash
           AND c.usado_em IS NULL AND c.revogado_em IS NULL AND c.expira_em > now()
    $$
    """,
    """
    CREATE FUNCTION public.buscar_usuario_por_login(p_login text)
    RETURNS TABLE (usuario_id uuid, credencial_hash text, ativo boolean)
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public
    AS $$
        SELECT u.id, u.credencial_hash, u.ativo
          FROM public.usuario u
         WHERE lower(u.identificador_login) = p_login
    $$
    """,
)


def upgrade() -> None:
    """Force RLS with one policy per table, open the owner, add the functions."""
    for table in ALL_TABLES:
        column = "id" if table == "escritorio" else "escritorio_id"
        rule = f"{column} = {CURRENT_FIRM}"
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY isolamento_escritorio ON public.{table}"
            f" FOR ALL TO {APP_ROLE} USING ({rule}) WITH CHECK ({rule})"
        )
        op.execute(
            f"CREATE POLICY acesso_do_dono ON public.{table}"
            f" FOR ALL TO {OWNER_ROLE} USING (true) WITH CHECK (true)"
        )

    op.execute(f"REVOKE SELECT ON public.usuario FROM {APP_ROLE}")
    op.execute(f"GRANT SELECT ({USER_READABLE_COLUMNS}) ON public.usuario TO {APP_ROLE}")

    for statement in CREATE_FUNCTIONS:
        op.execute(statement)
    for name, argument in FUNCTIONS:
        op.execute(f"REVOKE ALL ON FUNCTION public.{name}({argument}) FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION public.{name}({argument}) TO {APP_ROLE}")


def downgrade() -> None:
    """Undo upgrade(): drop the functions and the policies, give back the read of usuario."""
    for name, argument in FUNCTIONS:
        op.execute(f"DROP FUNCTION public.{name}({argument})")

    op.execute(f"REVOKE SELECT ({USER_READABLE_COLUMNS}) ON public.usuario FROM {APP_ROLE}")
    op.execute(f"GRANT SELECT ON public.usuario TO {APP_ROLE}")

    for table in reversed(ALL_TABLES):
        op.execute(f"DROP POLICY acesso_do_dono ON public.{table}")
        op.execute(f"DROP POLICY isolamento_escritorio ON public.{table}")
        op.execute(f"ALTER TABLE public.{table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY")
