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

from app.core.database import get_db
from app.models.user import User
from app.models.payroll import Payslip
from app.models.leaves import LeaveRequest
from app.models.service import TeamMember
from app.models.invoicing import Invoice, Device
from app.routers import invoicing

load_dotenv()

# Log through the stdlib rather than print(). The previous debug prints carried
# emoji, which raise UnicodeEncodeError on Windows consoles using cp1252 and
# turned every login into a 500. Keep all log messages ASCII-only.
log = logging.getLogger("dixpertia")

app = FastAPI()
# NOTE: the payslip router is intentionally not mounted. `app/routers/payroll.py`
# declares its routes as "/" and "/{payslip_id}", so mounting it under "/api"
# registers GET /api/{payslip_id}, which shadows GET /api/data. It also expects a
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
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
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

# --- Serialisation helper ---
# Fields that must never leave the API.
_PRIVATE_COLUMNS = {'hashedPassword', 'hashed_password', 'resetToken', 'resetTokenExpiry'}

def _row(obj):
    """Serialise a SQLAlchemy row, dropping internals and secrets.

    `obj.__dict__` carries SQLAlchemy's `_sa_instance_state` as well as every
    column, so returning it directly exposed password hashes and reset tokens.
    """
    return {
        k: v for k, v in obj.__dict__.items()
        if not k.startswith('_') and k not in _PRIVATE_COLUMNS
    }

# --- Pydantic models ---
class LeaveRequestCreate(BaseModel):
    employeeId: str
    employeeName: str
    department: Optional[str] = 'Operations'
    type: Optional[str] = 'Annual Leave'
    dates: Optional[str] = 'Oct 20, 2024'
    duration: Optional[int] = 1
    reason: Optional[str] = ''

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
def create_user(req: UserCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
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
# NOTE: an unauthenticated duplicate of GET /api/data used to be declared here.
# FastAPI matches routes in registration order, so it shadowed the authenticated
# definition further down and served every User row (password hashes included)
# to anonymous callers, while also bypassing that handler's per-role payslip
# filter. The single authenticated definition below is now the only one.

@app.post('/api/leave-requests', status_code=201)
def create_leave_request(req: LeaveRequestCreate, db: Session = Depends(get_db)):
    new_id = f"LR-00{db.query(LeaveRequest).count()+1:03d}"
    leave = LeaveRequest(
        id=new_id,
        employeeId=req.employeeId,
        employeeName=req.employeeName,
        department=req.department,
        type=req.type,
        dates=req.dates,
        duration=req.duration,
        status='Pending',
        reason=req.reason
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return leave

@app.post('/api/leave-requests/{req_id}/approve')
def approve_leave_request(req_id: str, db: Session = Depends(get_db)):
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == req_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    leave.status = 'Approved'
    db.commit()
    return {"message": "Leave request approved successfully"}

@app.post('/api/leave-requests/{req_id}/reject')
def reject_leave_request(req_id: str, body: RejectLeaveRequest, db: Session = Depends(get_db)):
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == req_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    leave.status = 'Rejected'
    leave.rejectionReason = body.comment or ''
    db.commit()
    return {"message": "Leave request rejected successfully"}

@app.post('/api/team-members', status_code=201)
def create_team_member(req: TeamMemberCreate, db: Session = Depends(get_db)):
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

@app.post('/api/invoices', status_code=201)
def create_invoice(req: InvoiceCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Only administrators can create invoices")
    from datetime import datetime, timedelta
    date_issued = req.dateIssued or datetime.now().strftime('%b %d, %Y')
    due_date = req.dueDate or (datetime.now() + timedelta(days=30)).strftime('%b %d, %Y')
    client_initials = req.clientInitials or req.client[:2].upper()
    new_id = req.id or f"INV-2024-00{db.query(Invoice).count()+1:03d}"
    invoice = Invoice(
        id=new_id,
        client=req.client,
        clientInitials=client_initials,
        amount=req.amount,
        dateIssued=date_issued,
        dueDate=due_date,
        status=req.status,
        items=[item.dict() for item in req.items] if req.items else [],
        deviceIds=req.deviceIds or [],
        createdAt=datetime.utcnow()
    )
    db.add(invoice)

    if req.deviceIds:
        for dev_id in req.deviceIds:
            dev = db.query(Device).filter(Device.id == dev_id).first()
            if dev and dev.status != 'Sold':
                dev.status = 'Sold'
    db.commit()
    db.refresh(invoice)
    return invoice


# --- Device endpoints ---
@app.get('/api/devices')
def get_devices(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user['role'] not in ['admin', 'accountant', 'employee']:
        raise HTTPException(status_code=403, detail="Not authorized")
    return db.query(Device).all()

@app.post('/api/devices', status_code=201)
def create_device(req: DeviceCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Only administrators can manage devices")
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
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Only administrators can manage devices")
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
def delete_device(device_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Only administrators can manage devices")
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
@app.post('/logs')
def logs_post():
    return []

@app.get('/api/data')
def get_data(
    current_user: User = Depends(get_current_user),  # <-- new
    db: Session = Depends(get_db)
):
    # Fetch all data (except payslips for now)
    leaves = db.query(LeaveRequest).all()
    team = db.query(TeamMember).all()
    invoices = db.query(Invoice).all()
    users = db.query(User).all()
    devices = db.query(Device).all()

    # Filter payslips based on user role
    if current_user.role in ['admin', 'accountant']:
        payslips = db.query(Payslip).all()
    else:
        # Employee – only their own payslips
        payslips = db.query(Payslip).filter(Payslip.employee_id == current_user.id).all()

    return {
        "payslips": [_row(p) for p in payslips],
        "leaveRequests": [_row(lr) for lr in leaves],
        "teamMembers": [_row(t) for t in team],
        "invoices": [_row(i) for i in invoices],
        "users": [_row(u) for u in users],
        "devices": [_row(d) for d in devices]
    }
