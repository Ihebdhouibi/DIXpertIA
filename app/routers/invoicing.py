from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError, IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.invoicing import (
    Client,
    Invoice,
    InvoiceDirection,
    InvoiceItem,
    InvoiceProcessingStatus,
    InvoiceReview,
    InvoiceReviewAction,
    InvoiceReviewStatus,
    InvoiceStatus,
    Supplier,
)
from app.models.audit import AuditEvent
from app.models.user import User
from app.services.audit import record_event
from app.services.notifications import notify, users_with_role
# InvoiceOut comes from app.schemas.api, not from .invoicing: that module
# holds the ORM-shaped schemas used to validate input, while the API's
# output contract is the translated one (#37 Option C). One response shape
# for every invoice endpoint means the UI never sees French column names.
from app.i18n import CATALOG, ApiError, current_locale, format_date, status_word, t, translate_db_message
from app.schemas.api import InvoiceOut
from app.schemas.audit import InvoiceHistoryEventOut
from app.schemas.invoicing import (
    ClientCreate,
    ClientOut,
    ClientUpdate,
    InvoiceCancellation,
    InvoiceCreate,
    InvoicePayment,
    InvoiceRejection,
    InvoiceUpdate,
    ProcessingStatusUpdate,
    SupplierCreate,
    SupplierInvoiceCreate,
    SupplierOut,
)
from app.services.invoice_generator import generate_invoice_pdf   # <-- new import

# Admin and accountant. An "rh" role used to be listed here too, but no
# account can hold it - users.role is CHECK-constrained to admin, employee and
# accountant (#58) - so it only suggested access nobody has (#77).
router = APIRouter(dependencies=[Depends(require_roles("admin", "accountant"))])

# Every list endpoint is paginated. The previous versions returned the whole
# table, so response size and query count grew without limit as data was added
# - on the seeded 20k-invoice dataset, listing invoices issued 20,002 queries
# and serialised every row the company had ever produced (#61).
DEFAULT_PAGE_SIZE = 50
# A hard cap, not a suggestion: without one, ?limit=1000000 restores the
# original behaviour on request.
MAX_PAGE_SIZE = 200

# The orders GET /api/invoices accepts. A closed list rather than a column name
# taken from the query string, so the client cannot sort on arbitrary columns.
InvoiceSort = Literal["date", "-date", "amount", "-amount"]
SORT_COLUMNS = {
    "date": (Invoice.date_emission, False),
    "-date": (Invoice.date_emission, True),
    "amount": (Invoice.montant_ttc, False),
    "-amount": (Invoice.montant_ttc, True),
}


def _paginate(response: Response, query, limit: int, offset: int):
    """Apply limit/offset and report the unpaginated total in a header.

    The total goes in X-Total-Count rather than wrapping the body in an
    envelope, so existing callers that expect a JSON array keep working.
    """
    response.headers["X-Total-Count"] = str(query.order_by(None).count())
    return query.limit(limit).offset(offset).all()


# ---- Clients ----

@router.get("/clients", response_model=list[ClientOut])
def list_clients(
    response: Response,
    db: Session = Depends(get_db),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
):
    return _paginate(response, db.query(Client).order_by(Client.nom), limit, offset)


# The client fields worth a line in the audit trail when they change (#63, #192).
_CLIENT_FIELDS = ("nom", "email", "telephone", "adresse", "locale")


