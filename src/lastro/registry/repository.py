"""Reads and writes of the `cliente` table for the registry module (CAD-03, I-7).

Every query takes the firm id of the session, never one from the request body. The caller
owns the transaction: nothing here commits.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from lastro.registry.models import Client


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
