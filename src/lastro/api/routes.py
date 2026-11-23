"""HTTP routes of the API, mounted under /api/v1 by `create_app()` (plan NUC-01, D4)."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from lastro.core.db import Database, get_database, is_database_reachable

PROBLEM_JSON = "application/problem+json"
DATABASE_UNAVAILABLE_TITLE = "Serviço indisponível"
DATABASE_UNAVAILABLE_DETAIL = (
    "O banco de dados não está respondendo. Tente de novo em alguns minutos."
)

router = APIRouter()


class HealthStatus(BaseModel):
    """Body of a healthy answer: the API is up and the database answered."""

    api: Literal["up"]
    database: Literal["connected"]


class Problem(BaseModel):
    """Error body in RFC 9457 (application/problem+json)."""

    type: str
    title: str
    status: int
    detail: str


@router.get(
    "/health",
    response_model=HealthStatus,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": Problem}},
)
async def health(
    database: Annotated[Database, Depends(get_database)],
) -> HealthStatus | JSONResponse:
    """Say whether the API and the database are up. No login; no internal detail."""
    if await is_database_reachable(database):
        return HealthStatus(api="up", database="connected")
    problem = Problem(
        type="about:blank",
        title=DATABASE_UNAVAILABLE_TITLE,
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=DATABASE_UNAVAILABLE_DETAIL,
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=problem.model_dump(),
        media_type=PROBLEM_JSON,
    )
