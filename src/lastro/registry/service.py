"""Public interface of the registry module (CAD-01, CAD-02, CAD-03; RF-CAD-01, RF-CAD-03, RF-AUT-03).

CNPJ validation is a pure function. Client registration, list and opening take the database
session and the `Membership` of the session (built by `api/` from the signed-in member); the
list and the opening also take a function that finds the active responsible member of each
client. This module never imports `access` (plan CAD-03, D3). Access follows the rule of
`lastro.core.service` (NUC-02, P-09).
"""

from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from lastro.core.contracts import (
    AccessDecision,
    Action,
    ClientScope,
    Membership,
    Role,
)
from lastro.core.service import decide_access, filter_visible_clients
from lastro.registry import bank_accounts, repository
from lastro.registry.banks import bank_name
from lastro.registry.chart_txt import _read_chart_of_accounts
from lastro.registry.cnpj import _validate_cnpj
from lastro.registry.contracts import (
    BankAccountSummary,
    ChartOfAccountsResult,
    ClientNotAssignedError,
    ClientNotFoundError,
    ClientSummary,
    CnpjValidationResult,
    DuplicateCnpjError,
    DuplicateNicknameError,
    InvalidBankAccountDataError,
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


def read_chart_of_accounts(source: bytes | Path) -> ChartOfAccountsResult:
    """Read and validate the client's chart of accounts exported as text (CAD-02).

    Bad content never raises: it becomes `refusal`, or a message in `errors` or
    `warnings`. The rule is in docs/modulos/registry.md.

    Args:
        source: raw bytes of the uploaded file, or the path of the file.

    Returns:
        The accepted accounts in file order with tolerated errors and warnings, or
        a single refusal message.

    Raises:
        OSError: `source` is a path that does not exist or cannot be read (plan D2).
    """
    return _read_chart_of_accounts(source)


async def register_client(
    db: AsyncSession, membership: Membership, name: str, cnpj: str
) -> ClientSummary:
    """Register a client with name and CNPJ in the member's firm (CAD-03, c1 and c2).

    Checks run in a fixed order and only the first failure is reported: role, name (empty,
    then length, after `strip()`), CNPJ.

    Args:
        db: database session; committed only when the client is stored.
        membership: membership of the session; the firm comes from here, never from
            the request.
        name: name typed by the manager.
        cnpj: CNPJ typed by the manager, with or without mask.

    Returns:
        The stored client, with the CNPJ without mask.

    Raises:
        ManagerOnlyError: the membership is not an active manager of a firm (P-02).
        InvalidClientDataError: empty or too long name, or invalid CNPJ.
        DuplicateCnpjError: the firm already has a client with this CNPJ.
    """
    firm_id = _firm_id(membership)
    if firm_id is None or membership.role is not Role.MANAGER:
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
        row = await repository.insert_client(db, firm_id, clean_name, result.normalized)
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
    db: AsyncSession, membership: Membership, find_responsibles: FindResponsibles
) -> list[ClientSummary]:
    """Clients of the member's firm that the access rule lets the member see (P-09).

    Args:
        db: database session; nothing is written.
        membership: membership of the session.
        find_responsibles: finds the active responsible member of each client.

    Returns:
        The visible clients, ordered by name.
    """
    firm_id = _firm_id(membership)
    if firm_id is None:
        return []
    rows = await repository.list_clients(db, firm_id)
    by_id = {str(row.client_id): row for row in rows}
    responsibles = await find_responsibles(db, str(firm_id), list(by_id))
    scopes = [
        ClientScope(client_id, str(firm_id), responsibles.get(client_id))
        for client_id in by_id
    ]
    visible = filter_visible_clients(membership, scopes)
    return [_summary(by_id[scope.client_id]) for scope in visible]


