import React, { useEffect, useState } from 'react';
import type { Invoice } from '../types';
import Button from './ui/Button';
import Dialog from './ui/Dialog';
import { Field, FormAlert, Input, Textarea } from './ui/Field';
import { useT } from '../i18n';

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
  const t = useT();
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
      setError(t('invoices.pay.required'));
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onPay(invoice, paidOn);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('invoices.pay.failed'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog
      open={invoice !== null}
      onClose={() => { if (!saving) onClose(); }}
      title={t('invoices.pay.title', { ref: invoice?.reference ?? '' })}
      description={t('invoices.pay.description')}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            {t('invoices.cancel')}
          </Button>
          <Button type="submit" form="pay-invoice-form" loading={saving}>
            {t('invoices.markPaid')}
          </Button>
        </>
      }
    >
      <form id="pay-invoice-form" onSubmit={submit} className="flex flex-col gap-4" noValidate>
        {error && <FormAlert>{error}</FormAlert>}
        <Field label={t('invoices.pay.date')} hint={invoice?.dateIssuedIso ? t('invoices.pay.dateHint') : undefined}>
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
  const t = useT();
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
      setError(t('invoices.cancel.required'));
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onCancelInvoice(invoice, reason.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : t('invoices.cancel.failed'));
    } finally {
      setSaving(false);
    }
  };

  const numbered = Boolean(invoice?.numero);
  return (
    <Dialog
      open={invoice !== null}
      onClose={() => { if (!saving) onClose(); }}
      title={t('invoices.cancel.title', { ref: invoice?.reference ?? '' })}
      description={numbered
        ? t('invoices.cancel.numbered')
        : t('invoices.cancel.draft')}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            {t('invoices.cancel.keep')}
          </Button>
          <Button variant="danger" type="submit" form="cancel-invoice-form" loading={saving}>
            {t('invoices.cancelInvoice')}
          </Button>
        </>
      }
    >
      <form id="cancel-invoice-form" onSubmit={submit} className="flex flex-col gap-4" noValidate>
        {error && <FormAlert>{error}</FormAlert>}
        <Field label={t('invoices.cancel.reason')}>
          {({ id }) => (
            <Textarea
              id={id}
              rows={3}
              required
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={t('invoices.cancel.placeholder')}
            />
          )}
        </Field>
      </form>
    </Dialog>
  );
}
