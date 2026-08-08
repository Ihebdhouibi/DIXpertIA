import os
import json
import secrets
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt
import bcrypt
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# --- CORS (allow frontend) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = os.path.join(os.getcwd(), 'db.json')

# --- Password hashing (direct bcrypt) ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# --- JWT settings ---
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Email sending (SMTP) ---
def send_email(to_email: str, subject: str, body: str):
    try:
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        from_email = os.getenv("SMTP_FROM", "no-reply@dixpertia.com")

        if not smtp_host or not smtp_user or not smtp_password:
            print("⚠️ SMTP credentials missing. Email not sent.")
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

        print(f"✅ Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

# --- Initial seed data ---
initial_payslips = [
  { "id": 'PS-001', "period": 'September 2024', "grossPay": 8450.00, "netPay": 6218.00, "issuedOn": 'Sep 30, 2024' },
  { "id": 'PS-002', "period": 'August 2024', "grossPay": 8450.00, "netPay": 6218.00, "issuedOn": 'Aug 31, 2024' },
  { "id": 'PS-003', "period": 'July 2024', "grossPay": 8450.00, "netPay": 6218.00, "issuedOn": 'Jul 31, 2024' },
  { "id": 'PS-004', "period": 'June 2024', "grossPay": 8450.00, "netPay": 6218.00, "issuedOn": 'Jun 30, 2024' },
  { "id": 'PS-005', "period": 'May 2024', "grossPay": 8450.00, "netPay": 6218.00, "issuedOn": 'May 31, 2024' },
  { "id": 'PS-006', "period": 'April 2024', "grossPay": 8450.00, "netPay": 6218.00, "issuedOn": 'Apr 30, 2024' },
  { "id": 'PS-007', "period": 'March 2024', "grossPay": 8450.00, "netPay": 6218.00, "issuedOn": 'Mar 31, 2024' },
  { "id": 'PS-008', "period": 'February 2024', "grossPay": 8450.00, "netPay": 6218.00, "issuedOn": 'Feb 29, 2024' },
  { "id": 'PS-009', "period": 'January 2024', "grossPay": 8450.00, "netPay": 6218.00, "issuedOn": 'Jan 31, 2024' }
]

initial_leave_requests = [
  {
    "id": 'LR-001',
    "employeeId": 'EMP-01',
    "employeeName": 'Alice Smith',
    "department": 'Engineering',
    "type": 'Annual Leave',
    "dates": 'Oct 12 - Oct 16, 2024',
    "duration": 5,
    "status": 'Approved',
    "reason": 'Family trip to the mountains'
  },
  {
    "id": 'LR-002',
    "employeeId": 'EMP-02',
    "employeeName": 'John Doe',
    "department": 'Marketing',
    "type": 'Sick Leave',
    "dates": 'Sep 01, 2024',
    "duration": 1,
    "status": 'Approved',
    "reason": 'Medical appointment'
  },
  {
    "id": 'LR-003',
    "employeeId": 'EMP-02',
    "employeeName": 'John Doe',
    "department": 'Marketing',
    "type": 'Personal Day',
    "dates": 'Nov 20, 2024',
    "duration": 1,
    "status": 'Pending',
    "reason": 'Urgent family matter'
  }
]

initial_team_members = [
  {
    "id": 'TM-001',
    "firstName": 'Sarah',
    "lastName": 'Jenkins',
    "email": 'sarah.j@dixpertia.com',
    "role": 'Senior Developer',
    "status": 'Active',
    "avatarUrl": 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=150&auto=format&fit=crop'
  },
  {
    "id": 'TM-002',
    "firstName": 'Marcus',
    "lastName": 'Rodriguez',
    "email": 'm.rodriguez@dixpertia.com',
    "role": 'Project Manager',
    "status": 'Active',
    "initials": 'MR'
  },
  {
    "id": 'TM-003',
    "firstName": 'David',
    "lastName": 'Chen',
    "email": 'd.chen@dixpertia.com',
    "role": 'System Administrator',
    "status": 'Inactive',
    "avatarUrl": 'https://images.unsplash.com/photo-1560250097-0b93528c311a?q=80&w=150&auto=format&fit=crop'
  },
  {
    "id": 'TM-004',
    "firstName": 'Amina',
    "lastName": 'Khalid',
    "email": 'a.khalid@dixpertia.com',
    "role": 'Security Analyst',
    "status": 'Active',
    "initials": 'AK'
  },
  {
    "id": 'TM-005',
    "firstName": 'John',
    "lastName": 'Doe',
    "email": 'john.doe@dixpertia.com',
    "role": 'Junior Developer',
    "status": 'Active',
    "avatarUrl": 'https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?q=80&w=150&auto=format&fit=crop'
  },
  {
    "id": 'TM-006',
    "firstName": 'Alice',
    "lastName": 'Smith',
    "email": 'alice.smith@dixpertia.com',
    "role": 'DevOps Engineer',
    "status": 'Active',
    "initials": 'AS'
  }
]

initial_invoices = [
  {
    "id": 'INV-2024-001',
    "client": 'Acme Corp',
    "clientInitials": 'AC',
    "amount": 12450.00,
    "dateIssued": 'Oct 12, 2024',
    "dueDate": 'Nov 11, 2024',
    "status": 'Sent',
    "items": [
      { "description": 'Cloud Infrastructure Setup', "qty": 1, "price": 5000.00, "total": 5000.00 },
      { "description": 'Security Audit Phase 1', "qty": 1, "price": 3450.00, "total": 3450.00 },
      { "description": 'Enterprise Support (Monthly)', "qty": 2, "price": 2000.00, "total": 4000.00 }
    ]
  },
  {
    "id": 'INV-2024-002',
    "client": 'Global Tech',
    "clientInitials": 'G',
    "amount": 8200.00,
    "dateIssued": 'Oct 15, 2024',
    "dueDate": 'Oct 25, 2024',
    "status": 'Overdue',
    "items": [
      { "description": 'React Frontend Development', "qty": 40, "price": 150.00, "total": 6000.00 },
      { "description": 'Figma UX Design Consultation', "qty": 10, "price": 220.00, "total": 2200.00 }
    ]
  },
  {
    "id": 'INV-2024-003',
    "client": 'Stark Industries',
    "clientInitials": 'S',
    "amount": 45000.00,
    "dateIssued": 'Oct 01, 2024',
    "dueDate": 'Oct 31, 2024',
    "status": 'Paid',
    "items": [
      { "description": 'AI Logic Model Training & Validation', "qty": 1, "price": 30000.00, "total": 30000.00 },
      { "description": 'Kubernetes Cluster Provisioning', "qty": 3, "price": 5000.00, "total": 15000.00 }
    ]
  },
  {
    "id": 'INV-2024-004',
    "client": 'Wayne Ent.',
    "clientInitials": 'W',
    "amount": 3500.00,
    "dateIssued": '-',
    "dueDate": '-',
    "status": 'Draft',
    "items": [
      { "description": 'Security Patch Compliance Audit', "qty": 1, "price": 3500.00, "total": 3500.00 }
    ]
  }
]

# --- NEW: Initial devices (empty) ---
initial_devices = []

# --- default_db includes 'devices' ---
default_db = {
    "payslips": initial_payslips,
    "leaveRequests": initial_leave_requests,
    "teamMembers": initial_team_members,
    "invoices": initial_invoices,
    "users": [],
    "devices": initial_devices
}

# --- DB helpers ---
def read_db():
    try:
        if not os.path.exists(DB_FILE):
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_db, f, indent=2)
            return default_db
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading DB: {e}")
        return default_db

