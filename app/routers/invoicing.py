from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.invoicing import Client, Invoice, InvoiceItem
from app.models.user import User
from app.schemas.invoicing import ClientCreate, ClientOut, InvoiceCreate, InvoiceOut
from app.services.invoice_generator import generate_invoice_pdf   # <-- new import

# Allow admin, rh, and accountant to access invoice routes
router = APIRouter(dependencies=[Depends(require_roles("rh", "admin", "accountant"))])


# ---- Clients ----

@router.get("/clients", response_model=list[ClientOut])
def list_clients(db: Session = Depends(get_db)):
    return db.query(Client).all()


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
def list_invoices(db: Session = Depends(get_db)):
    return db.query(Invoice).order_by(Invoice.date_emission.desc()).all()


@router.post("/invoices", response_model=InvoiceOut)
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items_data = [item.model_dump() for item in payload.items]
    montant_ht, montant_ttc = _compute_totals(items_data)

    invoice = Invoice(
        numero=_generate_invoice_number(db),
        client_id=payload.client_id,
        date_emission=date.today(),
        date_echeance=payload.date_echeance,
        montant_ht=montant_ht,
        montant_ttc=montant_ttc,
        cree_par_id=current_user.id,
    )
    db.add(invoice)
    db.flush()  # to get invoice.id before committing

    for item in items_data:
        db.add(InvoiceItem(invoice_id=invoice.id, **item))

    db.commit()
    db.refresh(invoice)
    # TODO: generate PDF (WeasyPrint) + send email to client
    return invoice


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).get(invoice_id)
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
    invoice = db.query(Invoice).filter(Invoice.numero == invoice_number).first()
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
