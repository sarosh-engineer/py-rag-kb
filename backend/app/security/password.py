"""Password hashing.

Argon2id via ``pwdlib`` is a memory-hard password hash. This module does not
implement the algorithm. Callers pass the plaintext in and receive a hash
string back. The plaintext is not logged.
"""

import logging

from pwdlib import PasswordHash

logger = logging.getLogger("app.security.password")

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128

_hasher = PasswordHash.recommended()


def validate_password(password: str) -> None:
    """Reject passwords that are too short, too long, or lack mixed characters.

    Length is the main control. One letter and one digit blocks a few
    obvious dictionary values without a long list of symbol rules.
    """
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be {MIN_PASSWORD_LENGTH} to {MAX_PASSWORD_LENGTH} characters."
        )
    if not any(character.isalpha() for character in password):
        raise ValueError("Password must include at least one letter.")
    if not any(character.isdigit() for character in password):
        raise ValueError("Password must include at least one digit.")


def hash_password(password: str) -> str:
    """Return an Argon2id hash. The result is not reversible."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return whether ``password`` matches ``password_hash``.

    A corrupt or unknown hash is a failed verification, not a server error.
    """
    try:
        return bool(_hasher.verify(password, password_hash))
    except Exception:
        logger.info("password hash could not be verified", extra={"exception_type": "hash_rejected"})
        return False
