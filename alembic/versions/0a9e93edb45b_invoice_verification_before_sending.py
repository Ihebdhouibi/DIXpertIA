"""invoice verification before sending

Revision ID: 0a9e93edb45b
Revises: aa6d4397586b
Create Date: 2026-10-14 15:30:00.000000

#118: the accountant verifies an outgoing invoice before it is sent, and the
legal number moves from draft creation to that approval (decided on #118,
13 October).

    Draft --submit--> Submitted --approve--> Approved --send--> Sent
                          |
                          +--reject (comment)--> Rejected --edit, submit--> Submitted

WHY THE NUMBER MOVES. Allocating FA-YYYY-NNNN when a draft was created meant
every abandoned or rejected draft held a legal number that then had to be
justified, and the series must never have a gap. The number is now given at
approval, in the same transaction, together with the issue date, so it keeps
following issue-date order (#39). A draft has no number; it is shown as BR- and
its internal id. numbering.py had named this move as the answer if draft-time
allocation ever became a problem.

SCHEMA
- invoices.numero becomes nullable. UNIQUE allows several NULLs, so drafts
  coexist. A CHECK keeps the invariant in one direction: an outgoing invoice
  that is approved, sent or paid has a number. A draft cancelled before
  approval (#126) never gets one - that is how an abandoned draft leaves no
  gap. Existing drafts that already hold a number (local development data
  only - nothing is deployed) keep it.
- invoices.review_status: NOT_SUBMITTED, SUBMITTED, APPROVED, REJECTED. A third
  axis next to statut (commercial) and processing_status (books), as #41 kept
  those apart.
- invoice_reviews: every submission and decision, with its author, time and
  comment. Append-only, row-level secured like invoices.

RULES, held by triggers so a direct SQL write is refused too (outgoing only;
supplier bills are recorded as received and are not reviewed):
1. A legal number is given only to an approved invoice, and never changes once
   given. The gapless check (invoice_number_is_sequential) used to run on
   INSERT only; it now runs whenever a number is set, which is an UPDATE at
   approval.
2. review_status moves only along the arrows above, and only while the invoice
   is a draft. Approved is final.
3. An invoice leaves draft (sent, paid) only once approved. Cancelling a draft
   is #126's business and stays possible.
4. Bookkeeping starts at sending: processing_status cannot move while an
   outgoing invoice is still a draft. Invoices that already moved keep their
   state; the rule applies to new transitions.
5. The content (due date, totals, lines) can change only while the draft is not
   under review: NOT_SUBMITTED or REJECTED. Extends #125's two triggers.
6. A decision is never taken by the invoice's creator, and a rejection carries
   a comment.
"""
from alembic import op
import sqlalchemy as sa

revision = '0a9e93edb45b'
down_revision = 'aa6d4397586b'
branch_labels = None
depends_on = None

ROLE = "nullif(current_setting('app.user_role', true), '')"

REVIEW_STATUS = sa.Enum('NOT_SUBMITTED', 'SUBMITTED', 'APPROVED', 'REJECTED',
                        name='invoicereviewstatus')
REVIEW_ACTION = sa.Enum('SUBMITTED', 'APPROVED', 'REJECTED', name='invoicereviewaction')

# Rule 1, gapless half. The same check as before (#38, #40), now also run when a
# number is set by an UPDATE, with the NULL case handled explicitly rather than
# by NULL comparisons happening to come out false.
SEQUENTIAL = """
CREATE OR REPLACE FUNCTION trg_invoice_number_is_sequential() RETURNS trigger AS $BODY$
DECLARE
    series      text;
    series_year text;
    allocated   integer;
    highest     integer;
BEGIN
    IF NEW.numero IS NULL OR NEW.numero !~ '^(FA|FF)-[0-9]{4}-[0-9]+$' THEN
        RETURN NEW;
    END IF;
    IF TG_OP = 'UPDATE' AND NEW.numero IS NOT DISTINCT FROM OLD.numero THEN
        RETURN NEW;
    END IF;

    series      := substring(NEW.numero from 1 for 2);
    series_year := substring(NEW.numero from 4 for 4);
    allocated   := substring(NEW.numero from 9)::integer;

    SELECT coalesce(max(substring(numero from 9)::integer), 0) INTO highest
    FROM invoices
    WHERE numero ~ ('^' || series || '-' || series_year || '-[0-9]+$');

    IF allocated <> highest + 1 THEN
        RAISE EXCEPTION
            'invoice number % breaks the % series: % was expected',
            NEW.numero, series,
            series || '-' || series_year || '-' || lpad((highest + 1)::text, 4, '0');
    END IF;
    RETURN NEW;
END;
$BODY$ LANGUAGE plpgsql;
"""

