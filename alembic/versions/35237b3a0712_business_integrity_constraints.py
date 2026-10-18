"""business integrity constraints

Revision ID: 35237b3a0712
Revises: 90554ddf8b26
Create Date: 2026-10-03 19:01:27.161616

"""
from alembic import op
import sqlalchemy as sa


revision = '35237b3a0712'
down_revision = '90554ddf8b26'
branch_labels = None
depends_on = None


# One CHECK per single-row business rule. The audit ran 30 invalid writes and
# 26 were accepted, because the database held only primary keys, 6 foreign keys
# and 3 unique constraints - and zero CHECK constraints (AUDIT-DB-014).
#
# Two rules from the audit are deliberately absent, because neither is a
# single-row rule and neither can be a CHECK:
#   - overlapping leave requests for one employee: needs an EXCLUDE constraint
#     with btree_gist, or an application-level check
#   - invoice header totals matching the sum of its lines: needs a trigger, a
#     generated column, or recomputation at issue time
# Both are noted on the issue rather than bodged in here.

CONSTRAINTS = [
    # --- invoices --------------------------------------------------------
    ("invoices", "ck_invoices_amounts",
     "montant_ht >= 0 AND montant_ttc >= montant_ht"),
    ("invoices", "ck_invoices_dates",
     "date_echeance >= date_emission"),
    # --- invoice lines ---------------------------------------------------
    ("invoice_items", "ck_invoice_items_quantite", "quantite > 0"),
    ("invoice_items", "ck_invoice_items_prix", "prix_unitaire >= 0"),
    ("invoice_items", "ck_invoice_items_tva", "taux_tva >= 0 AND taux_tva <= 100"),
    # --- leave requests --------------------------------------------------
    ("leave_requests", "ck_leave_dates", "date_fin >= date_debut"),
    # An employee must not approve their own leave.
    ("leave_requests", "ck_leave_no_self_validation",
     "valide_par_id IS NULL OR valide_par_id <> employee_id"),
    # A decided request must name who decided it.
    ("leave_requests", "ck_leave_decision_has_validator",
     "statut = 'EN_ATTENTE' OR valide_par_id IS NOT NULL"),
    # --- payslips --------------------------------------------------------
    ("payslips", "ck_payslip_amounts",
     "montant_brut >= 0 AND montant_net >= 0 AND montant_net <= montant_brut"),
    # periode is a Date standing for a month. Pinning it to the 1st makes the
    # month canonical, which is what lets the unique index below mean "one
    # payslip per employee per month" rather than "per employee per day".
    ("payslips", "ck_payslip_period_is_month_start",
     "extract(day FROM periode) = 1"),
    # --- devices ---------------------------------------------------------
    ("devices", "ck_devices_price", "price >= 0"),
]

# Columns the application already treats as mandatory, where the database did
# not. Defaults were declared on the SQLAlchemy side only, so any write outside
# the ORM produced NULL.
NOT_NULL = [
    ("invoices", "montant_ht", None),
    ("invoices", "montant_ttc", None),
    ("invoices", "cree_par_id", None),
    ("leave_requests", "employee_id", None),
    ("leave_requests", "statut", "'EN_ATTENTE'"),
    ("users", "role", None),
    ("users", "hashedPassword", None),
    ("users", "isActive", "true"),
]


def upgrade() -> None:
    for table, column, default in NOT_NULL:
        if default:
            op.execute(f'ALTER TABLE {table} ALTER COLUMN "{column}" SET DEFAULT {default}')
        op.execute(f'ALTER TABLE {table} ALTER COLUMN "{column}" SET NOT NULL')

    for table, name, expr in CONSTRAINTS:
        op.execute(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expr})")

    # Roles are a closed set. The audit inserted 'superadmin' cleanly.
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT ck_users_role "
        "CHECK (role IN ('admin', 'employee', 'accountant'))"
    )

    # Email is an identity, so it must be unique case-insensitively:
    # PROBE@x and probe@x were both accepted. A functional unique index does
    # what UNIQUE(email) cannot.
    op.execute("CREATE UNIQUE INDEX ux_users_email_ci ON users (lower(email))")

    # No index needed for "one payslip per employee per month": the existing
    # uq_employee_periode constraint already covers (employee_id, periode), and
    # the day-1 CHECK above is what makes that mean a month rather than a day.

    # Serial numbers identify hardware. Partial, so several devices may still
    # have no serial recorded.
    op.execute(
        'CREATE UNIQUE INDEX ux_devices_serial ON devices ("serialNumber") '
        'WHERE "serialNumber" IS NOT NULL'
    )

    # Client names, case-insensitively, to stop "Acme Corp" and "ACME CORP"
    # becoming two customers.
    op.execute("CREATE UNIQUE INDEX ux_clients_nom_ci ON clients (lower(nom))")


def downgrade() -> None:
    for index in ("ux_clients_nom_ci", "ux_devices_serial", "ux_users_email_ci"):
        op.execute(f"DROP INDEX IF EXISTS {index}")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_role")
    for table, name, _ in CONSTRAINTS:
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}")
    for table, column, default in NOT_NULL:
        op.execute(f'ALTER TABLE {table} ALTER COLUMN "{column}" DROP NOT NULL')
        if default:
            op.execute(f'ALTER TABLE {table} ALTER COLUMN "{column}" DROP DEFAULT')
