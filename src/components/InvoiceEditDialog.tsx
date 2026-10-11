import React, { useEffect, useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import * as api from '../api';
import type { InvoiceLineInput } from '../api';
import { formatTND } from '../format';
import type { Invoice } from '../types';
import Button from './ui/Button';
import Dialog from './ui/Dialog';
import { Field, FormAlert, Input, Select } from './ui/Field';

/** The VAT rates in force in Tunisia; a line keeps any other rate it already has. */
const VAT_RATES = [19, 13, 7, 0];

interface LineDraft {
  key: number;
  designation: string;
  quantite: string;
  prix_unitaire: string;
  taux_tva: string;
}

let nextKey = 0;
const blankLine = (): LineDraft => ({
  key: nextKey++, designation: '', quantite: '1', prix_unitaire: '', taux_tva: '19',
});

function linesOf(invoice: Invoice): LineDraft[] {
  if (!invoice.items?.length) return [blankLine()];
  return invoice.items.map((item) => ({
    key: nextKey++,
    designation: item.description,
    quantite: String(item.qty),
    prix_unitaire: String(item.price),
    taux_tva: String(item.vatRate ?? 19),
  }));
}

/** Same arithmetic as the server's _compute_totals, for the preview only: the server recomputes. */
function totals(lines: LineDraft[]) {
  let ht = 0;
  let ttc = 0;
  for (const l of lines) {
    const base = (Number(l.quantite) || 0) * (Number(l.prix_unitaire) || 0);
    ht += base;
    ttc += base * (1 + (Number(l.taux_tva) || 0) / 100);
  }
  return { ht, ttc };
}

function problemWith(lines: LineDraft[], dueDate: string): string | null {
  if (!dueDate) return 'Choose a due date.';
  for (const [i, l] of lines.entries()) {
    const n = i + 1;
    if (!l.designation.trim()) return `Line ${n} needs a description.`;
    if (!(Number(l.quantite) > 0)) return `Line ${n}: the quantity must be above zero.`;
    if (l.prix_unitaire === '' || !(Number(l.prix_unitaire) >= 0)) return `Line ${n} needs a unit price.`;
  }
  return null;
}

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
    setLines(linesOf(invoice));
    setDueDate(invoice.dueDateIso ?? '');
    setError(null);
  }, [invoice]);

  const update = (key: number, patch: Partial<LineDraft>) =>
    setLines((ls) => ls.map((l) => (l.key === key ? { ...l, ...patch } : l)));

  const { ht, ttc } = totals(lines);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!invoice) return;
    const problem = problemWith(lines, dueDate);
    if (problem) {
      setError(problem);
      return;
    }
    const items: InvoiceLineInput[] = lines.map((l) => ({
      designation: l.designation.trim(),
      quantite: Number(l.quantite),
      prix_unitaire: Number(l.prix_unitaire),
      taux_tva: Number(l.taux_tva),
    }));
    setSaving(true);
    setError(null);
    try {
      onSaved(await api.invoices.update(invoice.id, { date_echeance: dueDate, items }));
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

        <fieldset className="flex flex-col gap-3">
          <legend className="mb-2 font-mono text-[11px] font-medium uppercase tracking-[0.08em] text-on-surface-variant">
            Lines
          </legend>
          {lines.map((line, i) => {
            const n = i + 1;
            const rates = VAT_RATES.includes(Number(line.taux_tva))
              ? VAT_RATES
              : [Number(line.taux_tva), ...VAT_RATES];
            return (
              <div
                key={line.key}
                className="grid grid-cols-2 gap-2 rounded-lg border border-outline-variant p-3 md:grid-cols-[1fr_5rem_8rem_6rem_2.5rem] md:items-center md:border-0 md:p-0"
              >
                <Input
                  aria-label={`Line ${n} description`}
                  placeholder="Description"
                  value={line.designation}
                  onChange={(e) => update(line.key, { designation: e.target.value })}
                  className="col-span-2 md:col-span-1"
                />
                <Input
                  aria-label={`Line ${n} quantity`}
                  type="number"
                  min="0"
                  step="0.01"
                  value={line.quantite}
                  onChange={(e) => update(line.key, { quantite: e.target.value })}
                  className="font-mono"
                />
                <Input
                  aria-label={`Line ${n} unit price, TND excl. VAT`}
                  type="number"
                  min="0"
                  step="0.001"
                  placeholder="Unit price"
                  value={line.prix_unitaire}
                  onChange={(e) => update(line.key, { prix_unitaire: e.target.value })}
                  className="font-mono"
                />
                <Select
                  aria-label={`Line ${n} VAT rate`}
                  value={line.taux_tva}
                  onChange={(e) => update(line.key, { taux_tva: e.target.value })}
                  className="font-mono"
                >
                  {rates.map((r) => (
                    <option key={r} value={String(r)}>{r}%</option>
                  ))}
                </Select>
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label={`Remove line ${n}`}
                  title="Remove line"
                  disabled={lines.length === 1}
                  onClick={() => setLines((ls) => ls.filter((l) => l.key !== line.key))}
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
            );
          })}
          <div>
            <Button variant="secondary" size="sm" onClick={() => setLines((ls) => [...ls, blankLine()])}>
              <Plus className="h-4 w-4" aria-hidden="true" /> Add a line
            </Button>
          </div>
        </fieldset>

        <Field label="Due date">
          {({ id }) => (
            <Input id={id} type="date" required value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
          )}
        </Field>

        <dl className="ml-auto grid w-full max-w-xs grid-cols-2 gap-y-1 border-t border-outline-variant pt-3 text-sm">
          <dt className="text-on-surface-variant">Total excl. VAT</dt>
          <dd className="text-right font-mono tabular-nums text-on-surface">{formatTND(ht)}</dd>
          <dt className="font-semibold text-on-surface">Total incl. VAT</dt>
          <dd className="text-right font-mono font-semibold tabular-nums text-on-surface">{formatTND(ttc)}</dd>
        </dl>
      </form>
    </Dialog>
  );
}
