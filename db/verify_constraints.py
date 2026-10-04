"""Re-run the audit's constraint probe: attempt invalid writes, expect rejection.

    python db/verify_constraints.py

Every statement runs inside a transaction that is always rolled back, so the
database is never modified. This mirrors the method the database audit used
(AUDIT-DB-014), where 30 invalid writes were attempted and 26 were accepted
because the schema held no CHECK constraints at all.

Connects as the OWNER role deliberately. Under the application role a
row-level security policy could reject a row, which would look like a working
constraint here and hide a missing one.
"""

import sys
from pathlib import Path

# Running "python db/<script>.py" puts db/ on sys.path, not the project root, so
# "import app" would fail. Adding the root here keeps the command in the
# docstring working as written, as well as "python -m db.<script>".
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text  # noqa: E402

from app.core.config import settings  # noqa: E402

# (label, SQL) - the database must REJECT each of these.
# A third element of True means the write is legitimately allowed.
PROBES = [
    ("invoice with a negative amount",
     "INSERT INTO invoices (numero, client_id, date_emission, date_echeance,"
     " montant_ht, montant_ttc, statut, cree_par_id)"
     " VALUES ('P-1', :cid, '2026-01-01', '2026-02-01', -500, -500, 'BROUILLON', :uid)"),
    ("invoice due before issue",
     "INSERT INTO invoices (numero, client_id, date_emission, date_echeance,"
     " montant_ht, montant_ttc, statut, cree_par_id)"
     " VALUES ('P-2', :cid, '2026-02-01', '2026-01-01', 100, 119, 'BROUILLON', :uid)"),
    ("invoice with TTC below HT",
     "INSERT INTO invoices (numero, client_id, date_emission, date_echeance,"
     " montant_ht, montant_ttc, statut, cree_par_id)"
     " VALUES ('P-3', :cid, '2026-01-01', '2026-02-01', 200, 100, 'BROUILLON', :uid)"),
    ("invoice with no author",
     "INSERT INTO invoices (numero, client_id, date_emission, date_echeance,"
     " montant_ht, montant_ttc, statut)"
     " VALUES ('P-4', :cid, '2026-01-01', '2026-02-01', 100, 119, 'BROUILLON')"),
    ("invoice with no amounts",
     "INSERT INTO invoices (numero, client_id, date_emission, date_echeance, statut, cree_par_id)"
     " VALUES ('P-5', :cid, '2026-01-01', '2026-02-01', 'BROUILLON', :uid)"),

    ("line with a negative quantity",
     "INSERT INTO invoice_items (invoice_id, designation, quantite, prix_unitaire, taux_tva)"
     " VALUES (:inv, 'x', -4, 10, 19)"),
    ("line with a negative unit price",
     "INSERT INTO invoice_items (invoice_id, designation, quantite, prix_unitaire, taux_tva)"
     " VALUES (:inv, 'x', 1, -10, 19)"),
    ("line with negative VAT",
     "INSERT INTO invoice_items (invoice_id, designation, quantite, prix_unitaire, taux_tva)"
     " VALUES (:inv, 'x', 1, 10, -19)"),
    # Within 0..100, so the integrity rule permits it. Whether 99.99% is a
    # plausible VAT rate is a business rule, not a database one.
    ("line with VAT at 99.99 percent",
     "INSERT INTO invoice_items (invoice_id, designation, quantite, prix_unitaire, taux_tva)"
     " VALUES (:inv, 'x', 1, 10, 99.99)",
     True),

    ("leave with no employee",
     "INSERT INTO leave_requests (date_debut, date_fin, statut)"
     " VALUES ('2026-01-01', '2026-01-02', 'EN_ATTENTE')"),
    ("leave ending before it starts",
     "INSERT INTO leave_requests (employee_id, date_debut, date_fin, statut)"
     " VALUES (:eid, '2026-02-10', '2026-02-01', 'EN_ATTENTE')"),
    # Enforced by a trigger rather than a CHECK since #60: employee_id is an
    # employees.id while valide_par_id is a users.id, so the two are different
    # key spaces and a row-local comparison is meaningless.
    ("leave approved by the requester",
     "INSERT INTO leave_requests (employee_id, date_debut, date_fin, statut, valide_par_id)"
     " VALUES (:eid, '2026-03-01', '2026-03-02', 'APPROUVE',"
     "         (SELECT user_id FROM employees WHERE id = :eid))"),
    ("leave approved with no validator",
     "INSERT INTO leave_requests (employee_id, date_debut, date_fin, statut)"
     " VALUES (:eid, '2026-04-01', '2026-04-02', 'APPROUVE')"),

    ("payslip with net above gross",
     "INSERT INTO payslips (employee_id, periode, montant_brut, montant_net)"
     " VALUES (:eid, '2026-01-01', 100, 200)"),
    ("payslip with negative amounts",
     "INSERT INTO payslips (employee_id, periode, montant_brut, montant_net)"
     " VALUES (:eid, '2026-01-01', -100, -50)"),
    ("payslip dated mid-month",
     "INSERT INTO payslips (employee_id, periode, montant_brut, montant_net)"
     " VALUES (:eid, '2026-01-15', 100, 80)"),
    ("second payslip for the same employee and month",
     "INSERT INTO payslips (employee_id, periode, montant_brut, montant_net)"
     " VALUES (:eid, '2026-05-01', 100, 80)"),

    ("user with role superadmin",
     "INSERT INTO users (id, email, role, \"hashedPassword\", \"isActive\")"
     " VALUES ('P-U1', 'p1@x.tn', 'superadmin', 'h', true)"),
    ("user with no role",
     "INSERT INTO users (id, email, \"hashedPassword\", \"isActive\")"
     " VALUES ('P-U2', 'p2@x.tn', 'h', true)"),
    ("user with no password hash",
     "INSERT INTO users (id, email, role, \"isActive\")"
     " VALUES ('P-U3', 'p3@x.tn', 'employee', true)"),
    ("email differing only by case",
     "INSERT INTO users (id, email, role, \"hashedPassword\", \"isActive\")"
     " VALUES ('P-U4', :upper_email, 'employee', 'h', true)"),

    ("client name differing only by case",
     "INSERT INTO clients (nom, email) VALUES ('PROBE CLIENT', 'c@x.tn')"),
]


