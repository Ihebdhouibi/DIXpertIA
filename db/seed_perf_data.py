"""Generate a realistic dataset so index decisions can be measured, not guessed.

    python db/seed_perf_data.py           # insert
    python db/seed_perf_data.py --clear   # remove everything it created

The audit could not measure anything: the tables were empty, so every plan was
a sequential scan over nothing and the planner's choices meant little. This
creates enough rows for PostgreSQL to prefer an index when one helps, which is
the only way to tell a useful index from a guess.

Volumes are sized for a small consultancy with a few years of history, not for
load testing. Everything respects the constraints added in #58, so a failure
here means a constraint is wrong, not the seeder.

Connects as the OWNER role: the application role is subject to row-level
security, which would filter the inserts.
"""

import argparse
import random
import sys
from datetime import date, timedelta
from pathlib import Path

# Running "python db/<script>.py" puts db/ on sys.path, not the project root, so
# "import app" would fail. Adding the root here keeps the command in the
# docstring working as written, as well as "python -m db.<script>".
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text  # noqa: E402

from app.core.config import settings  # noqa: E402

# Defaults describe a small consultancy with three years of history. At that
# size several tables are one or two pages, where a sequential scan is genuinely
# cheaper than an index and PostgreSQL rightly refuses one -- so --scale exists
# to grow the tables that carry foreign keys until the planner's choice becomes
# visible, and the index decision can be read off a plan instead of argued.
EMPLOYEE_COUNT = 50
MONTHS_OF_PAYROLL = 36
CLIENT_COUNT = 30
INVOICE_COUNT = 2000
LEAVE_PER_EMPLOYEE = 12

# Everything created here carries these markers, so --clear removes exactly
# what was seeded and nothing an actual person entered.
USER_PREFIX = "PERF-"
CLIENT_PREFIX = "PerfClient"
INVOICE_PREFIX = "PERF-"

JOB_TITLES = ["Engineer", "Senior Engineer", "Designer", "Analyst",
              "Project Manager", "Consultant"]
LEAVE_TYPES = ["PAYE", "MALADIE", "SANS_SOLDE"]
LEAVE_STATUSES = ["EN_ATTENTE", "APPROUVE", "REFUSE"]
INVOICE_STATUSES = ["BROUILLON", "ENVOYEE", "PAYEE", "EN_RETARD", "ANNULEE"]
# The accountant's axis (#41), independent of the commercial one above.
PROCESSING_STATUSES = ["PENDING", "PROCESSED", "COMPLETED", "ARCHIVED"]


def clear(conn):
    conn.execute(text(
        "DELETE FROM invoice_items WHERE invoice_id IN "
        "(SELECT id FROM invoices WHERE numero LIKE :p)"), {"p": f"{INVOICE_PREFIX}%"})
    # Two rules refuse these deletes in normal use: #41 protects archived
    # invoices, and #38 protects every invoice because its number belongs to a
    # gapless series. Both are correct and neither is meant to cover fixtures,
    # so this steps past them deliberately rather than working around them.
    for trigger in ("invoice_archived_is_final", "invoice_is_never_deleted"):
        conn.execute(text(f"ALTER TABLE invoices DISABLE TRIGGER {trigger}"))
    conn.execute(text("DELETE FROM invoices WHERE numero LIKE :p"), {"p": f"{INVOICE_PREFIX}%"})
    for trigger in ("invoice_archived_is_final", "invoice_is_never_deleted"):
        conn.execute(text(f"ALTER TABLE invoices ENABLE TRIGGER {trigger}"))
    conn.execute(text("DELETE FROM clients WHERE nom LIKE :p"), {"p": f"{CLIENT_PREFIX}%"})
    conn.execute(text(
        "DELETE FROM leave_requests WHERE employee_id IN "
        "(SELECT id FROM employees WHERE user_id LIKE :p)"), {"p": f"{USER_PREFIX}%"})
    conn.execute(text(
        "DELETE FROM payslips WHERE employee_id IN "
        "(SELECT id FROM employees WHERE user_id LIKE :p)"), {"p": f"{USER_PREFIX}%"})
    conn.execute(text("DELETE FROM employees WHERE user_id LIKE :p"), {"p": f"{USER_PREFIX}%"})
    conn.execute(text("DELETE FROM users WHERE id LIKE :p"), {"p": f"{USER_PREFIX}%"})


