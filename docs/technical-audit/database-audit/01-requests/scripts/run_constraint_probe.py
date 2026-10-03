"""Prove which invalid rows the database ACCEPTS, without keeping any of them.

Usage (repository root):

    .venv/Scripts/python.exe docs/technical-audit/database-audit/01-requests/scripts/run_constraint_probe.py

Why
---
The tables are empty, so "no anomaly found" proves nothing. What matters is
whether the schema would *prevent* an anomaly. Each probe attempts to insert a
row that violates a business rule:

  * accepted  -> the database does not enforce the rule  (finding)
  * rejected  -> the database enforces it                 (control OK)

Safety
------
Every probe runs inside its own SAVEPOINT, all inside one outer transaction
that is ALWAYS rolled back at the end. Nothing is committed, ever. Rows are
also tagged AUDIT-PROBE so they would be recognisable if anything went wrong.

Also checks, in pure Python (no database), how SQLAlchemy binds the Enum
columns: the database stores member NAMES (BROUILLON), and insert_invoices.py
passes VALUES ("brouillon").
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.dialects import postgresql  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.models.invoicing import Invoice  # noqa: E402

OUT = ROOT / "docs/technical-audit/database-audit/11-evidence/data-integrity/constraint-probe.results.md"

# Fixture rows created first (inside the same rolled-back transaction).
SETUP = [
    "INSERT INTO users (id, email, role, \"hashedPassword\", \"isActive\") VALUES ('PRB-001', 'probe@audit.invalid', 'employee', 'x', true)",
    "INSERT INTO clients (id, nom) VALUES (-1, 'AUDIT-PROBE client')",
    "INSERT INTO invoices (id, numero, client_id, date_emission, date_echeance, montant_ht, montant_ttc, statut) "
    "VALUES (-1, 'AUDIT-PROBE-0', -1, DATE '2026-10-01', DATE '2026-10-31', 100, 119, 'BROUILLON')",
]

# (id, rule, rule source, SQL that violates the rule)
PROBES = [
    ("P-01", "Une facture a un montant positif", "pratique comptable",
     "INSERT INTO invoices (numero, client_id, date_emission, date_echeance, montant_ht, montant_ttc, statut) "
     "VALUES ('AUDIT-PROBE-1', -1, DATE '2026-10-01', DATE '2026-10-31', -500, -500, 'ENVOYEE')"),
    ("P-02", "L'échéance n'est pas antérieure à l'émission", "pratique comptable",
     "INSERT INTO invoices (numero, client_id, date_emission, date_echeance, montant_ht, montant_ttc, statut) "
     "VALUES ('AUDIT-PROBE-2', -1, DATE '2026-10-31', DATE '2020-01-01', 100, 119, 'ENVOYEE')"),
    ("P-03", "Le TTC n'est pas inférieur au HT", "pratique comptable",
     "INSERT INTO invoices (numero, client_id, date_emission, date_echeance, montant_ht, montant_ttc, statut) "
     "VALUES ('AUDIT-PROBE-3', -1, DATE '2026-10-01', DATE '2026-10-31', 1000, 1, 'ENVOYEE')"),
    ("P-04", "Une facture a toujours un statut", "R-FAC-08",
     "INSERT INTO invoices (numero, client_id, date_emission, date_echeance, montant_ht, montant_ttc) "
     "VALUES ('AUDIT-PROBE-4', -1, DATE '2026-10-01', DATE '2026-10-31', 100, 119)"),
    ("P-05", "Une facture a toujours un montant", "pratique comptable",
     "INSERT INTO invoices (numero, client_id, date_emission, date_echeance, statut) "
     "VALUES ('AUDIT-PROBE-5', -1, DATE '2026-10-01', DATE '2026-10-31', 'ENVOYEE')"),
    ("P-06", "Une facture a toujours un auteur", "R-FAC-01, traçabilité",
     "INSERT INTO invoices (numero, client_id, date_emission, date_echeance, montant_ht, montant_ttc, statut, cree_par_id) "
     "VALUES ('AUDIT-PROBE-6', -1, DATE '2026-10-01', DATE '2026-10-31', 100, 119, 'ENVOYEE', NULL)"),
    ("P-07", "Les montants de l'en-tête correspondent aux lignes", "valeur dérivée",
     "INSERT INTO invoice_items (invoice_id, designation, quantite, prix_unitaire, taux_tva) "
     "VALUES (-1, 'AUDIT-PROBE', 3, 999, 19)"),
    ("P-08", "Une ligne a une quantité strictement positive", "pratique comptable",
     "INSERT INTO invoice_items (invoice_id, designation, quantite, prix_unitaire, taux_tva) VALUES (-1, 'AUDIT-PROBE', -4, 10, 19)"),
    ("P-09", "Le taux de TVA est compris entre 0 et 100", "fiscal",
     "INSERT INTO invoice_items (invoice_id, designation, quantite, prix_unitaire, taux_tva) VALUES (-1, 'AUDIT-PROBE', 1, 10, 99.99)"),
    ("P-10", "Le taux de TVA n'est pas négatif", "fiscal",
     "INSERT INTO invoice_items (invoice_id, designation, quantite, prix_unitaire, taux_tva) VALUES (-1, 'AUDIT-PROBE', 1, 10, -19)"),
    ("P-11", "Une ligne a un prix positif", "pratique comptable",
     "INSERT INTO invoice_items (invoice_id, designation, quantite, prix_unitaire, taux_tva) VALUES (-1, 'AUDIT-PROBE', 1, -10, 19)"),
    ("P-12", "Une demande de congé a un employé", "R-CNG-01",
     "INSERT INTO leave_requests (employee_id, date_debut, date_fin, statut) VALUES (NULL, DATE '2026-10-01', DATE '2026-10-02', 'EN_ATTENTE')"),
    ("P-13", "Un congé finit après avoir commencé", "bon sens",
     "INSERT INTO leave_requests (employee_id, date_debut, date_fin, statut) VALUES ('PRB-001', DATE '2026-10-10', DATE '2026-10-01', 'EN_ATTENTE')"),
    ("P-14", "Un employé ne valide pas sa propre demande", "R-CNG-03",
     "INSERT INTO leave_requests (employee_id, valide_par_id, date_debut, date_fin, statut) "
     "VALUES ('PRB-001', 'PRB-001', DATE '2026-10-01', DATE '2026-10-02', 'APPROUVE')"),
    ("P-15", "Une décision de congé est attribuée à un valideur", "R-CNG-02, traçabilité",
     "INSERT INTO leave_requests (employee_id, date_debut, date_fin, statut) VALUES ('PRB-001', DATE '2026-11-01', DATE '2026-11-02', 'APPROUVE')"),
    ("P-16", "Deux congés d'un même employé ne se chevauchent pas", "R-CNG-06 (à confirmer)",
     "INSERT INTO leave_requests (employee_id, date_debut, date_fin, statut) VALUES "
     "('PRB-001', DATE '2026-12-01', DATE '2026-12-10', 'EN_ATTENTE'), ('PRB-001', DATE '2026-12-05', DATE '2026-12-15', 'EN_ATTENTE')"),
    ("P-17", "Le salaire net ne dépasse pas le brut", "R-PAY-05",
     "INSERT INTO payslips (employee_id, periode, montant_brut, montant_net) VALUES ('PRB-001', DATE '2026-09-01', 1000, 5000)"),
    ("P-18", "Les montants de paie sont positifs", "R-PAY-05",
     "INSERT INTO payslips (employee_id, periode, montant_brut, montant_net) VALUES ('PRB-001', DATE '2026-08-01', -1000, -800)"),
    ("P-19", "Un seul bulletin par employé et par mois (contrôle attendu : rejet)", "uq_employee_periode",
     "INSERT INTO payslips (employee_id, periode, montant_brut, montant_net) VALUES "
     "('PRB-001', DATE '2026-07-01', 1000, 800), ('PRB-001', DATE '2026-07-01', 1000, 800)"),
    ("P-20", "Deux bulletins dans le même mois avec des jours différents", "uq_employee_periode porte sur une DATE, pas sur un mois",
     "INSERT INTO payslips (employee_id, periode, montant_brut, montant_net) VALUES "
     "('PRB-001', DATE '2026-06-01', 1000, 800), ('PRB-001', DATE '2026-06-15', 1000, 800)"),
    ("P-21", "Un rôle appartient à la liste admin / employee / accountant", "R-USR-04",
     "INSERT INTO users (id, email, role) VALUES ('PRB-002', 'probe2@audit.invalid', 'superadmin')"),
    ("P-22", "Un compte a un mot de passe et un rôle", "R-USR-04",
     "INSERT INTO users (id, email) VALUES ('PRB-003', 'probe3@audit.invalid')"),
    ("P-23", "Un e-mail = un seul compte, quelle que soit la casse", "R-USR-05",
     "INSERT INTO users (id, email, role, \"hashedPassword\") VALUES ('PRB-004', 'PROBE@audit.invalid', 'employee', 'x')"),
    ("P-24", "Un compte inséré sans valeur explicite est actif ou inactif, jamais indéterminé", "valeurs par défaut côté Python seulement",
     "INSERT INTO users (id, email, role, \"hashedPassword\") VALUES ('PRB-005', 'probe5@audit.invalid', 'employee', 'x') RETURNING \"isActive\" IS NULL AS is_active_null"),
    ("P-25", "Deux appareils n'ont pas le même numéro de série", "inventaire",
     "INSERT INTO devices (id, \"serialNumber\", price, status) VALUES ('PRB-D1', 'SN-AUDIT', 10, 'Available'), ('PRB-D2', 'SN-AUDIT', 10, 'Available')"),
    ("P-26", "Un appareil a un prix positif et un statut connu", "inventaire",
     "INSERT INTO devices (id, price, status) VALUES ('PRB-D3', -99.99, 'Volé')"),
    ("P-27", "Deux clients ne portent pas le même nom", "R-FAC-04 (filtre par client)",
     "INSERT INTO clients (nom) VALUES ('AUDIT-PROBE client'), ('audit-probe CLIENT')"),
    ("P-28", "Supprimer une facture en SQL direct (FK invoice_items sans ON DELETE)", "contrôle attendu : rejet",
     "DELETE FROM invoices WHERE id = -1"),
    ("P-29", "Supprimer un utilisateur qui a des congés (FK NO ACTION)", "contrôle attendu : rejet",
     "DELETE FROM users WHERE id = 'PRB-001'"),
    ("P-30", "Une facture référence un client existant (FK)", "contrôle attendu : rejet",
     "INSERT INTO invoices (numero, client_id, date_emission, date_echeance) VALUES ('AUDIT-PROBE-30', -999, DATE '2026-10-01', DATE '2026-10-31')"),
]

# Probes whose secure outcome is "rejected" are controls; for all others the
# secure outcome is also "rejected" — the column says what was actually observed.


def main() -> int:
    engine = create_engine(settings.DATABASE_URL)
    rows = []
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            for stmt in SETUP:
                conn.execute(text(stmt))
            for pid, rule, source, sql in PROBES:
                sp = conn.begin_nested()
                try:
                    res = conn.execute(text(sql))
                    extra = ""
                    if res.returns_rows:
                        extra = f" — {dict(res.mappings().first())}"
                    rows.append((pid, rule, source, "ACCEPTÉE", f"{res.rowcount} ligne(s) affectée(s){extra}"))
                    sp.commit()  # releases the savepoint only; the outer transaction is still open
                except Exception as exc:  # noqa: BLE001 - the rejection IS the result
                    sp.rollback()
                    msg = str(getattr(exc, "orig", exc)).splitlines()[0]
                    rows.append((pid, rule, source, "REJETÉE", msg))
        finally:
            trans.rollback()  # nothing from this script is ever kept

    with engine.connect() as conn:
        leftovers = conn.execute(text(
            "SELECT (SELECT count(*) FROM users WHERE id LIKE 'PRB-%') + "
            "(SELECT count(*) FROM invoices WHERE numero LIKE 'AUDIT-PROBE%') + "
            "(SELECT count(*) FROM clients WHERE nom ILIKE 'audit-probe%') + "
            "(SELECT count(*) FROM devices WHERE id LIKE 'PRB-%')")).scalar()

    # Enum binding check — pure Python, no database round-trip.
    col = Invoice.__table__.c.statut
    proc = col.type.bind_processor(postgresql.dialect())
    enum_checks = []
    for value in ("BROUILLON", "brouillon"):
        try:
            enum_checks.append((value, f"accepté, envoyé à la base comme {proc(value)!r}"))
        except Exception as exc:  # noqa: BLE001
            enum_checks.append((value, f"REJETÉ par SQLAlchemy : {type(exc).__name__}: {str(exc).splitlines()[0]}"))

    lines = [
        "# Résultats — sondage des contraintes d'intégrité", "",
        f"- **Exécuté le :** {datetime.now().isoformat(timespec='seconds')}",
        "- **Script :** `01-requests/scripts/run_constraint_probe.py`",
        "- **Méthode :** chaque tentative dans un SAVEPOINT, le tout dans une transaction **toujours annulée**",
        f"- **Lignes résiduelles après rollback :** `{leftovers}` (attendu : 0)", "",
        "**Lecture :** une règle « ACCEPTÉE » n'est **pas** garantie par la base ; seule l'application",
        "pourrait l'appliquer, et la Phase 9 montre qu'elle ne le fait pas non plus.", "",
        "| Sonde | Règle métier | Source | Base | Détail |", "|---|---|---|---|---|",
    ]
    lines += [f"| {p} | {r} | {s} | **{v}** | {d.replace('|', '/')} |" for p, r, s, v, d in rows]
    accepted = sum(1 for r in rows if r[3] == "ACCEPTÉE")
    lines += ["", f"**{accepted} sondes acceptées sur {len(rows)}.**", "",
              "## Liaison des ENUM par SQLAlchemy (`invoices.statut`)", "",
              "La base stocke les **noms** des membres (Q-SCH-009 : `BROUILLON, ENVOYEE, …`).", "",
              "| Valeur passée par le code | Résultat |", "|---|---|"]
    lines += [f"| `{v}` | {r} |" for v, r in enum_checks]
    lines += ["", "`insert_invoices.py:110-119` passe la **valeur** (`\"brouillon\"`, `\"payee\"`…)."]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{accepted}/{len(rows)} acceptees, residus={leftovers} -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
