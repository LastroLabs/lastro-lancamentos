"""Reads and writes of the identity tables used by sign-in and sessions (ACE-01, I-7).

Only this file touches `usuario`, `membro`, `escritorio`, `sessao`, `convite` and
`atribuicao` for the access module. Nothing here reads `usuario.credencial_hash`, except the
login lookup of sign-in (ACE-02, c2 and c10). The caller owns the transaction: nothing here commits.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, insert, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from lastro.access.models import Assignment, Firm, Invitation, Member, Session, User
from lastro.core.db import use_firm


@dataclass(frozen=True, slots=True)
class SignInCandidate:
    """User found by login, with what sign-in needs to check."""

    user_id: UUID
    credential_hash: str | None
    is_active: bool


@dataclass(frozen=True, slots=True)
class MembershipRow:
    """Membership joined with its user and firm."""

    user_id: UUID
    member_id: UUID
    firm_id: UUID
    username: str
    name: str
    role: str
    firm_name: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class SessionRow:
    """Stored session with the membership it is bound to."""

    session_id: UUID
    firm_id: UUID
    created_at: datetime
    expires_at: datetime
    ended_at: datetime | None
    membership: MembershipRow


def _membership_columns():
    return (
        User.id,
        Member.id,
        Firm.id,
        User.identificador_login,
        User.nome,
        Member.papel,
        Firm.nome,
        User.ativo & Member.ativo & Firm.ativo,
    )


def _membership_joins(statement):
    return statement.join(User, User.id == Member.usuario_id).join(
        Firm, Firm.id == Member.escritorio_id
    )


async def find_users_by_login(
    db: AsyncSession, normalized_login: str
) -> list[SignInCandidate]:
    """Users whose login, in lower case, equals `normalized_login` (plan, question 4).

    Goes through a database function: the firm is not known yet (plan NUC-03, D4).
    """
    rows = await db.execute(
        text("SELECT * FROM public.buscar_usuario_por_login(:login)"),
        {"login": normalized_login},
    )
    return [SignInCandidate(*row) for row in rows]


async def find_active_memberships(
    db: AsyncSession, user_id: UUID
) -> list[MembershipRow]:
    """Active memberships of a user in active firms.

    The function finds which firms; each firm is then named in the session to read the
    full row under row level security. With two or more, the session ends up in the last.
    """
    found = await db.execute(
        text("SELECT * FROM public.buscar_vinculos_do_usuario(:user_id)"),
        {"user_id": user_id},
    )
    memberships = []
    for firm_id, member_id, _role in found.all():
        await use_firm(db, firm_id)
        statement = _membership_joins(
            select(*_membership_columns()).select_from(Member)
        ).where(Member.id == member_id, Member.ativo, Firm.ativo, User.ativo)
        memberships.extend(
            MembershipRow(*row) for row in await db.execute(statement)
        )
    return memberships


async def insert_session(
    db: AsyncSession,
    membership: MembershipRow,
    token_hash: str,
    created_at: datetime,
    expires_at: datetime,
) -> None:
    """Store a new session for a membership."""
    db.add(
        Session(
            escritorio_id=membership.firm_id,
            membro_id=membership.member_id,
            hash_token=token_hash,
            criada_em=created_at,
            expira_em=expires_at,
        )
    )
    await db.flush()


async def find_session(db: AsyncSession, token_hash: str) -> SessionRow | None:
    """The session with this token hash, with its membership, or None.

    The function (plan NUC-03, D4) gives firm, member and the two dates; the firm is then
    named in the session and the rest is read under row level security. The row is found
    again by member and dates, never by the hash, which is searched only by the function.
    """
    found = (
        await db.execute(
            text("SELECT * FROM public.buscar_sessao_por_hash(:token_hash)"),
            {"token_hash": token_hash},
        )
    ).one_or_none()
    if found is None:
        return None
    firm_id, member_id, expires_at, ended_at = found
    await use_firm(db, firm_id)
    statement = (
        _membership_joins(
            select(Session.id, Session.criada_em, *_membership_columns())
            .select_from(Session)
            .join(
                Member,
                (Member.escritorio_id == Session.escritorio_id)
                & (Member.id == Session.membro_id),
            )
        )
        .where(
            Session.membro_id == member_id,
            Session.expira_em == expires_at,
            Session.encerrada_em.is_not_distinct_from(ended_at),
        )
        .limit(2)
    )
    rows = (await db.execute(statement)).all()
    # Two sessions of the member with the same dates cannot be told apart without the hash:
    # refuse both (the user signs in again) instead of guessing and renewing the wrong one.
    if len(rows) != 1:
        return None
    session_id, created_at, *membership = rows[0]
    return SessionRow(
        session_id,
        firm_id,
        created_at,
        expires_at,
        ended_at,
        MembershipRow(*membership),
    )


async def end_session(
    db: AsyncSession, firm_id: UUID, session_id: UUID, ended_at: datetime
) -> None:
    """Mark a session as ended, if it was still open."""
    await db.execute(
        update(Session)
        .where(
            Session.escritorio_id == firm_id,
            Session.id == session_id,
            Session.encerrada_em.is_(None),
        )
        .values(encerrada_em=ended_at)
    )


async def renew_session(
    db: AsyncSession, firm_id: UUID, session_id: UUID, expires_at: datetime
) -> None:
    """Move the expiry of an open session (plan D9)."""
    await db.execute(
        update(Session)
        .where(
            Session.escritorio_id == firm_id,
            Session.id == session_id,
            Session.encerrada_em.is_(None),
        )
        .values(expira_em=expires_at)
    )


async def insert_firm_with_manager(
    db: AsyncSession,
    firm_name: str,
    login: str,
    name: str,
    credential_hash: str,
) -> None:
    """Add a firm, its user and an active `chefe` membership, without committing.

    The session is left in the name of the new firm."""
    # The id is made here so the session can name the firm before the first row, which
    # the policy of `escritorio` needs to accept (plan NUC-03, D5).
    firm = Firm(id=uuid4(), nome=firm_name)
    await use_firm(db, firm.id)
    user = User(identificador_login=login, nome=name, credencial_hash=credential_hash)
    db.add_all([firm, user])
    await db.flush()
    db.add(Member(escritorio_id=firm.id, usuario_id=user.id, papel="chefe"))
    await db.flush()


async def find_open_assignments(
    db: AsyncSession, firm_id: UUID, client_ids: list[UUID]
) -> list[tuple[UUID, UUID]]:
    """(client id, member id) of the open assignment (`fim IS NULL`) of each given client."""
    if not client_ids:
        return []
    rows = await db.execute(
        select(Assignment.cliente_id, Assignment.membro_id).where(
            Assignment.escritorio_id == firm_id,
            Assignment.cliente_id.in_(client_ids),
            Assignment.fim.is_(None),
        )
    )
    return [(client_id, member_id) for client_id, member_id in rows]


@dataclass(frozen=True, slots=True)
class PersonRow:
    """Active member of a firm with its user, columns only (never the credential)."""

    member_id: UUID
    user_id: UUID
    name: str
    username: str
    role: str


@dataclass(frozen=True, slots=True)
class InvitationLookup:
    """What `buscar_convite_por_hash` says about a valid invitation."""

    firm_id: UUID
    invitation_id: UUID
    member_id: UUID


def _person_columns():
    return (Member.id, User.id, User.nome, User.identificador_login, Member.papel)


def _active_people(firm_id: UUID):
    return (
        select(*_person_columns())
        .select_from(Member)
        .join(User, User.id == Member.usuario_id)
        .where(Member.escritorio_id == firm_id, Member.ativo, User.ativo)
    )


async def login_exists(db: AsyncSession, normalized_login: str) -> bool:
    """Whether any user, of any firm, has this login in lower case. Reads the login only."""
    found = await db.execute(
        select(User.id)
        .where(func.lower(User.identificador_login) == normalized_login)
        .limit(1)
    )
    return found.first() is not None


async def insert_accountant(
    db: AsyncSession, firm_id: UUID, login: str, name: str
) -> UUID:
    """Add a user without password and an active `contador` membership; return the member id.

    Raises:
        IntegrityError: the login already exists.
    """
    user_id = (
        await db.execute(
            insert(User)
            .values(identificador_login=login, nome=name)
            .returning(User.id)
        )
    ).scalar_one()
    return (
        await db.execute(
            insert(Member)
            .values(escritorio_id=firm_id, usuario_id=user_id, papel="contador")
            .returning(Member.id)
        )
    ).scalar_one()


async def list_people(db: AsyncSession, firm_id: UUID) -> list[PersonRow]:
    """Active people of the firm, managers first, then by name."""
    rows = await db.execute(
        _active_people(firm_id).order_by(Member.papel, User.nome, Member.id)
    )
    return [PersonRow(*row) for row in rows]


async def find_person(
    db: AsyncSession, firm_id: UUID, member_id: UUID
) -> PersonRow | None:
    """The active member with this id in the firm, or None (also for another firm's)."""
    row = (
        await db.execute(_active_people(firm_id).where(Member.id == member_id))
    ).one_or_none()
    return None if row is None else PersonRow(*row)


async def find_who_has_password(
    db: AsyncSession, user_ids: list[UUID]
) -> dict[UUID, bool]:
    """Yes or no per user of the firm of the transaction, by the database function (c10).

    People of other firms and unknown ids are absent from the answer.
    """
    if not user_ids:
        return {}
    rows = await db.execute(
        text(
            "SELECT usuario_id, tem_senha"
            " FROM public.usuarios_com_senha(CAST(:ids AS uuid[]))"
        ),
        {"ids": user_ids},
    )
    return {user_id: has_password for user_id, has_password in rows}


async def find_pending_invitations(
    db: AsyncSession, firm_id: UUID
) -> dict[UUID, bool]:
    """Member id -> whether its pending invitation is expired, by the database clock."""
    rows = await db.execute(
        select(Invitation.membro_id, Invitation.expira_em <= func.now()).where(
            Invitation.escritorio_id == firm_id,
            Invitation.usado_em.is_(None),
            Invitation.revogado_em.is_(None),
        )
    )
    return {member_id: is_expired for member_id, is_expired in rows}


async def revoke_pending_invitation(
    db: AsyncSession, firm_id: UUID, member_id: UUID
) -> None:
    """Revoke the pending invitation of the member, even an expired one."""
    await db.execute(
        update(Invitation)
        .where(
            Invitation.escritorio_id == firm_id,
            Invitation.membro_id == member_id,
            Invitation.usado_em.is_(None),
            Invitation.revogado_em.is_(None),
        )
        .values(revogado_em=func.now())
    )


async def insert_invitation(
    db: AsyncSession,
    firm_id: UUID,
    member_id: UUID,
    created_by: UUID,
    token_hash: str,
    valid_for: timedelta,
) -> datetime:
    """Store a pending invitation expiring `valid_for` from the database `now()`; return it.

    Raises:
        IntegrityError: the member still has a pending invitation.
    """
    return (
        await db.execute(
            insert(Invitation)
            .values(
                escritorio_id=firm_id,
                membro_id=member_id,
                hash_token=token_hash,
                criado_por=created_by,
                expira_em=func.now() + valid_for,
            )
            .returning(Invitation.expira_em)
        )
    ).scalar_one()


async def find_invitation(db: AsyncSession, token_hash: str) -> InvitationLookup | None:
    """The valid invitation with this code hash, found only by the database function."""
    found = (
        await db.execute(
            text("SELECT * FROM public.buscar_convite_por_hash(:token_hash)"),
            {"token_hash": token_hash},
        )
    ).one_or_none()
    return None if found is None else InvitationLookup(*found)


async def mark_invitation_used(
    db: AsyncSession, firm_id: UUID, invitation_id: UUID
) -> bool:
    """Spend the invitation if it is still pending and valid; False if someone beat us.

    Concurrent calls wait on the row lock, then see `usado_em` filled and update nothing.
    """
    spent = await db.execute(
        update(Invitation)
        .where(
            Invitation.escritorio_id == firm_id,
            Invitation.id == invitation_id,
            Invitation.usado_em.is_(None),
            Invitation.revogado_em.is_(None),
            Invitation.expira_em > func.now(),
        )
        .values(usado_em=func.now())
        .returning(Invitation.id)
    )
    return spent.first() is not None


async def set_credential(db: AsyncSession, user_id: UUID, credential_hash: str) -> None:
    """Write the password hash straight to the column, without loading the user."""
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(credencial_hash=credential_hash)
        .execution_options(synchronize_session=False)
    )


async def insert_assignment(
    db: AsyncSession,
    firm_id: UUID,
    client_id: UUID,
    member_id: UUID,
    assigned_by: UUID,
) -> None:
    """Open an assignment starting at the database `now()`.

    Raises:
        IntegrityError: the client already has an open assignment.
    """
    await db.execute(
        insert(Assignment).values(
            escritorio_id=firm_id,
            cliente_id=client_id,
            membro_id=member_id,
            atribuido_por=assigned_by,
            inicio=func.now(),
        )
    )
