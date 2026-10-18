"""Report the query plan for each access path the application actually uses.

    python db/measure_indexes.py            # plans for every path
    python db/measure_indexes.py --verbose  # full EXPLAIN output as well

Run db/seed_perf_data.py first: on empty tables PostgreSQL scans sequentially
whatever indexes exist, because reading nothing is cheaper than consulting an
index, so an empty database cannot tell a useful index from a useless one.

Every statement runs inside a transaction that is rolled back, so this never
changes data.

Connects as the OWNER role. Row-level security adds further quals to these same
WHERE clauses rather than replacing them, so it can only make an index more
attractive; the scan choice shown here is the conservative case.
"""

import argparse
import re
import sys
from pathlib import Path

# Running "python db/<script>.py" puts db/ on sys.path, not the project root, so
# "import app" would fail. Adding the root here keeps the command in the
# docstring working as written, as well as "python -m db.<script>".
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text  # noqa: E402

from app.core.config import settings  # noqa: E402

# (label, sql) -- each is a query main.py issues, or the shape it issues.
PATHS = [
    ("payslips for one employee",
     "SELECT * FROM payslips WHERE employee_id = :eid ORDER BY periode DESC"),
    ("leave requests for one employee",
     "SELECT * FROM leave_requests WHERE employee_id = :eid ORDER BY date_debut DESC"),
    ("leave requests awaiting a decision",
     "SELECT * FROM leave_requests WHERE statut = 'EN_ATTENTE' ORDER BY date_debut"),
    ("invoice lines for one invoice",
     "SELECT * FROM invoice_items WHERE invoice_id = :inv"),
    ("invoices for one client",
     "SELECT * FROM invoices WHERE client_id = :cid ORDER BY date_emission DESC"),
    ("invoices for one month (accountant close)",
     "SELECT * FROM invoices WHERE date_emission >= :mstart AND date_emission < :mend "
     "ORDER BY date_emission"),
    ("invoice list, newest first (first page)",
     "SELECT * FROM invoices ORDER BY date_emission DESC, id DESC LIMIT 25"),
    ("invoices in one status",
     "SELECT * FROM invoices WHERE statut = 'ENVOYEE' ORDER BY date_emission DESC"),
    ("invoices awaiting the accountant (processing status)",
     "SELECT * FROM invoices WHERE processing_status = 'PENDING' "
     "ORDER BY date_emission DESC"),
    ("employee record for the signed-in user (RLS hot path)",
     "SELECT * FROM employees WHERE user_id = :uid"),
    ("login by e-mail",
     "SELECT * FROM users WHERE email = :email"),
    ("invoice list with its lines (the 1+N query, joined)",
     "SELECT i.*, it.* FROM invoices i LEFT JOIN invoice_items it ON it.invoice_id = i.id "
     "WHERE i.id IN (SELECT id FROM invoices ORDER BY date_emission DESC LIMIT 25)"),
]


def params(conn):
    """Pick real values, so the planner sees selectivities it will see live."""
    return {
        "eid": conn.execute(text("SELECT id FROM employees ORDER BY id LIMIT 1")).scalar(),
        "inv": conn.execute(text("SELECT id FROM invoices ORDER BY id LIMIT 1")).scalar(),
        "cid": conn.execute(text("SELECT client_id FROM invoices LIMIT 1")).scalar(),
        "uid": conn.execute(text("SELECT user_id FROM employees LIMIT 1")).scalar(),
        "email": conn.execute(text("SELECT email FROM users LIMIT 1")).scalar(),
        "mstart": "2026-01-01",
        "mend": "2026-02-01",
    }


def scan_summary(plan):
    """Name the scans that decide the verdict, ignoring sorts and aggregates."""
    scans = re.findall(r"(Seq Scan on \w+|"
                       r"Index(?: Only)? Scan(?: Backward)? using \w+|"
                       r"Bitmap Heap Scan on \w+|Bitmap Index Scan on \w+)", plan)
    seen = list(dict.fromkeys(scans))
    return seen or ["(no scan node)"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true", help="print the full plans")
    args = parser.parse_args()

    engine = create_engine(settings.SCHEMA_DATABASE_URL)
    seq = 0
    with engine.connect() as conn:
        p = params(conn)
        if p["eid"] is None:
            raise SystemExit("No data. Run: python db/seed_perf_data.py")
        for label, sql in PATHS:
            used = {k: v for k, v in p.items() if f":{k}" in sql}
            rows = conn.execute(
                text(f"EXPLAIN (ANALYZE, BUFFERS) {sql}"), used).fetchall()
            plan = "\n".join(r[0] for r in rows)
            ms = re.search(r"Execution Time: ([\d.]+) ms", plan)
            scans = scan_summary(plan)
            flag = "SEQ " if any(s.startswith("Seq Scan") for s in scans) else "    "
            seq += 1 if flag.strip() else 0
            print(f"{flag}{label}")
            print(f"      {' + '.join(scans)}")
            print(f"      {ms.group(1) if ms else '?'} ms")
            if args.verbose:
                print("\n".join("        " + line for line in plan.splitlines()))
            print()
        conn.rollback()
    print(f"  {len(PATHS)} access paths, {seq} still falling back to a sequential scan")


if __name__ == "__main__":
    main()
