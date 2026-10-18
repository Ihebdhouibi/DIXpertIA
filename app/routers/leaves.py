from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.leaves import LeaveRequest
from app.models.user import User
from app.schemas.leaves import LeaveRequestCreate, LeaveRequestOut, LeaveRequestDecision

router = APIRouter()


@router.get("/", response_model=list[LeaveRequestOut])
def list_leave_requests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(LeaveRequest)
    if current_user.role not in ("rh", "admin"):
        if not current_user.employee_profile:
            return []
        query = query.filter(LeaveRequest.employee_id == current_user.employee_profile.id)
    return query.order_by(LeaveRequest.created_at.desc()).all()


@router.post("/", response_model=LeaveRequestOut)
def create_leave_request(
    payload: LeaveRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.employee_profile:
        raise HTTPException(status_code=400, detail="Aucun profil employé associé à ce compte")

    leave_request = LeaveRequest(**payload.model_dump(), employee_id=current_user.employee_profile.id)
    db.add(leave_request)
    db.commit()
    db.refresh(leave_request)
    # TODO: notifier le responsable RH
    return leave_request


@router.patch(
    "/{leave_id}/decision",
    response_model=LeaveRequestOut,
    dependencies=[Depends(require_roles("rh", "admin"))],
)
def decide_leave_request(
    leave_id: int,
    payload: LeaveRequestDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    leave_request = db.query(LeaveRequest).get(leave_id)
    if not leave_request:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    leave_request.statut = payload.statut
    leave_request.commentaire_validation = payload.commentaire_validation
    leave_request.valide_par_id = current_user.id
    db.commit()
    db.refresh(leave_request)
    # TODO: notifier l'employé du changement de statut
    return leave_request
