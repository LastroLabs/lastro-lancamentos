"""Command line of the access module: first access of a new firm (ADM-01).

    python -m lastro.access.admin criar-escritorio --escritorio ... --usuario ... --nome ...

The password comes only from the `LASTRO_SENHA_CHEFE` variable, or is typed twice without
echo when there is a terminal. It is never accepted as an argument and never written out.
Exit codes: 0 done, 1 login already exists or database failure, 2 wrong usage.
"""

import argparse
import asyncio
import getpass
import os
import sys
from collections.abc import Sequence
from typing import NoReturn

from sqlalchemy.exc import OperationalError, SQLAlchemyError

from lastro.access import service
from lastro.access.contracts import UsernameTakenError
from lastro.core.config import get_settings
from lastro.core.db import Database

ENV_VAR = "LASTRO_SENHA_CHEFE"
MIN_PASSWORD_LENGTH = 8

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_USAGE = 2

MSG_FIRM_MISSING = "Informe o nome do escritório."
MSG_USER_MISSING = "Informe o usuário do chefe."
MSG_NAME_MISSING = "Informe o nome do chefe."
MSG_PASSWORD_MISSING = f"Defina a senha do chefe na variável {ENV_VAR}."
MSG_PASSWORD_ARGUMENT = (
    f"Não escreva a senha no comando. Use a variável {ENV_VAR}."
)
MSG_PASSWORD_SHORT = (
    f"A senha do chefe deve ter pelo menos {MIN_PASSWORD_LENGTH} caracteres."
)
MSG_PASSWORDS_DIFFER = "As senhas digitadas são diferentes. Tente de novo."
MSG_DATABASE = (
    "Não foi possível acessar o banco de dados. Confira a conexão e tente de novo."
)
MSG_NOT_SAVED = "Não foi possível criar o escritório. Nada foi gravado."
MSG_USAGE = (
    "Use: python -m lastro.access.admin criar-escritorio"
    " --escritorio NOME --usuario LOGIN --nome NOME_DO_CHEFE"
)


class _Refused(Exception):
    """A usage error with the message to show; ends with exit code 2."""


class _Parser(argparse.ArgumentParser):
    """Parser whose errors are Portuguese and never echo what was typed."""

    def error(self, message: str) -> NoReturn:
        raise _Refused(MSG_USAGE)


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="python -m lastro.access.admin", allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", parser_class=_Parser)
    create = commands.add_parser(
        "criar-escritorio",
        help="cria um escritório e o seu chefe",
        allow_abbrev=False,
    )
    create.add_argument("--escritorio", default="", help="nome do escritório")
    create.add_argument("--usuario", default="", help="usuário (login) do chefe")
    create.add_argument("--nome", default="", help="nome do chefe")
    # Exists only to be refused; hidden from --help.
    create.add_argument("--senha", default=None, help=argparse.SUPPRESS)
    return parser


def _read_password() -> str:
    typed = os.environ.get(ENV_VAR)
    if typed is None and sys.stdin.isatty():
        typed = getpass.getpass("Senha do chefe: ")
        if typed and getpass.getpass("Repita a senha: ") != typed:
            raise _Refused(MSG_PASSWORDS_DIFFER)
    if not typed:
        raise _Refused(MSG_PASSWORD_MISSING)
    if len(typed) < MIN_PASSWORD_LENGTH:
        raise _Refused(MSG_PASSWORD_SHORT)
    return typed


def _validate(args: argparse.Namespace) -> tuple[str, str, str, str]:
    """Check the input in the order of plan D4; the first problem stops everything."""
    if args.senha is not None:
        raise _Refused(MSG_PASSWORD_ARGUMENT)
    firm = args.escritorio.strip()
    username = args.usuario.strip()
    name = args.nome.strip()
    if not firm:
        raise _Refused(MSG_FIRM_MISSING)
    if not username:
        raise _Refused(MSG_USER_MISSING)
    if not name:
        raise _Refused(MSG_NAME_MISSING)
    return firm, username, name, _read_password()


async def _create(firm: str, username: str, name: str, password: str) -> None:
    database = Database(get_settings().database_url)
    try:
        async with database.sessionmaker() as session:
            await service.create_firm_with_manager(
                session, firm, username, name, password
            )
    finally:
        await database.dispose()


def _write(stream, text: str) -> None:
    stream.write(text + "\n")
    stream.flush()


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command and return its exit code."""
    try:
        args = _build_parser().parse_args(argv)
        if args.command != "criar-escritorio":
            raise _Refused(MSG_USAGE)
        firm, username, name, password = _validate(args)
    except _Refused as refusal:
        _write(sys.stderr, str(refusal))
        return EXIT_USAGE
    except SystemExit as stop:  # --help
        return int(stop.code or 0)

    try:
        asyncio.run(_create(firm, username, name, password))
    except UsernameTakenError:
        _write(sys.stderr, f"O usuário {username} já existe. Nada foi alterado.")
        return EXIT_REFUSED
    except (OperationalError, OSError, TimeoutError):
        _write(sys.stderr, MSG_DATABASE)
        return EXIT_REFUSED
    except SQLAlchemyError:
        _write(sys.stderr, MSG_NOT_SAVED)
        return EXIT_REFUSED
    except Exception:  # noqa: BLE001 - e.g. missing DATABASE_URL; never show a traceback
        _write(sys.stderr, MSG_DATABASE)
        return EXIT_REFUSED
    _write(sys.stdout, f"Escritório {firm} criado. O chefe {username} já pode entrar.")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
