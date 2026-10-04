from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Index, String, text
from datetime import datetime
from sqlalchemy.orm import relationship

from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    firstName = Column(String)
    lastName = Column(String)
    role = Column(String, nullable=False)  # "admin", "employee", "accountant"
    department = Column(String, nullable=True)
    avatarUrl = Column(String, nullable=True)
    hashedPassword = Column(String, nullable=False)
    isActive = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    isVerified = Column(Boolean, default=False)
    resetToken = Column(String, nullable=True)
    resetTokenExpiry = Column(DateTime, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="user", uselist=False)

    __table_args__ = (
        # Roles are a closed set; the audit inserted 'superadmin' cleanly (#58).
        CheckConstraint("role IN ('admin', 'employee', 'accountant')", name="ck_users_role"),
        # Email is an identity, so uniqueness must ignore case: PROBE@x and
        # probe@x were both accepted. UNIQUE(email) cannot express this.
        Index("ux_users_email_ci", text("lower(email)"), unique=True),
    )
