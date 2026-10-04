from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.invoicing import Client, Invoice, InvoiceItem, InvoiceStatus
from app.models.user import User
from app.schemas.invoicing import ClientCreate, ClientOut, InvoiceCreate, InvoiceOut
from app.services.invoice_generator import generate_invoice_pdf   # <-- new import

# Allow admin, rh, and accountant to access invoice routes
router = APIRouter(dependencies=[Depends(require_roles("rh", "admin", "accountant"))])

# Every list endpoint is paginated. The previous versions returned the whole
# table, so response size and query count grew without limit as data was added
# - on the seeded 20k-invoice dataset, listing invoices issued 20,002 queries
# and serialised every row the company had ever produced (#61).
DEFAULT_PAGE_SIZE = 50
# A hard cap, not a suggestion: without one, ?limit=1000000 restores the
# original behaviour on request.
MAX_PAGE_SIZE = 200


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


@router.post("/clients", response_model=ClientOut)
def create_client(payload: ClientCreate, db: Session = Depends(get_db)):
    client = Client(**payload.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


# ---- Invoices ----

def _generate_invoice_number(db: Session) -> str:
    year = date.today().year
    count = db.query(Invoice).filter(Invoice.numero.like(f"FA-{year}-%")).count() + 1
    return f"FA-{year}-{count:04d}"


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
    client_id: int | None = None,
    statut: InvoiceStatus | None = None,
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$",
                              description="YYYY-MM: invoices issued in that month"),
):
    """List invoices, newest first.

    selectinload is what stops the 1+N: InvoiceOut serialises `items`, so
    without it each invoice in the page triggered its own query for its lines -
    one page of 50 cost 52 queries, and the unpaginated list cost 20,002 on the
    seeded dataset. With it, a page costs two.

    The ordering tie-breaks on id because date_emission is only a date: several
    invoices share one, and without a tie-break their relative order is
    undefined, so paging could show a row twice or skip it entirely.
    """
    query = (
        db.query(Invoice)
        .options(selectinload(Invoice.items))
        .order_by(Invoice.date_emission.desc(), Invoice.id.desc())
    )
    if client_id is not None:
        query = query.filter(Invoice.client_id == client_id)
    if statut is not None:
        query = query.filter(Invoice.statut == statut)
    if month is not None:
        start = date(int(month[:4]), int(month[5:]), 1)
        end = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
        query = query.filter(Invoice.date_emission >= start, Invoice.date_emission < end)
    return _paginate(response, query, limit, offset)


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
            return existing

    items_data = [item.model_dump() for item in payload.items]
    montant_ht, montant_ttc = _compute_totals(items_data)

    invoice = Invoice(
        numero=_generate_invoice_number(db),
        client_id=payload.client_id,
        date_emission=date.today(),
        date_echeance=payload.date_echeance,
        montant_ht=montant_ht,
        montant_ttc=montant_ttc,
        statut=InvoiceStatus.BROUILLON,
        cree_par_id=current_user.id,
        idempotency_key=idempotency_key,
    )
    db.add(invoice)
    db.flush()  # assigns invoice.id without committing

    for item in items_data:
        db.add(InvoiceItem(invoice_id=invoice.id, **item))
    db.flush()
    db.refresh(invoice)

    # Validate the response while the transaction can still be rolled back. If
    # this raises, nothing is persisted and the caller may safely retry.
    response = InvoiceOut.model_validate(invoice, from_attributes=True)

    db.commit()
    # TODO: generate PDF (WeasyPrint) + send email to client
    return response


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    # db.get, not the legacy Query.get, which is deprecated in SQLAlchemy 2.0.
    invoice = db.get(Invoice, invoice_id, options=[selectinload(Invoice.items)])
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture introuvable")
    return invoice


# ---- Download Invoice PDF (NEW) ----
@router.get("/invoices/{invoice_number}/download")
def download_invoice(
    invoice_number: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate and download an invoice as PDF.
    """
    invoice = (
        db.query(Invoice)
        .options(selectinload(Invoice.items), selectinload(Invoice.client))
        .filter(Invoice.numero == invoice_number)
        .first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Build items list
    items = []
    for item in invoice.items:
        items.append({
            "description": item.designation,
            "qty": float(item.quantite),
            "price": float(item.prix_unitaire),
            "total": float(item.quantite * item.prix_unitaire)
        })

    # Client info
    client = invoice.client
    client_name = client.nom if client else "Unknown"
    client_address = client.adresse if client else "N/A"

    # Prepare data for PDF generator
    invoice_data = {
        "invoice_id": invoice.numero,
        "client": client_name,
        "client_address": client_address,
        "date_issued": invoice.date_emission.strftime("%b %d, %Y"),
        "due_date": invoice.date_echeance.strftime("%b %d, %Y"),
        "status": (
            invoice.statut
            if isinstance(invoice.statut, str)
            else (invoice.statut.value if invoice.statut else "Sent")
        ),
        "items": items,
        "subtotal": float(invoice.montant_ht),
        "total": float(invoice.montant_ttc),
    }

    pdf_bytes = generate_invoice_pdf(invoice_data)
    filename = f"Invoice_{invoice.numero}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
