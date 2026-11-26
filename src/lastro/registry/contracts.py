"""Contracts of the registry module (CAD-01, RF-CAD-01).

Immutable data exchanged between `registry.service` and the modules that consume
CNPJ validation (such as client registration and the API layer).
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CnpjValidationResult:
    """Outcome of validating and normalizing a numeric or alphanumeric CNPJ.

    Attributes:
        is_valid: Whether the input passed format and check-digit validation.
        normalized: 14-character uppercase CNPJ without mask when valid; `None`
            otherwise.
        error_message: Plain-Portuguese message explaining why the input was
            refused when invalid; `None` when valid.
    """

    is_valid: bool
    normalized: str | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class ClientSummary:
    """Client of the signed-in member's firm, as shown in the list and when opened (CAD-03).

    Contract in version 0 (plan CAD-03, D5). The firm id is never part of it.

    Attributes:
        client_id: id of the client.
        name: name of the client, without surrounding spaces.
        cnpj: 14-character uppercase CNPJ without mask.
    """

    client_id: str
    name: str
    cnpj: str


class InvalidClientDataError(Exception):
    """The name or the CNPJ of the client was refused; nothing was written.

    Attributes:
        message: plain-Portuguese message that says what to fix.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ManagerOnlyError(Exception):
    """Only the manager of the firm may do this (P-02); nothing was written."""


class ClientNotFoundError(Exception):
    """The client does not exist or belongs to another firm; both look the same (P-01)."""


class ClientNotAssignedError(Exception):
    """The manager of the same firm is not the responsible member of the client (P-09)."""


class DuplicateCnpjError(Exception):
    """The firm already has a client with this CNPJ; nothing was written."""
