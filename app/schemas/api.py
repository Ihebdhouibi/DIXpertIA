"""Translation between the ORM schema and the camelCase API contract.

This is Option C from #37: `app/models/` keeps its normalised schema - real
dates, enums, numerics, foreign keys - and the API keeps the camelCase shape the
frontend already consumes. These schemas are the seam between them.
...
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.i18n import format_date, format_date_range as _format_date_range, format_month
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
# REMOVED: The "Personal Day" alias.

LEAVE_STATUS_TO_API = {
    LeaveStatus.EN_ATTENTE: "Pending",
    LeaveStatus.APPROUVE: "Approved",
    LeaveStatus.REFUSE: "Rejected",
}
LEAVE_STATUS_FROM_API = {v: k for k, v in LEAVE_STATUS_TO_API.items()}


def format_date_range(start: date, end: date) -> str:
    """Render a range the way the UI displays it, in the request's language (#135)."""
    return _format_date_range(start, end)


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


def employee_name(employee) -> str:
    """An Employee row's full name; the name lives on its user account."""
    user = getattr(employee, "user", None) if employee else None
    return f"{user.firstName} {user.lastName}".strip() if user else ""


class LeaveRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    employeeId: Optional[int] = None
    employeeName: str = ""
    jobTitle: Optional[str] = None
    type: str
    dates: str
    startDate: date
    endDate: date
    duration: int
    status: str
    reason: Optional[str] = None
    rejectionReason: Optional[str] = None

    @classmethod
    def from_orm_row(cls, row, employee=None) -> "LeaveRequestOut":
        return cls(
            id=str(row.id),
            employeeId=row.employee_id,
            employeeName=employee_name(employee),
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


# --- Leave Balances (#121) --------------------------------------------------

class LeaveBalanceOut(BaseModel):
    """The calculated balance for one leave type."""
    type: str
    entitlement: float = 0.0
    approvedDays: float = 0.0
    pendingDays: float = 0.0
    availableDays: float = 0.0

class LeaveBalancesOut(BaseModel):
    """The list of all leave balances for a given year."""
    year: int
    balances: list[LeaveBalanceOut]


# --- Payslips ---------------------------------------------------------------

class PayslipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    employeeId: Optional[int] = None
    employeeName: str = ""
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
            employeeName=employee_name(row.employee),
            period=format_month(row.periode),
            grossPay=float(row.montant_brut or 0),
            netPay=float(row.montant_net or 0),
            issuedOn=format_date(issued),
            pdfUrl=row.fichier_pdf,
        )


# --- Invoices ---------------------------------------------------------------

INVOICE_STATUS_TO_API = {
    "brouillon": "Draft",
    "envoyee": "Sent",
    "payee": "Paid",
    "en_retard": "Overdue",
    "annulee": "Cancelled",
}

INVOICE_PROCESSING_STATUS_TO_API = {
    "pending": "Pending",
    "processed": "Processed",
    "completed": "Completed",
    "archived": "Archived",
}

INVOICE_REVIEW_STATUS_TO_API = {
    "not_submitted": "Not submitted",
    "submitted": "Submitted",
    "approved": "Approved",
    "rejected": "Rejected",
}


class InvoiceReviewOut(BaseModel):
    action: str
    actor: str
    comment: str
    at: str