def write_db(data):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error writing DB: {e}")

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

def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    db = read_db()
    user = next((u for u in db.get('users', []) if u['id'] == payload.get('sub')), None)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

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

# --- UPDATED InvoiceCreate with deviceIds ---
class InvoiceCreate(BaseModel):
    id: Optional[str] = None
    client: str
    clientInitials: Optional[str] = None
    amount: float
    dateIssued: Optional[str] = None
    dueDate: Optional[str] = None
    status: Optional[str] = 'Sent'
    items: Optional[List[InvoiceItem]] = []
    deviceIds: Optional[List[str]] = []   # NEW

class UserCreate(BaseModel):
    email: EmailStr
    firstName: str
    lastName: str
    role: str   # "admin", "employee", or "accountant"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# --- Forgot / Reset Password models ---
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    newPassword: str

# --- NEW: Device model ---
class DeviceCreate(BaseModel):
    name: str
    model: str
    serialNumber: str
    price: float
    status: Optional[str] = 'Available'  # "Available", "Sold", "In Repair"

# --- Auth endpoints ---
@app.post('/api/login')
def login(req: LoginRequest):
    db = read_db()
    print(f"🔍 Login attempt for email: {req.email}")
    user = next((u for u in db.get('users', []) if u['email'] == req.email), None)
    if not user:
        print("❌ User not found")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    print(f"✅ User found, role: {user['role']}")
    print(f"Stored hash: {user['hashedPassword']}")
    if not verify_password(req.password, user['hashedPassword']):
        print("❌ Password verification failed")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    print("✅ Password verified")
    token = create_access_token(data={"sub": user['id'], "role": user['role']})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {k: v for k, v in user.items() if k != 'hashedPassword'}
    }