# The body from 60fef7016faf, restored on downgrade.
SEQUENTIAL_BEFORE = """
CREATE OR REPLACE FUNCTION trg_invoice_number_is_sequential() RETURNS trigger AS $BODY$
DECLARE
    series      text;
    series_year text;
    allocated   integer;
    highest     integer;
BEGIN
    IF NEW.numero !~ '^(FA|FF)-[0-9]{4}-[0-9]+$' THEN
        RETURN NEW;
    END IF;

    series      := substring(NEW.numero from 1 for 2);
    series_year := substring(NEW.numero from 4 for 4);
    allocated   := substring(NEW.numero from 9)::integer;

    SELECT coalesce(max(substring(numero from 9)::integer), 0) INTO highest
    FROM invoices
    WHERE numero ~ ('^' || series || '-' || series_year || '-[0-9]+$');

    IF allocated <> highest + 1 THEN
        RAISE EXCEPTION
            'invoice number % breaks the % series: % was expected',
            NEW.numero, series,
            series || '-' || series_year || '-' || lpad((highest + 1)::text, 4, '0');
    END IF;
    RETURN NEW;
END;
$BODY$ LANGUAGE plpgsql;
"""

# Rules 1 (number only at approval, never changed), 2, 3 and 4.
REVIEW_RULES = """
CREATE OR REPLACE FUNCTION trg_invoice_review_rules() RETURNS trigger AS $$
BEGIN
    IF NEW.direction <> 'OUTGOING' THEN
        RETURN NEW;
    END IF;

    -- 1. A number, once given, is final; and it is given only on approval.
    IF OLD.numero IS NOT NULL AND NEW.numero IS DISTINCT FROM OLD.numero THEN
        RAISE EXCEPTION 'invoice % already has its legal number; it cannot change', OLD.numero;
    END IF;
    IF OLD.numero IS NULL AND NEW.numero IS NOT NULL AND NEW.review_status <> 'APPROVED' THEN
        RAISE EXCEPTION 'draft % gets its legal number only when the accountant approves it', OLD.id;
    END IF;

    -- 2. Review moves along the flow, only while the invoice is a draft.
    IF NEW.review_status IS DISTINCT FROM OLD.review_status THEN
        IF OLD.statut <> 'BROUILLON' THEN
            RAISE EXCEPTION 'invoice % is no longer a draft; its review is closed',
                coalesce(OLD.numero, 'BR-' || lpad(OLD.id::text, 4, '0'));
        END IF;
        IF NOT (
               (OLD.review_status IN ('NOT_SUBMITTED', 'REJECTED') AND NEW.review_status = 'SUBMITTED')
            OR (OLD.review_status = 'SUBMITTED' AND NEW.review_status IN ('APPROVED', 'REJECTED'))
        ) THEN
            RAISE EXCEPTION 'invoice % cannot go from % to % in review',
                coalesce(OLD.numero, 'BR-' || lpad(OLD.id::text, 4, '0')),
                OLD.review_status, NEW.review_status;
        END IF;
    END IF;

    -- 3. Leaving draft (other than cancelling it, #126) needs an approval.
    IF OLD.statut = 'BROUILLON' AND NEW.statut NOT IN ('BROUILLON', 'ANNULEE')
       AND NEW.review_status <> 'APPROVED' THEN
        RAISE EXCEPTION 'invoice % cannot be sent before the accountant approves it',
            coalesce(OLD.numero, 'BR-' || lpad(OLD.id::text, 4, '0'));
    END IF;

    -- 4. The books start when the invoice is sent.
    IF NEW.processing_status IS DISTINCT FROM OLD.processing_status AND NEW.statut = 'BROUILLON' THEN
        RAISE EXCEPTION 'invoice % is still a draft; bookkeeping starts when it is sent',
            coalesce(OLD.numero, 'BR-' || lpad(OLD.id::text, 4, '0'));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

# Rule 5 on the invoice row: #125's function, now also closed during review.
DRAFT_IS_EDITABLE = """
CREATE OR REPLACE FUNCTION trg_invoice_draft_is_editable() RETURNS trigger AS $$
BEGIN
    IF OLD.direction = 'OUTGOING'
       AND (OLD.statut <> 'BROUILLON' OR OLD.review_status IN ('SUBMITTED', 'APPROVED'))
       AND (   NEW.date_echeance IS DISTINCT FROM OLD.date_echeance
            OR NEW.montant_ht IS DISTINCT FROM OLD.montant_ht
            OR NEW.montant_ttc IS DISTINCT FROM OLD.montant_ttc) THEN
        RAISE EXCEPTION
            'invoice % is under review or no longer a draft and cannot be edited',
            coalesce(OLD.numero, 'BR-' || lpad(OLD.id::text, 4, '0'));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

