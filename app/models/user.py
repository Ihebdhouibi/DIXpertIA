from sqlalchemy import Column, String, Boolean, DateTime
from datetime import datetime
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    firstName = Column(String)
    lastName = Column(String)
    role = Column(String)          # "admin", "employee", "accountant"
    department = Column(String, nullable=True)
    avatarUrl = Column(String, nullable=True)
    hashedPassword = Column(String)
    isActive = Column(Boolean, default=True)
    isVerified = Column(Boolean, default=False)
    resetToken = Column(String, nullable=True)
    resetTokenExpiry = Column(DateTime, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)
