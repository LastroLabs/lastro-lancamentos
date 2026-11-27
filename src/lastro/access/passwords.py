"""Password hashing with Argon2 (plan ACE-01, D4 and D5). Internal to the access module.

The parameters are the defaults of `argon2-cffi` (RFC 9106 low-memory profile). A stored
hash carries its own parameters, so changing them later does not break old hashes.
"""

import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

# Shortest password accepted when someone creates one (admin command and invitation accept).
MIN_PASSWORD_LENGTH = 8

_HASHER = PasswordHasher()
# Hash of a random secret that nobody knows, checked when there is no stored hash (plan D5).
# Built at import, so even the first refusal of the process costs one hash, like the others.
_THROWAWAY_HASH = _HASHER.hash(secrets.token_urlsafe(32))


def hash_password(password: str) -> str:
    """Hash a password for `usuario.credencial_hash`.

    Args:
        password: the password in clear; never stored nor logged.

    Returns:
        The Argon2 hash in PHC format.
    """
    return _HASHER.hash(password)


def verify_password(stored_hash: str | None, password: str) -> bool:
    """Tell whether a password matches a stored hash, with the same cost when there is none.

    Without a hash (unknown user or invitation still pending), the password is checked
    against a throwaway hash, so the answer takes as long as a real check and does not
    reveal which accounts exist (plan D5).

    Args:
        stored_hash: the hash from `usuario.credencial_hash`, or None.
        password: the password typed by the user.

    Returns:
        True only if there is a stored hash and the password matches it.
    """
    try:
        matches = _HASHER.verify(stored_hash or _THROWAWAY_HASH, password)
    except VerificationError, InvalidHashError:
        return False
    return matches and stored_hash is not None
