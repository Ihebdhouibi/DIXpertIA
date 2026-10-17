/**
 * The shape of a message file (#135). Each entry holds both languages side by
 * side; a count-dependent one holds both plural forms per language.
 *
 *   'invoices.count': { fr: { one: '{count} facture', other: '{count} factures' },
 *                       en: { one: '{count} invoice', other: '{count} invoices' } },
 *
 * Placeholders are {name}, filled from t(key, { name }). Every key starts with
 * its file's area ("invoices.", "people.") - checked by the compiler - so two
 * files can never define the same key: the catalog is the union of all of them.
 */
export type Plural = { one: string; other: string };
export type Message = { fr: string; en: string } | { fr: Plural; en: Plural };

export function defineMessages<const Area extends string, const T extends Record<string, Message>>(
  area: Area,
  // A key outside the area is typed `never`, so it fails to compile.
  messages: { [K in keyof T]: K extends `${Area}.${string}` ? T[K] : never },
): T {
  return messages as T;
}
