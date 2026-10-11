"""only a draft invoice can be edited

Revision ID: 2a1cdf8dd27c
Revises: 60fef7016faf
Create Date: 2026-10-11 16:40:00.000000

#125 adds PATCH /api/invoices/{id} so the admin can correct an invoice - the
step that makes a rejection in the verification flow (#118) lead somewhere.
The rule is that only a DRAFT can be corrected: once an invoice has left, the
client holds a copy, and a mistake is put right with a new document, never by
rewriting the one they have. As with every other invoice rule, the database
enforces it, so a direct SQL write cannot get round it.

TWO TRIGGERS, because an invoice is two tables.

`invoice_draft_is_editable` on invoices: the due date and the totals of an
OUTGOING invoice change only while it is BROUILLON. `numero`, `date_emission`,
`client_id` and `direction` are not listed: the API never changes them, and the
numbering triggers (#38, #39) and the archived seal already guard the ones that
matter legally. `statut` is not frozen either - leaving draft is precisely a
change of `statut`, and late payment must stay recordable.

`invoice_lines_follow_their_invoice` on invoice_items closes a gap found while
reading the existing seals: invoice_archived_is_final freezes an archived
invoice's own columns but not its lines, so a direct write could change the
lines of an archived invoice while its totals stayed put - an invoice that no
longer adds up. Now:

- the lines of an ARCHIVED invoice never change, whatever its direction;
- the lines of an OUTGOING invoice change only while it is BROUILLON.

INCOMING bills are deliberately outside the draft rule. They are created
already ENVOYEE - the supplier sent them - and their lines are inserted right
after, so a draft-only rule would refuse every new supplier bill. Correcting a
recorded supplier bill is a separate question; until it is answered they keep
today's behaviour, apart from the archived seal above.

DELETE ON invoice_items FOR THE APPLICATION ROLE. Replacing a draft's lines
deletes the old ones, and dixpertia_app had no DELETE on any accounting table
(db/sql/001-roles-and-grants.sql, #43). It is granted on invoice_items only,
here for existing databases and in the grants script for new ones. What keeps
it safe is the second trigger above: a line of an issued or archived invoice
still cannot be deleted. `invoices` itself stays without DELETE. The grant is
skipped where the role does not exist (a database not provisioned with the
script).

TRUNCATE does not fire row triggers, so the test suite's cleanup between tests
is unaffected.
"""
from alembic import op

revision = '2a1cdf8dd27c'
down_revision = '60fef7016faf'
branch_labels = None
depends_on = None

DRAFT_IS_EDITABLE = """
CREATE OR REPLACE FUNCTION trg_invoice_draft_is_editable() RETURNS trigger AS $$
BEGIN
    IF OLD.direction = 'OUTGOING' AND OLD.statut <> 'BROUILLON' AND (
           NEW.date_echeance IS DISTINCT FROM OLD.date_echeance
        OR NEW.montant_ht IS DISTINCT FROM OLD.montant_ht
        OR NEW.montant_ttc IS DISTINCT FROM OLD.montant_ttc
    ) THEN
        RAISE EXCEPTION
            'invoice % is no longer a draft and cannot be edited; correct it '
            'with a new document', OLD.numero;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

LINES_FOLLOW_THEIR_INVOICE = """
CREATE OR REPLACE FUNCTION trg_invoice_lines_follow_their_invoice() RETURNS trigger AS $$
DECLARE
    parent_id integer;
    parent record;
BEGIN
    IF TG_OP = 'DELETE' THEN
        parent_id := OLD.invoice_id;
    ELSE
        parent_id := NEW.invoice_id;
    END IF;

    SELECT numero, direction, statut, processing_status INTO parent
    FROM invoices WHERE id = parent_id;

    -- A line moved to another invoice must also be allowed to leave its old one.
    IF TG_OP = 'UPDATE' AND OLD.invoice_id IS DISTINCT FROM NEW.invoice_id THEN
        PERFORM 1 FROM invoices
        WHERE id = OLD.invoice_id
          AND (processing_status = 'ARCHIVED'
               OR (direction = 'OUTGOING' AND statut <> 'BROUILLON'));
        IF FOUND THEN
            RAISE EXCEPTION
                'a line cannot be moved out of an invoice that is no longer a draft';
        END IF;
    END IF;

    IF parent.processing_status = 'ARCHIVED' THEN
        RAISE EXCEPTION
            'invoice % is archived and its lines are read-only; correct it with '
            'a new document in the open month', parent.numero;
    END IF;
    IF parent.direction = 'OUTGOING' AND parent.statut <> 'BROUILLON' THEN
        RAISE EXCEPTION
            'invoice % is no longer a draft and its lines cannot be changed; '
            'correct it with a new document', parent.numero;
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade():
    op.execute(DRAFT_IS_EDITABLE)
    op.execute("""
        CREATE TRIGGER invoice_draft_is_editable
        BEFORE UPDATE OF date_echeance, montant_ht, montant_ttc ON invoices
        FOR EACH ROW EXECUTE FUNCTION trg_invoice_draft_is_editable()
    """)
    op.execute(LINES_FOLLOW_THEIR_INVOICE)
    op.execute("""
        CREATE TRIGGER invoice_lines_follow_their_invoice
        BEFORE INSERT OR UPDATE OR DELETE ON invoice_items
        FOR EACH ROW EXECUTE FUNCTION trg_invoice_lines_follow_their_invoice()
    """)
    op.execute(GRANT_DELETE_ON_LINES)


GRANT_DELETE_ON_LINES = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dixpertia_app') THEN
        GRANT DELETE ON TABLE invoice_items TO dixpertia_app;
    END IF;
END
$$;
"""

REVOKE_DELETE_ON_LINES = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dixpertia_app') THEN
        REVOKE DELETE ON TABLE invoice_items FROM dixpertia_app;
    END IF;
END
$$;
"""


def downgrade():
    op.execute(REVOKE_DELETE_ON_LINES)
    op.execute("DROP TRIGGER IF EXISTS invoice_lines_follow_their_invoice ON invoice_items")
    op.execute("DROP FUNCTION IF EXISTS trg_invoice_lines_follow_their_invoice()")
    op.execute("DROP TRIGGER IF EXISTS invoice_draft_is_editable ON invoices")
    op.execute("DROP FUNCTION IF EXISTS trg_invoice_draft_is_editable()")