def _commit_client(db: Session, name: str) -> None:
    """Commit, turning the case-insensitive unique name (ux_clients_nom_ci)
    into a clear 409. It used to surface as a 500."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(409, "client.name_taken", name=name) from exc


@router.post("/clients", response_model=ClientOut)
def create_client(payload: ClientCreate, db: Session = Depends(get_db)):
    client = Client(**payload.model_dump())
    db.add(client)
    try:
        db.flush()  # the id, for the audit event; a duplicate name fails here
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(409, "client.name_taken", name=payload.nom) from exc
    record_event(db, "client.created", "client", client.id, after=payload.model_dump())
    _commit_client(db, payload.nom)
    db.refresh(client)
    return client


@router.patch("/clients/{client_id}", response_model=ClientOut)
def update_client(client_id: int, payload: ClientUpdate, db: Session = Depends(get_db)):
    """Correct a client (#192): its name, contact details or invoice language.

    Only the fields sent change. The language decides how the client's invoices
    print from now on (#135); an invoice already issued is printed again in
    the new language, since the PDF is generated on each download.
    """
    client = db.get(Client, client_id)
    if client is None:
        raise ApiError(404, "client.not_found")
    changes = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    before = {k: getattr(client, k) for k in changes if getattr(client, k) != changes[k]}
    after = {k: changes[k] for k in before}
    if after:
        for field, value in after.items():
            setattr(client, field, value)
        record_event(db, "client.updated", "client", client.id, before=before, after=after)
        _commit_client(db, client.nom)
        db.refresh(client)
    return client


def _trigger_message(exc: DatabaseError) -> str:
    """Pull the database's own message out of the driver's wrapper.

    psycopg2 appends the failing statement and parameters to str(exc); only the
    first line is the message the trigger raised.
    """
    orig = getattr(exc, "orig", None)
    # The primary message without the severity prefix, which PostgreSQL writes
    # in the server's own locale ("ERROR:", "ERREUR:").
    diag = getattr(orig, "diag", None)
    line = getattr(diag, "message_primary", None)
    if not line:
        text_ = str(orig) if orig else str(exc)
        line = text_.strip().splitlines()[0].strip()
        for prefix in ("ERROR:", "ERREUR:", "FEHLER:"):
            if line.startswith(prefix):
                line = line[len(prefix):].strip()
    # Our own triggers raise in English; answer in the request's language
    # (#135). Anything else is shown as PostgreSQL wrote it.
    return translate_db_message(line) or line


# ---- Suppliers ----

@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(
    response: Response,
    db: Session = Depends(get_db),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
):
    return _paginate(response, db.query(Supplier).order_by(Supplier.nom), limit, offset)


@router.post("/suppliers", response_model=SupplierOut, status_code=201)
def create_supplier(payload: SupplierCreate, db: Session = Depends(get_db)):
    supplier = Supplier(**payload.model_dump())
    db.add(supplier)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # ux_suppliers_nom_ci. Two rows for one supplier would let the same bill
        # be entered once under each and so be paid twice.
        raise ApiError(409, "supplier.name_taken", name=payload.nom) from exc
    db.refresh(supplier)
    return supplier


# ---- Invoices ----

def _allocate_invoice_number(db: Session, series: str, year: int) -> str:
    """Take the next number in the year's series (#38).

    The accountant requires the series to start at 1 and increase by exactly 1,
    with no gaps and no duplicates. This replaces COUNT(*) + 1, which broke
    three ways: deleting an invoice made the next create collide with a number
    that already existed and fail with a 500; two concurrent creates computed
    the same number; and a failed transaction left a hole nobody detected.

    The UPDATE below takes a row lock held until this transaction commits, so a
    second create waits rather than reading a stale counter. If this
    transaction rolls back, the counter rolls back with it and the number is
    handed to the next caller instead of being burned.

    That serialises invoice creation on one row per series and year.
    Deliberate: a gapless counter and concurrent writes are in tension, and a
    few invoices a day does not strain it.

    `series` is 'FA' for invoices we issue and 'FF' for the internal reference
    given to a supplier's bill (#40). They are separate counters, so a purchase
    can never take a number out of the sales series.
    """
    # The year may have issued nothing yet. ON CONFLICT DO NOTHING rather than
    # a SELECT-then-INSERT, which would race with another first invoice.
    db.execute(
        text("INSERT INTO invoice_sequences (series, year, last_number)"
             " VALUES (:s, :y, 0) ON CONFLICT (series, year) DO NOTHING"),
        {"s": series, "y": year},
    )
    allocated = db.execute(
        text("UPDATE invoice_sequences SET last_number = last_number + 1"
             " WHERE series = :s AND year = :y RETURNING last_number"),
        {"s": series, "y": year},
    ).scalar_one()
    return f"{series}-{year}-{allocated:04d}"


def _compute_totals(items: list[dict]) -> tuple[Decimal, Decimal]:
    ht = sum(Decimal(str(i["quantite"])) * Decimal(str(i["prix_unitaire"])) for i in items) if items else Decimal(0)
    ttc = sum(
        Decimal(str(i["quantite"])) * Decimal(str(i["prix_unitaire"])) * (1 + Decimal(str(i["taux_tva"])) / 100)
        for i in items
    ) if items else Decimal(0)
    return ht, ttc


@router.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(
    response: Response,
    db: Session = Depends(get_db),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    direction: InvoiceDirection | None = None,
    client_id: int | None = None,
    supplier_id: int | None = None,
    statut: InvoiceStatus | None = None,
    processing_status: InvoiceProcessingStatus | None = None,
    review_status: InvoiceReviewStatus | None = None,
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$",
                              description="YYYY-MM: invoices issued in that month"),
    sort: InvoiceSort = Query("-date", description="date | -date | amount | -amount (- = descending)"),
):
    """List invoices, newest first unless `sort` says otherwise.

    selectinload is what stops the 1+N: InvoiceOut serialises `items`, so
    without it each invoice in the page triggered its own query for its lines -
    one page of 50 cost 52 queries, and the unpaginated list cost 20,002 on the
    seeded dataset. With it, a page costs two.

    The ordering tie-breaks on id because date_emission is only a date: several
    invoices share one, and without a tie-break their relative order is
    undefined, so paging could show a row twice or skip it entirely.
    """
    # Sorting happens here, not in the browser: the list is paginated, so
    # sorting one page client-side would rank 50 rows out of thousands (#113).
    # Every order tie-breaks on id, for the same stable-paging reason as below.
    column, descending = SORT_COLUMNS[sort]
    query = (
        db.query(Invoice)
        .options(selectinload(Invoice.items),
                 selectinload(Invoice.reviews).selectinload(InvoiceReview.actor))
        .order_by(column.desc() if descending else column.asc(),
                  Invoice.id.desc() if descending else Invoice.id.asc())
    )
    if direction is not None:
        query = query.filter(Invoice.direction == direction)
    if client_id is not None:
        query = query.filter(Invoice.client_id == client_id)
    if supplier_id is not None:
        query = query.filter(Invoice.supplier_id == supplier_id)
    if statut == InvoiceStatus.EN_RETARD:
        # Derived, as in Invoice.displayed_status() (#117): sent and past due.
        # "Sent" below excludes them, so each invoice is under one status.
        query = query.filter(Invoice.statut == InvoiceStatus.ENVOYEE, Invoice.date_echeance < date.today())
    elif statut == InvoiceStatus.ENVOYEE:
        query = query.filter(Invoice.statut == InvoiceStatus.ENVOYEE, Invoice.date_echeance >= date.today())
    elif statut is not None:
        query = query.filter(Invoice.statut == statut)
    if processing_status is not None:
        query = query.filter(Invoice.processing_status == processing_status)
    if review_status is not None:
        query = query.filter(Invoice.review_status == review_status)
    if month is not None:
        start = date(int(month[:4]), int(month[5:]), 1)
        end = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
        query = query.filter(Invoice.date_emission >= start, Invoice.date_emission < end)
    return [InvoiceOut.from_orm_row(i)
            for i in _paginate(response, query, limit, offset)]


# Creating an invoice is admin-only, overriding the router-wide list. The
# accountant reviews invoices; letting her create the ones she reviews removes
# the separation of duties (AUDIT-DB-010). Read access is unchanged.
@router.post(
    "/invoices",
    response_model=InvoiceOut,
    dependencies=[Depends(require_roles("admin"))],
)
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    """Create an invoice.

    An issued invoice cannot be deleted in accounting, so a duplicate costs a
    credit note to undo. Two things guard against that here:

    - An Idempotency-Key, if supplied, is stored with the invoice under a
      UNIQUE constraint. Replaying the same request returns the invoice that
      was already created instead of allocating a second legal number.
    - The response is built and validated BEFORE the commit. Previously
      `statut` was never set and stayed NULL, so serialising the response
      raised ResponseValidationError *after* the row was committed: the
      invoice existed, the client saw a 500, and the retry created a second
      one.
    """
    if idempotency_key:
        existing = db.query(Invoice).filter(
            Invoice.idempotency_key == idempotency_key
        ).first()
        if existing:
            return InvoiceOut.from_orm_row(existing)

    items_data = [item.model_dump() for item in payload.items]
    montant_ht, montant_ttc = _compute_totals(items_data)

    # No legal number yet: a draft gets one when the accountant approves it
    # (#118), so a draft that is rejected and abandoned never takes a number
    # out of the series. date_emission is the creation date until then, and
    # is set again to the approval date with the number.
    invoice = Invoice(
        client_id=payload.client_id,
        date_emission=date.today(),
        date_echeance=payload.date_echeance,
        montant_ht=montant_ht,
        montant_ttc=montant_ttc,
        statut=InvoiceStatus.BROUILLON,
        direction=InvoiceDirection.OUTGOING,
        cree_par_id=current_user.id,
        idempotency_key=idempotency_key,
    )
    db.add(invoice)
    db.flush()  # assigns invoice.id without committing

    for item in items_data:
        db.add(InvoiceItem(invoice_id=invoice.id, **item))
    db.flush()
    db.refresh(invoice)
    # Not on an idempotent replay above: that returns the existing invoice and
    # creates nothing, so it records nothing.
    record_event(db, "invoice.created", "invoice", invoice.id, after={
        "direction": invoice.direction, "client_id": invoice.client_id,
        "montant_ht": montant_ht, "montant_ttc": montant_ttc,
        "date_echeance": invoice.date_echeance, "lines": len(items_data),
    })

    # Validate the response while the transaction can still be rolled back. If
    # this raises, nothing is persisted and the caller may safely retry.
    response = InvoiceOut.from_orm_row(invoice)

    db.commit()
    # TODO: generate PDF (WeasyPrint) + send email to client
    return response


@router.post(
    "/supplier-invoices",
    response_model=InvoiceOut,
    status_code=201,
    dependencies=[Depends(require_roles("admin", "accountant"))],
)
def create_supplier_invoice(
    payload: SupplierInvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record a bill a supplier issued to us (#40).

    Admin and accountant only: booking an expense is bookkeeping, the same
    boundary as moving an invoice's processing status.

    The bill keeps the supplier's own number in `supplier_reference` and gets an
    internal FF-YYYY-NNNN reference of its own in `numero`. Two suppliers both
    numbering a bill "2026-001" is ordinary, so uniqueness on their reference is
    per supplier - which is also what stops the same bill being entered, and
    paid, twice.

    `date_emission` is the supplier's date, not today's. It decides which month
    the expense belongs to, so a bill whose month has already closed is refused
    by the period seal from #42 rather than quietly landing in the open one.
    """
    if not db.get(Supplier, payload.supplier_id):
        raise ApiError(404, "supplier.not_found")

    invoice = Invoice(
        numero=_allocate_invoice_number(db, "FF", payload.date_emission.year),
        direction=InvoiceDirection.INCOMING,
        supplier_id=payload.supplier_id,
        supplier_reference=payload.supplier_reference,
        date_emission=payload.date_emission,
        date_echeance=payload.date_echeance,
        # Taken from the bill, not computed from its lines: the supplier's
        # totals are theirs, and rounding conventions differ.
        montant_ht=payload.montant_ht,
        montant_ttc=payload.montant_ttc,
        statut=InvoiceStatus.ENVOYEE,
        cree_par_id=current_user.id,
    )
    # The flush is inside the guard, not only the commit: uq_supplier_reference
    # and the period seal both raise as soon as the row is sent, which is well
    # before commit. Guarding the commit alone let a duplicate bill surface as
    # an unhandled 500 instead of the 409 that tells the accountant it is
    # already recorded.
    try:
        db.add(invoice)
        db.flush()
        for item in payload.items:
            db.add(InvoiceItem(invoice_id=invoice.id, **item.model_dump()))
        db.flush()
        db.refresh(invoice)
        record_event(db, "invoice.created", "invoice", invoice.id, after={
            "direction": invoice.direction, "supplier_id": invoice.supplier_id,
            "supplier_reference": invoice.supplier_reference, "numero": invoice.numero,
            "montant_ht": invoice.montant_ht, "montant_ttc": invoice.montant_ttc,
            "date_emission": invoice.date_emission,
        })
        # Built before the commit, for the reason set out on create_invoice.
        response = InvoiceOut.from_orm_row(invoice)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(409, "supplier_invoice.duplicate", ref=payload.supplier_reference) from exc
    except DatabaseError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=_trigger_message(exc)) from exc
    return response


@router.patch(
    "/invoices/{invoice_id}/processing-status",
    response_model=InvoiceOut,
    dependencies=[Depends(require_roles("admin", "accountant"))],
)
def set_processing_status(
    invoice_id: int,
    payload: ProcessingStatusUpdate,
    db: Session = Depends(get_db),
):
    """Move an invoice through the accountant's workflow.

    Admin and accountant only: this is bookkeeping, not a commercial act.

    The legality of a move is not checked here. A trigger refuses anything that
    would change an archived invoice, so the rule holds for a direct SQL write
    too, and this endpoint only has to report the refusal.
    """
    invoice = db.get(Invoice, invoice_id, options=[selectinload(Invoice.items)])
    if not invoice:
        raise ApiError(404, "invoice.not_found")

    record_event(db, "invoice.processing_status_changed", "invoice", invoice.id,
                 before={"processing_status": invoice.processing_status},
                 after={"processing_status": payload.processing_status})
    invoice.processing_status = payload.processing_status
    try:
        db.commit()
    except DatabaseError as exc:
        db.rollback()
        # The trigger's message names the invoice and the reason; surfacing it
        # is more useful than a generic 409, and it is written for a reader.
        raise HTTPException(status_code=409, detail=_trigger_message(exc)) from exc
    db.refresh(invoice)
    return InvoiceOut.from_orm_row(invoice)


# Admin only, like creation: the accountant reviews invoices and notes the
# changes needed; the admin makes them (#118). Letting the reviewer edit what
# she reviews would remove the separation of duties creation already keeps.
@router.patch(
    "/invoices/{invoice_id}",
    response_model=InvoiceOut,
    dependencies=[Depends(require_roles("admin"))],
)
def update_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    db: Session = Depends(get_db),
):
    """Correct a draft invoice: replace its lines and its due date (#125).

    Only a draft of an invoice we issue can change. The checks here exist to
    answer with a clear status before touching anything; the rule itself is
    held by two triggers (invoice_draft_is_editable, invoice_lines_follow_their_
    invoice), so a direct SQL write is refused too, and a race between this
    check and the write is still caught at the database.

    Totals are recomputed from the new lines with the same arithmetic as
    creation; the client never supplies them.
    """
    invoice = db.get(Invoice, invoice_id, options=[selectinload(Invoice.items)])
    if not invoice:
        raise ApiError(404, "invoice.not_found")
    if invoice.direction != InvoiceDirection.OUTGOING:
        raise ApiError(409, "invoice.supplier_bill_not_editable", ref=invoice.reference)
    if invoice.statut != InvoiceStatus.BROUILLON:
        raise ApiError(409, "invoice.not_a_draft", ref=invoice.reference)
    # Frozen while the accountant verifies it, and once approved (#118).
    if invoice.review_status in (InvoiceReviewStatus.SUBMITTED, InvoiceReviewStatus.APPROVED):
        raise ApiError(409, "invoice.under_review", ref=invoice.reference)
    # Mirrors ck_invoices_dates with a field-level answer instead of a 500.
    if payload.date_echeance < invoice.date_emission:
        raise ApiError(422, "invoice.due_before_issue")

    items_data = [item.model_dump() for item in payload.items]
    montant_ht, montant_ttc = _compute_totals(items_data)
    before = {"date_echeance": invoice.date_echeance, "montant_ht": invoice.montant_ht,
              "montant_ttc": invoice.montant_ttc, "lines": len(invoice.items)}
    try:
        # Lines first, totals after: both are guarded, and the order keeps the
        # invoice and its lines consistent at every statement.
        invoice.items.clear()
        db.flush()
        for item in items_data:
            db.add(InvoiceItem(invoice_id=invoice.id, **item))
        invoice.date_echeance = payload.date_echeance
        invoice.montant_ht = montant_ht
        invoice.montant_ttc = montant_ttc
        db.flush()
        db.refresh(invoice)
        record_event(db, "invoice.updated", "invoice", invoice.id, before=before, after={
            "date_echeance": payload.date_echeance, "montant_ht": montant_ht,
            "montant_ttc": montant_ttc, "lines": len(items_data),
        })
        # Built before the commit, for the reason set out on create_invoice.
        response = InvoiceOut.from_orm_row(invoice)
        db.commit()
    except DatabaseError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=_trigger_message(exc)) from exc
    return response


