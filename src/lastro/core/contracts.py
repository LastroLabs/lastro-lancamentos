"""Contracts of the access rule (NUC-02, P-09).

Immutable data exchanged between `core.service` and the modules that consume the
rule (access, registry, api). Ids are opaque: the rule compares them only by
equality and never depends on database types.
"""

from dataclasses import dataclass
from enum import Enum


class Role(Enum):
    """Role of a member inside a firm."""

    MANAGER = "manager"
    ACCOUNTANT = "accountant"


class Action(Enum):
    """What the member wants to do with a client."""

    LIST = "list"
    ACCESS = "access"
    MANAGE_ASSIGNMENT = "manage_assignment"


class AccessDecision(Enum):
    """Outcome of the access rule.

    The API maps each value to a status and a message (I-14); the rule only says
    why access was refused.
    """

    ALLOWED = "allowed"
    NOT_FOUND = "not_found"
    NOT_ASSIGNED = "not_assigned"
    FORBIDDEN_ROLE = "forbidden_role"


@dataclass(frozen=True, slots=True)
class Membership:
    """Active membership of the session: who is asking.

    `firm_id` and `role` are `None` when the user has no firm or no known role.
    """

    member_id: str
    firm_id: str | None
    role: Role | None
    is_active: bool


@dataclass(frozen=True, slots=True)
class ClientScope:
    """What the rule needs to know about a client.

    `responsible_member_id` is the active responsible member, or `None` when the
    client has no one assigned.
    """

    client_id: str
    firm_id: str
    responsible_member_id: str | None
