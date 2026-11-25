"""HTTP routes of the API, mounted under /api/v1 by `create_app()` (plan NUC-01, D4).

Session routes (plan ACE-01, D1 and D2): `POST /session` signs in, `GET /session` says who is
signed in and `DELETE /session` signs out. The token travels only in the `lastro_session`
cookie (`HttpOnly`, `Secure`, `SameSite=Lax`), kept by the browser up to the 12-hour cap;
the 2-hour idle expiry is decided on the server (plan D9). Protected routes of later
features depend on `require_signed_in_member`.

Client routes (plan CAD-03, D4 and D5): `POST /clients` registers a client (manager only),
`GET /clients` lists the visible ones and `GET /clients/{client_id}` opens one. A missing
client and a client of another firm get the same 404 body (P-01).
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from lastro.access import service as access
from lastro.access.contracts import (
    InvalidCredentialsError,
    MultipleFirmsError,
    SessionEndedError,
    SignedInMember,
)
from lastro.core.db import Database, get_database, get_session, is_database_reachable
from lastro.registry import service as registry
from lastro.registry.contracts import (
    ClientNotAssignedError,
    ClientNotFoundError,
    ClientSummary,
    DuplicateCnpjError,
    InvalidClientDataError,
    ManagerOnlyError,
)

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
MULTIPLE_FIRMS_TITLE = "Mais de um escritório"
MULTIPLE_FIRMS_DETAIL = (
    "Este usuário está em mais de um escritório. "
    "Peça ao chefe um usuário para cada escritório."
)

# Plan CAD-03, questions 1 and 3 to 5 (25/11).
INVALID_DATA_TITLE = "Dados inválidos"
FORBIDDEN_TITLE = "Ação não permitida"
MANAGER_ONLY_DETAIL = "Só o chefe do escritório pode fazer isso."
NOT_ASSIGNED_DETAIL = "Atribua este cliente a você para fazer isso."
NOT_FOUND_TITLE = "Cliente não encontrado"
NO_CLIENT_ACCESS_DETAIL = "Você não tem acesso a este cliente."
DUPLICATE_CNPJ_TITLE = "CNPJ já cadastrado"
DUPLICATE_CNPJ_DETAIL = "Este CNPJ já está cadastrado no seu escritório."

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


class ClientRequest(BaseModel):
    """Name and CNPJ typed by the manager. Emptiness and format are checked by the registry,
    so the user gets the message of the ficha, not a validation text in English."""

    name: str
    cnpj: str


class ClientResponse(BaseModel):
    """Client as shown to the member: never the firm id (plan CAD-03, D5)."""

    id: str
    name: str
    cnpj: str


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


async def _multiple_firms(_request: Request, _error: Exception) -> JSONResponse:
    return _problem(
        status.HTTP_409_CONFLICT, MULTIPLE_FIRMS_TITLE, MULTIPLE_FIRMS_DETAIL
    )


async def _invalid_client_data(_request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, InvalidClientDataError)
    return _problem(
        status.HTTP_422_UNPROCESSABLE_CONTENT, INVALID_DATA_TITLE, error.message
    )


async def _manager_only(_request: Request, _error: Exception) -> JSONResponse:
    return _problem(status.HTTP_403_FORBIDDEN, FORBIDDEN_TITLE, MANAGER_ONLY_DETAIL)


async def _client_not_assigned(_request: Request, _error: Exception) -> JSONResponse:
    return _problem(status.HTTP_403_FORBIDDEN, FORBIDDEN_TITLE, NOT_ASSIGNED_DETAIL)


async def _client_not_found(_request: Request, _error: Exception) -> JSONResponse:
    # One body for a missing client and a client of another firm (P-01, c3).
    return _problem(status.HTTP_404_NOT_FOUND, NOT_FOUND_TITLE, NO_CLIENT_ACCESS_DETAIL)


async def _duplicate_cnpj(_request: Request, _error: Exception) -> JSONResponse:
    return _problem(
        status.HTTP_409_CONFLICT, DUPLICATE_CNPJ_TITLE, DUPLICATE_CNPJ_DETAIL
    )


# Registered by `create_app()`: error answers in RFC 9457 (plans ACE-01 D6, D10 and
# CAD-03 D4; I-14).
EXCEPTION_HANDLERS = {
    InvalidCredentialsError: _invalid_credentials,
    MultipleFirmsError: _multiple_firms,
    SessionEndedError: _session_ended,
    SignInRequiredError: _sign_in_required,
    InvalidClientDataError: _invalid_client_data,
    ManagerOnlyError: _manager_only,
    ClientNotAssignedError: _client_not_assigned,
    ClientNotFoundError: _client_not_found,
    DuplicateCnpjError: _duplicate_cnpj,
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
    "/session",
    response_model=SessionIdentity,
    responses={**UNAUTHORIZED_RESPONSES, status.HTTP_409_CONFLICT: {"model": Problem}},
)
async def sign_in(
    credentials: SignInRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> SessionIdentity:
    """Sign in with an individual login and open a session (ACE-01, c1, c2, c6; D10)."""
    opened = await access.sign_in(db, credentials.username, credentials.password)
    response.set_cookie(
        SESSION_COOKIE,
        opened.token,
        max_age=int(access.SESSION_MAX_DURATION.total_seconds()),
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


def _client_response(client: ClientSummary) -> ClientResponse:
    return ClientResponse(id=client.client_id, name=client.name, cnpj=client.cnpj)


@router.post(
    "/clients",
    status_code=status.HTTP_201_CREATED,
    response_model=ClientResponse,
    responses={
        **UNAUTHORIZED_RESPONSES,
        status.HTTP_403_FORBIDDEN: {"model": Problem},
        status.HTTP_409_CONFLICT: {"model": Problem},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": Problem},
    },
)
async def register_client(
    member: Annotated[SignedInMember, Depends(require_signed_in_member)],
    body: ClientRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ClientResponse:
    """Register a client with name and CNPJ in the manager's firm (CAD-03, c1, c2, c4)."""
    client = await registry.register_client(db, member, body.name, body.cnpj)
    return _client_response(client)


@router.get(
    "/clients", response_model=list[ClientResponse], responses=UNAUTHORIZED_RESPONSES
)
async def list_clients(
    member: Annotated[SignedInMember, Depends(require_signed_in_member)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[ClientResponse]:
    """Clients of the firm that the member may see (CAD-03, c1, c3; P-09)."""
    clients = await registry.list_clients(db, member, access.responsible_member_ids)
    return [_client_response(client) for client in clients]


@router.get(
    "/clients/{client_id}",
    response_model=ClientResponse,
    responses={
        **UNAUTHORIZED_RESPONSES,
        status.HTTP_403_FORBIDDEN: {"model": Problem},
        status.HTTP_404_NOT_FOUND: {"model": Problem},
    },
)
async def get_client(
    client_id: str,
    member: Annotated[SignedInMember, Depends(require_signed_in_member)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ClientResponse:
    """Open one client; missing or of another firm: the same 404 (CAD-03, c3; P-01)."""
    client = await registry.get_client(
        db, member, client_id, access.responsible_member_ids
    )
    return _client_response(client)