@app.post('/api/users', status_code=201)
def create_user(req: UserCreate, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Only administrators can create users")
    db = read_db()
    if 'users' not in db:
        db['users'] = []
    alphabet = string.ascii_letters + string.digits
    temp_password = ''.join(secrets.choice(alphabet) for _ in range(10))
    hashed = get_password_hash(temp_password)
    new_user = {
        "id": f"USR-{len(db['users'])+1:03d}",
        "email": req.email,
        "firstName": req.firstName,
        "lastName": req.lastName,
        "role": req.role,
        "hashedPassword": hashed,
        "isActive": True,
        "isVerified": False,
        "createdAt": datetime.now().isoformat()
    }
    db['users'].append(new_user)
    write_db(db)

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
        "id": new_user['id'],
        "email": req.email,
        "tempPassword": temp_password
    }

@app.post('/api/forgot-password')
def forgot_password(req: ForgotPasswordRequest):
    db = read_db()
    user = next((u for u in db.get('users', []) if u['email'] == req.email), None)
    if not user:
        return {"message": "If your email is registered, you will receive a password reset link."}
    expiry = datetime.utcnow() + timedelta(hours=1)
    token_data = {"sub": user['id'], "exp": expiry, "purpose": "reset"}
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    user['resetToken'] = token
    user['resetTokenExpiry'] = expiry.isoformat()
    write_db(db)

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    reset_link = f"{frontend_url}/reset-password?token={token}"
    email_body = f"""
Hello {user['firstName']},

You requested a password reset for your DIXpertIA account.

Click the link below to set a new password (valid for 1 hour):

{reset_link}

If you did not request this, please ignore this email.

Regards,
DIXpertIA Team
"""
    send_email(user['email'], "Password Reset Request", email_body)
    return {"message": "If your email is registered, you will receive a password reset link."}

