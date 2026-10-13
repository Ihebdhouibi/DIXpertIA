import React from 'react';
import { Plus, Trash2 } from 'lucide-react';
import type { InvoiceLineInput } from '../api';
import { formatTND } from '../format';
import type { InvoiceItem } from '../types';
import Button from './ui/Button';
import { Input, Select } from './ui/Field';

/**
 * The lines of an invoice, as one editor shared by creation (#128) and
 * correction (#125), so the two forms cannot drift apart.
 */

/** The VAT rates in force in Tunisia; a line keeps any other rate it already has. */
const VAT_RATES = [19, 13, 7, 0];

/** A line as typed: strings, so a half-typed number is not lost or reformatted. */
export interface LineDraft {
  key: number;
  designation: string;
  quantite: string;
  prix_unitaire: string;
  taux_tva: string;
}

let nextKey = 0;
export const blankLine = (): LineDraft => ({
  key: nextKey++, designation: '', quantite: '1', prix_unitaire: '', taux_tva: '19',
});

/** Lines to edit from an invoice's items; one blank line when it has none. */
export function linesOf(items: InvoiceItem[] | undefined): LineDraft[] {
  if (!items?.length) return [blankLine()];
  return items.map((item) => ({
    key: nextKey++,
    designation: item.description,
    quantite: String(item.qty),
    prix_unitaire: String(item.price),
    taux_tva: String(item.vatRate ?? 19),
  }));
}

/** The lines as the API takes them. Call after problemWithLines() returned null. */
export function toLineInputs(lines: LineDraft[]): InvoiceLineInput[] {
  return lines.map((l) => ({
    designation: l.designation.trim(),
    quantite: Number(l.quantite),
    prix_unitaire: Number(l.prix_unitaire),
    taux_tva: Number(l.taux_tva),
  }));
}

/** The first thing to fix before sending, in words for the form; null when the lines are complete. */
export function problemWithLines(lines: LineDraft[]): string | null {
  if (lines.length === 0) return 'Add at least one line.';
  for (const [i, l] of lines.entries()) {
    const n = i + 1;
    if (!l.designation.trim()) return `Line ${n} needs a description.`;
    if (!(Number(l.quantite) > 0)) return `Line ${n}: the quantity must be above zero.`;
    if (l.prix_unitaire === '' || !(Number(l.prix_unitaire) >= 0)) return `Line ${n} needs a unit price.`;
  }
  return null;
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

interface InvoiceLinesEditorProps {
  lines: LineDraft[];
  onChange: (lines: LineDraft[]) => void;
}

/** One row per line, with add and remove. */
export function InvoiceLinesEditor({ lines, onChange }: InvoiceLinesEditorProps) {
  const update = (key: number, patch: Partial<LineDraft>) =>
    onChange(lines.map((l) => (l.key === key ? { ...l, ...patch } : l)));

  return (
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
              onClick={() => onChange(lines.filter((l) => l.key !== line.key))}
            >
              <Trash2 className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
        );
      })}
      <div>
        <Button variant="secondary" size="sm" onClick={() => onChange([...lines, blankLine()])}>
          <Plus className="h-4 w-4" aria-hidden="true" /> Add a line
        </Button>
      </div>
    </fieldset>
  );
}

/** Live totals of the lines being typed. */
export function InvoiceLinesTotals({ lines }: { lines: LineDraft[] }) {
  const { ht, ttc } = totals(lines);
  return (
    <dl className="ml-auto grid w-full max-w-xs grid-cols-2 gap-y-1 border-t border-outline-variant pt-3 text-sm">
      <dt className="text-on-surface-variant">Total excl. VAT</dt>
      <dd className="text-right font-mono tabular-nums text-on-surface">{formatTND(ht)}</dd>
      <dt className="font-semibold text-on-surface">Total incl. VAT</dt>
      <dd className="text-right font-mono font-semibold tabular-nums text-on-surface">{formatTND(ttc)}</dd>
    </dl>
  );
}
