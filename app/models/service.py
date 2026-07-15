from sqlalchemy import Column, Integer, String, Text, Boolean

from app.core.database import Base


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    titre = Column(String(150), nullable=False)
    description = Column(Text, default="")
    image = Column(String(255), nullable=True)
    ordre_affichage = Column(Integer, default=0)
    actif = Column(Boolean, default=True)
