import React, { useEffect, useState } from 'react';
import type { Invoice } from '../types';
import Button from './ui/Button';
import Dialog from './ui/Dialog';
import { Field, FormAlert, Input, Textarea } from './ui/Field';

/**
 * Marking an invoice paid, and cancelling one (#126). Each sends one request
 * and keeps the form open with the server's message if it is refused.
 */

const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

interface PayInvoiceDialogProps {
  invoice: Invoice | null;
  onClose: () => void;
  /** Records the payment; rejects with the server's message on a refusal. */
  onPay: (invoice: Invoice, paidOn: string) => Promise<void>;
}

/** Paid in full on a date: not in the future, not before the issue date. */
export function PayInvoiceDialog({ invoice, onClose, onPay }: PayInvoiceDialogProps) {
  const [paidOn, setPaidOn] = useState(today());
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (invoice) {
      setPaidOn(today());
      setError(null);
    }
  }, [invoice]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!invoice) return;
    if (!paidOn) {
      setError('Enter the date the payment arrived.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onPay(invoice, paidOn);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not record the payment.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog
      open={invoice !== null}
      onClose={() => { if (!saving) onClose(); }}
      title={`Mark ${invoice?.reference ?? ''} as paid`}
      description="Paid in full on the date below. This cannot be undone."
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button type="submit" form="pay-invoice-form" loading={saving}>
            Mark as paid
          </Button>
        </>
      }
    >
      <form id="pay-invoice-form" onSubmit={submit} className="flex flex-col gap-4" noValidate>
        {error && <FormAlert>{error}</FormAlert>}
        <Field label="Payment date" hint={invoice?.dateIssuedIso ? `Between the issue date and today.` : undefined}>
          {({ id, describedBy }) => (
            <Input
              id={id}
              aria-describedby={describedBy}
              type="date"
              required
              value={paidOn}
              min={invoice?.dateIssuedIso ?? undefined}
              max={today()}
              onChange={(e) => setPaidOn(e.target.value)}
            />
          )}
        </Field>
      </form>
    </Dialog>
  );
}

interface CancelInvoiceDialogProps {
  invoice: Invoice | null;
  onClose: () => void;
  /** Cancels the invoice; rejects with the server's message on a refusal. */
  onCancelInvoice: (invoice: Invoice, reason: string) => Promise<void>;
}

/** The admin cancels with a mandatory reason. A numbered invoice keeps its number. */
export function CancelInvoiceDialog({ invoice, onClose, onCancelInvoice }: CancelInvoiceDialogProps) {
  const [reason, setReason] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (invoice) {
      setReason('');
      setError(null);
    }
  }, [invoice]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!invoice) return;
    if (!reason.trim()) {
      setError('Say why the invoice is cancelled.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onCancelInvoice(invoice, reason.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not cancel the invoice.');
    } finally {
      setSaving(false);
    }
  };

  const numbered = Boolean(invoice?.numero);
  return (
    <Dialog
      open={invoice !== null}
      onClose={() => { if (!saving) onClose(); }}
      title={`Cancel ${invoice?.reference ?? ''}`}
      description={numbered
        ? 'It keeps its number in the series, marked cancelled. The accountants are told, to book a credit note. This cannot be undone.'
        : 'The draft has no legal number, so nothing is left in the series. This cannot be undone.'}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Keep it
          </Button>
          <Button variant="danger" type="submit" form="cancel-invoice-form" loading={saving}>
            Cancel invoice
          </Button>
        </>
      }
    >
      <form id="cancel-invoice-form" onSubmit={submit} className="flex flex-col gap-4" noValidate>
        {error && <FormAlert>{error}</FormAlert>}
        <Field label="Reason">
          {({ id }) => (
            <Textarea
              id={id}
              rows={3}
              required
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. The client withdrew the order."
            />
          )}
        </Field>
      </form>
    </Dialog>
  );
}
