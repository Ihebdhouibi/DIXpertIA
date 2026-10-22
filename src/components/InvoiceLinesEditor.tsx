import React from 'react';
import { Plus, Trash2 } from 'lucide-react';
import type { InvoiceLineInput } from '../api';
import { formatMoney } from '../format';
import { t as translate, useT } from '../i18n';
import type { InvoiceItem } from '../types';
import Button from './ui/Button';
import { Input, Select, Textarea } from './ui/Field';

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
  detail: string;
  unite: string;
}

let nextKey = 0;
export const blankLine = (): LineDraft => ({
  key: nextKey++, designation: '', quantite: '1', prix_unitaire: '', taux_tva: '19', detail: '', unite: '',
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
    detail: item.detail ?? '',
    unite: item.unit ?? '',
  }));
}

/** The lines as the API takes them. Call after problemWithLines() returned null. */
export function toLineInputs(lines: LineDraft[]): InvoiceLineInput[] {
  return lines.map((l) => ({
    designation: l.designation.trim(),
    quantite: Number(l.quantite),
    prix_unitaire: Number(l.prix_unitaire),
    taux_tva: Number(l.taux_tva),
    // The server trims and stores blank as nothing (#194).
    detail: l.detail,
    unite: l.unite,
  }));
}

/** The first thing to fix before sending, in words for the form; null when the lines are complete. */
export function problemWithLines(lines: LineDraft[]): string | null {
  if (lines.length === 0) return translate('invoices.line.needOne');
  for (const [i, l] of lines.entries()) {
    const n = i + 1;
    if (!l.designation.trim()) return translate('invoices.line.needDescription', { n });
    if (!(Number(l.quantite) > 0)) return translate('invoices.line.needQuantity', { n });
    if (l.prix_unitaire === '' || !(Number(l.prix_unitaire) >= 0)) return translate('invoices.line.needUnitPrice', { n });
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
  /** An export of services (#195): every line at 0% VAT, the rate locked. */
  exportOfServices?: boolean;
}

/** The lines with their VAT set to 0%: an export of services carries none (#195). */
export function withoutVat(lines: LineDraft[]): LineDraft[] {
  return lines.map((l) => (l.taux_tva === '0' ? l : { ...l, taux_tva: '0' }));
}

/** One row per line, with add and remove. */
export function InvoiceLinesEditor({ lines, onChange, exportOfServices = false }: InvoiceLinesEditorProps) {
  const t = useT();
  const update = (key: number, patch: Partial<LineDraft>) =>
    onChange(lines.map((l) => (l.key === key ? { ...l, ...patch } : l)));

  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="mb-2 font-mono text-[11px] font-medium uppercase tracking-[0.08em] text-on-surface-variant">
        {t('invoices.lines')}
      </legend>
      {exportOfServices && (
        <p className="m-0 text-body-sm text-on-surface-variant">{t('invoices.line.exportNote')}</p>
      )}
      {lines.map((line, i) => {
        const n = i + 1;
        const rates = VAT_RATES.includes(Number(line.taux_tva))
          ? VAT_RATES
          : [Number(line.taux_tva), ...VAT_RATES];
        return (
          <div
            key={line.key}
            className="grid grid-cols-2 gap-2 rounded-lg border border-outline-variant p-3 md:grid-cols-[6rem_8rem_1fr_6rem_2.5rem] md:items-center"
          >
            <Input
              aria-label={t('invoices.line.descriptionLabel', { n })}
              placeholder={t('invoices.line.description')}
              value={line.designation}
              onChange={(e) => update(line.key, { designation: e.target.value })}
              className="col-span-2 md:order-1 md:col-span-4"
            />
            <Input
              aria-label={t('invoices.line.quantityLabel', { n })}
              type="number"
              min="0"
              step="0.01"
              value={line.quantite}
              onChange={(e) => update(line.key, { quantite: e.target.value })}
              className="font-mono md:order-3"
            />
            <Input
              aria-label={t('invoices.line.unitLabel', { n })}
              placeholder={t('invoices.line.unit')}
              maxLength={30}
              value={line.unite}
              onChange={(e) => update(line.key, { unite: e.target.value })}
              className="md:order-4"
            />
            <Input
              aria-label={t('invoices.line.unitPriceLabel', { n })}
              type="number"
              min="0"
              step="0.001"
              placeholder={t('invoices.line.unitPrice')}
              value={line.prix_unitaire}
              onChange={(e) => update(line.key, { prix_unitaire: e.target.value })}
              className="font-mono md:order-5"
            />
            <Select
              aria-label={t('invoices.line.vatLabel', { n })}
              value={exportOfServices ? '0' : line.taux_tva}
              disabled={exportOfServices}
              onChange={(e) => update(line.key, { taux_tva: e.target.value })}
              className="font-mono md:order-6"
            >
              {rates.map((r) => (
                <option key={r} value={String(r)}>{r}%</option>
              ))}
            </Select>
            <Button
              variant="ghost"
              size="sm"
              aria-label={t('invoices.line.removeLabel', { n })}
              title={t('invoices.line.remove')}
              disabled={lines.length === 1}
              className="order-last justify-self-start md:order-2 md:justify-self-auto"
              onClick={() => onChange(lines.filter((l) => l.key !== line.key))}
            >
              <Trash2 className="h-4 w-4" aria-hidden="true" />
            </Button>
            <Textarea
              aria-label={t('invoices.line.detailLabel', { n })}
              placeholder={t('invoices.line.detail')}
              rows={2}
              maxLength={1000}
              value={line.detail}
              onChange={(e) => update(line.key, { detail: e.target.value })}
              className="col-span-2 md:order-7 md:col-span-4"
            />
          </div>
        );
      })}
      <div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onChange([...lines, exportOfServices ? { ...blankLine(), taux_tva: '0' } : blankLine()])}
        >
          <Plus className="h-4 w-4" aria-hidden="true" /> {t('invoices.line.add')}
        </Button>
      </div>
    </fieldset>
  );
}

/** Live totals of the lines being typed. */
export function InvoiceLinesTotals({ lines, currency = 'TND' }: { lines: LineDraft[]; currency?: string }) {
  const t = useT();
  const { ht, ttc } = totals(lines);
  return (
    <dl className="ml-auto grid w-full max-w-xs grid-cols-2 gap-y-1 border-t border-outline-variant pt-3 text-sm">
      <dt className="text-on-surface-variant">{t('invoices.totalExclVat')}</dt>
      <dd className="text-right font-mono tabular-nums text-on-surface">{formatMoney(ht, currency)}</dd>
      <dt className="font-semibold text-on-surface">{t('invoices.totalInclVat')}</dt>
      <dd className="text-right font-mono font-semibold tabular-nums text-on-surface">{formatMoney(ttc, currency)}</dd>
    </dl>
  );
}
