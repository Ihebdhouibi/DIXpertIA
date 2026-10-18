import React, { useEffect, useState } from 'react';
import { Reveal, useReducedMotion } from './motion';
import { useLocale, useT } from '../../i18n';

const TYPE_START_MS = 900;
const TYPE_STEP_MS = 44;

/**
 * The headline types itself behind a lime block cursor (HP-05). Three details
 * keep the layout still while it types (HP-11 measured shifts up to 0.79
 * before them):
 * - Every letter is its own element, present from the start and transparent
 *   until typed. Typing only changes a colour; no text moves. A single
 *   "untyped rest" text node did move: its start shifted one letter per tick,
 *   which the browser counts as layout shift even when transparent.
 * - The cursor takes no width and is glued to the letters on either side
 *   (white-space: nowrap). A block is a line-break opportunity: left loose
 *   inside a word, it let "intelligence" break where it stood. A space next
 *   to it stays outside the glue, so the real break points do not change.
 * - Typing waits for the fonts, so it never runs during the font swap.
 * Screen readers get the sentence once, from aria-label; the letters are
 * hidden from them. Under reduced motion the sentence is complete at once.
 * The parent keys it on the language, so a switch types the new sentence
 * from the start rather than mixing two.
 */
function TypedHeadline({ headline }: { headline: string }) {
  const letters = [...headline];
  const reduced = useReducedMotion();
  const [typed, setTyped] = useState(reduced ? letters.length : 0);

  useEffect(() => {
    if (reduced) {
      setTyped(letters.length);
      return;
    }
    setTyped(0);
    let cancelled = false;
    let start: number | undefined;
    let step: number | undefined;
    const fonts = document.fonts ? document.fonts.ready : Promise.resolve();
    fonts.then(() => {
      if (cancelled) return;
      start = window.setTimeout(() => {
        step = window.setInterval(() => {
          setTyped((n) => {
            if (n + 1 >= letters.length) window.clearInterval(step);
            return Math.min(n + 1, letters.length);
          });
        }, TYPE_STEP_MS);
      }, TYPE_START_MS);
    });
    return () => {
      cancelled = true;
      window.clearTimeout(start);
      window.clearInterval(step);
    };
    // letters.length is fixed for this instance: a new sentence remounts it.
  }, [reduced]);

  const typing = typed > 0 && typed < letters.length;
  const letter = (i: number) => (
    <span key={i} className={i < typed ? undefined : 'text-transparent'}>
      {letters[i]}
    </span>
  );
  // The letters glued to the cursor: the one before and the one after it,
  // unless either is a space.
  const glueFrom = typed > 0 && letters[typed - 1] !== ' ' ? typed - 1 : typed;
  const glueTo = typed < letters.length && letters[typed] !== ' ' ? typed + 1 : typed;
  const range = (from: number, to: number) => Array.from({ length: Math.max(0, to - from) }, (_, k) => letter(from + k));

  return (
    <h1 id="hero-title" aria-label={headline} className="m-0 max-w-[9.07em] text-home-hero font-bold text-balance">
      <span aria-hidden="true">
        {range(0, glueFrom)}
        <span className="whitespace-nowrap">
          {range(glueFrom, typed)}
          <span
            className={`mr-[-0.46em] ml-[0.08em] inline-block h-[0.68em] w-[0.38em] rounded-[0.05em] bg-home-accent-text align-[-0.02em] ${typing ? '' : 'animate-home-blink'}`}
          />
          {range(typed, glueTo)}
        </span>
        {range(glueTo, letters.length)}
      </span>
    </h1>
  );
}

// Widths in em, not the handoff's ch: ch is the width of "0" in the font being
// shown, so the fallback font narrowed the headline and wrapped it on one more
// line until Space Grotesk arrived. The em values equal the ch ones in Space
// Grotesk (its "0" is 0.648em at 700, 0.641em at 400): 14ch = 9.07em.

/** The engineering grid: 48px squares of hairline, faded out by a vignette. */
const GRID: React.CSSProperties = {
  backgroundImage:
    'linear-gradient(var(--color-home-grid-line) 1px, transparent 1px), linear-gradient(90deg, var(--color-home-grid-line) 1px, transparent 1px)',
  backgroundSize: '48px 48px',
  backgroundPosition: '-1px -1px',
};
const VIGNETTE: React.CSSProperties = {
  background: 'radial-gradient(ellipse 80% 70% at 30% 40%, transparent 40%, var(--color-home-bg) 100%)',
};

export default function Hero({ onContact, onServices, console: panel }: {
  onContact: () => void;
  onServices: () => void;
  /** The animated "how we work" console, on the right (HP-06). */
  console?: React.ReactNode;
}) {
  const t = useT();
  const locale = useLocale();
  return (
    <section aria-labelledby="hero-title" className="relative overflow-hidden bg-home-bg" style={GRID}>
      <div aria-hidden="true" className="pointer-events-none absolute inset-0" style={VIGNETTE} />
      <div className="relative mx-auto flex max-w-[1312px] flex-col gap-[clamp(32px,4vw,56px)] px-[clamp(20px,5vw,48px)] pt-[clamp(56px,8vw,112px)] pb-[clamp(56px,7vw,96px)]">
        <div className="flex flex-wrap justify-between gap-3 font-mono text-home-meta leading-none font-medium tracking-[0.18em] text-home-fg/62 uppercase">
          <span>{t('home.hero.disciplines')}</span>
          <span>{t('home.hero.coordinates')}</span>
        </div>

        <TypedHeadline key={locale} headline={t('home.hero.headline')} />

        <div aria-hidden="true" className="h-px origin-left animate-home-draw bg-home-fg" />

        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,420px),1fr))] items-start gap-[clamp(32px,5vw,72px)]">
          <Reveal index={1} className="flex flex-col gap-7">
            <p className="m-0 max-w-[30.77em] text-home-lead text-pretty text-home-fg/72">
              {t('home.hero.lead')}
            </p>
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={onContact}
                className="inline-flex h-[52px] cursor-pointer items-center gap-2.5 rounded-[10px] bg-lime px-6 text-[15px] font-semibold text-ink ring-1 ring-ink/15 ring-inset transition duration-200 hover:-translate-y-px hover:bg-lime-hover"
              >
                {t('home.hero.contact')} <span aria-hidden="true">→</span>
              </button>
              <button
                type="button"
                onClick={onServices}
                className="inline-flex h-[52px] cursor-pointer items-center rounded-[10px] border border-home-fg/30 bg-home-bg px-6 text-[15px] font-semibold text-home-fg transition-colors duration-200 hover:border-home-fg"
              >
                {t('home.hero.services')}
              </button>
            </div>
          </Reveal>
          {panel && <Reveal index={2}>{panel}</Reveal>}
        </div>
      </div>
    </section>
  );
}
