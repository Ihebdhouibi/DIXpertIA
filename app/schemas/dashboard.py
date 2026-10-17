from typing import Optional

from pydantic import BaseModel, Field


class StatusFigure(BaseModel):
    """One invoice status: how many, and for how much (TTC)."""
    status: str
    count: int
    amount: float = 0.0


class InvoiceFigures(BaseModel):
    count: int
    amount: float
    # Every commercial status, zeros included, Overdue derived (#117).
    byStatus: list[StatusFigure]
    # Every processing state (#41), zeros included. Counts only.
    byProcessing: list[StatusFigure]


class LeaveFigures(BaseModel):
    # The caller's own for an employee or an accountant, everyone's for the
    # admin: row-level security decides, as for the leave list.
    pending: int


class TeamFigures(BaseModel):
    active: int
    total: int


class DashboardSummary(BaseModel):
    """The dashboard's figures, computed in SQL over every row (#120).

    Each block is present only for the roles that see it: `invoices` for the
    admin and the accountant, `team` for the admin. A block that is null is
    not "zero": the caller has no access to that data.
    """
    month: Optional[str] = Field(None, description="YYYY-MM when the invoice figures cover one month")
    invoices: Optional[InvoiceFigures] = None
    leave: LeaveFigures
    team: Optional[TeamFigures] = None
