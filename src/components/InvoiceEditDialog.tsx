import React, { useEffect, useState } from 'react';
import * as api from '../api';
import type { Invoice } from '../types';
import Button from './ui/Button';
import Dialog from './ui/Dialog';
import { Field, FormAlert, Input } from './ui/Field';
import {
  InvoiceLinesEditor,
  InvoiceLinesTotals,
  LineDraft,
  linesOf,
  problemWithLines,
  toLineInputs,
} from './InvoiceLinesEditor';

interface InvoiceEditDialogProps {
  invoice: Invoice | null;
  onClose: () => void;
  /** Called with the invoice as the server returned it. */
  onSaved: (invoice: Invoice) => void;
}

/**
 * Correct a draft invoice (#125): its lines and its due date. The number, the
 * issue date and the client are not editable, and the totals are recomputed by
 * the server - the preview here only mirrors them.
 */
export default function InvoiceEditDialog({ invoice, onClose, onSaved }: InvoiceEditDialogProps) {
  const [lines, setLines] = useState<LineDraft[]>([]);
  const [dueDate, setDueDate] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!invoice) return;
    setLines(linesOf(invoice.items));
    setDueDate(invoice.dueDateIso ?? '');
    setError(null);
  }, [invoice]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!invoice) return;
    const problem = dueDate ? problemWithLines(lines) : 'Choose a due date.';
    if (problem) {
      setError(problem);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      onSaved(await api.invoices.update(invoice.id, { date_echeance: dueDate, items: toLineInputs(lines) }));
    } catch (err) {
      // The server's own words: a refusal names the invoice and the reason.
      setError(err instanceof Error ? err.message : 'Could not save the invoice.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog
      open={invoice !== null}
      onClose={onClose}
      title={`Edit ${invoice?.numero ?? ''}`}
      description="Only a draft can be corrected. The number, issue date and client stay as they are."
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="edit-invoice-form" loading={saving}>
            Save changes
          </Button>
        </>
      }
    >
      <form id="edit-invoice-form" onSubmit={submit} className="flex flex-col gap-5" noValidate>
        {error && <FormAlert>{error}</FormAlert>}
        <InvoiceLinesEditor lines={lines} onChange={setLines} />
        <Field label="Due date">
          {({ id }) => (
            <Input id={id} type="date" required value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
          )}
        </Field>
        <InvoiceLinesTotals lines={lines} />
      </form>
    </Dialog>
  );
}