def main():
    engine = create_engine(settings.SCHEMA_DATABASE_URL)
    failures = []
    accepted = rejected = 0

    with engine.connect() as conn:
        uid = conn.execute(text("SELECT id FROM users LIMIT 1")).scalar()
        email = conn.execute(text("SELECT email FROM users LIMIT 1")).scalar()
        if not uid:
            sys.exit("No users in the database; run seed_users.py first.")
        # Payslips and leave reference employees.id since #60, not users.id.
        eid = conn.execute(text("SELECT id FROM employees LIMIT 1")).scalar()
        if not eid:
            sys.exit("No employees in the database; create one first.")

        # The SELECTs above have already autobegun a transaction; everything
        # below runs inside it and is rolled back at the end, so the database
        # is never modified.
        # Fixtures live inside that same transaction and vanish with it.
        conn.execute(text(
            "INSERT INTO clients (id, nom, email, telephone, adresse)"
            " VALUES (99001, 'Probe Client', 'p@x.tn', '', '')"))
        conn.execute(text(
            "INSERT INTO invoices (id, numero, client_id, date_emission, date_echeance,"
            " montant_ht, montant_ttc, statut, cree_par_id)"
            " VALUES (99001, 'PROBE-1', 99001, '2026-01-01', '2026-02-01',"
            " 100, 119, 'BROUILLON', :uid)"), {"uid": uid})
        conn.execute(text(
            "INSERT INTO payslips (employee_id, periode, montant_brut, montant_net)"
            " VALUES (:eid, '2026-05-01', 100, 80)"), {"eid": eid})

        params = {"cid": 99001, "uid": uid, "eid": eid, "inv": 99001,
                  "upper_email": email.upper()}

        for probe in PROBES:
            label, sql = probe[0], probe[1]
            should_pass = probe[2] if len(probe) > 2 else False
            savepoint = conn.begin_nested()
            try:
                conn.execute(text(sql), params)
                savepoint.rollback()
                accepted += 1
                ok = should_pass
                print(f"  {'ok  ' if ok else 'FAIL'} accepted: {label}")
            except Exception:
                savepoint.rollback()
                rejected += 1
                ok = not should_pass
                print(f"  {'ok  ' if ok else 'FAIL'} rejected: {label}")
            if not ok:
                failures.append(label)

        conn.rollback()

    print()
    print(f"  {len(PROBES)} probes: {rejected} rejected, {accepted} accepted")
    if failures:
        print("\n  UNEXPECTED:")
        for f in failures:
            print(f"    - {f}")
        sys.exit(1)
    print("  Every invalid write was rejected by the database.")


if __name__ == "__main__":
    main()