DRAFT_IS_EDITABLE_BEFORE = """
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

# Rule 5 on the lines: #125's function, now also closed during review.
LINES_FOLLOW = """
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

    SELECT id, numero, direction, statut, processing_status, review_status INTO parent
    FROM invoices WHERE id = parent_id;

    IF TG_OP = 'UPDATE' AND OLD.invoice_id IS DISTINCT FROM NEW.invoice_id THEN
        PERFORM 1 FROM invoices
        WHERE id = OLD.invoice_id
          AND (processing_status = 'ARCHIVED'
               OR (direction = 'OUTGOING'
                   AND (statut <> 'BROUILLON' OR review_status IN ('SUBMITTED', 'APPROVED'))));
        IF FOUND THEN
            RAISE EXCEPTION 'a line cannot be moved out of an invoice that is under review or no longer a draft';
        END IF;
    END IF;

    IF parent.processing_status = 'ARCHIVED' THEN
        RAISE EXCEPTION
            'invoice % is archived and its lines are read-only; correct it with '
            'a new document in the open month', parent.numero;
    END IF;
    IF parent.direction = 'OUTGOING'
       AND (parent.statut <> 'BROUILLON' OR parent.review_status IN ('SUBMITTED', 'APPROVED')) THEN
        RAISE EXCEPTION
            'invoice % is under review or no longer a draft; its lines cannot be changed',
            coalesce(parent.numero, 'BR-' || lpad(parent.id::text, 4, '0'));
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

LINES_FOLLOW_BEFORE = """
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

# Rule 6, and the history is append-only.
REVIEW_HISTORY = """
CREATE OR REPLACE FUNCTION trg_invoice_review_is_valid() RETURNS trigger AS $$
DECLARE
    creator text;
