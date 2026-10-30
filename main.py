import asyncio
import contextlib
import logging
import html
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import List, Literal, Optional
from fastapi import FastAPI, Depends, Query, Request, Response
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload
from starlette.concurrency import run_in_threadpool
from dotenv import load_dotenv

from app.core.config import settings
from app.core.identity import clear_identity, set_identity
from app.schemas.api import (
    HealthOut,
    ActivationSentOut,
    EmployeeOut,
    LoginOut,
    MessageOut,
    UserCreatedOut,
    LeaveRequestCreate,
    LeaveRequestOut,
    PayslipOut,
    UserOut,
)
from app.core.database import SessionLocal, get_db
from app.core.deps import get_current_user, session_identity
from app.core.security import (
    MFA_CHALLENGE,
    MFA_ENROL,
    burn_password_check,
    create_access_token,
    create_purpose_token,
    hash_password,
    password_problem,
    unusable_password_hash,
    verify_password,
)
# app.models imports every model module, which is what populates SQLAlchemy's
# registry so relationship("Payslip") and friends can resolve. See its docstring.
import app.models  # noqa: F401
from app.models.user import User
from app.models.leaves import LeaveRequest, LeaveStatus
from app.models.payroll import Payslip
from app.models.employee import Employee
from app.routers import accounting, audit, contact, dashboard, invoicing, mfa as mfa_router, notifications
from app.i18n import ApiError, set_locale, t
from app.services import accounts, mfa, throttle
from app.services.audit import record_event
from app.services.email import send_email
from app.services.email_template import render_html_email
from app.services.reminders import reminder_loop

load_dotenv()

# Log through the stdlib rather than print(). The previous debug prints carried
# emoji, which raise UnicodeEncodeError on Windows consoles using cp1252 and
# turned every login into a 500. Keep all log messages ASCII-only.
log = logging.getLogger("dixpertia")

# --- Authentication by default ---
# Every route requires a valid access token, except the explicit allow-list
# below: a route that forgets to declare authentication is closed, not open
# (#55). Role checks are still declared per route. FastAPI's own documentation
# routes (/docs, /redoc, /openapi.json) are not API routes and are not affected.
PUBLIC_PATHS = frozenset({
    "/api/login",
    "/api/forgot-password",
    "/api/reset-password",
    "/api/activate",
    # The website's contact form (#98): anonymous, rate limited in the database.
    "/api/contact",
    # Container health check (#185): says only whether the database answers.
    "/api/health",
    # The sign-in's second step (#44): each carries its own short-lived token,
    # checked by the route, since there is no session yet.
    "/api/mfa/verify",
    "/api/mfa/enrol/setup",
    "/api/mfa/enrol/confirm",
})
_optional_bearer = OAuth2PasswordBearer(tokenUrl="/api/login", auto_error=False)


async def require_authentication(request: Request, token: Optional[str] = Depends(_optional_bearer)) -> None:
    """Reject any request to a non-public route that has no valid access token.

    Also publishes the caller's identity for row-level security (#43). The
    account's state is read through auth_session(), a SECURITY DEFINER
    function (#76): users is under row-level security, and no identity is set
    yet at this point, so a plain query would see no row.

    Declared async deliberately. As a sync dependency FastAPI runs this in a
    worker thread, where ContextVar.set() mutates that worker's copy of the
    context and the endpoint - dispatched to a different worker - never sees
    it. Awaited on the event loop, the value is in the context that is copied
    into the endpoint's worker. Verified: as a sync def, every insert was
    rejected by the policies because the role arrived as NULL.
    """
    clear_identity()
    # The language of this request's messages (#135): what the UI sends in
    # Accept-Language, French without one. Set before anything can refuse.
    set_locale(request.headers.get("accept-language"))
    if request.url.path in PUBLIC_PATHS:
        return
    identity = await run_in_threadpool(_identity_for, token) if token else None
    if identity is None:
        raise ApiError(401, "auth.not_authenticated", headers={"WWW-Authenticate": "Bearer"})
    set_identity(*identity)