@app.post('/api/reset-password')
def reset_password(req: ResetPasswordRequest):
    db = read_db()
    try:
        payload = jwt.decode(req.token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Reset token has expired.")
    except jwt.JWTError:
        raise HTTPException(status_code=400, detail="Invalid token.")
    user_id = payload.get('sub')
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid token.")
    user = next((u for u in db.get('users', []) if u['id'] == user_id), None)
    if not user:
        raise HTTPException(status_code=400, detail="User not found.")
    if user.get('resetToken') != req.token:
        raise HTTPException(status_code=400, detail="Invalid token.")
    expiry = user.get('resetTokenExpiry')
    if expiry:
        expiry_dt = datetime.fromisoformat(expiry)
        if datetime.utcnow() > expiry_dt:
            raise HTTPException(status_code=400, detail="Token has expired.")
    hashed = get_password_hash(req.newPassword)
    user['hashedPassword'] = hashed
    user.pop('resetToken', None)
    user.pop('resetTokenExpiry', None)
    write_db(db)
    return {"message": "Password updated successfully."}

# --- Existing endpoints (payslips, leave, team) ---
@app.get('/api/data')
def get_data():
    return read_db()

@app.post('/api/leave-requests', status_code=201)
def create_leave_request(req: LeaveRequestCreate):
    db = read_db()
    created_req = {
        "id": f"LR-00{len(db['leaveRequests']) + 1}",
        "employeeId": req.employeeId,
        "employeeName": req.employeeName,
        "department": req.department,
        "type": req.type,
        "dates": req.dates,
        "duration": req.duration,
        "status": 'Pending',
        "reason": req.reason
    }
    db['leaveRequests'] = [created_req] + db['leaveRequests']
    write_db(db)
    return created_req

@app.post('/api/leave-requests/{req_id}/approve')
def approve_leave_request(req_id: str):
    db = read_db()
    found = False
    new_requests = []
    for item in db['leaveRequests']:
        if item['id'] == req_id:
            found = True
            item['status'] = 'Approved'
        new_requests.append(item)
    if not found:
        raise HTTPException(status_code=404, detail="Leave request not found")
    db['leaveRequests'] = new_requests
    write_db(db)
    return {"message": "Leave request approved successfully"}

@app.post('/api/leave-requests/{req_id}/reject')
def reject_leave_request(req_id: str, body: RejectLeaveRequest):
    db = read_db()
    found = False
    new_requests = []
    for item in db['leaveRequests']:
        if item['id'] == req_id:
            found = True
            item['status'] = 'Rejected'
            item['rejectionReason'] = body.comment or ''
        new_requests.append(item)
    if not found:
        raise HTTPException(status_code=404, detail="Leave request not found")
    db['leaveRequests'] = new_requests
    write_db(db)
    return {"message": "Leave request rejected successfully"}

@app.post('/api/team-members', status_code=201)
def create_team_member(req: TeamMemberCreate):
    db = read_db()
    email = req.email or f"{req.firstName.lower()}.{req.lastName.lower()}@dixpertia.com"
    initials = req.initials or f"{req.firstName[0]}{req.lastName[0]}".upper()
    created_emp = {
        "id": f"TM-00{len(db['teamMembers']) + 1}",
        "firstName": req.firstName,
        "lastName": req.lastName,
        "email": email,
        "role": req.role,
        "status": 'Active',
        "initials": initials,
        "avatarUrl": req.avatarUrl
    }
    db['teamMembers'] = [created_emp] + db['teamMembers']
    write_db(db)
    return created_emp

# --- UPDATED Invoice endpoint with device integration ---
@app.post('/api/invoices', status_code=201)
def create_invoice(req: InvoiceCreate, current_user: dict = Depends(get_current_user)):
    # Only admins can create invoices (accountants are read‑only)
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Only administrators can create invoices")
    db = read_db()
    from datetime import datetime, timedelta
    date_issued = req.dateIssued or datetime.now().strftime('%b %d, %Y')
    due_date = req.dueDate or (datetime.now() + timedelta(days=30)).strftime('%b %d, %Y')
    client_initials = req.clientInitials or req.client[:2].upper()
    created_inv = {
        "id": req.id or f"INV-2024-00{len(db['invoices']) + 1}",
        "client": req.client,
        "clientInitials": client_initials,
        "amount": req.amount,
        "dateIssued": date_issued,
        "dueDate": due_date,
        "status": req.status,
        "items": [item.dict() for item in req.items] if req.items else [],
        "deviceIds": req.deviceIds or [],
        "createdAt": datetime.now().isoformat()
    }
    db['invoices'] = [created_inv] + db['invoices']

    # Update device status to "Sold" if device IDs are provided
    if req.deviceIds:
        devices = db.get('devices', [])
        for dev_id in req.deviceIds:
            dev = next((d for d in devices if d['id'] == dev_id), None)
            if dev and dev.get('status') != 'Sold':
                dev['status'] = 'Sold'
        write_db(db)
    else:
        write_db(db)
    return created_inv

#Device CRUD endpoints ---
@app.get('/api/devices')
def get_devices(current_user: dict = Depends(get_current_user)):
    # Allow admin, accountant, and employee to view devices
    if current_user['role'] not in ['admin', 'accountant', 'employee']:
        raise HTTPException(status_code=403, detail="Not authorized")
    db = read_db()
    return db.get('devices', [])

@app.post('/api/devices', status_code=201)
def create_device(req: DeviceCreate, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Only administrators can manage devices")
    db = read_db()
    if 'devices' not in db:
        db['devices'] = []
    new_device = {
        "id": f"DEV-{len(db['devices'])+1:03d}",
        "name": req.name,
        "model": req.model,
        "serialNumber": req.serialNumber,
        "price": req.price,
        "status": req.status or "Available",
        "createdAt": datetime.now().isoformat()
    }
    db['devices'].append(new_device)
    write_db(db)
    return new_device

@app.put('/api/devices/{device_id}')
def update_device(device_id: str, req: DeviceCreate, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Only administrators can manage devices")
    db = read_db()
    device = next((d for d in db.get('devices', []) if d['id'] == device_id), None)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    device.update(req.dict())
    write_db(db)
    return device

@app.delete('/api/devices/{device_id}')
def delete_device(device_id: str, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Only administrators can manage devices")
    db = read_db()
    devices = db.get('devices', [])
    device = next((d for d in devices if d['id'] == device_id), None)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    db['devices'] = [d for d in devices if d['id'] != device_id]
    write_db(db)
    return {"message": "Device deleted"}