BEGIN
    IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'the review history is append-only';
    END IF;
    IF NEW.action IN ('APPROVED', 'REJECTED') THEN
        SELECT cree_par_id INTO creator FROM invoices WHERE id = NEW.invoice_id;
        IF creator = NEW.actor_id THEN
            RAISE EXCEPTION 'an invoice is never approved or rejected by the person who created it';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade():
    # --- invoices: review state, a number only once approved -----------------
    REVIEW_STATUS.create(op.get_bind(), checkfirst=True)
    op.add_column('invoices', sa.Column('review_status', REVIEW_STATUS,
                                        server_default='NOT_SUBMITTED', nullable=False))
    # The "awaiting verification" queue is the accountant's first view.
    op.create_index('ix_invoices_review_status', 'invoices', ['review_status', 'date_emission'])
    op.alter_column('invoices', 'numero', existing_type=sa.String(length=30), nullable=True)
    op.create_check_constraint(
        'ck_invoices_numbered_once_approved', 'invoices',
        "direction <> 'OUTGOING' OR numero IS NOT NULL "
        "OR (statut IN ('BROUILLON', 'ANNULEE') AND review_status <> 'APPROVED')",
    )

    op.execute(SEQUENTIAL)
    op.execute("DROP TRIGGER invoice_number_is_sequential ON invoices")
    op.execute("""
        CREATE TRIGGER invoice_number_is_sequential
        BEFORE INSERT OR UPDATE OF numero ON invoices
        FOR EACH ROW EXECUTE FUNCTION trg_invoice_number_is_sequential()
    """)
    op.execute(REVIEW_RULES)
    op.execute("""
        CREATE TRIGGER invoice_review_rules
        BEFORE UPDATE ON invoices
        FOR EACH ROW EXECUTE FUNCTION trg_invoice_review_rules()
    """)
    op.execute(DRAFT_IS_EDITABLE)
    op.execute(LINES_FOLLOW)

    # --- invoice_reviews: who submitted or decided, when, and why ------------
    # create_table creates the invoicereviewaction type itself.
    op.create_table(
        'invoice_reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('actor_id', sa.String(), nullable=False),
        sa.Column('action', REVIEW_ACTION, nullable=False),
        sa.Column('comment', sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("action <> 'REJECTED' OR length(btrim(comment)) > 0",
                           name='ck_invoice_reviews_rejection_has_comment'),
    )
    op.create_index('ix_invoice_reviews_invoice_id', 'invoice_reviews', ['invoice_id', 'created_at'])
    op.create_index('ix_invoice_reviews_actor_id', 'invoice_reviews', ['actor_id'])
    op.execute(REVIEW_HISTORY)
    op.execute("""
        CREATE TRIGGER invoice_review_is_valid
        BEFORE INSERT OR UPDATE OR DELETE ON invoice_reviews
        FOR EACH ROW EXECUTE FUNCTION trg_invoice_review_is_valid()
    """)

    # Row-level security, the same shape as invoices (#43).
    op.execute("ALTER TABLE invoice_reviews ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE invoice_reviews FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY invoice_reviews_owner_all ON invoice_reviews
        FOR ALL TO dixpertia_owner USING (true) WITH CHECK (true)
    """)
    op.execute(f"""
        CREATE POLICY invoice_reviews_billing ON invoice_reviews
        FOR ALL TO dixpertia_app
        USING ({ROLE} IN ('admin', 'accountant'))
        WITH CHECK ({ROLE} IN ('admin', 'accountant'))
    """)


def downgrade():
    op.execute("DROP POLICY IF EXISTS invoice_reviews_billing ON invoice_reviews")
    op.execute("DROP POLICY IF EXISTS invoice_reviews_owner_all ON invoice_reviews")
    op.execute("DROP TRIGGER IF EXISTS invoice_review_is_valid ON invoice_reviews")
    op.execute("DROP FUNCTION IF EXISTS trg_invoice_review_is_valid()")
    op.drop_index('ix_invoice_reviews_actor_id', table_name='invoice_reviews')
    op.drop_index('ix_invoice_reviews_invoice_id', table_name='invoice_reviews')
    op.drop_table('invoice_reviews')
    REVIEW_ACTION.drop(op.get_bind(), checkfirst=True)

    op.execute(LINES_FOLLOW_BEFORE)
    op.execute(DRAFT_IS_EDITABLE_BEFORE)
    op.execute("DROP TRIGGER IF EXISTS invoice_review_rules ON invoices")
    op.execute("DROP FUNCTION IF EXISTS trg_invoice_review_rules()")
    op.execute("DROP TRIGGER invoice_number_is_sequential ON invoices")
    op.execute(SEQUENTIAL_BEFORE)
    op.execute("""
        CREATE TRIGGER invoice_number_is_sequential
        BEFORE INSERT ON invoices
        FOR EACH ROW EXECUTE FUNCTION trg_invoice_number_is_sequential()
    """)
    op.drop_constraint('ck_invoices_numbered_once_approved', 'invoices', type_='check')
    # Drafts created since the upgrade have no number; the old schema cannot
    # hold them. Local development data only (#118): refuse rather than invent.
    op.alter_column('invoices', 'numero', existing_type=sa.String(length=30), nullable=False)
    op.drop_index('ix_invoices_review_status', table_name='invoices')
    op.drop_column('invoices', 'review_status')
    REVIEW_STATUS.drop(op.get_bind(), checkfirst=True)
