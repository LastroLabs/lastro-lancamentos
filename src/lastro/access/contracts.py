"""Contracts of the access module: who is signed in and why signing in failed (ACE-01).

The role uses `lastro.core.contracts.Role`, the same values as the access rule of NUC-02,
so later features build a `Membership` straight from a `SignedInMember`.
"""

from dataclasses import dataclass
from datetime import datetime

from lastro.core.contracts import Role


@dataclass(frozen=True, slots=True)
class SignedInMember:
    """Member identified by an open session.

    Attributes:
        user_id: id of the global user.
        member_id: id of the membership the session is bound to.
        firm_id: id of the firm of that membership.
        username: login of the user.
        name: display name of the user.
        role: role of the membership in the firm.
        firm_name: name of the firm.
    """

    user_id: str
    member_id: str
    firm_id: str
    username: str
    name: str
    role: Role
    firm_name: str


@dataclass(frozen=True, slots=True)
class OpenedSession:
    """Session created by a successful sign-in.

    Attributes:
        token: secret sent to the browser once; the database keeps only its hash.
        expires_at: when the session stops being accepted.
        member: who signed in.
    """

    token: str
    expires_at: datetime
    member: SignedInMember


class InvalidCredentialsError(Exception):
    """Sign-in refused. Never says whether the login, the password or the account failed."""


class SessionEndedError(Exception):
    """The session token is unknown, ended, expired or bound to an inactive membership."""


class MultipleFirmsError(Exception):
    """Right password, but the user has active memberships in more than one firm (plan D10).

    The MVP keeps one active membership per user: whoever works for two firms gets one
    user per firm. Raised only after the password matched, so it never tells a stranger
    that the account exists. No session is opened.
    """


@dataclass(frozen=True, slots=True)
class CreatedFirm:
    """Firm and first manager created together (ADM-01).

    Attributes:
        firm_name: name of the new firm.
        username: login stored for the manager, in lower case.
    """

    firm_name: str
    username: str


class UsernameTakenError(Exception):
    """The login already exists (any letter case, active or not); nothing was written."""
