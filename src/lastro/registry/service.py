"""Public interface of the registry module (CAD-01, CAD-03; RF-CAD-01, RF-AUT-03).

CNPJ validation is a pure function. Client registration, list and opening take the database
session and the signed-in member; the list and the opening also take a function that finds
the active responsible member of each client (plan CAD-03, D3), so this module never imports
`access`. Access follows the rule of `lastro.core.service` (NUC-02, P-09).
"""

from collections.abc import Awaitable, Callable, Sequence
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from lastro.access.contracts import SignedInMember
from lastro.core.contracts import (
    AccessDecision,
    Action,
    ClientScope,
    Membership,
    Role,
)
from lastro.core.service import decide_access, filter_visible_clients
from lastro.registry import repository
from lastro.registry.cnpj import _validate_cnpj
from lastro.registry.contracts import (
    ClientNotAssignedError,
    ClientNotFoundError,
    ClientSummary,
    CnpjValidationResult,
    DuplicateCnpjError,
    InvalidClientDataError,
    ManagerOnlyError,
)

NAME_MAX_LENGTH = 255
EMPTY_NAME_MESSAGE = "Informe o nome do cliente."
LONG_NAME_MESSAGE = (
    f"O nome do cliente deve ter no máximo {NAME_MAX_LENGTH} caracteres."
)

# (db, firm_id, client_ids) -> {client_id: active responsible member_id or None}
FindResponsibles = Callable[
    [AsyncSession, str, Sequence[str]], Awaitable[dict[str, str | None]]
]


def validate_cnpj(cnpj: str) -> CnpjValidationResult:
    """Validate and normalize a client's numeric or alphanumeric CNPJ.

    Args:
        cnpj: Raw CNPJ string, with or without the official mask.

    Returns:
        Validation outcome with the normalized 14-character uppercase CNPJ when
        valid, or a plain-Portuguese refusal message when invalid.
    """
    return _validate_cnpj(cnpj)


async def register_client(
    db: AsyncSession, member: SignedInMember, name: str, cnpj: str
) -> ClientSummary:
    """Register a client with name and CNPJ in the member's firm (CAD-03, c1 and c2).

    Checks run in a fixed order and only the first failure is reported: role, name (empty,
    then length, after `strip()`), CNPJ.

    Args:
        db: database session; committed only when the client is stored.
        member: who is signed in; the firm comes from here, never from the request.
        name: name typed by the manager.
        cnpj: CNPJ typed by the manager, with or without mask.

    Returns:
        The stored client, with the CNPJ without mask.

    Raises:
        ManagerOnlyError: the member is not the manager of the firm (P-02).
        InvalidClientDataError: empty or too long name, or invalid CNPJ.
        DuplicateCnpjError: the firm already has a client with this CNPJ.
    """
    if member.role is not Role.MANAGER:
        raise ManagerOnlyError
    clean_name = name.strip()
    if not clean_name:
        raise InvalidClientDataError(EMPTY_NAME_MESSAGE)
    if len(clean_name) > NAME_MAX_LENGTH:
        raise InvalidClientDataError(LONG_NAME_MESSAGE)
    result = validate_cnpj(cnpj)
    if not result.is_valid or result.normalized is None:
        raise InvalidClientDataError(result.error_message or "")

    try:
        row = await repository.insert_client(
            db, UUID(member.firm_id), clean_name, result.normalized
        )
        await db.commit()
    except IntegrityError as error:
        # The UNIQUE (escritorio_id, cnpj_normalizado) refused it, even under a race.
        await db.rollback()
        raise DuplicateCnpjError from error
    except BaseException:
        await db.rollback()
        raise
    return _summary(row)


async def list_clients(
    db: AsyncSession, member: SignedInMember, find_responsibles: FindResponsibles
) -> list[ClientSummary]:
    """Clients of the member's firm that the access rule lets the member see (P-09).

    Args:
        db: database session; nothing is written.
        member: who is signed in.
        find_responsibles: finds the active responsible member of each client.

    Returns:
        The visible clients, ordered by name.
    """
    rows = await repository.list_clients(db, UUID(member.firm_id))
    by_id = {str(row.client_id): row for row in rows}
    responsibles = await find_responsibles(db, member.firm_id, list(by_id))
    scopes = [
        ClientScope(client_id, member.firm_id, responsibles.get(client_id))
        for client_id in by_id
    ]
    visible = filter_visible_clients(_membership(member), scopes)
    return [_summary(by_id[scope.client_id]) for scope in visible]


async def get_client(
    db: AsyncSession,
    member: SignedInMember,
    client_id: str,
    find_responsibles: FindResponsibles,
) -> ClientSummary:
    """Open one client, if the access rule allows it (P-01, P-09).

    A malformed id, a missing client and a client of another firm all raise the same
    `ClientNotFoundError`, so nobody learns that a client of another firm exists.

    Args:
        db: database session; nothing is written.
        member: who is signed in.
        client_id: id from the address.
        find_responsibles: finds the active responsible member of each client.

    Returns:
        The client.

    Raises:
        ClientNotFoundError: missing, malformed or of another firm, or not visible.
        ClientNotAssignedError: manager of the same firm who is not the responsible.
    """
    try:
        parsed_id = UUID(client_id)
    except ValueError as error:
        raise ClientNotFoundError from error
    row = await repository.find_client(db, UUID(member.firm_id), parsed_id)
    scope = None
    if row is not None:
        key = str(row.client_id)
        responsibles = await find_responsibles(db, member.firm_id, [key])
        scope = ClientScope(key, member.firm_id, responsibles.get(key))

    decision = decide_access(_membership(member), Action.ACCESS, scope)
    if decision is AccessDecision.NOT_ASSIGNED:
        raise ClientNotAssignedError
    if decision is not AccessDecision.ALLOWED or row is None:
        raise ClientNotFoundError
    return _summary(row)


def _membership(member: SignedInMember) -> Membership:
    """The session only reaches here after `identify`, which refused inactive ones (D3)."""
    return Membership(
        member_id=member.member_id,
        firm_id=member.firm_id,
        role=member.role,
        is_active=True,
    )


def _summary(row: repository.ClientRow) -> ClientSummary:
    return ClientSummary(client_id=str(row.client_id), name=row.name, cnpj=row.cnpj)
