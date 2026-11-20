import enum
from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship
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

    id = Column(Integer, primary_key=True)
    # RESTRICT: leave history must outlive any attempt to delete the person.
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="RESTRICT"),
                         nullable=False)
    date_debut = Column(Date, nullable=False)
    date_fin = Column(Date, nullable=False)
    type_conge = Column(Enum(LeaveType), default=LeaveType.PAYE)
    motif = Column(Text, default="")
    statut = Column(Enum(LeaveStatus), nullable=False, default=LeaveStatus.EN_ATTENTE,
                    server_default=text("'EN_ATTENTE'"))
    # The approver is a login account (an admin), not an employee record.
    valide_par_id = Column(String, ForeignKey("users.id", ondelete="RESTRICT"))
    commentaire_validation = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee", back_populates="leave_requests",
                            foreign_keys=[employee_id])
    validated_by = relationship("User", foreign_keys=[valide_par_id])

    __table_args__ = (
        CheckConstraint("date_fin >= date_debut", name="ck_leave_dates"),
        # Self-validation is no longer expressible as a CHECK: employee_id now
        # references employees.id while valide_par_id references users.id, so
        # the two are different key spaces and a row-local comparison is
        # meaningless. Enforced by a trigger instead - see the migration.
        # A decided request must name who decided it.
        CheckConstraint("statut = 'EN_ATTENTE' OR valide_par_id IS NOT NULL",
                        name="ck_leave_decision_has_validator"),
        # One employee's leave history - the employee's own list view.
        Index("ix_leave_requests_employee_id", "employee_id"),
        # Not for reads: makes the RESTRICT check on deleting a user an index
        # lookup instead of a full scan.
        Index("ix_leave_requests_valide_par_id", "valide_par_id"),
    )


class LeaveEntitlement(Base):
    """The paid leave an employee has for one year (#121).

    Only `paye` has an entitlement: sick and unpaid leave are counted, not
    capped. The row of a year is created from `Employee.annual_entitlement_days`
    the first time that year's balance is read, then fixed, so a later change
    of `annual_entitlement_days` never rewrites a year already recorded. An
    admin corrects a year by editing its row. See migration 76f00c250ad1.
    """
    __tablename__ = "leave_entitlements"

    id = Column(Integer, primary_key=True)
    # RESTRICT, like leave_requests: leave history outlives the person's deletion.
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)
    year = Column(Integer, nullable=False)
    type_conge = Column(Enum(LeaveType), nullable=False, default=LeaveType.PAYE)
    # Numeric, for the half days of #254 and a corrected figure such as 10.5.
    days = Column(Numeric(5, 2), nullable=False)

    employee = relationship("Employee")

    __table_args__ = (
        UniqueConstraint("employee_id", "year", "type_conge", name="uq_employee_year_type"),
        CheckConstraint("type_conge = 'PAYE'", name="ck_leave_entitlements_paid_only"),
        CheckConstraint("days >= 0 AND days <= 365", name="ck_leave_entitlements_days"),
        Index("ix_leave_entitlements_employee_id", "employee_id"),
    )
