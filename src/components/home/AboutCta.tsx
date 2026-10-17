import React, { useRef } from 'react';
import { Reveal, useReducedMotion } from './motion';

const GRID: React.CSSProperties = {
  backgroundImage:
    'linear-gradient(var(--color-home-cta-grid-line) 1px, transparent 1px), linear-gradient(90deg, var(--color-home-cta-grid-line) 1px, transparent 1px)',
  backgroundSize: '48px 48px',
};

/** A mouse or a trackpad: the magnet makes no sense on touch. */
const finePointer = () => window.matchMedia('(hover: hover) and (pointer: fine)').matches;

/**
 * The closing call to action (HP-09), always dark. "Get started today" leans
 * towards the pointer within its zone (up to 15px across, 11px down) over a
 * pulsing lime glow. The magnet only works with a fine pointer and without
 * reduced motion; the button itself is an ordinary button, always clickable
 * and focusable.
 */
export default function AboutCta({ onStart }: { onStart: () => void }) {
  const reduced = useReducedMotion();
  const button = useRef<HTMLButtonElement>(null);

  const pull = (e: React.PointerEvent<HTMLDivElement>) => {
    if (reduced || e.pointerType !== 'mouse' || !finePointer() || !button.current) return;
    const r = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - 0.5;
    const y = (e.clientY - r.top) / r.height - 0.5;
    button.current.style.transform = `translate(${x * 30}px, ${y * 22}px)`;
  };
  const release = () => {
    if (button.current) button.current.style.transform = '';
  };

  return (
    <section
      id="about"
      aria-labelledby="cta-title"
      className="relative scroll-mt-[68px] overflow-hidden border-t border-home-panel-border bg-home-cta text-paper"
      style={GRID}
    >
      <div className="relative mx-auto grid max-w-[1312px] grid-cols-[repeat(auto-fit,minmax(min(100%,460px),1fr))] items-center gap-10 px-[clamp(20px,5vw,48px)] py-[clamp(80px,10vw,136px)]">
        <div className="flex flex-col gap-5">
          <Reveal as="p" className="m-0 font-mono text-caption leading-none font-semibold tracking-[0.18em] text-lime uppercase">
            03 — About
          </Reveal>
          <Reveal as="h2" index={1} id="cta-title" className="m-0 max-w-[10.37em] text-home-closing font-bold text-balance">
            Ready to transform your IT infrastructure?
          </Reveal>
          <Reveal as="p" index={2} className="m-0 max-w-[29.49em] text-home-lead text-paper/74">
            Partner with DI Xpertia to bring modern, reliable technology to your organisation.
          </Reveal>
        </div>

        <Reveal index={3} className="relative justify-self-center px-4 py-14 sm:px-[72px]" onPointerMove={pull} onPointerLeave={release}>
          <div
            aria-hidden="true"
            className="pointer-events-none absolute top-1/2 left-1/2 -mt-[50px] -ml-[140px] h-[100px] w-[280px] animate-home-glow rounded-full bg-lime opacity-28 blur-[42px]"
          />
          <button
            ref={button}
            type="button"
            onClick={onStart}
            className="relative inline-flex h-[60px] cursor-pointer items-center gap-2.5 whitespace-nowrap rounded-xl bg-lime px-8 text-[17px] font-semibold text-ink transition-[transform,background-color] duration-450 ease-home-magnet hover:bg-lime-hover"
          >
            Get started today <span aria-hidden="true">→</span>
          </button>
        </Reveal>
      </div>
    </section>
  );
}
