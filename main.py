import logging
import os
import secrets
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import bcrypt
from dotenv import load_dotenv

from app.core.config import settings
from app.core.identity import clear_identity, set_identity
from app.schemas.api import LeaveRequestCreate, LeaveRequestOut
from app.core.database import get_db
from app.models.user import User
from app.models.leaves import LeaveRequest, LeaveStatus
from app.models.service import TeamMember
from app.models.invoicing import Device
from app.routers import invoicing

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
})
_optional_bearer = OAuth2PasswordBearer(tokenUrl="/api/login", auto_error=False)


async def require_authentication(request: Request, token: Optional[str] = Depends(_optional_bearer)) -> None:
    """Reject any request to a non-public route that has no valid access token.

    Also publishes the caller's identity for row-level security (#43). It is
    taken from the JWT claims, not from a database lookup: the lookup is itself
    subject to the policies, so deriving identity from it would be circular.

    Declared async deliberately. As a sync dependency FastAPI runs this in a
    worker thread, where ContextVar.set() mutates that worker's copy of the
    context and the endpoint - dispatched to a different worker - never sees
    it. Awaited on the event loop, the value is in the context that is copied
    into the endpoint's worker. Verified: as a sync def, every insert was
    rejected by the policies because the role arrived as NULL.
    """
    clear_identity()
    if request.url.path in PUBLIC_PATHS:
        return
    payload = decode_token(token) if token else None
    if not token or payload is None:
        raise HTTPException(status_code=401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    set_identity(payload.get("sub"), payload.get("role"))


app = FastAPI(dependencies=[Depends(require_authentication)])
# NOTE: the payslip router is intentionally not mounted. `app/routers/payroll.py`
# declares its routes as "/" and "/{payslip_id}", so mounting it under "/api"
# registers GET /api/{payslip_id}, which shadows other GET /api/<name> routes. It also expects a
# "rh" role and a `User.employee_profile` relationship that this data model does
# not have. Mounting it needs those reconciled first.
app.include_router(invoicing.router, prefix="/api")
# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Password hashing ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# --- JWT ---
# Single source of truth: app.core.config validates these at import time and
# refuses to start without them. main.py must not keep its own copy with a
# fallback - that is what allowed a public signing key into deployments
# (AUDIT-DB-007).
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Email ---
def send_email(to_email: str, subject: str, body: str):
    try:
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        from_email = os.getenv("SMTP_FROM", "no-reply@dixpertia.com")

        if not smtp_host or not smtp_user or not smtp_password:
            log.warning("SMTP credentials missing. Email not sent.")
            return False

        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        log.info("Email sent to %s", to_email)
        return True
    except Exception as e:
        log.error("Email error: %s", e)
        return False

# --- JWT helpers ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == payload.get('sub')).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Administrator role required")
    return current_user

# --- Pydantic models ---
class RejectLeaveRequest(BaseModel):
    comment: Optional[str] = ''

class TeamMemberCreate(BaseModel):
    firstName: str
    lastName: str
    email: Optional[str] = None
    role: Optional[str] = 'Contributor'
    status: Optional[str] = 'Active'
    initials: Optional[str] = None
    avatarUrl: Optional[str] = None

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
    deviceIds: Optional[List[str]] = []

class UserCreate(BaseModel):
    email: EmailStr
    firstName: str
    lastName: str
    role: str   # "admin", "employee", or "accountant"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    newPassword: str

class DeviceCreate(BaseModel):
    name: str
    model: str
    serialNumber: str
    price: float
    status: Optional[str] = 'Available'

# --- Auth endpoints ---
@app.post('/api/login')
def login(req: LoginRequest, db: Session = Depends(get_db)):
    log.info("Login attempt for %s", req.email)
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        log.info("Login failed: no user for %s", req.email)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(req.password, user.hashedPassword):
        log.info("Login failed: bad password for %s", req.email)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    log.info("Login OK for %s (role=%s)", req.email, user.role)
    token = create_access_token(data={"sub": user.id, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "firstName": user.firstName,
            "lastName": user.lastName,
            "role": user.role,
            "department": user.department,
            "avatarUrl": user.avatarUrl,
            "isActive": user.isActive,
            "isVerified": user.isVerified,
            "createdAt": user.createdAt.isoformat() if user.createdAt else None
        }
    }

@app.post('/api/users', status_code=201)
def create_user(req: UserCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Only administrators can create users")
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    alphabet = string.ascii_letters + string.digits
    temp_password = ''.join(secrets.choice(alphabet) for _ in range(10))
    hashed = get_password_hash(temp_password)
    user = User(
        id=f"USR-{db.query(User).count()+1:03d}",
        email=req.email,
        firstName=req.firstName,
        lastName=req.lastName,
        role=req.role,
        hashedPassword=hashed,
        isActive=True,
        isVerified=False,
        createdAt=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    email_body = f"""
Hello {req.firstName},

Your DIXpertIA employee account has been created.

Login email: {req.email}
Temporary password: {temp_password}

Please log in and change your password immediately.

Regards,
DIXpertIA Team
"""
    send_email(req.email, "Your DIXpertIA Account Credentials", email_body)

    return {
        "message": "User created successfully",
        "id": user.id,
        "email": user.email,
        "tempPassword": temp_password
    }

@app.post('/api/forgot-password')
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        return {"message": "If your email is registered, you will receive a password reset link."}

    expiry = datetime.utcnow() + timedelta(hours=1)
    token_data = {"sub": user.id, "exp": expiry, "purpose": "reset"}
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    user.resetToken = token
    user.resetTokenExpiry = expiry
    db.commit()

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    reset_link = f"{frontend_url}/reset-password?token={token}"
    email_body = f"""
Hello {user.firstName},

You requested a password reset for your DIXpertIA account.

Click the link below to set a new password (valid for 1 hour):

{reset_link}

If you did not request this, please ignore this email.

Regards,
DIXpertIA Team
"""
    send_email(user.email, "Password Reset Request", email_body)
    return {"message": "If your email is registered, you will receive a password reset link."}

@app.post('/api/reset-password')
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(req.token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Reset token has expired.")
    except jwt.JWTError:
        raise HTTPException(status_code=400, detail="Invalid token.")
    user_id = payload.get('sub')
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid token.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found.")
    if user.resetToken != req.token:
        raise HTTPException(status_code=400, detail="Invalid token.")
    if user.resetTokenExpiry and datetime.utcnow() > user.resetTokenExpiry:
        raise HTTPException(status_code=400, detail="Token has expired.")
    hashed = get_password_hash(req.newPassword)
    user.hashedPassword = hashed
    user.resetToken = None
    user.resetTokenExpiry = None
    db.commit()
    return {"message": "Password updated successfully."}

# --- Data endpoints ---
# GET /api/data used to return every table (all users, invoices, leave requests,
# devices and team members) to any authenticated user, whatever their role. It
# was removed in #55; per-entity endpoints with explicit response schemas replace
# it as the UI needs them (#65).

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
        raise HTTPException(status_code=422, detail="endDate cannot be before startDate")

    leave = LeaveRequest(employee_id=current_user.id, **req.to_orm_kwargs())
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return LeaveRequestOut.from_orm_row(leave, current_user)

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
        raise HTTPException(status_code=404, detail="Leave request not found")
    leave.statut = LeaveStatus.APPROUVE
    leave.valide_par_id = admin.id
    db.commit()
    db.refresh(leave)
    employee = db.query(User).filter(User.id == leave.employee_id).first()
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
        raise HTTPException(status_code=404, detail="Leave request not found")
    leave.statut = LeaveStatus.REFUSE
    leave.commentaire_validation = body.comment or ''
    leave.valide_par_id = admin.id
    db.commit()
    db.refresh(leave)
    employee = db.query(User).filter(User.id == leave.employee_id).first()
    return LeaveRequestOut.from_orm_row(leave, employee)

@app.post('/api/team-members', status_code=201)
def create_team_member(req: TeamMemberCreate, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    email = req.email or f"{req.firstName.lower()}.{req.lastName.lower()}@dixpertia.com"
    initials = req.initials or f"{req.firstName[0]}{req.lastName[0]}".upper()
    new_id = f"TM-00{db.query(TeamMember).count()+1:03d}"
    member = TeamMember(
        id=new_id,
        firstName=req.firstName,
        lastName=req.lastName,
        email=email,
        role=req.role,
        status='Active',
        initials=initials,
        avatarUrl=req.avatarUrl
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member

# NOTE: an older POST /api/invoices lived here. It was unreachable - the
# invoicing router is registered first, so it won by registration order - and
# it wrote camelCase attributes (client, clientInitials, amount, dateIssued,
# deviceIds) that the Invoice model does not have, so it would have raised
# TypeError had it ever been called. The single handler is now
# app/routers/invoicing.py, which is admin-only (#59).
#
# Its device side effect - marking a Device as 'Sold' when it is billed - had
# no equivalent and was never reachable either. The device/invoice link is
# modelled properly in #60.


# --- Device endpoints ---
@app.get('/api/devices')
def get_devices(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # The previous check listed admin, accountant and employee - every role in
    # UserRole - so it rejected nothing while crashing on current_user['role'].
    # Authentication is already required globally (#55); any signed-in user may
    # list devices, and RLS decides which rows they see (#43).
    return db.query(Device).all()

@app.post('/api/devices', status_code=201)
def create_device(req: DeviceCreate, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    new_id = f"DEV-{db.query(Device).count()+1:03d}"
    device = Device(
        id=new_id,
        name=req.name,
        model=req.model,
        serialNumber=req.serialNumber,
        price=req.price,
        status=req.status or "Available",
        createdAt=datetime.utcnow()
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device

@app.put('/api/devices/{device_id}')
def update_device(
    device_id: str,
    req: DeviceCreate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    device.name = req.name
    device.model = req.model
    device.serialNumber = req.serialNumber
    device.price = req.price
    device.status = req.status or device.status
    db.commit()
    db.refresh(device)
    return device

@app.delete('/api/devices/{device_id}')
def delete_device(device_id: str, _admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    db.delete(device)
    db.commit()
    return {"message": "Device deleted"}

# --- Logs endpoint (handles OPTIONS preflight) ---
@app.api_route('/logs', methods=['GET', 'POST', 'OPTIONS'])
def logs(request: Request):
    return []
# NOTE: a second POST /logs handler was declared here. The api_route above
# already registers POST, so it won by registration order and this one was
# unreachable - the same duplicate-route pattern as GET /api/data (#35) and
# POST /api/invoices (#59).
