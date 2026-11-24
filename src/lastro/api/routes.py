"""HTTP routes of the API, mounted under /api/v1 by `create_app()` (plan NUC-01, D4).

Session routes (plan ACE-01, D1 and D2): `POST /session` signs in, `GET /session` says who is
signed in and `DELETE /session` signs out. The token travels only in the `lastro_session`
cookie (`HttpOnly`, `Secure`, `SameSite=Lax`). Protected routes of later features depend on
`require_signed_in_member`.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from lastro.access import service as access
from lastro.access.contracts import (
    InvalidCredentialsError,
    SessionEndedError,
    SignedInMember,
)
from lastro.core.db import Database, get_database, get_session, is_database_reachable

PROBLEM_JSON = "application/problem+json"
DATABASE_UNAVAILABLE_TITLE = "Serviço indisponível"
DATABASE_UNAVAILABLE_DETAIL = (
    "O banco de dados não está respondendo. Tente de novo em alguns minutos."
)

SESSION_COOKIE = "lastro_session"
SESSION_COOKIE_PATH = "/api"
UNAUTHORIZED_TITLE = "Sem acesso"
WRONG_CREDENTIALS_DETAIL = "Usuário ou senha incorretos."
SESSION_ENDED_DETAIL = "Sua sessão terminou. Entre de novo."
SIGN_IN_REQUIRED_DETAIL = "Entre para continuar."

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


class SignInRequest(BaseModel):
    """Credentials typed on the sign-in page. The password may be empty (ACE-01, c6)."""

    username: str
    password: str


class SessionIdentity(BaseModel):
    """Who is signed in. Never carries the password, its hash or the session token."""

    username: str
    name: str
    role: Literal["manager", "accountant"]
    firm_id: str
    firm_name: str


class SignInRequiredError(Exception):
    """A protected route was called without a session cookie."""


def _problem(status_code: int, title: str, detail: str) -> JSONResponse:
    problem = Problem(
        type="about:blank", title=title, status=status_code, detail=detail
    )
    return JSONResponse(
        status_code=status_code, content=problem.model_dump(), media_type=PROBLEM_JSON
    )


def _unauthorized(detail: str) -> JSONResponse:
    return _problem(status.HTTP_401_UNAUTHORIZED, UNAUTHORIZED_TITLE, detail)


async def _invalid_credentials(_request: Request, _error: Exception) -> JSONResponse:
    return _unauthorized(WRONG_CREDENTIALS_DETAIL)


async def _session_ended(_request: Request, _error: Exception) -> JSONResponse:
    response = _unauthorized(SESSION_ENDED_DETAIL)
    response.delete_cookie(
        SESSION_COOKIE, path=SESSION_COOKIE_PATH, secure=True, httponly=True
    )
    return response


async def _sign_in_required(_request: Request, _error: Exception) -> JSONResponse:
    return _unauthorized(SIGN_IN_REQUIRED_DETAIL)


# Registered by `create_app()`: the 401 answers in RFC 9457 (plan ACE-01, D6; I-14).
EXCEPTION_HANDLERS = {
    InvalidCredentialsError: _invalid_credentials,
    SessionEndedError: _session_ended,
    SignInRequiredError: _sign_in_required,
}

UNAUTHORIZED_RESPONSES = {status.HTTP_401_UNAUTHORIZED: {"model": Problem}}


def _session_token(request: Request) -> str:
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        raise SignInRequiredError
    return cookie


async def require_signed_in_member(
    request: Request, db: Annotated[AsyncSession, Depends(get_session)]
) -> SignedInMember:
    """FastAPI dependency for protected routes: the member of the session cookie.

    Raises:
        SignInRequiredError: without the cookie (401 "Entre para continuar.").
        SessionEndedError: with a cookie that no longer opens a session (401 "Sua sessão
            terminou. Entre de novo.").
    """
    return await access.identify(db, _session_token(request))


def _identity(member: SignedInMember) -> SessionIdentity:
    return SessionIdentity(
        username=member.username,
        name=member.name,
        role=member.role.value,
        firm_id=member.firm_id,
        firm_name=member.firm_name,
    )


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
    return _problem(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        DATABASE_UNAVAILABLE_TITLE,
        DATABASE_UNAVAILABLE_DETAIL,
    )


@router.post(
    "/session", response_model=SessionIdentity, responses=UNAUTHORIZED_RESPONSES
)
async def sign_in(
    credentials: SignInRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> SessionIdentity:
    """Sign in with an individual login and open a session (ACE-01, c1, c2 and c6)."""
    opened = await access.sign_in(db, credentials.username, credentials.password)
    response.set_cookie(
        SESSION_COOKIE,
        opened.token,
        expires=opened.expires_at,
        path=SESSION_COOKIE_PATH,
        secure=True,
        httponly=True,
        samesite="lax",
    )
    return _identity(opened.member)


@router.get(
    "/session", response_model=SessionIdentity, responses=UNAUTHORIZED_RESPONSES
)
async def current_session(
    member: Annotated[SignedInMember, Depends(require_signed_in_member)],
) -> SessionIdentity:
    """Say who is signed in: login, name, role and firm (ACE-01, c1, c3, c4 and c5)."""
    return _identity(member)


@router.delete(
    "/session",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=UNAUTHORIZED_RESPONSES,
)
async def sign_out(
    request: Request, db: Annotated[AsyncSession, Depends(get_session)]
) -> Response:
    """End the session now; the same cookie no longer gives access (ACE-01, c4)."""
    await access.sign_out(db, _session_token(request))
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        SESSION_COOKIE, path=SESSION_COOKIE_PATH, secure=True, httponly=True
    )
    return response
