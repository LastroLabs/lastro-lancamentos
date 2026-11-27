"""Public interface of the access module: sign in, identify the session and sign out (ACE-01).

Sessions live on the server (ARQ-03, I-5): the browser gets a random token once, and the
database keeps only its SHA-256. Every refusal to sign in is the same
`InvalidCredentialsError`, so nobody learns whether a login exists (plan D5).

The caller passes the database session; `sign_in`, `identify` (it renews the expiry, D9) and
`sign_out` commit their change.
"""

import hashlib
import secrets
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from lastro.access import passwords, repository
from lastro.access.contracts import (
    AccountantAlreadyActiveError,
    AccountantNotFoundError,
    ClientAlreadyAssignedError,
    CreatedFirm,
    InvalidAccessDataError,
    InvalidCredentialsError,
    InvalidInvitationError,
    IssuedInvitation,
    MultipleFirmsError,
    OpenedSession,
    PersonStatus,
    Responsible,
    ResponsibleNotFoundError,
    SessionEndedError,
    SignedInMember,
    TeamMember,
    UsernameTakenError,
)
from lastro.access.passwords import MIN_PASSWORD_LENGTH
from lastro.core.contracts import AccessDecision, Action, ClientScope, Membership, Role
from lastro.core.db import use_firm
from lastro.core.service import decide_access
from lastro.registry.contracts import ClientNotFoundError, ManagerOnlyError

# Plan D9 (answer to question 1): a session ends after 2 hours without use, and never lasts
# more than 12 hours from sign-in, however much it is used.
SESSION_IDLE_TIMEOUT = timedelta(hours=2)
SESSION_MAX_DURATION = timedelta(hours=12)
# Same size as the client link token (I-6).
SESSION_TOKEN_BYTES = 32

_ROLES = {"chefe": Role.MANAGER, "contador": Role.ACCOUNTANT}

# ACE-02, plan D1: 32 random bytes in URL-safe text are 43 characters, like the session token.
INVITATION_CODE_BYTES = 32
EMPTY_ACCOUNTANT_NAME_MESSAGE = "Informe o nome do contador."
EMPTY_ACCOUNTANT_USERNAME_MESSAGE = "Informe o usuário de entrada do contador."
SHORT_PASSWORD_MESSAGE = (
    f"A senha precisa ter pelo menos {MIN_PASSWORD_LENGTH} caracteres."
)

# (db, firm_id, client_id) -> whether the firm has that client (`registry.client_exists`)
ClientExists = Callable[[AsyncSession, str, str], Awaitable[bool]]


def hash_password(password: str) -> str:
    """Hash a password with Argon2 for `usuario.credencial_hash` (plan D4).

    Args:
        password: the password in clear.

    Returns:
        The hash in PHC format; the password itself is never stored.
    """
    return passwords.hash_password(password)


async def sign_in(db: AsyncSession, username: str, password: str) -> OpenedSession:
    """Check the credentials and open a new session.

    The login is compared in lower case, without surrounding spaces. Signing in needs an
    active user with a password, and exactly one active membership in an active firm
    (plan D10: one firm per user in the MVP).

    Args:
        db: database session; committed when the session is stored.
        username: login typed by the user.
        password: password typed by the user; may be empty.

    Returns:
        The new session, with the token to send to the browser.

    Raises:
        InvalidCredentialsError: for any refusal, always the same.
        MultipleFirmsError: right password, but active memberships in two or more firms.
    """
    candidates = await repository.find_users_by_login(db, username.strip().lower())
    user = candidates[0] if len(candidates) == 1 else None
    # Always run the hash check, even without a user, so every refusal costs the same.
    is_match = passwords.verify_password(
        user.credential_hash if user else None, password
    )
    if user is None or not is_match or not user.is_active:
        raise InvalidCredentialsError

    memberships = await repository.find_active_memberships(db, user.user_id)
    if not memberships:
        raise InvalidCredentialsError
    if len(memberships) > 1:
        raise MultipleFirmsError
    membership = memberships[0]

    session_key = secrets.token_urlsafe(SESSION_TOKEN_BYTES)
    created_at = datetime.now(UTC)
    expires_at = _next_expiry(created_at, created_at)
    await repository.insert_session(
        db, membership, _hash_token(session_key), created_at, expires_at
    )
    await db.commit()
    return OpenedSession(
        token=session_key, expires_at=expires_at, member=_to_member(membership)
    )


