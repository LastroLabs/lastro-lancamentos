"""Reads and writes of the `cliente` table for the registry module (CAD-03, I-7).

Every query takes the firm id of the session, never one from the request body. The caller
owns the transaction: nothing here commits.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid7

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from lastro.registry.models import BankAccount, Client


@dataclass(frozen=True, slots=True)
class ClientRow:
    """Client stored in one firm."""

    client_id: UUID
    name: str
    cnpj: str


async def insert_client(
    db: AsyncSession, firm_id: UUID, name: str, cnpj: str
) -> ClientRow:
    """Add a client to the firm and return it with the generated id, without committing.

    Raises:
        IntegrityError: the firm already has a client with this CNPJ.
    """
    client_id = (
        await db.execute(
            insert(Client)
            .values(escritorio_id=firm_id, nome=name, cnpj_normalizado=cnpj)
            .returning(Client.id)
        )
    ).scalar_one()
    return ClientRow(client_id=client_id, name=name, cnpj=cnpj)


async def list_clients(db: AsyncSession, firm_id: UUID) -> list[ClientRow]:
    """Clients of the firm, ordered by name and then by id."""
    rows = await db.execute(
        select(Client.id, Client.nome, Client.cnpj_normalizado)
        .where(Client.escritorio_id == firm_id)
        .order_by(Client.nome, Client.id)
    )
    return [ClientRow(*row) for row in rows]


async def find_client(
    db: AsyncSession, firm_id: UUID, client_id: UUID
) -> ClientRow | None:
    """The client with this id in the firm, or None (also for a client of another firm)."""
    row = (
        await db.execute(
            select(Client.id, Client.nome, Client.cnpj_normalizado).where(
                Client.escritorio_id == firm_id, Client.id == client_id
            )
        )
    ).one_or_none()
    return None if row is None else ClientRow(*row)


@dataclass(frozen=True, slots=True)
class BankAccountRow:
    """Bank account stored for one client."""

    account_id: UUID
    bank: str
    nickname: str
    currency: str
    first_month: date | None
    last_month: date | None


_ACCOUNT_COLUMNS = (
    BankAccount.id,
    BankAccount.banco,
    BankAccount.apelido,
    BankAccount.moeda,
    BankAccount.cobertura_inicio,
    BankAccount.cobertura_fim,
)


async def lock_client(db: AsyncSession, firm_id: UUID, client_id: UUID) -> None:
    """Lock the client row until the end of the transaction, so two writers of accounts of
    the same client run one after the other (plan CAD-04, answer P2)."""
    await db.execute(
        select(Client.id)
        .where(Client.escritorio_id == firm_id, Client.id == client_id)
        .with_for_update()
    )


async def list_bank_accounts(
    db: AsyncSession, firm_id: UUID, client_id: UUID
) -> list[BankAccountRow]:
    """Accounts of the client in the order they were created (ids are time-ordered)."""
    rows = await db.execute(
        select(*_ACCOUNT_COLUMNS)
        .where(
            BankAccount.escritorio_id == firm_id, BankAccount.cliente_id == client_id
        )
        .order_by(BankAccount.id)
    )
    return [BankAccountRow(*row) for row in rows]


async def find_bank_account(
    db: AsyncSession, firm_id: UUID, client_id: UUID, account_id: UUID
) -> BankAccountRow | None:
    """The account of this client with this id, or None."""
    row = (
        await db.execute(
            select(*_ACCOUNT_COLUMNS).where(
                BankAccount.escritorio_id == firm_id,
                BankAccount.cliente_id == client_id,
                BankAccount.id == account_id,
            )
        )
    ).one_or_none()
    return None if row is None else BankAccountRow(*row)


async def insert_bank_account(
    db: AsyncSession,
    firm_id: UUID,
    client_id: UUID,
    bank: str,
    nickname: str,
    first_month: date | None,
    last_month: date | None,
) -> BankAccountRow:
    """Add an account in BRL, without committing. The id is a UUIDv7, so ids sort by creation."""
    account_id = uuid7()
    await db.execute(
        insert(BankAccount).values(
            escritorio_id=firm_id,
            cliente_id=client_id,
            id=account_id,
            banco=bank,
            apelido=nickname,
            cobertura_inicio=first_month,
            cobertura_fim=last_month,
        )
    )
    return BankAccountRow(account_id, bank, nickname, "BRL", first_month, last_month)


async def update_bank_account(
    db: AsyncSession,
    firm_id: UUID,
    client_id: UUID,
    account_id: UUID,
    nickname: str,
    first_month: date | None,
    last_month: date | None,
) -> None:
    """Set nickname and months of the account, without committing. The bank is never changed."""
    await db.execute(
        update(BankAccount)
        .where(
            BankAccount.escritorio_id == firm_id,
            BankAccount.cliente_id == client_id,
            BankAccount.id == account_id,
        )
        .values(
            apelido=nickname, cobertura_inicio=first_month, cobertura_fim=last_month
        )
    )