class InvoiceItemOut(BaseModel):
    description: str
    qty: float
    price: float
    total: float
    vatRate: float
    detail: str | None = None
    unit: str | None = None


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    numero: Optional[str] = None
    reference: str
    direction: str
    counterparty: str
    counterpartyInitials: str
    counterpartyEmail: str = ""
    counterpartyAddress: str = ""
    supplierReference: Optional[str] = None
    amountHT: float
    amountTTC: float
    currency: str = "TND"
    export: bool = False
    dateIssued: str
    dueDate: str
    dueDateIso: Optional[str] = None
    dateIssuedIso: Optional[str] = None
    paidOn: Optional[str] = None
    cancelledAt: Optional[str] = None
    cancellationReason: Optional[str] = None
    status: str
    processingStatus: str
    reviewStatus: str = "Not submitted"
    reviews: list[InvoiceReviewOut] = Field(default_factory=list)
    items: list[InvoiceItemOut] = Field(default_factory=list)

    @classmethod
    def from_orm_row(cls, row) -> "InvoiceOut":
        direction = getattr(row.direction, "value", row.direction) or "outgoing"
        party = row.supplier if direction == "incoming" else row.client
        name = getattr(party, "nom", None) or "Unknown"
        initials = "".join(w[0] for w in name.split()[:2]).upper() or "?"
        shown = row.displayed_status() if hasattr(row, "displayed_status") else row.statut
        statut = getattr(shown, "value", shown) or "envoyee"
        processing = getattr(row.processing_status, "value", row.processing_status) or "pending"
        review = getattr(row.review_status, "value", row.review_status) or "not_submitted"
        return cls(
            id=str(row.id),
            numero=row.numero,
            reference=row.numero or f"BR-{row.id:04d}",
            reviewStatus=INVOICE_REVIEW_STATUS_TO_API.get(review, "Not submitted"),
            reviews=[
                InvoiceReviewOut(
                    action=getattr(r.action, "value", r.action),
                    actor=(f"{r.actor.firstName or ''} {r.actor.lastName or ''}".strip()
                           if r.actor else "") or (r.actor_id or ""),
                    comment=r.comment or "",
                    at=r.created_at.isoformat() if r.created_at else "",
                )
                for r in (row.reviews or [])
            ],
            direction=direction,
            counterparty=name,
            counterpartyInitials=initials,
            counterpartyEmail=getattr(party, "email", None) or "",
            counterpartyAddress=getattr(party, "adresse", None) or "",
            supplierReference=row.supplier_reference,
            amountHT=float(row.montant_ht or Decimal(0)),
            amountTTC=float(row.montant_ttc or Decimal(0)),
            currency=getattr(row, "devise", None) or "TND",
            export=bool(getattr(row, "export", False)),
            dateIssued=format_date(row.date_emission) or "-",
            dueDate=format_date(row.date_echeance) or "-",
            dueDateIso=row.date_echeance.isoformat() if row.date_echeance else None,
            dateIssuedIso=row.date_emission.isoformat() if row.date_emission else None,
            paidOn=format_date(row.paid_on),
            cancelledAt=row.cancelled_at.isoformat() if row.cancelled_at else None,
            cancellationReason=row.cancellation_reason,
            status=INVOICE_STATUS_TO_API.get(statut, "Sent"),
            processingStatus=INVOICE_PROCESSING_STATUS_TO_API.get(processing, "Pending"),
            items=[
                InvoiceItemOut(
                    description=i.designation,
                    qty=float(i.quantite or 0),
                    price=float(i.prix_unitaire or 0),
                    total=float((i.quantite or 0) * (i.prix_unitaire or 0)),
                    vatRate=float(i.taux_tva if i.taux_tva is not None else 0),
                    detail=i.detail,
                    unit=i.unite,
                )
                for i in row.items
            ],
        )


# --- Employees and users ----------------------------------------------------

class EmployeeOut(BaseModel):
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
    locale: str = "fr"

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
            locale=getattr(row, "locale", None) or "fr",
        )


# --- Small responses (#77) ---------------------------------------------------

class LoginOut(BaseModel):
    access_token: Optional[str] = None
    token_type: str = "bearer"
    user: Optional[UserOut] = None
    mfaRequired: bool = False
    challengeToken: Optional[str] = None
    mfaEnrolmentRequired: bool = False
    enrolToken: Optional[str] = None


class UserCreatedOut(BaseModel):
    id: str
    email: str
    activationEmailSent: bool


class ActivationSentOut(BaseModel):
    id: str
    activationEmailSent: bool


class MessageOut(BaseModel):
    message: str


class HealthOut(BaseModel):
    status: str


class NotificationsUpdatedOut(BaseModel):
    updated: int


class NotificationsDismissedOut(BaseModel):
    dismissed: int
