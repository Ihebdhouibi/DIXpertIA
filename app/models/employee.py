import enum

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class EmploymentStatus(str, enum.Enum):
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    TERMINATED = "terminated"


class Employee(Base):
    """A person employed by the company, distinct from their login account.

    Payroll and leave hang off this record rather than off `users` (#60), so a
    login can be deactivated or deleted without taking the payroll history with
    it. The audit found both attached directly to the login account, which left
    no safe way to offboard anyone.

    This also replaces `team_members`, which duplicated names, e-mail and a
    free-text "role" from `users` with no foreign key, so the two could
    describe the same person differently.
    """

    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    # RESTRICT: a login that owns payroll history must not be deletable. Use
    # employment_status, or deactivate the user, instead of deleting.
    user_id = Column(
        String,
        ForeignKey("users.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    job_title = Column(String(150))
    hired_on = Column(Date, nullable=False)
    # Contractual days per year. Deliberately has no default: it is a per-person
    # term, and guessing a company-wide number would bake an invented figure
    # into every employee record. A company default can be added later once the
    # real figure is confirmed.
    annual_entitlement_days = Column(Integer, nullable=False)
    employment_status = Column(
        Enum(EmploymentStatus),
        nullable=False,
        server_default=EmploymentStatus.ACTIVE.name,
    )

    user = relationship("User", back_populates="employee")
    payslips = relationship("Payslip", back_populates="employee")
    leave_requests = relationship(
        "LeaveRequest",
        back_populates="employee",
        foreign_keys="LeaveRequest.employee_id",
    )

    __table_args__ = (
        CheckConstraint(
            "annual_entitlement_days >= 0 AND annual_entitlement_days <= 365",
            name="ck_employees_entitlement",
        ),
        # The payslip and leave policies resolve the caller through
        # employees.user_id on every row read, so this is on the hot path.
        Index("ix_employees_user_id", "user_id"),
    )

    # The leave balance is derived, never stored: entitlement minus approved
    # leave in the current calendar year, with no carry-over (decided on #60).
    # A stored column would drift out of step with the leave table the moment a
    # request was approved, and nothing would record why.
