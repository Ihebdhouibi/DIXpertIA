"""index the access paths the application uses

Revision ID: 79239abcd291
Revises: f1f441a6bc13
Create Date: 2026-10-04 16:34:39.891233

Every index here was chosen by measurement, not by habit (#61). The procedure
is reproducible:

    python db/seed_perf_data.py --scale 10
    python db/measure_indexes.py

DROPPED -- eight "ix_<table>_id" indexes duplicating the primary key, plus
ix_employees_user_id duplicating the UNIQUE constraint on employees.user_id.
PostgreSQL creates a unique index for a primary key and for a UNIQUE
constraint, so each of these was a second copy of an existing index: pure write
and disk cost, never chosen by the planner over the original. Dropping
ix_employees_user_id was confirmed by removing it and re-planning the lookup,
which then used employees_user_id_key and was no slower.

KEPT -- ix_users_email, which looks redundant beside ux_users_email_ci but is
not: that one indexes lower(email) and cannot serve "WHERE email = ?". Removing
it turned login into a sequential scan.

CREATED -- five foreign keys had no index, and the invoice list had no usable
ordering. Measured at scale 10 (20k invoices, 60k lines):

    invoice_items(invoice_id)        2.540 ms -> 0.036 ms
    invoices(date_emission, id)      1.989 ms -> 0.052 ms
    invoices(client_id)              1.116 ms -> 0.109 ms
    invoices(cree_par_id)            1.724 ms -> 0.045 ms   (FK check, see below)
    leave_requests(employee_id)      0.278 ms -> 0.062 ms
    invoices(statut)                 1.753 ms -> 0.792 ms

The two indexes on cree_par_id and valide_par_id serve no SELECT the
application issues. They matter because both columns are ON DELETE RESTRICT:
deleting a user who owns no invoices makes PostgreSQL scan the whole child
table to prove absence, while holding locks.

NOTE for a future production deployment: CREATE INDEX takes a lock that blocks
writes to the table for its duration. That is irrelevant at today's volumes and
on a database with no users yet, but once this runs against live data these
should become CREATE INDEX CONCURRENTLY, which cannot run inside a transaction
and so needs its own migration with the transaction disabled.
"""
from alembic import op

revision = '79239abcd291'
down_revision = 'f1f441a6bc13'
branch_labels = None
depends_on = None

# (index name, table) -- duplicates of the primary key or of a UNIQUE constraint.
REDUNDANT = [
    ('ix_clients_id', 'clients'),
    ('ix_employees_id', 'employees'),
    ('ix_employees_user_id', 'employees'),
    ('ix_invoice_items_id', 'invoice_items'),
    ('ix_invoices_id', 'invoices'),
    ('ix_leave_requests_id', 'leave_requests'),
    ('ix_payslips_id', 'payslips'),
    ('ix_services_id', 'services'),
    ('ix_users_id', 'users'),
]

# (index name, table, columns)
WANTED = [
    ('ix_invoice_items_invoice_id', 'invoice_items', ['invoice_id']),
    ('ix_invoices_client_id', 'invoices', ['client_id']),
    ('ix_invoices_cree_par_id', 'invoices', ['cree_par_id']),
    # Ascending even though the list reads newest first: a btree scans backward
    # at the same cost, so one index serves both that and the ascending month
    # range the accountant's close uses.
    ('ix_invoices_date_emission', 'invoices', ['date_emission', 'id']),
    ('ix_invoices_statut', 'invoices', ['statut']),
    ('ix_leave_requests_employee_id', 'leave_requests', ['employee_id']),
    ('ix_leave_requests_valide_par_id', 'leave_requests', ['valide_par_id']),
]

# payslips.employee_id is deliberately absent: uq_employee_periode is
# (employee_id, periode), and a btree on a leading column already serves
# lookups by that column alone. A separate index would be a third copy.


def upgrade():
    for name, table in REDUNDANT:
        op.drop_index(name, table_name=table)
    for name, table, cols in WANTED:
        op.create_index(name, table, cols, unique=False)


def downgrade():
    for name, table, _ in reversed(WANTED):
        op.drop_index(name, table_name=table)
    for name, table in reversed(REDUNDANT):
        col = 'user_id' if name == 'ix_employees_user_id' else 'id'
        op.create_index(name, table, [col], unique=False)
