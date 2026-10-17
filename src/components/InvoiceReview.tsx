import React, { useEffect, useState } from 'react';
import { formatDateTime } from '../format';
import { useT, type MessageKey } from '../i18n';
import type { Invoice } from '../types';
import { ReviewBadge } from './StatusBadge';
import Button from './ui/Button';
import Dialog from './ui/Dialog';
import { Field, FormAlert, Textarea } from './ui/Field';

/**
 * The accountant's verification of an invoice before it is sent (#118): where
 * it stands, and every submission and decision with its comment.
 */

const ACTION_LABEL: Record<Invoice['reviews'][number]['action'], MessageKey> = {
  submitted: 'invoices.review.submitted',
  approved: 'invoices.review.approved',
  rejected: 'invoices.review.rejected',
};

const when = (iso: string) => (iso ? formatDateTime(iso, { year: false }) : '');

export function InvoiceReviewPanel({ invoice }: { invoice: Invoice }) {
  const t = useT();
  const lastRejection = [...invoice.reviews].reverse().find((r) => r.action === 'rejected');
  return (
    <section className="rounded-xl border border-outline-variant bg-surface-container-lowest p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-on-surface">{t('invoices.review.title')}</h3>
        <ReviewBadge status={invoice.reviewStatus} />
      </div>

      {/* What the admin has to correct, before anything else. */}
      {invoice.reviewStatus === 'Rejected' && lastRejection && (
        <div role="note" className="mb-4 rounded-lg border border-danger/25 bg-danger-container px-3 py-2.5 text-sm text-danger">
          <p className="font-semibold">{t('invoices.review.toCorrect', { actor: lastRejection.actor || t('invoices.review.theAccountant') })}</p>
          <p className="mt-1 whitespace-pre-line text-on-surface">{lastRejection.comment}</p>
        </div>
      )}

      {invoice.reviews.length === 0 ? (
        <p className="text-sm text-on-surface-variant">
          {invoice.numero
            ? t('invoices.review.numberedBefore')
            : t('invoices.review.notSubmitted')}
        </p>
      ) : (
        <ol className="flex flex-col gap-3 border-l border-outline-variant pl-4">
          {invoice.reviews.map((r, i) => (
            <li key={i} className="text-sm">
              <p className="font-semibold text-on-surface">{t(ACTION_LABEL[r.action])}</p>
              <p className="font-mono text-[11px] text-on-surface-variant">
                {when(r.at)}
                {r.actor ? ` · ${r.actor}` : ''}
              </p>
              {r.comment && <p className="mt-1 whitespace-pre-line text-on-surface-variant">{r.comment}</p>}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

interface RejectInvoiceDialogProps {
  invoice: Invoice | null;
  onClose: () => void;
  /** Sends the rejection; rejects with the server's message on a refusal. */
  onReject: (invoice: Invoice, comment: string) => Promise<void>;
}

/** The accountant sends an invoice back with what to correct; the comment is mandatory. */
export function RejectInvoiceDialog({ invoice, onClose, onReject }: RejectInvoiceDialogProps) {
  const t = useT();
  const [comment, setComment] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (invoice) {
      setComment('');
      setError(null);
    }
  }, [invoice]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!invoice) return;
    if (!comment.trim()) {
      setError(t('invoices.reject.required'));
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onReject(invoice, comment.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : t('invoices.reject.failed'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog
      open={invoice !== null}
      onClose={() => { if (!saving) onClose(); }}
      title={t('invoices.reject.title', { ref: invoice?.reference ?? '' })}
      description={t('invoices.reject.description')}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            {t('invoices.cancel')}
          </Button>
          <Button variant="danger" type="submit" form="reject-invoice-form" loading={saving}>
            {t('invoices.reject')}
          </Button>
        </>
      }
    >
      <form id="reject-invoice-form" onSubmit={submit} className="flex flex-col gap-4" noValidate>
        {error && <FormAlert>{error}</FormAlert>}
        <Field label={t('invoices.reject.field')}>
          {({ id }) => (
            <Textarea
              id={id}
              rows={4}
              required
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder={t('invoices.reject.placeholder')}
            />
          )}
        </Field>
      </form>
    </Dialog>
  );
}
