"""Two-factor authentication endpoints (#44).

Signed in (a session):
- GET  /api/mfa                     whether it is on, required, codes left
- POST /api/mfa/setup               a new secret, its QR code; not active yet
- POST /api/mfa/confirm             prove one code: active, recovery codes once
- POST /api/mfa/recovery-codes      new codes, against a current code
- POST /api/mfa/disable             against the password; not for a required role
- POST /api/users/{id}/mfa/reset    the admin, for someone's lost phone

The sign-in's second step, public, each with its own short-lived token (#44):
- POST /api/mfa/verify              the challenge token and a code -> a session
- POST /api/mfa/enrol/setup         the enrolment token -> a secret, a QR code
- POST /api/mfa/enrol/confirm       the enrolment token and a code -> a session

Every code attempt counts against MFA_MAX_FAILURES per account (#175's
counters), so the million 6-digit codes cannot be tried; a used code's step is
recorded, so it cannot be replayed. Enabling, disabling and resetting sign the
account out everywhere else (token_version); the answers that follow carry a
fresh session for the caller.
"""

from fastapi import APIRouter, Depends
from jose import JWTError
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.identity import set_identity
from app.core.security import (
    MFA_CHALLENGE, MFA_ENROL, create_access_token, decode_purpose_token, verify_password,
)
from app.i18n import ApiError
from app.models.user import User
from app.schemas.api import LoginOut, UserOut
from app.services import mfa, throttle
from app.services.audit import record_event

router = APIRouter()
public = APIRouter(dependencies=[Depends(throttle.limit_public_requests)])


# --- Request and response bodies ------------------------------------------------------

class CodeIn(BaseModel):
    code: str = Field(min_length=6, max_length=8)


class PasswordIn(BaseModel):
    password: str = Field(min_length=1, max_length=200)


class VerifyIn(BaseModel):
    challengeToken: str
    # One of the two: the app's 6-digit code, or a recovery code.
    code: str | None = Field(None, max_length=8)
    recoveryCode: str | None = Field(None, max_length=20)


class EnrolSetupIn(BaseModel):
    enrolToken: str


class EnrolConfirmIn(BaseModel):
    enrolToken: str
    code: str = Field(min_length=6, max_length=8)


class StatusOut(BaseModel):
    available: bool
    enabled: bool
    required: bool
    recoveryCodesLeft: int


class SetupOut(BaseModel):
    """The new secret, once: as a QR code, and as text for manual entry."""
    secret: str
    otpauthUri: str
    qrCode: str


class RecoveryCodesOut(BaseModel):
    """Shown once. Only their HMAC is kept."""
    recoveryCodes: list[str]
    # A fresh session: enabling signs every older one out, this one included.
    access_token: str | None = None
    token_type: str = "bearer"
    user: UserOut | None = None


class SessionOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Helpers --------------------------------------------------------------------------

def _require_configured() -> None:
    if not mfa.enabled():
        raise ApiError(503, "mfa.not_configured")


def _session_state(db: Session, user_id: str):
    return db.execute(text("SELECT * FROM auth_session(:u)"), {"u": user_id}).mappings().first()


def _fresh_token(db: Session, user_id: str) -> str:
    state = _session_state(db, user_id)
    return create_access_token(data={"sub": user_id, "role": state["role"], "ver": state["token_version"]})


def _purpose_identity(db: Session, token: str, purpose: str) -> tuple[str, str]:
    """(user id, role) from a challenge or enrolment token, if it still holds:
    the right purpose, not expired, the account active and its sessions not
    revoked since. Then the request acts as that account."""
    try:
        claims = decode_purpose_token(token, purpose)
    except JWTError:
        raise ApiError(401, "mfa.expired") from None
    user_id = claims.get("sub")
    state = _session_state(db, user_id) if user_id else None
    if (state is None or not state["isActive"] or not state["isVerified"]
            or claims.get("ver") != state["token_version"]):
        raise ApiError(401, "mfa.expired")
    set_identity(user_id, state["role"])
    # The identity reaches PostgreSQL when a transaction begins (#43), and one
    # is already open from the check above: end it, so the next one carries
    # this account, which the auth_mfa_*() functions check.
    db.commit()
    return user_id, state["role"]


def _count_attempt(db: Session, user_id: str) -> None:
    """One code attempt against the account's limit; committed at once, so it
    counts even when the code is then wrong."""
    result = throttle.hit(db, throttle.MFA_ACCOUNT, throttle.account_key(user_id),
                          settings.MFA_MAX_FAILURES, settings.LOGIN_LOCKOUT_MINUTES * 60)
    db.commit()
    if result < 0:
        raise throttle.too_many(-result)


def _passed(db: Session, user_id: str) -> None:
    throttle.clear(db, throttle.MFA_ACCOUNT, throttle.account_key(user_id))


def _setup(db: Session, user_id: str, email: str) -> SetupOut:
    secret = mfa.new_secret()
    if not mfa.begin(db, user_id, secret):
        raise ApiError(409, "mfa.already_enabled")
    db.commit()
    uri = mfa.provisioning_uri(secret, email)
    return SetupOut(secret=secret, otpauthUri=uri, qrCode=mfa.qr_svg_data_uri(uri))


def _confirm(db: Session, user_id: str, code: str) -> list[str]:
    """Prove the first code; activate; return the recovery codes, once."""
    state = mfa.state(db, user_id)
    if state is None or state.secret is None:
        raise ApiError(409, "mfa.not_started")
    if state.enabled:
        raise ApiError(409, "mfa.already_enabled")
    _count_attempt(db, user_id)
    step = mfa.matching_step(state.secret, code)
    codes = mfa.new_recovery_codes()
    if step is None or not mfa.enable(db, user_id, step, codes):
        db.commit()
        raise ApiError(400, "mfa.wrong_code")
    _passed(db, user_id)
    record_event(db, "user.mfa_enabled", "user", user_id)
    db.commit()
    return codes


