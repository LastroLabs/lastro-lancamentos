"""Database connection: async engine, sessions and a reachability probe (plan NUC-01, D3).

Nothing connects at import time or when a `Database` is built: the engine is created on the
first use and only then opens connections. The URL never goes to logs or error messages.
"""

import asyncio
import logging
from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT_SECONDS = 3
# Upper bound for the whole probe (DNS, connection and query), above the connect timeout.
REACHABILITY_TIMEOUT_SECONDS = 5


class Database:
    """Lazy holder of the engine and of the session factory for one database URL."""

    def __init__(self, url: str) -> None:
        """Keep the URL; no engine and no connection yet.

        Args:
            url: SQLAlchemy URL with the `postgresql+psycopg` driver.
        """
        self._url = url
        self._engine: AsyncEngine | None = None
        self._sessionmaker: async_sessionmaker[AsyncSession] | None = None

    def __repr__(self) -> str:
        return "Database(url=<hidden>)"

    @property
    def engine(self) -> AsyncEngine:
        """The async engine, created on the first access."""
        if self._engine is None:
            self._engine = create_async_engine(
                self._url,
                pool_pre_ping=True,
                connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS},
            )
        return self._engine

    @property
    def sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        """The session factory bound to `engine`, created on the first access."""
        if self._sessionmaker is None:
            self._sessionmaker = async_sessionmaker(self.engine, expire_on_commit=False)
        return self._sessionmaker

    async def dispose(self) -> None:
        """Close the pool, if the engine was ever created."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None


async def is_database_reachable(database: Database) -> bool:
    """Tell whether the database answers a trivial query within a few seconds.

    Args:
        database: the database to probe.

    Returns:
        True if `SELECT 1` succeeded; False on any connection error or timeout.
    """
    try:
        async with asyncio.timeout(REACHABILITY_TIMEOUT_SECONDS):
            async with database.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError, TimeoutError) as error:
        # Only the error type: the message of the driver carries host, port and user.
        logger.warning("database is not reachable (%s)", type(error).__name__)
        return False
    return True


def get_database(request: Request) -> Database:
    """FastAPI dependency: the `Database` of the running app (set by `create_app()`)."""
    return request.app.state.database


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per request, closed at the end of the request."""
    async with get_database(request).sessionmaker() as session:
        yield session
