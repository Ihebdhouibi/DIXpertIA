from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Payslip(Base):
    __tablename__ = "payslips"

    id = Column(Integer, primary_key=True)
    # RESTRICT: payroll history must outlive any attempt to delete the person.
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="RESTRICT"),
                         nullable=False)
    periode = Column(Date, nullable=False)
    montant_brut = Column(Numeric(10, 2), nullable=False)
    montant_net = Column(Numeric(10, 2), nullable=False)
    fichier_pdf = Column(String(255), nullable=True)
    date_emission = Column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee", back_populates="payslips")

    __table_args__ = (
        # Already present: one payslip per employee per *date*. The audit noted
        # that this did not prevent two payslips in the same month, because
        # nothing pinned `periode` to a single day. The CHECK below does, which
        # turns this constraint into "one per employee per month" (#58).
        UniqueConstraint("employee_id", "periode", name="uq_employee_periode"),
        CheckConstraint(
            "montant_brut >= 0 AND montant_net >= 0 AND montant_net <= montant_brut",
            name="ck_payslip_amounts",
        ),
        # periode is a Date standing for a month; pinning it to the 1st makes
        # the month canonical.
        CheckConstraint(
            "extract(day FROM periode) = 1",
            name="ck_payslip_period_is_month_start",
        ),
    )
