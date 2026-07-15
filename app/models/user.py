import enum
from sqlalchemy import Column, Integer, String, Boolean, Enum, ForeignKey, DateTime, Numeric, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class RoleEnum(str, enum.Enum):
    EMPLOYE = "employe"
    RH = "rh"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), default="")
    last_name = Column(String(100), default="")
    role = Column(Enum(RoleEnum), default=RoleEnum.EMPLOYE, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    employee_profile = relationship("Employee", back_populates="user", uselist=False)


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    poste = Column(String(100), default="")
    date_embauche = Column(Date, nullable=True)
    solde_conges = Column(Numeric(5, 2), default=0)
    manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)

    user = relationship("User", back_populates="employee_profile")
    manager = relationship("Employee", remote_side=[id])