# ---- Verification before sending (#118) ----
#
#   Draft --submit (admin)--> Submitted --approve (accountant)--> Approved --send (admin)--> Sent
#                                 |
#                                 +--reject with comment (accountant)--> Rejected --edit, submit-->
#
# The checks below answer with a clear status and message before touching
# anything. The rules themselves live in the database (trg_invoice_review_rules,
# trg_invoice_review_is_valid, ck_invoices_numbered_once_approved), so a direct
# SQL write is refused too, and a race between a check and its write is still
# caught there and reported as a 409.


def _outgoing_draft(db: Session, invoice_id: int) -> Invoice:
    invoice = db.get(Invoice, invoice_id, options=[
        selectinload(Invoice.items),
        selectinload(Invoice.reviews).selectinload(InvoiceReview.actor),
    ])
    if not invoice:
        raise ApiError(404, "invoice.not_found")
    if invoice.direction != InvoiceDirection.OUTGOING:
        raise ApiError(409, "invoice.supplier_bill_not_reviewed", ref=invoice.reference)
    return invoice


def _counterparty(invoice: Invoice) -> str | None:
    """The client's or supplier's name, for a notification; None if unknown,
    which the notification text renders in the reader's language (#135)."""
    party = invoice.supplier if invoice.direction == InvoiceDirection.INCOMING else invoice.client
    return party.nom if party else None


