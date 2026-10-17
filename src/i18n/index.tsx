import { useSyncExternalStore } from 'react';
import { catalog, type MessageKey } from './catalog';

/**
 * French and English for the whole interface (#135).
 *
 * Which language shows, first match wins:
 * 1. the choice made in this browser with the FR / EN toggle;
 * 2. once signed in, the account's language (it also decides the language of
 *    the account's e-mails and notifications);
 * 3. the domain: dixpertia.com is English, dixpertia.tn and anything else
 *    (localhost, previews) French.
 *
 * A choice made in the browser is also saved on the account when signed in,
 * so the next device and the next e-mail follow it.
 *
 * Messages live in ./messages, one file per area, each entry carrying both
 * languages side by side so a missing translation is visible in review. Keys
 * are typed: a key that does not exist fails `tsc`.
 */
export type Locale = 'fr' | 'en';
export const LOCALES: readonly Locale[] = ['fr', 'en'];

const STORAGE_KEY = 'dixpertia_locale';

/** The language a domain opens in, before anyone chooses. */
export function domainLocale(hostname: string = window.location.hostname): Locale {
  return /(^|\.)dixpertia\.com$/i.test(hostname) ? 'en' : 'fr';
}

function readChoice(): Locale | null {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'fr' || saved === 'en') return saved;
  } catch {
    // Storage unavailable (private mode, blocked site data): no saved choice.
  }
  return null;
}

let chosen = readChoice();
let account: Locale | null = null;
let current: Locale = chosen ?? domainLocale();

const listeners = new Set<() => void>();

function update() {
  const next = chosen ?? account ?? domainLocale();
  if (next === current) return;
  current = next;
  document.documentElement.lang = next;
  listeners.forEach((listener) => listener());
}

document.documentElement.lang = current;

/** The language now showing. For code outside React, such as the API client. */
export function getLocale(): Locale {
  return current;
}

/** The toggle: remembered in this browser. The caller saves it on the account. */
export function chooseLocale(next: Locale) {
  chosen = next;
  try {
    localStorage.setItem(STORAGE_KEY, next);
  } catch {
    // The choice still applies for this session.
  }
  update();
}

/**
 * The signed-in account's language, or null on sign-out. It applies only when
 * nothing was chosen in this browser.
 */
export function setAccountLocale(locale: string | null | undefined) {
  account = locale === 'fr' || locale === 'en' ? locale : null;
  update();
}

/** Whether this browser has an explicit choice, which then wins over the account's. */
export function hasChosenLocale(): boolean {
  return chosen !== null;
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function useLocale(): Locale {
  return useSyncExternalStore(subscribe, () => current);
}

export type Params = Record<string, string | number>;

const pluralRules: Record<Locale, Intl.PluralRules> = {
  fr: new Intl.PluralRules('fr'),
  en: new Intl.PluralRules('en'),
};

function interpolate(text: string, params?: Params): string {
  if (!params) return text;
  return text.replace(/\{(\w+)\}/g, (whole, name: string) =>
    name in params ? String(params[name]) : whole,
  );
}

/**
 * The message for `key` in `locale`. A plural entry ({ one, other }) picks its
 * form from `params.count` by the language's own rule: French says "0 facture",
 * English "0 invoices".
 */
export function translate(locale: Locale, key: MessageKey, params?: Params): string {
  const entry = catalog[key][locale] as string | { one: string; other: string };
  if (typeof entry === 'string') return interpolate(entry, params);
  const count = Number(params?.count ?? 0);
  const form = pluralRules[locale].select(count) === 'one' ? entry.one : entry.other;
  return interpolate(form, params);
}

/** `t(key, params)` in the current language, outside React. */
export function t(key: MessageKey, params?: Params): string {
  return translate(current, key, params);
}

/** `t(key, params)` in the current language; re-renders when the language changes. */
export function useT(): (key: MessageKey, params?: Params) => string {
  const locale = useLocale();
  return (key, params) => translate(locale, key, params);
}

/**
 * The translation of a value the API sends in English - a status, a leave
 * type - looked up as `${prefix}.${value}`. A value with no entry is returned
 * as it is, so a new value from the API still shows rather than breaking.
 */
export function labelOf(
  t: (key: MessageKey, params?: Params) => string,
  prefix: 'common.status' | 'common.leaveType',
  value: string,
): string {
  const key = `${prefix}.${value}`;
  return key in catalog ? t(key as MessageKey) : value;
}

export type { MessageKey };
