from sqlalchemy import Column, Integer, ForeignKey, Date, Numeric, String, DateTime, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class Payslip(Base):
    __tablename__ = "payslips"
    __table_args__ = (UniqueConstraint("employee_id", "periode", name="uq_employee_periode"),)

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, ForeignKey("users.id"), nullable=False) 
    periode = Column(Date, nullable=False)
    montant_brut = Column(Numeric(10, 2), nullable=False)
    montant_net = Column(Numeric(10, 2), nullable=False)
    fichier_pdf = Column(String(255), nullable=True)
    date_emission = Column(DateTime(timezone=True), server_default=func.now())
