import enum
from sqlalchemy import Column, Integer, ForeignKey, Date, String, Text, Enum, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class LeaveType(str, enum.Enum):
    PAYE = "paye"
    MALADIE = "maladie"
    SANS_SOLDE = "sans_solde"


class LeaveStatus(str, enum.Enum):
    EN_ATTENTE = "en_attente"
    APPROUVE = "approuve"
    REFUSE = "refuse"


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, ForeignKey("users.id"))
    date_debut = Column(Date, nullable=False)
    date_fin = Column(Date, nullable=False)
    type_conge = Column(Enum(LeaveType), default=LeaveType.PAYE)
    motif = Column(Text, default="")
    statut = Column(Enum(LeaveStatus), default=LeaveStatus.EN_ATTENTE)
    valide_par_id = Column(String, ForeignKey("users.id"))
    commentaire_validation = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
