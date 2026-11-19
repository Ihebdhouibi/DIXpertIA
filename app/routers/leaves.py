from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.employee import Employee
from app.models.leaves import LeaveEntitlement, LeaveRequest, LeaveStatus, LeaveType
from app.models.user import User
from app.schemas.api import (
    LeaveBalanceOut,
    LeaveBalancesOut,
    LeaveRequestCreate,
    LeaveRequestOut
)

router = APIRouter()

def _get_employee(db: Session, user_id: str) -> Optional[Employee]:
    return db.query(Employee).filter(Employee.user_id == user_id).first()

def _days_in_year(start: date, end: date, target_year: int) -> float:
    """Calculate the number of leave days falling within a specific year."""
    year_start = date(target_year, 1, 1)
    year_end = date(target_year, 12, 31)

    # Find the overlap
    actual_start = max(start, year_start)
    actual_end = min(end, year_end)

    if actual_start > actual_end:
        return 0.0

    # Assuming calendar days for simplicity (can be adapted for working days)
    return float((actual_end - actual_start).days + 1)


@router.get("/balances", response_model=LeaveBalancesOut)
def get_leave_balances(
    year: int = Query(default_factory=lambda: datetime.now().year, description="The year to calculate balances for"),
    employee_id: Optional[int] = Query(None, description="Admin only: view another employee's balance"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Calculate the leave balance for the authenticated employee (or another, if admin)."""

    if employee_id and current_user.role == 'admin':
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
    else:
        employee = _get_employee(db, current_user.id)
        if not employee:
            raise HTTPException(status_code=404, detail="No employee profile associated with this account")

    start_of_year = date(year, 1, 1)
    end_of_year = date(year, 12, 31)

    requests = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee.id,
        LeaveRequest.date_debut <= end_of_year,
        LeaveRequest.date_fin >= start_of_year
    ).all()

    entitlements = db.query(LeaveEntitlement).filter(
        LeaveEntitlement.employee_id == employee.id,
        LeaveEntitlement.year == year
    ).all()

    ent_map = {e.type_conge: float(e.days) for e in entitlements}

    balances = {}

    # Initialize all types
    for lt in LeaveType:
        balances[lt] = LeaveBalanceOut(
            type=lt.value,
            entitlement=ent_map.get(lt, 0.0) if lt == LeaveType.PAYE else 0.0,
            approvedDays=0.0,
            pendingDays=0.0,
            availableDays=0.0
        )

    for req in requests:
        # Calculate how many days of this request fall into the target year
        days = _days_in_year(req.date_debut, req.date_fin, year)

        if req.statut == LeaveStatus.APPROUVE:
            balances[req.type_conge].approvedDays += days
        elif req.statut == LeaveStatus.EN_ATTENTE:
            balances[req.type_conge].pendingDays += days

    for lt, bal in balances.items():
        if lt == LeaveType.PAYE:
            bal.availableDays = bal.entitlement - bal.approvedDays

    return LeaveBalancesOut(year=year, balances=list(balances.values()))


@router.get("/", response_model=list[LeaveRequestOut])
def list_leave_requests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(LeaveRequest)
    if current_user.role not in ("rh", "admin"):
        employee = _get_employee(db, current_user.id)
        if not employee:
            return []
        query = query.filter(LeaveRequest.employee_id == employee.id)
    return query.order_by(LeaveRequest.created_at.desc()).all()


@router.post("/", response_model=LeaveRequestOut)
def create_leave_request(
    payload: LeaveRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee = _get_employee(db, current_user.id)
    if not employee:
        raise HTTPException(status_code=400, detail="Aucun profil employé associé à ce compte")

    leave_request = LeaveRequest(
        date_debut=payload.startDate,
        date_fin=payload.endDate,
        type_conge=LeaveType(payload.type.lower().replace(" ", "_")), # fallback basique
        motif=payload.reason,
        employee_id=employee.id
    )
    db.add(leave_request)
    db.commit()
    db.refresh(leave_request)
    return leave_request
