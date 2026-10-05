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
    """An invoice as the UI reads it (#37 Option C, updated for #40 and #41).

    The translation layer between the ORM and the API lives here on purpose:
    the columns are French and snake_case because the business is, while the
    UI contract is English and camelCase. Keeping the seam explicit means
    renaming a column does not break the frontend, and the frontend never has
    to know that `statut` and `processing_status` are different axes.

    `counterparty` replaced `client`, because an invoice now has one or the
    other depending on its direction (#40). A supplier bill rendered through
    the old field read "Unknown".
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    numero: str
    direction: str
    # Whoever is on the other side: the client we billed, or the supplier who
    # billed us. Which it is follows from `direction`.
    counterparty: str
    counterpartyInitials: str
    # The supplier's own number, on an incoming invoice only. Never merged with
    # `numero`, which is always ours.
    supplierReference: Optional[str] = None
    amountHT: float
    amountTTC: float
    dateIssued: str
    dueDate: str
    # The commercial state the counterparty sees.
    status: str
    # The accountant's workflow state - a separate axis, not a spelling of the
    # line above. An invoice is routinely "Paid" and "Pending" at once.
    processingStatus: str
    items: list[InvoiceItemOut] = Field(default_factory=list)

    @classmethod
    def from_orm_row(cls, row) -> "InvoiceOut":
        direction = getattr(row.direction, "value", row.direction) or "outgoing"
        party = row.supplier if direction == "incoming" else row.client
        name = getattr(party, "nom", None) or "Unknown"
        initials = "".join(w[0] for w in name.split()[:2]).upper() or "?"
        statut = getattr(row.statut, "value", row.statut) or "envoyee"
        processing = getattr(row.processing_status, "value", row.processing_status) or "pending"
        return cls(
            id=str(row.id),
            numero=row.numero,
            direction=direction,
            counterparty=name,
            counterpartyInitials=initials,
            supplierReference=row.supplier_reference,
            amountHT=float(row.montant_ht or Decimal(0)),
            amountTTC=float(row.montant_ttc or Decimal(0)),
            dateIssued=row.date_emission.strftime("%b %d, %Y") if row.date_emission else "-",
            dueDate=row.date_echeance.strftime("%b %d, %Y") if row.date_echeance else "-",
            status=INVOICE_STATUS_TO_API.get(statut, "Sent"),
            processingStatus=INVOICE_PROCESSING_STATUS_TO_API.get(processing, "Pending"),
            items=[
                InvoiceItemOut(
                    description=i.designation,
                    qty=float(i.quantite or 0),
                    price=float(i.prix_unitaire or 0),
                    total=float((i.quantite or 0) * (i.prix_unitaire or 0)),
                )
                for i in row.items
            ],
        )


# --- Employees and users ----------------------------------------------------

class EmployeeOut(BaseModel):
    """An employee, with the name carried by their login account.

    The two are separate records since #60: `employees` holds the employment
    terms, `users` the login. The UI shows one person, so this joins them back
    together for display rather than making the frontend do it.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    userId: str
    name: str
    email: str
    jobTitle: Optional[str] = None
    role: str
    hiredOn: date
    employmentStatus: str
    annualEntitlementDays: int

    @classmethod
    def from_orm_row(cls, row) -> "EmployeeOut":
        user = row.user
        status = row.employment_status
        return cls(
            id=row.id,
            userId=row.user_id,
            name=f"{user.firstName or ''} {user.lastName or ''}".strip(),
            email=user.email,
            jobTitle=row.job_title,
            role=user.role,
            hiredOn=row.hired_on,
            employmentStatus=getattr(status, "value", status),
            annualEntitlementDays=row.annual_entitlement_days,
        )


class UserOut(BaseModel):
    """A login account.

    hashedPassword, resetToken and resetTokenExpiry are deliberately absent.
    The audit found the removed GET /api/data returning whole user rows, hashes
    included, to any authenticated caller; an explicit output schema is what
    stops that happening again by accident.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    role: str
    department: Optional[str] = None
    avatarUrl: Optional[str] = None
    isActive: bool
    isVerified: bool
    createdAt: Optional[str] = None

    @classmethod
    def from_orm_row(cls, row) -> "UserOut":
        return cls(
            id=row.id,
            email=row.email,
            firstName=row.firstName,
            lastName=row.lastName,
            role=row.role,
            department=row.department,
            avatarUrl=row.avatarUrl,
            isActive=bool(row.isActive),
            isVerified=bool(row.isVerified),
            createdAt=row.createdAt.isoformat() if row.createdAt else None,
        )
