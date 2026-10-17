import React, { useEffect, useState } from 'react';
import { Reveal, useReducedMotion } from './motion';

const HEADLINE = 'Digital intelligence, expertly engineered.';
const TYPE_START_MS = 900;
const TYPE_STEP_MS = 44;

/**
 * The headline types itself behind a lime block cursor (HP-05). The whole
 * sentence is laid out from the start, its untyped part transparent, so the
 * line breaks never move while it types. Screen readers get the sentence once,
 * from aria-label; the visual spans are hidden from them. Under reduced
 * motion the sentence is complete at once.
 */
function TypedHeadline() {
  const reduced = useReducedMotion();
  const [typed, setTyped] = useState(reduced ? HEADLINE.length : 0);

  useEffect(() => {
    if (reduced) {
      setTyped(HEADLINE.length);
      return;
    }
    setTyped(0);
    let step: number | undefined;
    const start = window.setTimeout(() => {
      step = window.setInterval(() => {
        setTyped((n) => {
          if (n + 1 >= HEADLINE.length) window.clearInterval(step);
          return Math.min(n + 1, HEADLINE.length);
        });
      }, TYPE_STEP_MS);
    }, TYPE_START_MS);
    return () => {
      window.clearTimeout(start);
      window.clearInterval(step);
    };
  }, [reduced]);

  const typing = typed > 0 && typed < HEADLINE.length;
  return (
    <h1 id="hero-title" aria-label={HEADLINE} className="m-0 max-w-[14ch] text-home-hero font-bold text-balance">
      <span aria-hidden="true">
        {HEADLINE.slice(0, typed)}
        <span
          className={`mr-[-0.38em] ml-[0.08em] inline-block h-[0.68em] w-[0.38em] rounded-[0.05em] bg-home-accent-text align-[-0.02em] ${typing ? '' : 'animate-home-blink'}`}
        />
        <span className="text-transparent">{HEADLINE.slice(typed)}</span>
      </span>
    </h1>
  );
}

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
  return (
    <section aria-labelledby="hero-title" className="relative overflow-hidden bg-home-bg" style={GRID}>
      <div aria-hidden="true" className="pointer-events-none absolute inset-0" style={VIGNETTE} />
      <div className="relative mx-auto flex max-w-[1312px] flex-col gap-[clamp(32px,4vw,56px)] px-[clamp(20px,5vw,48px)] pt-[clamp(56px,8vw,112px)] pb-[clamp(56px,7vw,96px)]">
        <div className="flex flex-wrap justify-between gap-3 font-mono text-home-meta leading-none font-medium tracking-[0.18em] text-home-fg/62 uppercase">
          <span>Cloud · Cybersecurity · Custom software</span>
          <span>36.45° N&nbsp;&nbsp;10.73° E — Nabeul</span>
        </div>

        <TypedHeadline />

        <div aria-hidden="true" className="h-px origin-left animate-home-draw bg-home-fg" />

        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,420px),1fr))] items-start gap-[clamp(32px,5vw,72px)]">
          <Reveal index={1} className="flex flex-col gap-7">
            <p className="m-0 max-w-[48ch] text-home-lead text-pretty text-home-fg/72">
              We design, build and run the systems your organisation depends on — cloud infrastructure, security and
              software, engineered for reliability from the first line.
            </p>
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={onContact}
                className="inline-flex h-[52px] cursor-pointer items-center gap-2.5 rounded-[10px] bg-lime px-6 text-[15px] font-semibold text-ink ring-1 ring-ink/15 ring-inset transition duration-200 hover:-translate-y-px hover:bg-lime-hover"
              >
                Contact us <span aria-hidden="true">→</span>
              </button>
              <button
                type="button"
                onClick={onServices}
                className="inline-flex h-[52px] cursor-pointer items-center rounded-[10px] border border-home-fg/30 bg-home-bg px-6 text-[15px] font-semibold text-home-fg transition-colors duration-200 hover:border-home-fg"
              >
                Our services
              </button>
            </div>
          </Reveal>
          {panel && <Reveal index={2}>{panel}</Reveal>}
        </div>
      </div>
    </section>
  );
}
