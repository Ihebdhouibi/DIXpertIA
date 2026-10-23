"""Two-factor authentication: TOTP codes and recovery codes (#44).

What lives where:
- the TOTP secret is encrypted here (Fernet, MFA_ENCRYPTION_KEY) before it
  reaches the database, and decrypted here to check a code: the key never
  enters the database, so read access to the database alone mints no code;
- recovery codes are shown once, then kept only as an HMAC keyed with the
  same secret key: a dump cannot even be brute-forced offline without it;
- the rows are reached through the auth_mfa_*() SECURITY DEFINER functions
  (migration e9c3a1f7b204), never read by the application role directly.

A code is accepted for the current 30-second step or one either side (clock
drift), and only if that step is later than the last one accepted: the same
code cannot be used twice, even inside its window.
"""

import base64
import hashlib
import hmac
import io
import secrets
import time
from dataclasses import dataclass

import pyotp
import segno
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings

ISSUER = "DI Xpertia"
STEP_SECONDS = 30
DRIFT_STEPS = 1
RECOVERY_CODES = 10
# 10 characters of base32 (50 bits each): long enough that, with the HMAC key,
# none can be guessed, short enough to type from paper.
_RECOVERY_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def enabled() -> bool:
    """Whether two-factor is configured at all on this server."""
    return bool(settings.MFA_ENCRYPTION_KEY)


def required_for(role: str) -> bool:
    return enabled() and role in settings.MFA_REQUIRED_ROLES


def _fernet() -> Fernet:
    return Fernet(settings.MFA_ENCRYPTION_KEY.encode())


def encrypt(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt(secret_enc: str) -> str | None:
    try:
        return _fernet().decrypt(secret_enc.encode()).decode()
    except InvalidToken:
        # Encrypted under another key: the key was lost or rotated. The
        # account cannot use this secret any more and must be reset.
        return None


def new_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret, interval=STEP_SECONDS).provisioning_uri(name=email, issuer_name=ISSUER)


def qr_svg_data_uri(uri: str) -> str:
    """The QR code for an authenticator app, as an SVG data URI the page can
    show directly: drawn here, so no QR library is shipped to the browser."""
    out = io.BytesIO()
    segno.make(uri, error="m").save(out, kind="svg", scale=5, border=2, dark="#0b0b0f", light="#ffffff")
    return "data:image/svg+xml;base64," + base64.b64encode(out.getvalue()).decode()


def matching_step(secret: str, code: str, now: float | None = None) -> int | None:
    """The 30-second step `code` belongs to, within the drift allowed, or None."""
    code = (code or "").strip().replace(" ", "")
    if not (len(code) == 6 and code.isdigit()):
        return None
    totp = pyotp.TOTP(secret, interval=STEP_SECONDS)
    current = int((now if now is not None else time.time()) // STEP_SECONDS)
    for step in range(current - DRIFT_STEPS, current + DRIFT_STEPS + 1):
        if hmac.compare_digest(totp.at(step * STEP_SECONDS), code):
            return step
    return None


def new_recovery_codes() -> list[str]:
    """Ten codes like `k7mq-2xrpd`, shown to the account once."""
    def one() -> str:
        raw = "".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(10))
        return f"{raw[:5]}-{raw[5:]}"
    return [one() for _ in range(RECOVERY_CODES)]


def recovery_hash(code: str) -> str:
    normalised = (code or "").strip().lower().replace("-", "").replace(" ", "")
    return hmac.new(settings.MFA_ENCRYPTION_KEY.encode(), normalised.encode(), hashlib.sha256).hexdigest()


# --- The database, through the auth_mfa_*() functions ------------------------------

@dataclass
class State:
    enabled: bool
    secret: str | None
    last_step: int | None
    recovery_left: int


def state(db: Session, user_id: str) -> State | None:
    row = db.execute(text("SELECT * FROM auth_mfa_state(:u)"), {"u": user_id}).mappings().first()
    if row is None:
        return None
    return State(enabled=row["enabled"], secret=decrypt(row["secret_enc"]),
                 last_step=row["last_step"], recovery_left=row["recovery_left"])


def begin(db: Session, user_id: str, secret: str) -> bool:
    return db.execute(text("SELECT auth_mfa_begin(:u, :s)"), {"u": user_id, "s": encrypt(secret)}).scalar_one()


def enable(db: Session, user_id: str, step: int, codes: list[str]) -> bool:
    return db.execute(text("SELECT auth_mfa_enable(:u, :st, :h)"),
                      {"u": user_id, "st": step, "h": [recovery_hash(c) for c in codes]}).scalar_one()


def use_step(db: Session, user_id: str, step: int) -> bool:
    return db.execute(text("SELECT auth_mfa_use_step(:u, :st)"), {"u": user_id, "st": step}).scalar_one()


def use_recovery(db: Session, user_id: str, code: str) -> bool:
    return db.execute(text("SELECT auth_mfa_use_recovery(:u, :h)"),
                      {"u": user_id, "h": recovery_hash(code)}).scalar_one()


def replace_recovery(db: Session, user_id: str, codes: list[str]) -> bool:
    return db.execute(text("SELECT auth_mfa_replace_recovery(:u, :h)"),
                      {"u": user_id, "h": [recovery_hash(c) for c in codes]}).scalar_one()


def remove(db: Session, user_id: str) -> bool:
    return db.execute(text("SELECT auth_mfa_remove(:u)"), {"u": user_id}).scalar_one()