def _identity_for(token: str) -> Optional[tuple[str, str]]:
    """(user id, role) if the token may still be used, else None (#62).

    The token's signature alone is not enough any more: the account must be
    active and activated, and the token issued under its current
    token_version, so deactivation or a role or password change revokes
    sessions at once. Checked here, before any route, so a route that never
    loads the current user is covered as well.

    Its own short session, not the request's: that one must not begin a
    transaction before the identity is set, or the policies would see none.
    The role published for row-level security is the account's, not the
    token's claim.
    """
    db = SessionLocal()
    try:
        return session_identity(token, db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Start the reminder job with the API (#134), and stop it with it."""
    task = asyncio.create_task(reminder_loop()) if settings.REMINDERS_ENABLED else None
    yield
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


# The interactive API documentation (/docs, /redoc, /openapi.json) maps every
# route and schema: useful in development and on staging, not something to hand
# the internet in production (#185). Off unless API_DOCS is set.
_docs = settings.API_DOCS
app = FastAPI(
    dependencies=[Depends(require_authentication)],
    lifespan=lifespan,
    docs_url="/docs" if _docs else None,
    redoc_url="/redoc" if _docs else None,
    openapi_url="/openapi.json" if _docs else None,
)


@app.exception_handler(ApiError)
async def _api_error(_request: Request, exc: ApiError) -> JSONResponse:
    """A catalog error (#135): its message in the request's language, and its
    key in `code`, so the UI and the tests recognise it without parsing text."""
    return JSONResponse(status_code=exc.status_code, headers=exc.headers,
                        content={"detail": exc.detail, "code": exc.code})

# NOTE: the payslip router is intentionally not mounted. `app/routers/payroll.py`
# declares its routes as "/" and "/{payslip_id}", so mounting it under "/api"
# registers GET /api/{payslip_id}, which shadows other GET /api/<name> routes. It also expects a
# "rh" role and a `User.employee_profile` relationship that this data model does
# not have. Mounting it needs those reconciled first.
app.include_router(invoicing.router, prefix="/api")
app.include_router(accounting.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(contact.public, prefix="/api")
app.include_router(contact.admin, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(mfa_router.router, prefix="/api")
app.include_router(mfa_router.public, prefix="/api")
# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Authentication helpers ---
# Hashing, tokens and the "may this token still be used" check live in
# app.core.security and app.core.deps (#62). main.py kept its own copies of
# them, so a rule added in one place was missing from the other.

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != 'admin':
        raise ApiError(403, "auth.admin_required")
    return current_user

# --- Pydantic models ---
class RejectLeaveRequest(BaseModel):
    comment: Optional[str] = ''

class EmployeeCreate(BaseModel):
    """An employee record for an existing login account.

    Replaces TeamMemberCreate. team_members duplicated names, e-mail and a
    free-text role from users with no foreign key, so the two could describe
    the same person differently (#60). Identity now lives once, on the user.
    """

    userId: str
    jobTitle: Optional[str] = None
    hiredOn: date
    # No default: contractual days per year is a per-person term (#60).
    annualEntitlementDays: int = Field(ge=0, le=365)

class InvoiceItem(BaseModel):
    description: str
    qty: int
    price: float
    total: float

class InvoiceCreate(BaseModel):
    id: Optional[str] = None
    client: str
    clientInitials: Optional[str] = None
    amount: float
    dateIssued: Optional[str] = None
    dueDate: Optional[str] = None
    status: Optional[str] = 'Sent'
    items: Optional[List[InvoiceItem]] = []

Role = Literal["admin", "employee", "accountant"]

Locale = Literal["fr", "en"]

class UserCreate(BaseModel):
    email: EmailStr
    firstName: str
    lastName: str
    role: Role
    # The language of the activation e-mail and of the account (#135).
    locale: Locale = "fr"

class UserUpdate(BaseModel):
    """What the admin may change on an account (#62). All optional; the e-mail
    is the login identity and is not changed here."""
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    role: Optional[Role] = None
    isActive: Optional[bool] = None
    locale: Optional[Locale] = None

class LocaleUpdate(BaseModel):
    """The signed-in account's own language (#135)."""
    locale: Locale

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    newPassword: str

class ActivateRequest(BaseModel):
    token: str
    newPassword: str


def _require_acceptable(password: str) -> None:
    problem = password_problem(password)
    if problem:
        key, params = problem
        raise ApiError(422, key, **params)


def _account_by_email(db: Session, email: str):
    """The account for an e-mail, hash included, or None (#76).

    Through auth_account_by_email(): sign-in and forgot-password run before
    anyone is identified, so row-level security would hide every row from a
    plain query, and the application role cannot read the hash column at all.
    The row is read-only, not an ORM object.
    """
    return db.execute(text("SELECT * FROM auth_account_by_email(:e)"), {"e": email}).first()


@app.get('/api/health', response_model=HealthOut)
def health(response: Response):
    """Whether the API is up and reaches the database (#185).

    For the container health check and the uptime monitor (#188). Public, so
    it reveals nothing: no version, no host, no error text - only ok or not.
    Not rate limited: it is cheap, and a refusing health check would have the
    platform restart a healthy container.
    """
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        log.warning("Health check: the database did not answer", exc_info=True)
        response.status_code = 503
        return HealthOut(status="unavailable")
    return HealthOut(status="ok")


def _locked(wait_seconds: int) -> ApiError:
    """An e-mail locked by failed sign-ins (#220): how long, in minutes."""
    return ApiError(429, "auth.locked", headers={"Retry-After": str(wait_seconds)},
                    minutes=max(1, -(-wait_seconds // 60)))


def _unlock(db: Session, user_id: str) -> None:
    """Clear the account's failed sign-ins (#220), once its owner proved they
    control it: a reset or an activation link was spent. Otherwise the new
    password stays refused until the lock runs out."""
    # The account's own row, as the account: users is under row-level security.
    set_identity(user_id, None)
    db.commit()
    email = db.query(User.email).filter(User.id == user_id).scalar()
    if email:
        throttle.clear(db, throttle.LOGIN_ACCOUNT, throttle.email_key(email))
        db.commit()


# --- Auth endpoints ---
# Every public route is limited per address (#175), declared on the route so
# that a public route added later shows whether it has a limit.
PUBLIC_LIMIT = [Depends(throttle.limit_public_requests)]


@app.post('/api/login', response_model=LoginOut, dependencies=PUBLIC_LIMIT)
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Exchange e-mail and password for an access token.

    Every refusal is the same 401 and costs the same time (#62): an unknown
    e-mail still runs one bcrypt check against a dummy hash, and an inactive or
    not yet activated account is refused only after its password is checked.
    Answering faster, or differently, for those would tell a caller which
    e-mails have accounts and in what state.

    Guessing is limited (#175). Each attempt is counted before the password
    is checked, so parallel guesses cannot all slip under a limit; a success
    takes its attempts back. Too many failures from one address: 429. Too
    many on one e-mail: 429 too, saying the e-mail is locked and for how long
    (#220). An unknown e-mail locks exactly the same way, so this reveals
    nothing; answering "wrong password" instead told a locked-out user their
    right password was wrong.
    """
    from_ip = throttle.hit(db, throttle.LOGIN_IP, throttle.ip_key(request),
                           settings.LOGIN_MAX_FAILURES_PER_IP, settings.LOGIN_LOCKOUT_MINUTES * 60)
    if from_ip < 0:
        db.commit()
        log.info("Login refused: too many failures from one address")
        raise throttle.too_many(-from_ip)
    account = throttle.email_key(req.email)
    on_account = throttle.hit(db, throttle.LOGIN_ACCOUNT, account,
                              settings.LOGIN_MAX_FAILURES, settings.LOGIN_LOCKOUT_MINUTES * 60)
    # Counted now, whatever happens next.
    db.commit()
    if on_account < 0:
        log.info("Login refused: account locked")
        raise _locked(-on_account)

    user = _account_by_email(db, req.email)
    if user is None:
        burn_password_check(req.password)
        ok = False
    else:
        ok = verify_password(req.password, user.hashedPassword) and user.isActive and user.isVerified
    if not ok:
        log.info("Login refused")
        raise ApiError(401, "auth.invalid_credentials")
    throttle.forget(db, from_ip)
    throttle.clear(db, throttle.LOGIN_ACCOUNT, account)
    db.commit()

    # The second factor (#44): the password alone gives no session when it is
    # on, or when the role requires it and it is not set up yet.
    if mfa.enabled():
        second = mfa.state(db, user.id)
        if second is not None and second.enabled:
            log.info("Login: password OK for %s, second factor next", user.id)
            return LoginOut(mfaRequired=True,
                            challengeToken=create_purpose_token(MFA_CHALLENGE, user.id, user.token_version))
        if mfa.required_for(user.role):
            log.info("Login: password OK for %s, enrolment required", user.id)
            return LoginOut(mfaEnrolmentRequired=True,
                            enrolToken=create_purpose_token(MFA_ENROL, user.id, user.token_version))
    log.info("Login OK for %s (role=%s)", user.id, user.role)
    token = create_access_token(data={"sub": user.id, "role": user.role, "ver": user.token_version})
    return LoginOut(access_token=token, user=UserOut.from_orm_row(user))


def _send_activation(user: User, token: str) -> bool:
    """In the new account's language (#135), which the admin chose at creation."""
    link = accounts.link(accounts.ACTIVATION, token)

    # 1. Plain text version
    plain_body = t("email.activation.body", user.locale, name=user.firstName, link=link)

    # 2. HTML version (#211), with escaping for the name
    safe_name = html.escape(user.firstName)
    html_msg = t("email.activation.html_message", user.locale, name=safe_name)

    html_body = render_html_email(
        lang=user.locale,
        title=t("email.activation.html_title", user.locale),
        message_html=html_msg,
        action_url=link,
        action_text=t("email.activation.html_action", user.locale),
        footer_text=t("email.activation.html_footer", user.locale)
    )

    # 3. Send both parts
    return send_email(
        to_email=user.email,
        subject=t("email.activation.subject", user.locale),
        body=plain_body,
        html_text=html_body
    )


# require_admin as a dependency rather than a check inside the body: FastAPI
# validates the request model before the handler runs, so an in-body role check
# let a non-admin get a 422 describing the schema before being refused.
# Authorisation should be decided before anything else is (#57).
@app.post('/api/users', status_code=201, response_model=UserCreatedOut, dependencies=[Depends(require_admin)])
def create_user(req: UserCreate, db: Session = Depends(get_db)):
    """Create an account and e-mail its owner an activation link (#62).

    No password is chosen here and none is returned: the temporary password
    used to travel in this response and in a plain e-mail. The account cannot
    log in until its owner sets a password through the link. If the e-mail
    cannot be sent, activationEmailSent says so and the admin can send it
    again with POST /api/users/{id}/activation.
    """
    if db.query(User).filter(User.email == req.email).first():
        raise ApiError(400, "user.email_taken")
    # No id: the database allocates it from users_id_seq (#85).
    user = User(
        email=req.email,
        firstName=req.firstName,
        lastName=req.lastName,
        role=req.role,
        hashedPassword=unusable_password_hash(),
        isActive=True,
        isVerified=False,
        createdAt=datetime.utcnow(),
        locale=req.locale,
    )
    db.add(user)
    db.flush()
    token = accounts.issue_token(db, user.id, accounts.ACTIVATION)
    record_event(db, "user.created", "user", user.id, after={"role": user.role, "isActive": True})
    db.commit()
    db.refresh(user)
    # After the commit: the link must not reach anyone for an account that
    # was rolled back.
    sent = _send_activation(user, token)
    return UserCreatedOut(id=user.id, email=user.email, activationEmailSent=sent)


@app.post('/api/users/{user_id}/activation', response_model=ActivationSentOut,
          dependencies=[Depends(require_admin)])
def resend_activation(user_id: str, db: Session = Depends(get_db)):
    """Send a new activation link; the previous one stops working."""
    user = db.get(User, user_id)
    if user is None:
        raise ApiError(404, "user.not_found")
    if user.isVerified:
        raise ApiError(409, "user.already_activated")
    token = accounts.issue_token(db, user.id, accounts.ACTIVATION)
    record_event(db, "user.activation_sent", "user", user.id)
    db.commit()
    return ActivationSentOut(id=user.id, activationEmailSent=_send_activation(user, token))


@app.post('/api/activate', response_model=MessageOut, dependencies=PUBLIC_LIMIT)
def activate_account(req: ActivateRequest, db: Session = Depends(get_db)):
    """Set the first password through the activation link, and activate."""
    _require_acceptable(req.newPassword)
    # One call spends the link, sets the password, activates the account and
    # revokes its sessions, inside the database (#76).
    user_id = accounts.spend_token(db, req.token, accounts.ACTIVATION, hash_password(req.newPassword))
    if user_id is None:
        db.rollback()
        raise ApiError(400, "auth.invalid_link")
    record_event(db, "user.activated", "user", user_id)
    db.commit()
    _unlock(db, user_id)
    return MessageOut(message=t("account.activated"))


def _apply_user_update(db: Session, admin: User, user: User, changes: dict) -> dict:
    """Apply the admin's changes to an account; returns the fields changed.

    Revokes the account's sessions (token_version) on deactivation and on a
    role change, so neither waits for the token to expire.

    An admin cannot demote or deactivate themselves. That is also what keeps
    at least one admin: the caller is an active admin, and only ever changes
    someone else.
    """
    changed = {k: v for k, v in changes.items() if v is not None and getattr(user, k) != v}
    if not changed:
        return {}
    if user.id == admin.id and ('role' in changed or changed.get('isActive') is False):
        raise ApiError(409, "user.cannot_change_self")
    before = {k: getattr(user, k) for k in changed}
    for field, value in changed.items():
        setattr(user, field, value)
    if 'role' in changed or changed.get('isActive') is False:
        user.token_version += 1
    if changed.get('isActive') is False:
        action = "user.deactivated"
    elif changed.get('isActive') is True:
        action = "user.reactivated"
    elif 'role' in changed:
        action = "user.role_changed"
    else:
        action = "user.updated"
    record_event(db, action, "user", user.id, before=before, after=changed)
    return changed


@app.patch('/api/users/{user_id}', response_model=UserOut)
def update_user(user_id: str, req: UserUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Change an account's name, role or status (#62). One audit event."""
    user = db.get(User, user_id)
    if user is None:
        raise ApiError(404, "user.not_found")
    _apply_user_update(db, admin, user, req.model_dump())
    db.commit()
    db.refresh(user)
    return UserOut.from_orm_row(user)


@app.post('/api/users/{user_id}/deactivate', response_model=UserOut)
def deactivate_user(user_id: str, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Block an account at once, including the sessions it already holds.

    There is no delete: payslips and leave requests reference the account and
    payroll must be kept, so a departure is a deactivation (#62).
    """
    user = db.get(User, user_id)
    if user is None:
        raise ApiError(404, "user.not_found")
    _apply_user_update(db, admin, user, {"isActive": False})
    db.commit()
    db.refresh(user)
    return UserOut.from_orm_row(user)


@app.post('/api/forgot-password', response_model=MessageOut, dependencies=PUBLIC_LIMIT)
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """E-mail a single-use reset link. The answer never says whether the
    e-mail has an account, and an inactive or not yet activated account gets
    no link: activation has its own.

    At most RESET_MAILS_PER_HOUR links per account (#175). Past it nothing is
    sent and the answer is unchanged: the form cannot flood an inbox."""
    answer = MessageOut(message=t("account.reset_sent"))
    user = _account_by_email(db, req.email)
    if user is None or not user.isActive or not user.isVerified:
        return answer
    sent_lately = throttle.hit(db, throttle.RESET_MAIL, throttle.email_key(req.email),
                               settings.RESET_MAILS_PER_HOUR, 3600)
    if sent_lately < 0:
        db.commit()
        log.info("Password reset not sent: hourly limit for the account")
        return answer
    token = accounts.issue_token(db, user.id, accounts.RESET)
    # The token itself never goes in the trail.
    record_event(db, "user.password_reset_requested", "user", user.id)
    db.commit()
    link = accounts.link(accounts.RESET, token)
    plain_body = t("email.reset.body", user.locale, name=user.firstName, link=link)
    safe_name = html.escape(user.firstName)
    html_msg = t("email.reset.html_message", user.locale, name=safe_name)
    html_body = render_html_email(
        lang=user.locale,
        title=t("email.reset.html_title", user.locale),
        message_html=html_msg,
        action_url=link,
        action_text=t("email.reset.html_action", user.locale),
        footer_text=t("email.reset.html_footer", user.locale)
    )
    send_email(
        to_email=user.email,
        subject=t("email.reset.subject", user.locale),
        body=plain_body,
        html_text=html_body
    )

    return answer


@app.post('/api/reset-password', response_model=MessageOut, dependencies=PUBLIC_LIMIT)
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Set a new password with a reset link. Spends the token, and revokes
    every session the account holds: whoever had the old password is out."""
    _require_acceptable(req.newPassword)
    user_id = accounts.spend_token(db, req.token, accounts.RESET, hash_password(req.newPassword))
    if user_id is None:
        db.rollback()
        raise ApiError(400, "auth.invalid_link")
    record_event(db, "user.password_reset", "user", user_id)
    db.commit()
    _unlock(db, user_id)
    return MessageOut(message=t("account.password_updated"))

# --- Data endpoints ---
# GET /api/data used to return every table (all users, invoices, leave requests,
# and team members) to any authenticated user, whatever their role. It
# was removed in #55; per-entity endpoints with explicit response schemas replace
# it as the UI needs them (#65).

@app.get('/api/me', response_model=UserOut)
def read_me(current_user: User = Depends(get_current_user)):
    """The signed-in user, resolved from the bearer token.

    Exists so the browser never has to store the user (#65). Previously the
    whole user object was kept in localStorage and trusted on reload, which
    meant the client decided its own role: editing one key in devtools was
    enough to render the admin screens. The server refused the admin *actions*,
    so nothing could actually be done - but the UI lied, and the fix is for the
    identity to come from the token on every load.
    """
    return UserOut.from_orm_row(current_user)


@app.put('/api/me/locale', response_model=UserOut)
def set_my_locale(req: LocaleUpdate, current_user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """Save the signed-in account's language (#135): the UI's toggle calls this,
    so e-mails and notifications follow the choice on every device.

    Through auth_set_locale(), which changes that one column of the caller's own
    row: only the admin may update users otherwise (#76).
    """
    db.execute(text("SELECT auth_set_locale(:l)"), {"l": req.locale})
    db.commit()
    db.refresh(current_user)
    return UserOut.from_orm_row(current_user)


class PasswordChange(BaseModel):
    currentPassword: str = Field(min_length=1, max_length=200)
    newPassword: str = Field(min_length=1, max_length=200)


class SessionOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


@app.post('/api/me/password', response_model=SessionOut)
def change_my_password(req: PasswordChange, current_user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """Change one's own password (#220), against the current one.

    A wrong current password counts against the e-mail's sign-in limit (#175),
    so this cannot be used to guess it. Every other session is signed out
    (token_version); the answer carries a fresh one for this browser.
    """
    account_key = throttle.email_key(current_user.email)
    attempt = throttle.hit(db, throttle.LOGIN_ACCOUNT, account_key,
                           settings.LOGIN_MAX_FAILURES, settings.LOGIN_LOCKOUT_MINUTES * 60)
    db.commit()
    if attempt < 0:
        raise _locked(-attempt)
    account = _account_by_email(db, current_user.email)
    if account is None or not verify_password(req.currentPassword, account.hashedPassword):
        # 400, not 401: the UI reads a 401 on a signed-in request as an expired
        # session and signs the user out, for one mistyped character.
        raise ApiError(400, "auth.wrong_current_password")
    _require_acceptable(req.newPassword)
    if not db.execute(text("SELECT auth_set_own_password(:u, :h)"),
                      {"u": current_user.id, "h": hash_password(req.newPassword)}).scalar_one():
        raise ApiError(401, "auth.not_authenticated")
    throttle.clear(db, throttle.LOGIN_ACCOUNT, account_key)
    record_event(db, "user.password_changed", "user", current_user.id)
    db.commit()
    db.refresh(current_user)
    token = create_access_token(data={"sub": current_user.id, "role": current_user.role,
                                      "ver": current_user.token_version})
    return SessionOut(access_token=token)


# Every list endpoint is paginated and capped, as the invoice ones are (#61).
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


@app.get('/api/leave-requests', response_model=List[LeaveRequestOut])
def list_leave_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
):
    """Leave requests the caller is allowed to see.

    No role check here on purpose. The row-level security policy added in #74
    already decides it: an admin sees every row, and everyone else sees the
    rows belonging to their own employee record. An accountant therefore sees
    their own leave and nobody else's - they are an employee with an
    entitlement like anyone else, and the decision on #10 was that they do not
    get the leave *administration* screen, not that they cannot see their own.

    Repeating the rule in Python would mean two places to keep in step, and the
    one that actually holds is the database.
    """
    rows = (
        db.query(LeaveRequest)
        .options(joinedload(LeaveRequest.employee).joinedload(Employee.user))
        .order_by(LeaveRequest.date_debut.desc(), LeaveRequest.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [LeaveRequestOut.from_orm_row(r, r.employee) for r in rows]


@app.get('/api/payslips', response_model=List[PayslipOut])
def list_payslips(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
):
    """Payslips the caller is allowed to see.

    Scoped by the same row-level security policy: an employee sees their own,
    admin and accountant see all. Verified by db/verify_rls.py, which proves an
    employee asking directly for someone else's payslip gets no rows.
    """
    rows = (
        db.query(Payslip)
        .options(joinedload(Payslip.employee).joinedload(Employee.user))
        .order_by(Payslip.periode.desc(), Payslip.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [PayslipOut.from_orm_row(r) for r in rows]


@app.get('/api/employees', response_model=List[EmployeeOut])
def list_employees(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
):
    """The team: employee records with the name from their login account.

    joinedload, not lazy access: the serialiser reads employee.user for every
    row, which without it is one query per employee (#61).
    """
    rows = (
        db.query(Employee)
        .options(joinedload(Employee.user))
        .order_by(Employee.id)
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [EmployeeOut.from_orm_row(r) for r in rows]


@app.get('/api/users', response_model=List[UserOut])
def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
):
    """Login accounts. Admin only.

    Checked here as well as by row-level security on `users` (#76), which lets
    the accountant read every account too: this list is the admin's.
    """
    if current_user.role != 'admin':
        raise ApiError(403, "auth.admin_required")
    rows = (
        db.query(User)
        .order_by(User.id)
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [UserOut.from_orm_row(r) for r in rows]


@app.post('/api/leave-requests', status_code=201, response_model=LeaveRequestOut)
def create_leave_request(
    req: LeaveRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a leave request for the authenticated employee.

    Previously this assigned camelCase attributes (employeeId, dates, status)
    that do not exist on the LeaveRequest model, so SQLAlchemy raised
    TypeError and the endpoint returned 500 on every call. The request body is
    now translated to the real columns by LeaveRequestCreate.to_orm_kwargs
    (#37).
    """
    if req.endDate < req.startDate:
        raise ApiError(422, "leave.end_before_start")

    # Leave belongs to the employee record, not the login account (#60), so the
    # caller is resolved through employees. A user with no employee record
    # cannot request leave - which is correct: an admin account that is not an
    # employee has no entitlement.
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise ApiError(409, "leave.no_employee_record")

    leave = LeaveRequest(employee_id=employee.id, **req.to_orm_kwargs())
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return LeaveRequestOut.from_orm_row(leave, employee)

@app.post('/api/leave-requests/{req_id}/approve', response_model=LeaveRequestOut)
def approve_leave_request(req_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Approve a leave request.

    Previously this set `leave.status`, a name the model does not have, so
    SQLAlchemy tracked nothing and commit() wrote nothing - the endpoint
    reported success while leaving the row untouched (AUDIT-DB-013). It now
    writes `statut`, and records who approved it.
    """
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == req_id).first()
    if not leave:
        raise ApiError(404, "leave.not_found")
    record_event(db, "leave_request.approved", "leave_request", leave.id,
                 before={"statut": leave.statut}, after={"statut": LeaveStatus.APPROUVE})
    leave.statut = LeaveStatus.APPROUVE
    leave.valide_par_id = admin.id
    db.commit()
    db.refresh(leave)
    employee = db.query(Employee).filter(Employee.id == leave.employee_id).first()
    return LeaveRequestOut.from_orm_row(leave, employee)

@app.post('/api/leave-requests/{req_id}/reject', response_model=LeaveRequestOut)
def reject_leave_request(
    req_id: int,
    body: RejectLeaveRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Reject a leave request. Same defect as approve: it set `status` and
    `rejectionReason`, neither of which is a column, so nothing was written."""
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == req_id).first()
    if not leave:
        raise ApiError(404, "leave.not_found")
    record_event(db, "leave_request.rejected", "leave_request", leave.id,
                 before={"statut": leave.statut},
                 after={"statut": LeaveStatus.REFUSE, "comment": body.comment or ''})
    leave.statut = LeaveStatus.REFUSE
    leave.commentaire_validation = body.comment or ''
    leave.valide_par_id = admin.id
    db.commit()
    db.refresh(leave)
    employee = db.query(Employee).filter(Employee.id == leave.employee_id).first()
    return LeaveRequestOut.from_orm_row(leave, employee)

@app.post('/api/employees', status_code=201, response_model=EmployeeOut)
def create_employee(req: EmployeeCreate, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Attach an employee record to an existing login account.

    Answers with the same EmployeeOut as the list, instead of a dict built
    by hand (#77).
    """
    user = db.query(User).filter(User.id == req.userId).first()
    if not user:
        raise ApiError(404, "user.not_found")
    if db.query(Employee).filter(Employee.user_id == req.userId).first():
        raise ApiError(409, "employee.already_exists")

    employee = Employee(
        user_id=req.userId,
        job_title=req.jobTitle,
        hired_on=req.hiredOn,
        annual_entitlement_days=req.annualEntitlementDays,
    )
    db.add(employee)
    db.flush()
    record_event(db, "employee.created", "employee", employee.id, after={
        "user_id": employee.user_id, "job_title": employee.job_title,
        "hired_on": employee.hired_on, "annual_entitlement_days": employee.annual_entitlement_days,
    })
    db.commit()
    db.refresh(employee)
    return EmployeeOut.from_orm_row(employee)

# NOTE: an older POST /api/invoices lived here. It was unreachable - the
# invoicing router is registered first, so it won by registration order - and
# it wrote camelCase attributes (client, clientInitials, amount, dateIssued)
# that the Invoice model does not have, so it would have raised TypeError had
# it ever been called. The single handler is now app/routers/invoicing.py,
# which is admin-only (#59).



@app.api_route('/logs', methods=['GET', 'POST', 'OPTIONS'])
def logs(request: Request):
    return []
# NOTE: a second POST /logs handler was declared here. The api_route above
# already registers POST, so it won by registration order and this one was
# unreachable - the same duplicate-route pattern as GET /api/data (#35) and
# POST /api/invoices (#59).
