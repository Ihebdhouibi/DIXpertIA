from app.core.database import SessionLocal
from app.models.invoicing import Invoice, Client, InvoiceItem
from datetime import datetime
from decimal import Decimal

db = SessionLocal()

# Create clients if not exist
clients_data = [
    {"nom": "Acme Corp", "email": "acme@example.com", "telephone": "123", "adresse": "123 Main St"},
    {"nom": "Global Tech", "email": "global@example.com", "telephone": "456", "adresse": "456 Tech Ave"},
    {"nom": "Stark Industries", "email": "stark@example.com", "telephone": "789", "adresse": "789 Industry Blvd"},
    {"nom": "Wayne Ent.", "email": "wayne@example.com", "telephone": "101", "adresse": "101 Gotham St"},
    {"nom": "Technodev", "email": "tech@example.com", "telephone": "202", "adresse": "202 Dev Lane"},
]

client_map = {}
for c in clients_data:
    existing = db.query(Client).filter(Client.nom == c["nom"]).first()
    if existing:
        client_map[c["nom"]] = existing
    else:
        new_client = Client(**c)
        db.add(new_client)
        db.commit()
        db.refresh(new_client)
        client_map[c["nom"]] = new_client

# Map frontend status to enum values
status_map = {
    "Draft": "brouillon",
    "Sent": "envoyee",
    "Paid": "payee",
    "Overdue": "en_retard",
}

invoices_data = [
    {
        "numero": "INV-2024-001",
        "client": "Acme Corp",
        "amount": 12450.00,
        "date_issued": "Oct 12, 2024",
        "due_date": "Nov 11, 2024",
        "status": "Sent",
        "items": [{"designation": "Consulting", "quantite": 1, "prix_unitaire": 12450.00, "taux_tva": 0}],
    },
    {
        "numero": "INV-2024-002",
        "client": "Global Tech",
        "amount": 8200.00,
        "date_issued": "Oct 15, 2024",
        "due_date": "Oct 25, 2024",
        "status": "Overdue",
        "items": [
            {"designation": "React Frontend", "quantite": 40, "prix_unitaire": 150.00, "taux_tva": 0},
            {"designation": "UX Design", "quantite": 10, "prix_unitaire": 220.00, "taux_tva": 0}
        ],
    },
    {
        "numero": "INV-2024-003",
        "client": "Stark Industries",
        "amount": 45000.00,
        "date_issued": "Oct 01, 2024",
        "due_date": "Oct 31, 2024",
        "status": "Paid",
        "items": [{"designation": "Infrastructure", "quantite": 1, "prix_unitaire": 45000.00, "taux_tva": 0}],
    },
    {
        "numero": "INV-2024-004",
        "client": "Wayne Ent.",
        "amount": 3500.00,
        "date_issued": "2024-10-15",
        "due_date": "2024-11-15",
        "status": "Draft",
        "items": [{"designation": "Security Audit", "quantite": 1, "prix_unitaire": 3500.00, "taux_tva": 0}],
    },
    {
        "numero": "INV-2024-005",
        "client": "Technodev",
        "amount": 1460.00,
        "date_issued": "2026-09-09",
        "due_date": "2026-09-09",
        "status": "Paid",
        "items": [{"designation": "Dev Support", "quantite": 1, "prix_unitaire": 1460.00, "taux_tva": 0}],
    }
]

def parse_date(date_str):
    if not date_str or date_str == "-":
        return None
    for fmt in ("%Y-%m-%d", "%b %d, %Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None

for inv in invoices_data:
    existing = db.query(Invoice).filter(Invoice.numero == inv["numero"]).first()
    if existing:
        print(f"SKIP: invoice {inv['numero']} already exists.")
        continue

    client = client_map.get(inv["client"])
    if not client:
        print(f"SKIP: client {inv['client']} not found.")
        continue

    # Map status to enum value
    statut_enum = status_map.get(inv["status"], "brouillon")

    invoice = Invoice(
        numero=inv["numero"],
        client_id=client.id,
        date_emission=parse_date(inv["date_issued"]),
        date_echeance=parse_date(inv["due_date"]),
        montant_ht=Decimal(str(inv["amount"])),
        montant_ttc=Decimal(str(inv["amount"])),
        statut=statut_enum,
        cree_par_id=None,   # omit
    )
    db.add(invoice)
    db.flush()

    for item in inv["items"]:
        db.add(InvoiceItem(
            invoice_id=invoice.id,
            designation=item["designation"],
            quantite=Decimal(str(item["quantite"])),
            prix_unitaire=Decimal(str(item["prix_unitaire"])),
            taux_tva=Decimal(str(item.get("taux_tva", 0)))
        ))

    db.commit()
    print(f"OK: inserted invoice {inv['numero']} with {len(inv['items'])} items.")

db.close()
print("Done: all invoices inserted.")