# --- Signed in --------------------------------------------------------------------------

@router.get("/mfa", response_model=StatusOut)
def status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    state = mfa.state(db, user.id) if mfa.enabled() else None
    return StatusOut(available=mfa.enabled(), enabled=bool(state and state.enabled),
                     required=mfa.required_for(user.role),
                     recoveryCodesLeft=state.recovery_left if state and state.enabled else 0)


@router.post("/mfa/setup", response_model=SetupOut)
def setup(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_configured()
    return _setup(db, user.id, user.email)


@router.post("/mfa/confirm", response_model=RecoveryCodesOut)
def confirm(body: CodeIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_configured()
    codes = _confirm(db, user.id, body.code)
    return RecoveryCodesOut(recoveryCodes=codes, access_token=_fresh_token(db, user.id))


@router.post("/mfa/recovery-codes", response_model=RecoveryCodesOut)
def renew_recovery_codes(body: CodeIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """New recovery codes; the old ones stop working. Asks for a current code,
    so a session left open on someone else's screen cannot take them."""
    _require_configured()
    state = mfa.state(db, user.id)
    if state is None or not state.enabled or state.secret is None:
        raise ApiError(409, "mfa.not_enabled")
    _count_attempt(db, user.id)
    step = mfa.matching_step(state.secret, body.code)
    if step is None or not mfa.use_step(db, user.id, step):
        db.commit()
        raise ApiError(400, "mfa.wrong_code")
    codes = mfa.new_recovery_codes()
    mfa.replace_recovery(db, user.id, codes)
    _passed(db, user.id)
    record_event(db, "user.mfa_recovery_renewed", "user", user.id)
    db.commit()
    return RecoveryCodesOut(recoveryCodes=codes)


@router.post("/mfa/disable", response_model=SessionOut)
def disable(body: PasswordIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Turn it off, against the password. Refused for a role that requires it:
    that account would only be sent back to enrolment at its next sign-in."""
    _require_configured()
    if mfa.required_for(user.role):
        raise ApiError(409, "mfa.required")
    account = db.execute(text("SELECT * FROM auth_account_by_email(:e)"), {"e": user.email}).first()
    if account is None or not verify_password(body.password, account.hashedPassword):
        # 400, not 401: the UI reads a 401 on a signed-in request as an expired
        # session and signs the user out (#220).
        raise ApiError(400, "auth.wrong_current_password")
    if not mfa.remove(db, user.id):
        raise ApiError(409, "mfa.not_enabled")
    record_event(db, "user.mfa_disabled", "user", user.id)
    db.commit()
    return SessionOut(access_token=_fresh_token(db, user.id))


@router.post("/users/{user_id}/mfa/reset", status_code=204)
def reset(user_id: str, db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))):
    """For a lost phone: removes the account's second factor and signs it out
    everywhere. Its next sign-in enrols again if its role requires it. The
    admin's own goes through disable, or deploy's reset_mfa.py."""
    if user_id == admin.id:
        raise ApiError(409, "mfa.reset_self")
    if not mfa.remove(db, user_id):
        raise ApiError(404, "mfa.not_enabled")
    record_event(db, "user.mfa_reset", "user", user_id)
    db.commit()


# --- The sign-in's second step ----------------------------------------------------------

@public.post("/mfa/verify", response_model=LoginOut)
def verify(body: VerifyIn, db: Session = Depends(get_db)):
    """The challenge token from /api/login and a code (or a recovery code)
    become a session."""
    _require_configured()
    user_id, _role = _purpose_identity(db, body.challengeToken, MFA_CHALLENGE)
    _count_attempt(db, user_id)
    state = mfa.state(db, user_id)
    if state is None or not state.enabled or state.secret is None:
        raise ApiError(401, "mfa.expired")
    if body.recoveryCode:
        ok = mfa.use_recovery(db, user_id, body.recoveryCode)
        if ok:
            record_event(db, "user.mfa_recovery_used", "user", user_id)
    else:
        step = mfa.matching_step(state.secret, body.code or "")
        ok = step is not None and mfa.use_step(db, user_id, step)
    if not ok:
        db.commit()
        raise ApiError(400, "mfa.wrong_code")
    _passed(db, user_id)
    db.commit()
    user = db.query(User).filter(User.id == user_id).first()
    return LoginOut(access_token=_fresh_token(db, user_id), user=UserOut.from_orm_row(user))


@public.post("/mfa/enrol/setup", response_model=SetupOut)
def enrol_setup(body: EnrolSetupIn, db: Session = Depends(get_db)):
    """Enrolment for a role that requires a second factor, before its first
    session: the enrolment token from /api/login stands in for one."""
    _require_configured()
    user_id, _role = _purpose_identity(db, body.enrolToken, MFA_ENROL)
    user = db.query(User).filter(User.id == user_id).first()
    return _setup(db, user_id, user.email)


@public.post("/mfa/enrol/confirm", response_model=RecoveryCodesOut)
def enrol_confirm(body: EnrolConfirmIn, db: Session = Depends(get_db)):
    _require_configured()
    user_id, _role = _purpose_identity(db, body.enrolToken, MFA_ENROL)
    codes = _confirm(db, user_id, body.code)
    user = db.query(User).filter(User.id == user_id).first()
    return RecoveryCodesOut(recoveryCodes=codes, access_token=_fresh_token(db, user_id),
                            user=UserOut.from_orm_row(user))
