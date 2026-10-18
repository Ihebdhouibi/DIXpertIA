"""Passwords, access tokens and single-use account tokens.

One module for all of it (#62). main.py used to keep its own copies of the
hashing and JWT helpers, so a rule added in one place was missing from the
other.

Two kinds of token, deliberately different in shape:

- Access tokens are JWTs carrying `typ: "access"` and the account's
  token_version. decode_access_token() refuses anything else, so a JWT minted
  for another purpose can never pass as a session.
- Reset and activation tokens are opaque random strings, not JWTs. Only their
  SHA-256 is stored (account_tokens), each is single use, and they are checked
  against the database, never by signature.
"""

import hashlib
import secrets
from datetime import datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

ACCESS = "access"

# A new password must be at least this long (#62). bcrypt reads at most 72
# bytes, so anything longer would be silently truncated: refused instead.
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        # Not a bcrypt hash, e.g. the unusable placeholder of an account that
        # was never activated.
        return False


# Checked when the e-mail matches no account, so a login takes as long whether
# the account exists or not (AUDIT-DB-009: 24 ms against 292 ms gave the
# existence of an account away). Same cost factor as a real hash.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def burn_password_check(plain_password: str) -> None:
    """Spend the time of one password check, for an e-mail with no account."""
    verify_password(plain_password, _DUMMY_HASH)


def unusable_password_hash() -> str:
    """A hash no password matches: the account must be activated first.

    Not a bcrypt string at all, so verify_password() answers False without
    any chance of a collision, and it cannot be mistaken for a real hash.
    """
    return "!unusable:" + secrets.token_hex(16)


def password_problem(password: str) -> tuple[str, dict] | None:
    """Why a new password is refused, as a message key and its parameters
    (app.i18n), or None if it is acceptable."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return "password.too_short", {"min": MIN_PASSWORD_LENGTH}
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return "password.too_long", {"max": MAX_PASSWORD_BYTES}
    if not password.strip():
        return "password.blank", {}
    return None


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """A session token. `data` carries sub and role; `ver` defaults to 0."""
    to_encode = {"ver": 0, **data, "typ": ACCESS}
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """The claims of a valid access token. Raises JWTError for anything else."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("typ") != ACCESS:
        raise JWTError("not an access token")
    return payload


def new_account_token() -> tuple[str, str]:
    """A fresh opaque token and the hash to store: (token, sha256 hex)."""
    token = secrets.token_urlsafe(32)
    return token, hash_account_token(token)


def hash_account_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
