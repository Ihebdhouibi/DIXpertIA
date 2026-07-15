from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel


class PayslipBase(BaseModel):
    employee_id: int
    periode: date
    montant_brut: Decimal
    montant_net: Decimal


class PayslipCreate(PayslipBase):
    pass


class PayslipOut(PayslipBase):
    id: int
    fichier_pdf: str | None
    date_emission: datetime

    class Config:
        from_attributes = True
