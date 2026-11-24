"""Creation of the FastAPI app (plan NUC-01, c2).

Other features register their routers under `API_V1_PREFIX`:

    app.include_router(router, prefix=API_V1_PREFIX)

Creating the app does not connect to the database; the first request that needs it does.
Uvicorn builds it with `uvicorn lastro.api.app:create_app --factory`.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from lastro.ai.service import load_name_protection_level
from lastro.api import routes
from lastro.core.config import Settings, get_settings
from lastro.core.db import Database

API_V1_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app with its database holder and the /api/v1 routes.

    Args:
        settings: settings to use; when None, they are read from the environment.

    Returns:
        The FastAPI app. `app.state.settings` and `app.state.database` hold the settings and
        the lazy `Database` used by the routes.

    Raises:
        InvalidNameProtectionLevelError: if `NAME_PROTECTION_LEVEL` is not a known level; the
            app does not start without name protection (IA-01, c4).
    """
    settings = settings or get_settings()
    name_protection_level = load_name_protection_level()
    database = Database(settings.database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        await database.dispose()

    app = FastAPI(title="Lastro", lifespan=lifespan)
    app.state.settings = settings
    app.state.database = database
    app.state.name_protection_level = name_protection_level
    for error, handler in routes.EXCEPTION_HANDLERS.items():
        app.add_exception_handler(error, handler)
    app.include_router(routes.router, prefix=API_V1_PREFIX)
    return app
