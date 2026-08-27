from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.models.user import User
from app.models.payroll import Payslip
from app.models.leaves import LeaveRequest
from app.models.service import Service, TeamMember
from app.models.invoicing import Invoice, Device

# Hardcoded connection (works)
DATABASE_URL = "postgresql://postgres:admin@localhost:5432/dixpertia"

engine = create_engine(DATABASE_URL)
Base = declarative_base()

Base.metadata.create_all(bind=engine)
print("✅ Tables created successfully.")