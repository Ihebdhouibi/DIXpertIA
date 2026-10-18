import { chooseLocale, LOCALES, useLocale, useT } from '../i18n';

/**
 * FR | EN (#135). Two buttons rather than a menu: one tap, and the current
 * language is visible at a glance. aria-pressed tells a screen reader which
 * is on; each button's label names its language in that language, so a
 * French speaker on the English site still recognises "Français".
 *
 * `tone` follows the surface: the app's tokens, or the public site's.
 */
const NAMES = { fr: 'Français', en: 'English' } as const;

export default function LanguageToggle({ tone = 'app' }: { tone?: 'app' | 'home' }) {
  const locale = useLocale();
  const t = useT();
  const frame = tone === 'home' ? 'border-home-fg/20' : 'border-outline-variant';
  const on = tone === 'home' ? 'bg-home-fg/10 text-home-fg' : 'bg-surface-container-high text-on-surface';
  const off =
    tone === 'home'
      ? 'text-home-fg/66 hover:text-home-fg'
      : 'text-on-surface-variant hover:text-on-surface';

  return (
    <div role="group" aria-label={t('common.language')} className={`inline-flex rounded-lg border p-0.5 ${frame}`}>
      {LOCALES.map((code) => (
        <button
          key={code}
          type="button"
          lang={code}
          aria-label={NAMES[code]}
          aria-pressed={locale === code}
          onClick={() => chooseLocale(code)}
          className={`h-7 min-w-9 cursor-pointer rounded-md px-2 font-mono text-xs font-medium uppercase transition-colors ${
            locale === code ? on : off
          }`}
        >
          {code}
        </button>
      ))}
    </div>
  );
}
