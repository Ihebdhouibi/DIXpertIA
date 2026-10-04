"""Translation between the ORM schema and the camelCase API contract.

This is Option C from #37: `app/models/` keeps its normalised schema - real
dates, enums, numerics, foreign keys - and the API keeps the camelCase shape the
frontend already consumes. These schemas are the seam between them.

The alternatives were to rewrite the API onto the ORM names (which would rename
fields across ~10 frontend files, colliding with the v2 rebrand) or to flatten
the ORM onto the API shape (which would discard the normalised model and break
the invoice PDF generator). The seam costs one mapping per entity and leaves
both sides alone.

It also makes the response an allowlist. Every field returned is named here, so
a column added to a model later is not exposed by accident - the failure mode of
the `obj.__dict__` minus denylist approach that leaked password hashes
(AUDIT-DB-020, #35).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.leaves import LeaveStatus, LeaveType

# --- Vocabulary -------------------------------------------------------------
# The database stores French enum values; the frontend's union types are
# English. Mapping them here keeps both stable, and keeps the translation in one
# place instead of scattered through handlers.

LEAVE_TYPE_TO_API = {
    LeaveType.PAYE: "Annual Leave",
    LeaveType.MALADIE: "Sick Leave",
    LeaveType.SANS_SOLDE: "Unpaid Leave",
}
LEAVE_TYPE_FROM_API = {v: k for k, v in LEAVE_TYPE_TO_API.items()}
# The frontend also offers "Personal Day", which has no distinct database value.
LEAVE_TYPE_FROM_API["Personal Day"] = LeaveType.SANS_SOLDE

LEAVE_STATUS_TO_API = {
    LeaveStatus.EN_ATTENTE: "Pending",
    LeaveStatus.APPROUVE: "Approved",
    LeaveStatus.REFUSE: "Rejected",
}
LEAVE_STATUS_FROM_API = {v: k for k, v in LEAVE_STATUS_TO_API.items()}


def format_date_range(start: date, end: date) -> str:
    """Render a range the way the UI displays it today."""
    if start == end:
        return start.strftime("%b %d, %Y")
    if (start.year, start.month) == (end.year, end.month):
        return f"{start.strftime('%b %d')} - {end.strftime('%d, %Y')}"
    if start.year == end.year:
        return f"{start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}"
    return f"{start.strftime('%b %d, %Y')} - {end.strftime('%b %d, %Y')}"


# --- Leave requests ---------------------------------------------------------

class LeaveRequestCreate(BaseModel):
    """What a client may send. The employee is taken from the token, never the
    body (#55), so no employeeId field is accepted here."""

    startDate: date
    endDate: date
    type: str = "Annual Leave"
    reason: Optional[str] = ""

    @model_validator(mode="after")
    def _end_not_before_start(self) -> "LeaveRequestCreate":
        # Mirrors ck_leave_dates. Validating here turns a database error into a
        # 422 naming the field (#58).
        if self.endDate < self.startDate:
            raise ValueError("endDate cannot be before startDate")
        return self

    def to_orm_kwargs(self) -> dict:
        return {
            "date_debut": self.startDate,
            "date_fin": self.endDate,
            "type_conge": LEAVE_TYPE_FROM_API.get(self.type, LeaveType.PAYE),
            "motif": self.reason or "",
        }


class LeaveRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    employeeId: Optional[int] = None
    employeeName: str = ""
    jobTitle: Optional[str] = None
    type: str
    # `dates` is what the UI renders today. startDate/endDate are the real
    # columns, exposed so the UI can migrate off the formatted string without a
    # breaking change - the lossy mapping flagged on #37.
    dates: str
    startDate: date
    endDate: date
    duration: int
    status: str
    reason: Optional[str] = None
    rejectionReason: Optional[str] = None

    @classmethod
    def from_orm_row(cls, row, employee=None) -> "LeaveRequestOut":
        """`employee` is an Employee row; the person's name lives on its user."""
        user = getattr(employee, "user", None) if employee else None
        name = f"{user.firstName} {user.lastName}".strip() if user else ""
        return cls(
            id=str(row.id),
            employeeId=row.employee_id,
            employeeName=name,
            jobTitle=getattr(employee, "job_title", None),
            type=LEAVE_TYPE_TO_API.get(row.type_conge, "Annual Leave"),
            dates=format_date_range(row.date_debut, row.date_fin),
            startDate=row.date_debut,
            endDate=row.date_fin,
            duration=(row.date_fin - row.date_debut).days + 1,
            status=LEAVE_STATUS_TO_API.get(row.statut, "Pending"),
            reason=row.motif or None,
            rejectionReason=row.commentaire_validation or None,
        )


# --- Payslips ---------------------------------------------------------------

class PayslipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    employeeId: Optional[int] = None
    period: str
    grossPay: float
    netPay: float
    issuedOn: Optional[str] = None
    pdfUrl: Optional[str] = None

    @classmethod
    def from_orm_row(cls, row) -> "PayslipOut":
        issued: Optional[datetime] = row.date_emission
        return cls(
            id=str(row.id),
            employeeId=row.employee_id,
            period=row.periode.strftime("%B %Y"),
            grossPay=float(row.montant_brut or 0),
            netPay=float(row.montant_net or 0),
            issuedOn=issued.strftime("%b %d, %Y") if issued else None,
            pdfUrl=row.fichier_pdf,
        )


# --- Invoices ---------------------------------------------------------------

# The commercial state, as the UI labels it.
INVOICE_STATUS_TO_API = {
    "brouillon": "Draft",
    "envoyee": "Sent",
    "payee": "Paid",
    "en_retard": "Overdue",
    "annulee": "Cancelled",
}

# The accountant's workflow state (#41) - a separate axis, not an alternative
# spelling of the above. An invoice is routinely "Paid" and "Pending" at once:
# the client has paid, nobody has booked it yet.
INVOICE_PROCESSING_STATUS_TO_API = {
    "pending": "Pending",
    "processed": "Processed",
    "completed": "Completed",
    "archived": "Archived",
}


class InvoiceItemOut(BaseModel):
    description: str
    qty: float
    price: float
    total: float


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    numero: str
    client: str
    clientInitials: str
    amount: float
    dateIssued: str
    dueDate: str
    status: str
    items: list[InvoiceItemOut] = Field(default_factory=list)

    @classmethod
    def from_orm_row(cls, row) -> "InvoiceOut":
        client_name = row.client.nom if row.client else "Unknown"
        initials = "".join(w[0] for w in client_name.split()[:2]).upper() or "?"
        statut = row.statut.value if hasattr(row.statut, "value") else (row.statut or "envoyee")
        return cls(
            id=str(row.id),
            numero=row.numero,
            client=client_name,
            clientInitials=initials,
            amount=float(row.montant_ttc or Decimal(0)),
            dateIssued=row.date_emission.strftime("%b %d, %Y") if row.date_emission else "-",
            dueDate=row.date_echeance.strftime("%b %d, %Y") if row.date_echeance else "-",
            status=INVOICE_STATUS_TO_API.get(statut, "Sent"),
            items=[
                InvoiceItemOut(
                    description=i.designation,
                    qty=float(i.quantite or 0),
                    price=float(i.prix_unitaire or 0),
                    total=float((i.quantite or 0) * (i.prix_unitaire or 0)),
                )
                for i in (row.items or [])
            ],
        )