def _commit_review(db: Session, invoice: Invoice) -> InvoiceOut:
    """Flush, build the response while it can still roll back, then commit."""
    try:
        db.flush()
        db.refresh(invoice)
        response = InvoiceOut.from_orm_row(invoice)
        db.commit()
    except DatabaseError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=_trigger_message(exc)) from exc
    return response


@router.post(
    "/invoices/{invoice_id}/submit",
    response_model=InvoiceOut,
    dependencies=[Depends(require_roles("admin"))],
)
def submit_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a draft to the accountant for verification (#118). Admin only.

    A first submission, or a resubmission after a rejection once the admin has
    corrected the draft (#125). From here the content is frozen.
    """
    invoice = _outgoing_draft(db, invoice_id)
    if invoice.statut != InvoiceStatus.BROUILLON or invoice.review_status not in (
            InvoiceReviewStatus.NOT_SUBMITTED, InvoiceReviewStatus.REJECTED):
        raise ApiError(409, "invoice.not_submittable", ref=invoice.reference)
    if not invoice.items:
        raise ApiError(422, "invoice.needs_a_line")
    record_event(db, "invoice.submitted", "invoice", invoice.id,
                 before={"review_status": invoice.review_status},
                 after={"review_status": InvoiceReviewStatus.SUBMITTED})
    invoice.review_status = InvoiceReviewStatus.SUBMITTED
    db.add(InvoiceReview(invoice_id=invoice.id, actor_id=current_user.id,
                         action=InvoiceReviewAction.SUBMITTED, comment=""))
    # Every accountant is told (#116): whoever is free picks it up.
    notify(db, users_with_role(db, "accountant"), kind="invoice_submitted", tone="info",
           params={"ref": invoice.reference, "party": _counterparty(invoice)},
           link="invoices", ref_type="invoice", ref_id=invoice.id, exclude=current_user.id)
    return _commit_review(db, invoice)


@router.post(
    "/invoices/{invoice_id}/approve",
    response_model=InvoiceOut,
    dependencies=[Depends(require_roles("accountant"))],
)
def approve_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve a submitted invoice: it gets its legal number now (#118).

    Accountant only. The number comes from the gapless series (#38) inside this
    transaction, with today as the issue date, so numbers keep following issue
    dates (#39). A draft that was rejected and abandoned never took a number,
    which is the point of allocating here rather than at creation.
    """
    invoice = _outgoing_draft(db, invoice_id)
    if invoice.statut != InvoiceStatus.BROUILLON or invoice.review_status != InvoiceReviewStatus.SUBMITTED:
        raise ApiError(409, "invoice.not_awaiting_review", ref=invoice.reference)
    if invoice.cree_par_id == current_user.id:
        raise ApiError(403, "invoice.no_self_approval")
    issued_on = date.today()
    # ck_invoices_dates would refuse it at the database; say what to do instead.
    if invoice.date_echeance < issued_on:
        raise ApiError(409, "invoice.due_before_today", ref=invoice.reference,
                       due=format_date(invoice.date_echeance))
    before = {"review_status": invoice.review_status, "numero": invoice.numero,
              "date_emission": invoice.date_emission}
    invoice.review_status = InvoiceReviewStatus.APPROVED
    # A legacy draft may already hold a number from before #118; it keeps it.
    if invoice.numero is None:
        invoice.numero = _allocate_invoice_number(db, "FA", issued_on.year)
        invoice.date_emission = issued_on
    record_event(db, "invoice.approved", "invoice", invoice.id, before=before, after={
        "review_status": invoice.review_status, "numero": invoice.numero,
        "date_emission": invoice.date_emission,
    })
    db.add(InvoiceReview(invoice_id=invoice.id, actor_id=current_user.id,
                         action=InvoiceReviewAction.APPROVED, comment=""))
    notify(db, [invoice.cree_par_id], kind="invoice_approved", tone="success",
           params={"ref": invoice.numero, "party": _counterparty(invoice)},
           link="invoices", ref_type="invoice", ref_id=invoice.id, exclude=current_user.id)
    return _commit_review(db, invoice)


@router.post(
    "/invoices/{invoice_id}/reject",
    response_model=InvoiceOut,
    dependencies=[Depends(require_roles("accountant"))],
)
def reject_invoice(
    invoice_id: int,
    payload: InvoiceRejection,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a submitted invoice back with what to correct (#118).

    Accountant only, and the comment is mandatory: it is what the admin works
    from. The draft becomes editable again (#125) and can be resubmitted.
    """
    invoice = _outgoing_draft(db, invoice_id)
    if invoice.statut != InvoiceStatus.BROUILLON or invoice.review_status != InvoiceReviewStatus.SUBMITTED:
        raise ApiError(409, "invoice.not_awaiting_review", ref=invoice.reference)
    if invoice.cree_par_id == current_user.id:
        raise ApiError(403, "invoice.no_self_rejection")
    record_event(db, "invoice.rejected", "invoice", invoice.id,
                 before={"review_status": invoice.review_status},
                 after={"review_status": InvoiceReviewStatus.REJECTED, "comment": payload.comment})
    invoice.review_status = InvoiceReviewStatus.REJECTED
    db.add(InvoiceReview(invoice_id=invoice.id, actor_id=current_user.id,
                         action=InvoiceReviewAction.REJECTED, comment=payload.comment))
    notify(db, [invoice.cree_par_id], kind="invoice_rejected", tone="warning",
           params={"ref": invoice.reference, "party": _counterparty(invoice), "comment": payload.comment},
           link="invoices", ref_type="invoice", ref_id=invoice.id, exclude=current_user.id)
    return _commit_review(db, invoice)


@router.post(
    "/invoices/{invoice_id}/send",
    response_model=InvoiceOut,
    dependencies=[Depends(require_roles("admin"))],
)
def send_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Mark an approved invoice as sent to the client (#118). Admin only.

    Refused unless the accountant approved it; the database refuses it too
    (trg_invoice_review_rules). From here the books can take it (#96).
    Delivering the PDF by e-mail is not part of this step yet.
    """
    invoice = _outgoing_draft(db, invoice_id)
    if invoice.statut != InvoiceStatus.BROUILLON:
        raise ApiError(409, "invoice.already_left_draft", ref=invoice.reference)
    if invoice.review_status != InvoiceReviewStatus.APPROVED:
        raise ApiError(409, "invoice.send_before_approval", ref=invoice.reference)
    record_event(db, "invoice.sent", "invoice", invoice.id,
                 before={"statut": invoice.statut}, after={"statut": InvoiceStatus.ENVOYEE})
    invoice.statut = InvoiceStatus.ENVOYEE
    return _commit_review(db, invoice)


# ---- Paid and cancelled (#126) ----
#
#   Draft     --cancel (admin, reason)--> Cancelled      (not while under verification)
#   Sent      --pay (admin or accountant, date)--> Paid
#   Sent      --cancel (admin, reason)--> Cancelled      (not once its month is closed)
#
# Paid and Cancelled are final. The checks below answer with a clear status
# before touching anything; trg_invoice_commercial_transitions holds the same
# rules for a direct SQL write, and a race is still caught there as a 409.

# Overdue is not a stored status (#117): an overdue invoice is stored as sent.
AWAITING_PAYMENT = (InvoiceStatus.ENVOYEE,)


def _any_invoice(db: Session, invoice_id: int) -> Invoice:
    invoice = db.get(Invoice, invoice_id, options=[
        selectinload(Invoice.items),
        selectinload(Invoice.reviews).selectinload(InvoiceReview.actor),
    ])
    if not invoice:
        raise ApiError(404, "invoice.not_found")
    return invoice


@router.post(
    "/invoices/{invoice_id}/pay",
    response_model=InvoiceOut,
    dependencies=[Depends(require_roles("admin", "accountant"))],
)
def pay_invoice(invoice_id: int, payload: InvoicePayment, db: Session = Depends(get_db)):
    """Record that an invoice was paid in full on `paid_on` (#126).

    Admin or accountant, for an invoice we issued or a bill we received. Also
    after the month is closed: late payment is why the archived seal leaves
    the commercial status alone (#41). Partial payments are not modelled.
    """
    invoice = _any_invoice(db, invoice_id)
    if invoice.statut not in AWAITING_PAYMENT:
        raise ApiError(409, "invoice.not_payable", ref=invoice.reference, status=status_word(invoice.statut))
    if payload.paid_on > date.today():
        raise ApiError(422, "payment.in_future")
    if payload.paid_on < invoice.date_emission:
        raise ApiError(422, "payment.before_issue", date=format_date(invoice.date_emission))
    record_event(db, "invoice.paid", "invoice", invoice.id,
                 before={"statut": invoice.statut},
                 after={"statut": InvoiceStatus.PAYEE, "paid_on": payload.paid_on})
    invoice.statut = InvoiceStatus.PAYEE
    invoice.paid_on = payload.paid_on
    return _commit_review(db, invoice)


@router.post(
    "/invoices/{invoice_id}/cancel",
    response_model=InvoiceOut,
    dependencies=[Depends(require_roles("admin"))],
)
def cancel_invoice(
    invoice_id: int,
    payload: InvoiceCancellation,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel an invoice, with a reason (#126). Admin only.

    A draft has no legal number, so nothing is left in the series. An approved
    or sent invoice keeps its number, now ANNULEE: the series stays gapless
    and the number stays justified. Its credit note is a separate document,
    so the accountants are told, to book it.
    """
    invoice = _any_invoice(db, invoice_id)
    if invoice.statut not in (InvoiceStatus.BROUILLON, *AWAITING_PAYMENT):
        raise ApiError(409, "invoice.not_cancellable", ref=invoice.reference, status=status_word(invoice.statut))
    if invoice.review_status == InvoiceReviewStatus.SUBMITTED and invoice.statut == InvoiceStatus.BROUILLON:
        raise ApiError(409, "invoice.cancel_under_review", ref=invoice.reference)
    if invoice.processing_status == InvoiceProcessingStatus.ARCHIVED:
        raise ApiError(409, "invoice.cancel_closed_month", ref=invoice.reference)
    record_event(db, "invoice.cancelled", "invoice", invoice.id,
                 before={"statut": invoice.statut, "numero": invoice.numero},
                 after={"statut": InvoiceStatus.ANNULEE, "reason": payload.reason})
    invoice.statut = InvoiceStatus.ANNULEE
    invoice.cancelled_at = datetime.now(timezone.utc)
    invoice.cancellation_reason = payload.reason
    if invoice.numero:
        notify(db, users_with_role(db, "accountant"), kind="invoice_cancelled", tone="warning",
               params={"ref": invoice.numero, "party": _counterparty(invoice), "reason": payload.reason},
               link="invoices", ref_type="invoice", ref_id=invoice.id, exclude=current_user.id)
    return _commit_review(db, invoice)


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    # db.get, not the legacy Query.get, which is deprecated in SQLAlchemy 2.0.
    invoice = db.get(Invoice, invoice_id, options=[
        selectinload(Invoice.items),
        selectinload(Invoice.reviews).selectinload(InvoiceReview.actor),
    ])
    if not invoice:
        raise ApiError(404, "invoice.not_found")
    return InvoiceOut.from_orm_row(invoice)


def _history_label(event: AuditEvent) -> str:
    """One audit event of an invoice, in words (#115), in the request's language (#135)."""
    before, after = event.before or {}, event.after or {}
    if event.action == "invoice.created":
        if after.get("direction") == InvoiceDirection.INCOMING.value:
            return t("history.bill_recorded", ref=after.get("numero") or t("history.bill"))
        return t("history.created")
    if event.action == "invoice.updated":
        return t("history.updated")
    if event.action == "invoice.submitted":
        return t("history.submitted")
    if event.action == "invoice.approved":
        number = after.get("numero")
        return t("history.approved_numbered", number=number) if number else t("history.approved")
    if event.action == "invoice.rejected":
        comment = after.get("comment")
        return t("history.rejected_because", comment=comment) if comment else t("history.rejected")
    if event.action == "invoice.sent":
        return t("history.sent")
    if event.action == "invoice.paid":
        paid_on = after.get("paid_on")
        if paid_on:
            return t("history.paid_on", date=format_date(date.fromisoformat(paid_on)))
        return t("history.paid")
    if event.action == "invoice.cancelled":
        reason = after.get("reason")
        return t("history.cancelled_because", reason=reason) if reason else t("history.cancelled")
    if event.action == "invoice.processing_status_changed":
        def label(value):
            key = f"processing.{value}"
            return t(key) if value and key in CATALOG else (value or "?")
        return t("history.books", from_=label(before.get("processing_status")),
                 to=label(after.get("processing_status")))
    return event.action


@router.get("/invoices/{invoice_id}/history", response_model=list[InvoiceHistoryEventOut])
def invoice_history(invoice_id: int, db: Session = Depends(get_db)):
    """Every recorded step of one invoice, newest first (#115).

    Read from the audit trail of #63, the single record of what happened, so
    the history and the trail can never disagree. Admin and accountant, like
    the rest of this router; the policy audit_events_invoice_history_read_by_
    accountant lets the accountant see invoice events and nothing else.
    """
    if not db.get(Invoice, invoice_id):
        raise ApiError(404, "invoice.not_found")
    rows = (
        db.query(AuditEvent, User.firstName, User.lastName)
        .outerjoin(User, User.id == AuditEvent.actor_id)
        .filter(AuditEvent.entity == "invoice", AuditEvent.entity_id == str(invoice_id))
        .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
        .all()
    )
    return [
        InvoiceHistoryEventOut(
            id=str(event.id),
            occurredAt=event.occurred_at,
            action=event.action,
            label=_history_label(event),
            actorName=f"{first or ''} {last or ''}".strip() or t("history.unknown_actor"),
            actorRole=event.actor_role,
        )
        for event, first, last in rows
    ]


def _pdf_data(invoice: Invoice) -> dict:
    """What the PDF generator needs from an invoice.

    The counterparty follows the direction (#40): the client for an invoice we
    issue, the supplier for a bill we received. Reading only `invoice.client`
    printed "Unknown" on every supplier bill (#86).
    """
    party = invoice.supplier if invoice.direction == InvoiceDirection.INCOMING else invoice.client
    locale = (invoice.client.locale if invoice.direction == InvoiceDirection.OUTGOING and invoice.client
              else current_locale())
    items = [
        {
            "description": item.designation,
            "qty": float(item.quantite),
            "price": float(item.prix_unitaire),
            "total": float(item.quantite * item.prix_unitaire),
        }
        for item in invoice.items
    ]
    return {
        # A draft has no legal number yet: the PDF shows its BR- reference and
        # a DRAFT watermark, so it cannot pass for an invoice (#118).
        "invoice_id": invoice.reference,
        "draft": invoice.numero is None,
        "client": party.nom if party else "",
        "client_address": party.adresse if party else "",
        # The client's language (#135): the same invoice always prints the same
        # way, whoever downloads it. A supplier bill is ours to read: the
        # request's language.
        "locale": locale,
        "date_issued": format_date(invoice.date_emission, locale),
        "due_date": format_date(invoice.date_echeance, locale),
        # As the API shows it: Overdue is derived from the due date (#117).
        "status": invoice.displayed_status().value,
        "items": items,
        "subtotal": float(invoice.montant_ht),
        "total": float(invoice.montant_ttc),
    }


# By the internal id, like every other invoice route. It used to match
# `numero`, while the UI sends the id, so the Download button answered 404 for
# every invoice (#86). The id also exists before an invoice has a legal number,
# which drafts will not have once #118 assigns it at approval.
@router.get("/invoices/{invoice_id}/download")
def download_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    inline: bool = Query(False, description="Display in the browser instead of saving (#127)."),
):
    """Generate an invoice as PDF, to save or, with ?inline=true, to display.

    The invoice detail embeds the same file the Download button saves, so what
    the accountant reviews is exactly what the client receives (#127, #118).
    """
    invoice = db.get(Invoice, invoice_id, options=[
        selectinload(Invoice.items), selectinload(Invoice.client), selectinload(Invoice.supplier),
    ])
    if not invoice:
        raise ApiError(404, "invoice.not_found")

    pdf_bytes = generate_invoice_pdf(_pdf_data(invoice))
    filename = f"Invoice_{invoice.reference}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'{"inline" if inline else "attachment"}; filename="{filename}"'}
    )
