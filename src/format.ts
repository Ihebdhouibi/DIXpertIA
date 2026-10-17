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

const DINARS = {
  fr: new Intl.NumberFormat(TAG.fr, { minimumFractionDigits: 3, maximumFractionDigits: 3 }),
  en: new Intl.NumberFormat(TAG.en, { minimumFractionDigits: 3, maximumFractionDigits: 3 }),
};

/**
 * Dinar amounts. DI Xpertia is a Tunisian company and invoices in TND; the
 * dinar has three decimal places, so they are always shown.
 */
export function formatTND(value: number): string {
  return `${DINARS[getLocale()].format(value)} TND`;
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
