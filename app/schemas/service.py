from pydantic import BaseModel


class ServiceBase(BaseModel):
    titre: str
    description: str = ""
    ordre_affichage: int = 0
    actif: bool = True


class ServiceCreate(ServiceBase):
    pass


class ServiceOut(ServiceBase):
    id: int
    image: str | None

    class Config:
        from_attributes = True
