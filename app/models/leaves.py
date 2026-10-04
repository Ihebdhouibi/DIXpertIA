import enum
from sqlalchemy import CheckConstraint, Column, Date, DateTime, Enum, ForeignKey, Integer, String, Text, text
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
    employee_id = Column(String, ForeignKey("users.id"), nullable=False)
    date_debut = Column(Date, nullable=False)
    date_fin = Column(Date, nullable=False)
    type_conge = Column(Enum(LeaveType), default=LeaveType.PAYE)
    motif = Column(Text, default="")
    statut = Column(Enum(LeaveStatus), nullable=False, default=LeaveStatus.EN_ATTENTE,
                    server_default=text("'EN_ATTENTE'"))
    valide_par_id = Column(String, ForeignKey("users.id"))
    commentaire_validation = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("date_fin >= date_debut", name="ck_leave_dates"),
        # An employee must not approve their own leave.
        CheckConstraint("valide_par_id IS NULL OR valide_par_id <> employee_id",
                        name="ck_leave_no_self_validation"),
        # A decided request must name who decided it.
        CheckConstraint("statut = 'EN_ATTENTE' OR valide_par_id IS NOT NULL",
                        name="ck_leave_decision_has_validator"),
    )