async def identify(db: AsyncSession, token: str) -> SignedInMember:
    """Say who owns an open session, and renew its expiry (plan D9).

    Every accepted call moves the expiry to 2 hours from now, never past 12 hours from
    sign-in.

    Args:
        db: database session; committed after the expiry is renewed.
        token: the session token sent by the browser.

    Returns:
        The member bound to the session.

    Raises:
        SessionEndedError: if the token is unknown, the session ended, passed its expiry
            or its 12 hours, or the user, membership or firm is no longer active.
    """
    stored = await _open_session(db, token)
    now = datetime.now(UTC)
    await repository.renew_session(
        db, stored.firm_id, stored.session_id, _next_expiry(stored.created_at, now)
    )
    await db.commit()
    return _to_member(stored.membership)


async def sign_out(db: AsyncSession, token: str) -> None:
    """End an open session now.

    Args:
        db: database session; committed after the session is ended.
        token: the session token sent by the browser.

    Raises:
        SessionEndedError: if the session was not open (same rule as `identify`).
    """
    stored = await _open_session(db, token)
    await repository.end_session(
        db, stored.firm_id, stored.session_id, datetime.now(UTC)
    )
    await db.commit()


async def create_firm_with_manager(
    db: AsyncSession, firm_name: str, username: str, name: str, password: str
) -> CreatedFirm:
    """Create a firm, its first manager and the active `chefe` membership (ADM-01).

    Everything is written in one transaction with a single commit. The login is stored in
    lower case and compared the same way as in `sign_in`.

    Args:
        db: database session; committed when all three rows are stored.
        firm_name: name of the new firm (repeated names are allowed).
        username: login of the manager.
        name: display name of the manager.
        password: password in clear; only its Argon2 hash is stored.

    Returns:
        The firm name and the stored login.

    Raises:
        UsernameTakenError: the login already exists; nothing was written or changed.
    """
    login = username.strip().lower()
    if await repository.find_users_by_login(db, login):
        raise UsernameTakenError
    try:
        await repository.insert_firm_with_manager(
            db, firm_name, login, name, hash_password(password)
        )
        await db.commit()
    except IntegrityError as error:
        # Another command took the login between the check and the insert.
        await db.rollback()
        raise UsernameTakenError from error
    except BaseException:
        await db.rollback()
        raise
    return CreatedFirm(firm_name=firm_name, username=login)


async def responsible_member_ids(
    db: AsyncSession, firm_id: str, client_ids: Sequence[str]
) -> dict[str, str | None]:
    """Active responsible member of each client of the firm (plan CAD-03, D3).

    Used by `api/` and passed to `lastro.registry.service`, which does not read
    `atribuicao`. Nothing is written.

    Args:
        db: database session.
        firm_id: firm of the session; clients of other firms never get a responsible.
        client_ids: ids of the clients to look up.

    Returns:
        For every given id, the member id of its open assignment, or None.
    """
    found = await repository.find_open_assignments(
        db, UUID(firm_id), [UUID(client_id) for client_id in client_ids]
    )
    responsible = {str(client_id): str(member_id) for client_id, member_id in found}
    return {client_id: responsible.get(client_id) for client_id in client_ids}


