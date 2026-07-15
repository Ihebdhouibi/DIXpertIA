from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.payroll import Payslip
from app.models.user import User
from app.schemas.payroll import PayslipCreate, PayslipOut

router = APIRouter()


@router.get("/", response_model=list[PayslipOut])
def list_payslips(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """RH/admin voient tout ; un employé ne voit que ses propres fiches."""
    query = db.query(Payslip)
    if current_user.role not in ("rh", "admin"):
        if not current_user.employee_profile:
            return []
        query = query.filter(Payslip.employee_id == current_user.employee_profile.id)
    return query.order_by(Payslip.periode.desc()).all()


@router.post("/", response_model=PayslipOut, dependencies=[Depends(require_roles("rh", "admin"))])
def create_payslip(payload: PayslipCreate, db: Session = Depends(get_db)):
    payslip = Payslip(**payload.model_dump())
    db.add(payslip)
    db.commit()
    db.refresh(payslip)
    # TODO: notifier l'employé (email / notification in-app)
    return payslip


@router.get("/{payslip_id}", response_model=PayslipOut)
def get_payslip(payslip_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    payslip = db.query(Payslip).get(payslip_id)
    if not payslip:
        raise HTTPException(status_code=404, detail="Fiche de paie introuvable")
    if current_user.role not in ("rh", "admin") and (
        not current_user.employee_profile or payslip.employee_id != current_user.employee_profile.id
    ):
        raise HTTPException(status_code=403, detail="Accès refusé")
    return payslip
