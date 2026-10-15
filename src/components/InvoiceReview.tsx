import React, { useEffect, useState } from 'react';
import type { Invoice } from '../types';
import { ReviewBadge } from './StatusBadge';
import Button from './ui/Button';
import Dialog from './ui/Dialog';
import { Field, FormAlert, Textarea } from './ui/Field';

/**
 * The accountant's verification of an invoice before it is sent (#118): where
 * it stands, and every submission and decision with its comment.
 */

const ACTION_LABEL: Record<Invoice['reviews'][number]['action'], string> = {
  submitted: 'Submitted for verification',
  approved: 'Approved',
  rejected: 'Rejected',
};

const when = (iso: string) =>
  iso ? new Date(iso).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '';

export function InvoiceReviewPanel({ invoice }: { invoice: Invoice }) {
  const lastRejection = [...invoice.reviews].reverse().find((r) => r.action === 'rejected');
  return (
    <section className="rounded-xl border border-outline-variant bg-surface-container-lowest p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-on-surface">Verification</h3>
        <ReviewBadge status={invoice.reviewStatus} />
      </div>

      {/* What the admin has to correct, before anything else. */}
      {invoice.reviewStatus === 'Rejected' && lastRejection && (
        <div role="note" className="mb-4 rounded-lg border border-danger/25 bg-danger-container px-3 py-2.5 text-sm text-danger">
          <p className="font-semibold">To correct, from {lastRejection.actor || 'the accountant'}</p>
          <p className="mt-1 whitespace-pre-line text-on-surface">{lastRejection.comment}</p>
        </div>
      )}

      {invoice.reviews.length === 0 ? (
        <p className="text-sm text-on-surface-variant">
          {invoice.numero
            ? 'Numbered before verification existed.'
            : 'Not submitted yet. The legal number is assigned when the accountant approves it.'}
        </p>
      ) : (
        <ol className="flex flex-col gap-3 border-l border-outline-variant pl-4">
          {invoice.reviews.map((r, i) => (
            <li key={i} className="text-sm">
              <p className="font-semibold text-on-surface">{ACTION_LABEL[r.action]}</p>
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
      setError('Say what the admin should correct.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onReject(invoice, comment.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not reject the invoice.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog
      open={invoice !== null}
      onClose={() => { if (!saving) onClose(); }}
      title={`Reject ${invoice?.reference ?? ''}`}
      description="The admin sees this comment, corrects the draft and submits it again."
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button variant="danger" type="submit" form="reject-invoice-form" loading={saving}>
            Reject
          </Button>
        </>
      }
    >
      <form id="reject-invoice-form" onSubmit={submit} className="flex flex-col gap-4" noValidate>
        {error && <FormAlert>{error}</FormAlert>}
        <Field label="What should be corrected">
          {({ id }) => (
            <Textarea
              id={id}
              rows={4}
              required
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="e.g. Training is billed at 7% VAT, not 19%."
            />
          )}
        </Field>
      </form>
    </Dialog>
  );
}