async def register_accountant(
    db: AsyncSession, membership: Membership, name: str, username: str, valid_for: timedelta
) -> IssuedInvitation:
    """Register an accountant without a password and issue the first invitation (ACE-02, c1).

    Checks run in this order: role, name, username, login already taken. Everything is
    written in one transaction.

    Args:
        db: database session; committed when user, membership and invitation are stored.
        membership: session membership; the firm comes from here, never from the request.
        name: display name typed by the manager.
        username: login typed by the manager; stored in lower case.
        valid_for: how long the invitation is valid, counted by the database clock.

    Returns:
        The accountant and the invitation code, shown only this once.

    Raises:
        ManagerOnlyError: the member is not the manager of the firm.
        InvalidAccessDataError: empty name or username.
        UsernameTakenError: the login exists in this or any other firm; nothing is written.
    """
    firm_id = _manager_firm(membership)
    clean_name = name.strip()
    if not clean_name:
        raise InvalidAccessDataError(EMPTY_ACCOUNTANT_NAME_MESSAGE)
    login = username.strip().lower()
    if not login:
        raise InvalidAccessDataError(EMPTY_ACCOUNTANT_USERNAME_MESSAGE)
    if await repository.login_exists(db, login):
        raise UsernameTakenError
    try:
        member_id = await repository.insert_accountant(db, firm_id, login, clean_name)
        code, expires_at = await _store_invitation(
            db, firm_id, member_id, UUID(membership.member_id), valid_for
        )
        await db.commit()
    except IntegrityError as error:
        # Another request took the login between the check and the insert.
        await db.rollback()
        raise UsernameTakenError from error
    except BaseException:
        await db.rollback()
        raise
    member = TeamMember(
        str(member_id), clean_name, login, Role.ACCOUNTANT, PersonStatus.INVITATION_PENDING
    )
    return IssuedInvitation(member=member, code=code, expires_at=expires_at)


async def list_team(db: AsyncSession, membership: Membership) -> list[TeamMember]:
    """Active people of the firm, the manager included, with the password situation (c1, c5).

    Whether someone created the password comes from the database function, never from the
    credential column; an invitation is expired by the database clock, like the acceptance.

    Raises:
        ManagerOnlyError: the member is not the manager of the firm.
    """
    firm_id = _manager_firm(membership)
    people = await repository.list_people(db, firm_id)
    has_password = await repository.find_who_has_password(db, [p.user_id for p in people])
    pending = await repository.find_pending_invitations(db, firm_id)
    return [
        _team_member(person, has_password.get(person.user_id, False), pending)
        for person in people
    ]


async def issue_invitation(
    db: AsyncSession, membership: Membership, member_id: str, valid_for: timedelta
) -> IssuedInvitation:
    """Issue a new invitation; the pending one, even expired, is revoked first (c5).

    Raises:
        ManagerOnlyError: the member is not the manager of the firm.
        AccountantNotFoundError: no such active person in the firm.
        AccountantAlreadyActiveError: the person already created the password.
    """
    firm_id = _manager_firm(membership)
    person = await _find_person(db, firm_id, member_id)
    try:
        # The lock comes before every check, so a request that waited sees the other's result.
        await repository.lock_member(db, firm_id, person.member_id)
        has_password = await repository.find_who_has_password(db, [person.user_id])
        if has_password.get(person.user_id, False):
            raise AccountantAlreadyActiveError
        await repository.revoke_pending_invitation(db, firm_id, person.member_id)
        code, expires_at = await _store_invitation(
            db, firm_id, person.member_id, UUID(membership.member_id), valid_for
        )
        await db.commit()
    except BaseException:
        await db.rollback()
        raise
    member = _team_member(person, False, {person.member_id: False})
    return IssuedInvitation(member=member, code=code, expires_at=expires_at)


async def cancel_invitation(
    db: AsyncSession, membership: Membership, member_id: str
) -> None:
    """Revoke the pending invitation, if any; without one, nothing changes (c5).

    Raises:
        ManagerOnlyError: the member is not the manager of the firm.
        AccountantNotFoundError: no such active person in the firm.
    """
    firm_id = _manager_firm(membership)
    person = await _find_person(db, firm_id, member_id)
    try:
        await repository.lock_member(db, firm_id, person.member_id)
        await repository.revoke_pending_invitation(db, firm_id, person.member_id)
        await db.commit()
    except BaseException:
        await db.rollback()
        raise


