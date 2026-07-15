import os
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

DB_FILE = os.path.join(os.getcwd(), 'db.json')

# Initial seed data
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

default_db = {
  "payslips": initial_payslips,
  "leaveRequests": initial_leave_requests,
  "teamMembers": initial_team_members,
  "invoices": initial_invoices
}

def read_db():
    try:
        if not os.path.exists(DB_FILE):
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_db, f, indent=2)
            return default_db
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading database file: {e}")
        return default_db

def write_db(data):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error writing database file: {e}")

# Pydantic models for incoming requests
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

@app.post('/api/invoices', status_code=201)
def create_invoice(req: InvoiceCreate):
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
        "items": [item.dict() for item in req.items] if req.items else []
    }
    db['invoices'] = [created_inv] + db['invoices']
    write_db(db)
    return created_inv
