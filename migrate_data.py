import json
from app.core.database import SessionLocal, Base, engine

from app.models.user import User
from app.models.payroll import Payslip
from app.models.leaves import LeaveRequest
from app.models.invoicing import Invoice
from datetime import datetime


Base.metadata.create_all(bind=engine)

db = SessionLocal()

with open('db.json', 'r') as f:
    data = json.load(f)

# Users
for u in data.get('users', []):
    user = User(
        id=u['id'],
        email=u['email'],
        firstName=u.get('firstName', ''),
        lastName=u.get('lastName', ''),
        role=u.get('role', 'employee'),
        department=u.get('department'),
        avatarUrl=u.get('avatarUrl'),
        hashedPassword=u['hashedPassword'],
        isActive=u.get('isActive', True),
        isVerified=u.get('isVerified', False),
        resetToken=u.get('resetToken'),
        resetTokenExpiry=u.get('resetTokenExpiry'),
        createdAt=datetime.fromisoformat(u.get('createdAt', datetime.now().isoformat()))
    )
    db.add(user)

# Payslips
for p in data.get('payslips', []):
    payslip = Payslip(
        id=p['id'],
        period=p['period'],
        grossPay=p['grossPay'],
        netPay=p['netPay'],
        issuedOn=p['issuedOn']
    )
    db.add(payslip)

# Leave Requests
for lr in data.get('leaveRequests', []):
    leave = LeaveRequest(
        id=lr['id'],
        employeeId=lr['employeeId'],
        employeeName=lr['employeeName'],
        department=lr['department'],
        type=lr['type'],
        dates=lr['dates'],
        duration=lr['duration'],
        status=lr['status'],
        reason=lr.get('reason'),
        rejectionReason=lr.get('rejectionReason')
    )
    db.add(leave)


# Invoices
for inv in data.get('invoices', []):
    invoice = Invoice(
        id=inv['id'],
        client=inv['client'],
        clientInitials=inv['clientInitials'],
        amount=inv['amount'],
        dateIssued=inv['dateIssued'],
        dueDate=inv['dueDate'],
        status=inv['status'],
        items=inv.get('items', []),
        createdAt=datetime.now()
    )
    db.add(invoice)


db.commit()
db.close()
print("Done: data migration completed successfully.")