async def accept_invitation(
    db: AsyncSession, code: str, username: str, password: str
) -> None:
    """Create the accountant's password from an invitation code, once (ACE-02, c2, c3, c11).

    No session is needed. Order: invitation and username (one refusal for both), password
    length, then the invitation is spent and the password written in one transaction. A
    short password does not spend the invitation. The invitation is found only by the
    database lookup, which also gives the firm of the transaction.

    Args:
        db: database session; committed when the password is stored.
        code: the invitation code of the link.
        username: login typed by the accountant; must be the invited one.
        password: password in clear; only its Argon2 hash is stored.

    Raises:
        InvalidInvitationError: unknown, expired, used or cancelled invitation, username that
            does not match, or someone else accepted it first.
        InvalidAccessDataError: password shorter than 8 characters.
    """
    lookup = await repository.find_invitation(db, _hash_token(code))
    if lookup is None:
        raise InvalidInvitationError
    await use_firm(db, lookup.firm_id)
    person = await repository.find_person(db, lookup.firm_id, lookup.member_id)
    if person is None or person.username.lower() != username.strip().lower():
        raise InvalidInvitationError
    already = await repository.find_who_has_password(db, [person.user_id])
    if already.get(person.user_id, False):
        raise InvalidInvitationError
    if len(password) < MIN_PASSWORD_LENGTH:
        raise InvalidAccessDataError(SHORT_PASSWORD_MESSAGE)
    # Hash first, so the row lock of the invitation is held as briefly as possible.
    credential_hash = hash_password(password)
    try:
        if not await repository.mark_invitation_used(
            db, lookup.firm_id, lookup.invitation_id
        ):
            raise InvalidInvitationError
        await repository.set_credential(db, person.user_id, credential_hash)
        await db.commit()
    except BaseException:
        await db.rollback()
        raise


async def assign_client(
    db: AsyncSession,
    membership: Membership,
    client_id: str,
    member_id: str,
    client_exists: ClientExists,
) -> None:
    """Give a client without a responsible to an active member, by the manager (ACE-02, c6).

    Order (P-09): missing or foreign client, role, responsible member, client already taken.

    Args:
        db: database session; committed when the assignment is stored.
        membership: session membership; the firm comes from here.
        client_id: id from the address.
        member_id: id of the member who becomes responsible; may be the manager.
        client_exists: tells whether the firm has the client (`registry.client_exists`).

    Raises:
        ClientNotFoundError: client missing, malformed or of another firm.
        ManagerOnlyError: the member is not the manager of the firm.
        ResponsibleNotFoundError: no such active member in the firm.
        ClientAlreadyAssignedError: the client already has an active responsible (ACE-04).
    """
    firm_id = _firm_of(membership)
    scope = await _client_scope(db, membership, client_id, client_exists)
    decision = decide_access(membership, Action.MANAGE_ASSIGNMENT, scope)
    if decision is AccessDecision.FORBIDDEN_ROLE:
        raise ManagerOnlyError
    if decision is not AccessDecision.ALLOWED or scope is None:
        raise ClientNotFoundError
    target = await _find_person_or_none(db, firm_id, member_id)
    if target is None:
        raise ResponsibleNotFoundError
    if scope.responsible_member_id is not None:
        raise ClientAlreadyAssignedError
    try:
        await repository.insert_assignment(
            db, firm_id, UUID(client_id), target.member_id, UUID(membership.member_id)
        )
        await db.commit()
    except IntegrityError as error:
        # The unique index of open assignments refused it: someone assigned it meanwhile.
        await db.rollback()
        raise ClientAlreadyAssignedError from error
    except BaseException:
        await db.rollback()
        raise