def seed(conn, rng, scale):
    today = date.today()
    employee_count = EMPLOYEE_COUNT * scale
    client_count = CLIENT_COUNT * scale
    invoice_count = INVOICE_COUNT * scale

    # --- users and employees ------------------------------------------------
    users = [(f"{USER_PREFIX}{i:05d}", f"perf{i:05d}@dixpertia.test") for i in range(employee_count)]
    conn.execute(
        text('INSERT INTO users (id, email, "firstName", "lastName", role, '
             '"hashedPassword", "isActive", "isVerified", "createdAt") '
             "VALUES (:id, :em, 'Perf', 'Fixture', 'employee', 'x', true, true, now())"),
        [{"id": u, "em": e} for u, e in users],
    )
    conn.execute(
        text("INSERT INTO employees (user_id, job_title, hired_on, annual_entitlement_days) "
             "VALUES (:u, :t, :h, 21)"),
        [{"u": u, "t": rng.choice(JOB_TITLES),
          "h": today - timedelta(days=rng.randint(200, 2500))} for u, _ in users],
    )
    employee_ids = [r[0] for r in conn.execute(
        text("SELECT id FROM employees WHERE user_id LIKE :p ORDER BY id"), {"p": f"{USER_PREFIX}%"})]
    admin_id = conn.execute(
        text("SELECT id FROM users WHERE role = 'admin' AND id NOT LIKE :p LIMIT 1"),
        {"p": f"{USER_PREFIX}%"}).scalar()
    if not admin_id:
        raise SystemExit("No non-seeded admin user found; run seed_users.py first.")

    # --- payslips: one per employee per month, periode pinned to the 1st ----
    # ck_payslip_period_is_month_start requires day 1, and uq_employee_periode
    # requires each month to appear once per employee -- so step by whole months
    # rather than by 31 days, which would skip and repeat around short months.
    payslips = []
    months_since_epoch = today.year * 12 + (today.month - 1)
    for eid in employee_ids:
        for m in range(MONTHS_OF_PAYROLL):
            y, mo = divmod(months_since_epoch - m, 12)
            gross = rng.randint(1800, 6000)
            payslips.append({"e": eid, "p": date(y, mo + 1, 1), "b": gross,
                             "n": round(gross * rng.uniform(0.72, 0.85), 2)})
    conn.execute(text("INSERT INTO payslips (employee_id, periode, montant_brut, montant_net) "
                      "VALUES (:e, :p, :b, :n)"), payslips)

    # --- leave requests -----------------------------------------------------
    leaves = []
    for eid in employee_ids:
        for _ in range(LEAVE_PER_EMPLOYEE):
            start = today - timedelta(days=rng.randint(0, 900))
            status = rng.choice(LEAVE_STATUSES)
            leaves.append({
                "e": eid, "s": start, "f": start + timedelta(days=rng.randint(0, 9)),
                "t": rng.choice(LEAVE_TYPES), "st": status,
                # ck_leave_decision_has_validator: a decided request names its
                # validator, and the trigger forbids validating your own.
                "v": None if status == "EN_ATTENTE" else admin_id,
            })
    conn.execute(text(
        "INSERT INTO leave_requests (employee_id, date_debut, date_fin, type_conge, statut, valide_par_id) "
        "VALUES (:e, :s, :f, CAST(:t AS leavetype), CAST(:st AS leavestatus), :v)"), leaves)

    # --- clients ------------------------------------------------------------
    # A real address, not an empty string: #86 showed the invoice PDF fails on a
    # client without one, and a fixture that dodges that hides the bug again.
    conn.execute(text("INSERT INTO clients (nom, email, telephone, adresse) "
                      "VALUES (:n, :e, :t, :a)"),
                 [{"n": f"{CLIENT_PREFIX} {i:03d}", "e": f"client{i:03d}@perf.test",
                   "t": f"+216 70 {i:03d} {i:03d}",
                   "a": f"{i + 1} rue de Carthage, 1000 Tunis"}
                  for i in range(client_count)])
    client_ids = [r[0] for r in conn.execute(
        text("SELECT id FROM clients WHERE nom LIKE :p"), {"p": f"{CLIENT_PREFIX}%"})]

    # --- invoices and their lines ------------------------------------------
    invoices, items = [], []
    for i in range(invoice_count):
        issued = today - timedelta(days=rng.randint(0, 1095))
        ht = round(rng.uniform(200, 15000), 2)
        invoices.append({
            "num": f"{INVOICE_PREFIX}{i:06d}", "c": rng.choice(client_ids),
            "de": issued, "dc": issued + timedelta(days=30),
            "ht": ht, "ttc": round(ht * 1.19, 2),
            "st": rng.choice(INVOICE_STATUSES), "by": admin_id,
            "ps": rng.choice(PROCESSING_STATUSES),
        })
    conn.execute(text(
        "INSERT INTO invoices (numero, client_id, date_emission, date_echeance, "
        "montant_ht, montant_ttc, statut, processing_status, cree_par_id) "
        "VALUES (:num, :c, :de, :dc, :ht, :ttc, CAST(:st AS invoicestatus), "
        "CAST(:ps AS invoiceprocessingstatus), :by)"), invoices)

    invoice_ids = [r[0] for r in conn.execute(
        text("SELECT id FROM invoices WHERE numero LIKE :p"), {"p": f"{INVOICE_PREFIX}%"})]
    for inv in invoice_ids:
        for _ in range(rng.randint(1, 5)):
            items.append({"i": inv, "d": "Consulting", "q": rng.randint(1, 20),
                          "p": round(rng.uniform(50, 900), 2), "t": 19})
    conn.execute(text(
        "INSERT INTO invoice_items (invoice_id, designation, quantite, prix_unitaire, taux_tva) "
        "VALUES (:i, :d, :q, :p, :t)"), items)

    return {"users": len(users), "payslips": len(payslips), "leave_requests": len(leaves),
            "clients": client_count, "invoices": len(invoices), "invoice_items": len(items)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clear", action="store_true", help="remove the seeded rows and exit")
    parser.add_argument("--seed", type=int, default=20261004, help="RNG seed, for repeatability")
    parser.add_argument("--scale", type=int, default=1,
                        help="multiply employee, client and invoice volumes")
    args = parser.parse_args()

    engine = create_engine(settings.SCHEMA_DATABASE_URL)
    with engine.begin() as conn:
        clear(conn)
        if args.clear:
            print("  seeded rows removed")
            return
        counts = seed(conn, random.Random(args.seed), args.scale)
        for name, n in counts.items():
            print(f"  {name:16} {n:>6}")
    # ANALYZE outside the transaction so the planner sees the new statistics.
    with engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT").execute(text("ANALYZE"))
    print("  ANALYZE done - planner statistics refreshed")


if __name__ == "__main__":
    main()
