"""Contracts of the access module: who is signed in and why signing in failed (ACE-01).

The role uses `lastro.core.contracts.Role`, the same values as the access rule of NUC-02,
so later features build a `Membership` straight from a `SignedInMember`.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

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

    Contract in version 0 (issue `contrato:` #68), with `UsernameTakenError` and
    `service.create_firm_with_manager`. Used by the first-access command and, later, by
    ACE-02. If it changes, comment on #68 and warn the module owners.

    Attributes:
        firm_name: name of the new firm.
        username: login stored for the manager, in lower case.
    """

    firm_name: str
    username: str


class UsernameTakenError(Exception):
    """The login already exists (any letter case, active or not); nothing was written.

    Contract in version 0 (issue `contrato:` #68).
    """


class PersonStatus(StrEnum):
    """Where a person of the firm stands with the password (ACE-02, c1, c2, c5).

    Contract in version 0, like the rest of ACE-02. Values are the ones the manager sees.
    """

    ACTIVE = "ativo"
    INVITATION_PENDING = "convite_pendente"
    INVITATION_EXPIRED = "convite_vencido"
    NO_INVITATION = "sem_convite"


@dataclass(frozen=True, slots=True)
class TeamMember:
    """Active person of the firm, as the manager's list shows it. Never carries a secret.

    Attributes:
        member_id: id of the membership (the id of a person in the API).
        name: display name.
        username: login, in lower case.
        role: role of the membership in the firm.
        status: password and invitation situation.
    """

    member_id: str
    name: str
    username: str
    role: Role
    status: PersonStatus


@dataclass(frozen=True, slots=True)
class IssuedInvitation:
    """Invitation just created: the only time its code is shown.

    Attributes:
        member: the invited accountant, with status `convite_pendente`.
        code: random code of the link; the database keeps only its SHA-256.
        expires_at: when the invitation stops being accepted, by the database clock.
    """

    member: TeamMember
    code: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class Responsible:
    """Active responsible member of a client."""

    member_id: str
    name: str
    username: str


class InvalidAccessDataError(Exception):
    """Empty name or username, or a password that is too short (422). Carries the message."""

    def __init__(self, message: str) -> None:
        """Keep the message to show the user."""
        super().__init__(message)
        self.message = message


class AccountantNotFoundError(Exception):
    """The person does not exist in the firm of the session (also for another firm's)."""


class AccountantAlreadyActiveError(Exception):
    """The accountant already created the password, so no invitation is issued."""


class InvalidInvitationError(Exception):
    """Unknown, expired, used, cancelled invitation, or username that does not match.

    One error for all five, so the refusal never tells which one it was.
    """


class ResponsibleNotFoundError(Exception):
    """The chosen member does not exist, or is not active, in the firm of the session."""


class ClientAlreadyAssignedError(Exception):
    """The client already has an active responsible; changing it is ACE-04."""
