from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.invoicing import Client, Invoice, InvoiceItem
from app.models.user import User
from app.schemas.invoicing import ClientCreate, ClientOut, InvoiceCreate, InvoiceOut

router = APIRouter(dependencies=[Depends(require_roles("rh", "admin"))])


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
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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
    db.flush()  # pour obtenir invoice.id avant le commit

    for item in items_data:
        db.add(InvoiceItem(invoice_id=invoice.id, **item))

    db.commit()
    db.refresh(invoice)
    # TODO: génération PDF (WeasyPrint) + envoi par e-mail au client
    return invoice


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).get(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture introuvable")
    return invoice