async def get_responsible(
    db: AsyncSession,
    membership: Membership,
    client_id: str,
    client_exists: ClientExists,
) -> Responsible | None:
    """The active responsible of a client, or None when it has none (ACE-02, c6).

    Raises:
        ClientNotFoundError: client missing, malformed, of another firm, or not visible.
    """
    scope = await _client_scope(db, membership, client_id, client_exists)
    if decide_access(membership, Action.LIST, scope) is not AccessDecision.ALLOWED:
        raise ClientNotFoundError
    if scope is None or scope.responsible_member_id is None:
        return None
    person = await _find_person_or_none(
        db, _firm_of(membership), scope.responsible_member_id
    )
    if person is None:
        return None
    return Responsible(str(person.member_id), person.name, person.username)


def _firm_of(membership: Membership) -> UUID:
    if membership.firm_id is None:
        raise ManagerOnlyError
    return UUID(membership.firm_id)


def _manager_firm(membership: Membership) -> UUID:
    """Firm of an active manager; anyone else is refused."""
    if not membership.is_active or membership.role is not Role.MANAGER:
        raise ManagerOnlyError
    return _firm_of(membership)


async def _client_scope(
    db: AsyncSession, membership: Membership, client_id: str, client_exists: ClientExists
) -> ClientScope | None:
    firm_id = _firm_of(membership)
    if not await client_exists(db, str(firm_id), client_id):
        return None
    responsibles = await responsible_member_ids(db, str(firm_id), [client_id])
    return ClientScope(client_id, str(firm_id), responsibles.get(client_id))


async def _find_person_or_none(
    db: AsyncSession, firm_id: UUID, member_id: str
) -> repository.PersonRow | None:
    try:
        parsed = UUID(member_id)
    except ValueError:
        return None
    return await repository.find_person(db, firm_id, parsed)


async def _find_person(
    db: AsyncSession, firm_id: UUID, member_id: str
) -> repository.PersonRow:
    person = await _find_person_or_none(db, firm_id, member_id)
    if person is None:
        raise AccountantNotFoundError
    return person


async def _store_invitation(
    db: AsyncSession,
    firm_id: UUID,
    member_id: UUID,
    created_by: UUID,
    valid_for: timedelta,
) -> tuple[str, datetime]:
    """Make a code, store only its hash and return (code, expiry by the database clock)."""
    code = secrets.token_urlsafe(INVITATION_CODE_BYTES)
    expires_at = await repository.insert_invitation(
        db, firm_id, member_id, created_by, _hash_token(code), valid_for
    )
    return code, expires_at


def _team_member(
    person: repository.PersonRow, has_password: bool, pending: dict[UUID, bool]
) -> TeamMember:
    if has_password:
        status = PersonStatus.ACTIVE
    elif person.member_id not in pending:
        status = PersonStatus.NO_INVITATION
    elif pending[person.member_id]:
        status = PersonStatus.INVITATION_EXPIRED
    else:
        status = PersonStatus.INVITATION_PENDING
    return TeamMember(
        str(person.member_id), person.name, person.username, _ROLES[person.role], status
    )


async def _open_session(db: AsyncSession, token: str) -> repository.SessionRow:
    stored = await repository.find_session(db, _hash_token(token))
    now = datetime.now(UTC)
    if (
        stored is None
        or stored.ended_at is not None
        or stored.expires_at <= now
        or stored.created_at + SESSION_MAX_DURATION <= now
        or not stored.membership.is_active
        or stored.membership.role not in _ROLES
    ):
        raise SessionEndedError
    return stored


def _next_expiry(created_at: datetime, now: datetime) -> datetime:
    """Two hours from now, but never past 12 hours from sign-in (plan D9)."""
    return min(now + SESSION_IDLE_TIMEOUT, created_at + SESSION_MAX_DURATION)


def _hash_token(token: str) -> str:
    """SHA-256 of the token in lower-case hex, the only form stored in `sessao.hash_token`."""
    return hashlib.sha256(token.encode()).hexdigest()


def _to_member(row: repository.MembershipRow) -> SignedInMember:
    return SignedInMember(
        user_id=str(row.user_id),
        member_id=str(row.member_id),
        firm_id=str(row.firm_id),
        username=row.username,
        name=row.name,
        role=_ROLES[row.role],
        firm_name=row.firm_name,
    )
