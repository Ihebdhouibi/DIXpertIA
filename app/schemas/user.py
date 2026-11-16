from datetime import date
from decimal import Decimal
from pydantic import BaseModel, EmailStr

from app.models.user import RoleEnum


class UserBase(BaseModel):
    email: EmailStr
    first_name: str = ""
    last_name: str = ""


class UserCreate(UserBase):
    password: str
    role: RoleEnum = RoleEnum.EMPLOYE


class UserOut(UserBase):
    id: int
    role: RoleEnum
    is_active: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class EmployeeOut(BaseModel):
    id: int
    poste: str
    date_embauche: date | None
    solde_conges: Decimal
    user: UserOut

    class Config:
        from_attributes = True
