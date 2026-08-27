from sqlalchemy import Column, Integer, String, Text, Boolean
from app.core.database import Base

# Existing Service model (keep as is)
class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    titre = Column(String(150), nullable=False)
    description = Column(Text, default="")
    image = Column(String(255), nullable=True)
    ordre_affichage = Column(Integer, default=0)
    actif = Column(Boolean, default=True)

# NEW: TeamMember model (for user management)
class TeamMember(Base):
    __tablename__ = "team_members"
    id = Column(String, primary_key=True, index=True)
    firstName = Column(String)
    lastName = Column(String)
    email = Column(String)
    role = Column(String)
    status = Column(String)  # Active, Inactive
    initials = Column(String, nullable=True)
    avatarUrl = Column(String, nullable=True)