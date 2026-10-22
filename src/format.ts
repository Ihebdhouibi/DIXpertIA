import { getLocale } from './i18n';

/**
 * Numbers, amounts and dates in the language showing (#135), the same way the
 * API and the invoice PDF write them: '1,234.500 TND' / '1 234,500 TND',
 * 'Oct 17, 2026' / '17 oct. 2026'.
 *
 * Each call reads the current language, so a component re-rendered after the
 * toggle shows the new format. App re-renders the whole tree when the
 * language changes.
 */

const TAG = { fr: 'fr-FR', en: 'en-US' } as const;

/** The currencies an invoice can be in (#195), and their decimal places: the dinar has three. */
export type Currency = 'TND' | 'EUR' | 'USD' | 'GBP';
export const CURRENCIES: Currency[] = ['TND', 'EUR', 'USD', 'GBP'];
const DECIMALS: Record<string, number> = { TND: 3, EUR: 2, USD: 2, GBP: 2 };

/**
 * An amount in its currency, the way the invoice PDF writes it:
 * '4,800.50 USD' / '4 800,50 USD', '1,234.500 TND'. Never converted.
 */
export function formatMoney(value: number, currency: string = 'TND'): string {
  const digits = DECIMALS[currency] ?? 2;
  const number = new Intl.NumberFormat(TAG[getLocale()], { minimumFractionDigits: digits, maximumFractionDigits: digits });
  return `${number.format(value)} ${currency}`;
}

/** Dinar amounts: payslips, and anything not tied to an invoice's currency. */
export function formatTND(value: number): string {
  return formatMoney(value, 'TND');
}

/**
 * Totals in several currencies, side by side: '2 380,000 TND · 2 000,00 USD'.
 * Never one sum: dollars added to dinars mean nothing (#195).
 */
export function formatAmounts(amounts: { currency: string; amount: number }[] | undefined, fallback = 0): string {
  if (!amounts || amounts.length === 0) return formatMoney(fallback, 'TND');
  return amounts.map((a) => formatMoney(a.amount, a.currency)).join(' · ');
}

/** A plain number, grouped the local way: 1,234.5 / 1 234,5. */
export function formatNumber(value: number, options?: Intl.NumberFormatOptions): string {
  return new Intl.NumberFormat(TAG[getLocale()], options).format(value);
}

function toDate(value: string | number | Date): Date {
  return value instanceof Date ? value : new Date(value);
}

/** 'Oct 17, 2026' / '17 oct. 2026'. */
export function formatDate(value: string | number | Date): string {
  return toDate(value).toLocaleDateString(TAG[getLocale()], { day: 'numeric', month: 'short', year: 'numeric' });
}

/** 'Oct 17' / '17 oct.': a date within the current year. */
export function formatDayMonth(value: string | number | Date): string {
  return toDate(value).toLocaleDateString(TAG[getLocale()], { day: 'numeric', month: 'short' });
}

/** 'Oct 17, 2026, 14:05' / '17 oct. 2026, 14:05'. 24-hour in both. */
export function formatDateTime(value: string | number | Date, { year = true } = {}): string {
  return toDate(value).toLocaleString(TAG[getLocale()], {
    day: 'numeric', month: 'short', ...(year ? { year: 'numeric' } : {}),
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  });
}

/** 'October 2026' / 'octobre 2026'. */
export function formatMonth(value: string | number | Date): string {
  return toDate(value).toLocaleDateString(TAG[getLocale()], { month: 'long', year: 'numeric' });
}
