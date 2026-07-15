from datetime import date, datetime
from pydantic import BaseModel

from app.models.leaves import LeaveType, LeaveStatus


class LeaveRequestBase(BaseModel):
    date_debut: date
    date_fin: date
    type_conge: LeaveType = LeaveType.PAYE
    motif: str = ""


class LeaveRequestCreate(LeaveRequestBase):
    pass


class LeaveRequestDecision(BaseModel):
    statut: LeaveStatus
    commentaire_validation: str = ""


class LeaveRequestOut(LeaveRequestBase):
    id: int
    employee_id: int
    statut: LeaveStatus
    commentaire_validation: str
    created_at: datetime

    class Config:
        from_attributes = True
