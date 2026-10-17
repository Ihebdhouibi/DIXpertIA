/**
 * Dinar amounts. DI Xpertia is a Tunisian company and invoices in TND; the
 * dinar has three decimal places, so minimumFractionDigits is set rather than
 * left to the currency default.
 */
const TND = new Intl.NumberFormat('fr-TN', { style: 'currency', currency: 'TND', minimumFractionDigits: 3 });

export function formatTND(value: number): string {
  return TND.format(value);
}

/**
 * The word for a count: "invoice" for 1, "invoices" otherwise - 0 and 0.5
 * included, as English has it (#155). The plural defaults to singular + "s".
 */
export function plural(count: number, singular: string, pluralForm = `${singular}s`): string {
  return count === 1 ? singular : pluralForm;
}
