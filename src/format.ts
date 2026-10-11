/**
 * Dinar amounts. DI Xpertia is a Tunisian company and invoices in TND; the
 * dinar has three decimal places, so minimumFractionDigits is set rather than
 * left to the currency default.
 */
const TND = new Intl.NumberFormat('fr-TN', { style: 'currency', currency: 'TND', minimumFractionDigits: 3 });

export function formatTND(value: number): string {
  return TND.format(value);
}
