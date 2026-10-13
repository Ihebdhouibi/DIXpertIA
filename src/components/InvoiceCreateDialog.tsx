import React, { useEffect, useState } from 'react';
import * as api from '../api';
import type { Client, Invoice } from '../types';
import Button from './ui/Button';
import Dialog from './ui/Dialog';
import { Field, FormAlert, Input, Select } from './ui/Field';
import {
  InvoiceLinesEditor,
  InvoiceLinesTotals,
  LineDraft,
  blankLine,
  problemWithLines,
  toLineInputs,
} from './InvoiceLinesEditor';

/**
 * A fresh key per opening of the form. crypto.randomUUID exists only in a
 * secure context (https or localhost), so the app reached over plain http on a
 * LAN address falls back to getRandomValues, which works everywhere.
 */
function newIdempotencyKey(): string {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
  return Array.from(crypto.getRandomValues(new Uint8Array(16)), (b) => b.toString(16).padStart(2, '0')).join('');
}

/** Today as YYYY-MM-DD in local time; toISOString() would give the UTC date, a day off around midnight. */
const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

interface InvoiceCreateDialogProps {
  open: boolean;
  clients: Client[];
  onClose: () => void;
  /** Called with the invoice as the server created it. */
  onCreated: (invoice: Invoice) => void;
}

/**
 * Create a draft invoice with real lines (#128).
 *
 * The number, the issue date and the status come from the server: the number
 * belongs to a gapless series (#38), and letting the client choose any of them
 * is how duplicates and out-of-order invoices happen. The dialog stays open
 * until the server answers, so a refusal is shown here with the entry intact,
 * and the Idempotency-Key makes a double submission create one invoice only.
 */
export default function InvoiceCreateDialog({ open, clients, onClose, onCreated }: InvoiceCreateDialogProps) {
  const [clientId, setClientId] = useState('');
  const [lines, setLines] = useState<LineDraft[]>([]);
  const [dueDate, setDueDate] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [idempotencyKey, setIdempotencyKey] = useState('');

  // A new opening starts a new form and a new key. Reopening after a failure
  // also starts afresh: the key only has to survive retries of one submission.
  useEffect(() => {
    if (!open) return;
    setClientId('');
    setLines([blankLine()]);
    setDueDate('');
    setError(null);
    setIdempotencyKey(newIdempotencyKey());
  }, [open]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (saving) return;
    const problem = !clientId
      ? 'Choose a client.'
      : !dueDate
        ? 'Choose a due date.'
        : dueDate < today()
          ? 'The due date cannot be in the past.'
          : problemWithLines(lines);
    if (problem) {
      setError(problem);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const invoice = await api.invoices.create(
        { client_id: Number(clientId), date_echeance: dueDate, items: toLineInputs(lines) },
        idempotencyKey,
      );
      onCreated(invoice);
    } catch (err) {
      // The entry stays as typed; the server's own words say what to fix.
      setError(err instanceof Error ? err.message : 'Could not create the invoice.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={() => { if (!saving) onClose(); }}
      title="Create new invoice"
      description="Created as a draft. The number and the issue date are assigned by the server."
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button type="submit" form="new-invoice-form" loading={saving}>
            Create invoice
          </Button>
        </>
      }
    >
      <form id="new-invoice-form" onSubmit={submit} className="flex flex-col gap-5" noValidate>
        {error && <FormAlert>{error}</FormAlert>}
        {/*
          A chosen client, not a typed name. An invoice references a real
          client row, so a free-text field could only ever produce an invoice
          that does not belong to anybody.
        */}
        <Field
          label="Client"
          hint={clients.length === 0 ? 'No clients yet. Add one before issuing an invoice.' : undefined}
        >
          {({ id, describedBy }) => (
            <Select id={id} aria-describedby={describedBy} required value={clientId} onChange={(e) => setClientId(e.target.value)}>
              <option value="">Choose a client</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>{c.nom}</option>
              ))}
            </Select>
          )}
        </Field>
        <InvoiceLinesEditor lines={lines} onChange={setLines} />
        <Field label="Due date">
          {({ id }) => (
            <Input id={id} type="date" required min={today()} value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
          )}
        </Field>
        <InvoiceLinesTotals lines={lines} />
      </form>
    </Dialog>
  );
}