async def get_client(
    db: AsyncSession,
    membership: Membership,
    client_id: str,
    find_responsibles: FindResponsibles,
) -> ClientSummary:
    """Open one client, if the access rule allows it (P-01, P-09).

    A malformed id, a missing client and a client of another firm all raise the same
    `ClientNotFoundError`, so nobody learns that a client of another firm exists.

    Args:
        db: database session; nothing is written.
        membership: membership of the session.
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
    firm_id = _firm_id(membership)
    row = None
    if firm_id is not None:
        row = await repository.find_client(db, firm_id, parsed_id)
    scope = None
    if row is not None:
        key = str(row.client_id)
        responsibles = await find_responsibles(db, str(firm_id), [key])
        scope = ClientScope(key, str(firm_id), responsibles.get(key))

    decision = decide_access(membership, Action.ACCESS, scope)
    if decision is AccessDecision.NOT_ASSIGNED:
        raise ClientNotAssignedError
    if decision is not AccessDecision.ALLOWED or row is None:
        raise ClientNotFoundError
    return _summary(row)


async def client_exists(db: AsyncSession, firm_id: str, client_id: str) -> bool:
    """Whether the firm has a client with this id; false for a malformed id or another firm's.

    Passed by `api/` to `lastro.access.service`, which does not read `cliente` (ACE-02, plan
    question 3). Nothing is written.

    Args:
        db: database session, in the name of the firm.
        firm_id: firm of the session.
        client_id: id from the address.
    """
    try:
        parsed_id = UUID(client_id)
    except ValueError:
        return False
    return await repository.find_client(db, UUID(firm_id), parsed_id) is not None


async def _own_client(
    db: AsyncSession,
    membership: Membership,
    client_id: str,
    find_responsibles: FindResponsibles,
) -> tuple[UUID, UUID]:
    """Firm and client ids after the access rule allowed it (plan CAD-04, D1)."""
    summary = await get_client(db, membership, client_id, find_responsibles)
    firm_id = _firm_id(membership)
    assert firm_id is not None  # get_client raised otherwise
    return firm_id, UUID(summary.client_id)


async def add_bank_account(
    db: AsyncSession,
    membership: Membership,
    client_id: str,
    find_responsibles: FindResponsibles,
    bank: str | None,
    nickname: str | None,
    first_month: str | None = None,
    last_month: str | None = None,
) -> BankAccountSummary:
    """Give a bank account to the member's client (CAD-04, c1, c2, c4, c5, c6, c8).

    Order: access (404, 403) -> data (422, order of plan answer P5) -> repeated nickname (409).

    Args:
        db: database session; committed only when the account is stored.
        membership: membership of the session.
        client_id: id from the address.
        find_responsibles: finds the active responsible member of each client.
        bank: 3-digit bank code, spaces at the ends are ignored.
        nickname: nickname typed by the accountant.
        first_month: first month of use, `AAAA-MM`, optional.
        last_month: last month of use, `AAAA-MM`, optional.

    Raises:
        ClientNotFoundError: no access to the client (P-01).
        ClientNotAssignedError: manager who is not the responsible (P-09).
        InvalidBankAccountDataError: bank, nickname or months refused.
        DuplicateNicknameError: the client already has this nickname.
    """
    firm_id, parsed_client = await _own_client(
        db, membership, client_id, find_responsibles
    )
    valid = bank_accounts.validate_new_account(bank, nickname, first_month, last_month)
    try:
        await repository.lock_client(db, firm_id, parsed_client)
        existing = await repository.list_bank_accounts(db, firm_id, parsed_client)
        _check_nickname_free(existing, valid.nickname, None)
        row = await repository.insert_bank_account(
            db,
            firm_id,
            parsed_client,
            valid.bank,
            valid.nickname,
            valid.first_month,
            valid.last_month,
        )
        await db.commit()
    except BaseException:
        await db.rollback()
        raise
    return _account_summary(row)


async def list_bank_accounts(
    db: AsyncSession,
    membership: Membership,
    client_id: str,
    find_responsibles: FindResponsibles,
) -> list[BankAccountSummary]:
    """Bank accounts of a client the member may open, in the order they were created (CAD-04).

    Raises:
        ClientNotFoundError: no access to the client (P-01).
        ClientNotAssignedError: manager who is not the responsible (P-09).
    """
    firm_id, parsed_client = await _own_client(
        db, membership, client_id, find_responsibles
    )
    rows = await repository.list_bank_accounts(db, firm_id, parsed_client)
    return [_account_summary(row) for row in rows]


async def update_bank_account(
    db: AsyncSession,
    membership: Membership,
    client_id: str,
    account_id: str,
    find_responsibles: FindResponsibles,
    changes: dict[str, str | None],
) -> BankAccountSummary:
    """Change nickname and months of use of an account; the bank never changes (CAD-04, c7).

    `changes` holds only the fields the request sent (plan answer P4): a missing field stays;
    `first_month` or `last_month` as None clears it; `nickname` None or empty is refused;
    `bank` equal to the stored one is accepted, any other is refused.

    Raises:
        ClientNotFoundError: no access to the client, or the account is not of this client.
        ClientNotAssignedError: manager who is not the responsible (P-09).
        InvalidBankAccountDataError: nickname, bank or months refused.
        DuplicateNicknameError: another account of the client has this nickname.
    """
    firm_id, parsed_client = await _own_client(
        db, membership, client_id, find_responsibles
    )
    try:
        parsed_account = UUID(account_id)
    except ValueError as error:
        raise ClientNotFoundError from error
    try:
        # Lock first, read after: a PATCH that waited here must see what the one before it
        # committed, or it would write back the old nickname or month (rubric CAD-04).
        await repository.lock_client(db, firm_id, parsed_client)
        current = await repository.find_bank_account(
            db, firm_id, parsed_client, parsed_account
        )
        if current is None:
            raise ClientNotFoundError

        nickname = current.nickname
        if "nickname" in changes:
            nickname = bank_accounts.clean_nickname(changes["nickname"])
        if "bank" in changes and (changes["bank"] or "").strip() != current.bank:
            raise InvalidBankAccountDataError(bank_accounts.BANK_CHANGE_MESSAGE)
        bank_accounts.check_nickname_length(nickname)
        first = current.first_month
        last = current.last_month
        if "first_month" in changes:
            first = bank_accounts.parse_month(changes["first_month"])
        if "last_month" in changes:
            last = bank_accounts.parse_month(changes["last_month"])
        bank_accounts.check_month_order(first, last)

        existing = await repository.list_bank_accounts(db, firm_id, parsed_client)
        _check_nickname_free(existing, nickname, parsed_account)
        await repository.update_bank_account(
            db, firm_id, parsed_client, parsed_account, nickname, first, last
        )
        await db.commit()
    except BaseException:
        await db.rollback()
        raise
    return _account_summary(
        repository.BankAccountRow(
            parsed_account, current.bank, nickname, current.currency, first, last
        )
    )


def _check_nickname_free(
    existing: list[repository.BankAccountRow], nickname: str, own_id: UUID | None
) -> None:
    wanted = bank_accounts.normalize_nickname(nickname)
    for row in existing:
        if row.account_id != own_id and (
            bank_accounts.normalize_nickname(row.nickname) == wanted
        ):
            raise DuplicateNicknameError


def _account_summary(row: repository.BankAccountRow) -> BankAccountSummary:
    return BankAccountSummary(
        account_id=str(row.account_id),
        bank=row.bank,
        bank_name=bank_name(row.bank) or "",
        nickname=row.nickname,
        currency=row.currency,
        first_month=bank_accounts.format_month(row.first_month),
        last_month=bank_accounts.format_month(row.last_month),
    )


def _firm_id(membership: Membership) -> UUID | None:
    """Firm of an active membership, or None (inactive or without a firm sees nothing)."""
    if not membership.is_active or membership.firm_id is None:
        return None
    return UUID(membership.firm_id)


def _summary(row: repository.ClientRow) -> ClientSummary:
    return ClientSummary(client_id=str(row.client_id), name=row.name, cnpj=row.cnpj)
