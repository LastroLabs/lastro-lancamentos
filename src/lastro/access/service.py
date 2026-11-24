"""Public interface of the access module: sign in, identify the session and sign out (ACE-01).

Sessions live on the server (ARQ-03, I-5): the browser gets a random token once, and the
database keeps only its SHA-256. Every refusal to sign in is the same
`InvalidCredentialsError`, so nobody learns whether a login exists (plan D5).

The caller passes the database session; `sign_in`, `identify` (it renews the expiry, D9) and
`sign_out` commit their change.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from lastro.access import passwords, repository
from lastro.access.contracts import (
    InvalidCredentialsError,
    MultipleFirmsError,
    OpenedSession,
    SessionEndedError,
    SignedInMember,
)
from lastro.core.contracts import Role

# Plan D9 (answer to question 1): a session ends after 2 hours without use, and never lasts
# more than 12 hours from sign-in, however much it is used.
SESSION_IDLE_TIMEOUT = timedelta(hours=2)
SESSION_MAX_DURATION = timedelta(hours=12)
# Same size as the client link token (I-6).
SESSION_TOKEN_BYTES = 32

_ROLES = {"chefe": Role.MANAGER, "contador": Role.ACCOUNTANT}


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
