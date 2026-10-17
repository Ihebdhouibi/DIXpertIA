import React from 'react';
import { Reveal } from './motion';

const SERVICES = [
  {
    n: '01',
    title: 'Cloud Infrastructure',
    tags: 'Architecture · Migration · Operations',
    desc: 'Scalable, secure cloud architecture designed for high availability and enterprise performance.',
  },
  {
    n: '02',
    title: 'Cybersecurity',
    tags: 'Audit · Hardening · Compliance',
    desc: 'Threat protection and compliance management that keeps your critical data assets safe.',
  },
  {
    n: '03',
    title: 'Custom Software',
    tags: 'Web · Mobile · Integrations',
    desc: 'Bespoke applications built around your operational workflows — not the other way round.',
  },
];

/** A section's eyebrow and title, with the note on the right (services, engagement). */
export function SectionHeading({ eyebrow, title, id, note }: { eyebrow: string; title: string; id: string; note: string }) {
  return (
    <Reveal className="flex flex-wrap items-end justify-between gap-4">
      <div className="flex flex-col gap-3.5">
        <p className="m-0 font-mono text-caption leading-none font-semibold tracking-[0.18em] text-home-accent-text uppercase">{eyebrow}</p>
        <h2 id={id} className="m-0 text-home-section font-bold">{title}</h2>
      </div>
      <p className="m-0 max-w-[38ch] text-[15px] leading-[1.6] text-home-fg/68">{note}</p>
    </Reveal>
  );
}

/**
 * The services as an indexed list (HP-07). Each row is one button to the
 * contact page, and a lime spotlight follows the pointer across it. The
 * spotlight is off on touch screens and under reduced motion, where no
 * hover exists or motion was declined.
 */
export default function Services({ onPick }: { onPick: () => void }) {
  const spot = (e: React.PointerEvent<HTMLButtonElement>) => {
    if (e.pointerType !== 'mouse') return;
    const r = e.currentTarget.getBoundingClientRect();
    e.currentTarget.style.setProperty('--mx', `${e.clientX - r.left}px`);
    e.currentTarget.style.setProperty('--my', `${e.clientY - r.top}px`);
  };
  const spotOff = (e: React.PointerEvent<HTMLButtonElement>) => {
    e.currentTarget.style.removeProperty('--mx');
    e.currentTarget.style.removeProperty('--my');
  };

  return (
    <section id="services" aria-labelledby="services-title" className="scroll-mt-[68px] border-t border-home-fg/10 bg-home-bg">
      <div className="mx-auto flex max-w-[1312px] flex-col gap-[clamp(32px,4vw,48px)] px-[clamp(20px,5vw,48px)] py-[clamp(72px,9vw,128px)]">
        <SectionHeading
          eyebrow="01 — Services"
          title="What we do"
          id="services-title"
          note="Three disciplines, one team — so the cloud, the security and the code are designed together."
        />
        <ul className="m-0 list-none border-t border-home-fg p-0">
          {SERVICES.map((s, i) => (
            <Reveal as="li" key={s.n} index={i + 1}>
              <button
                type="button"
                onClick={onPick}
                onPointerMove={spot}
                onPointerLeave={spotOff}
                aria-label={`${s.title}: ${s.desc} Contact us`}
                className="home-spotlight flex w-full cursor-pointer flex-wrap items-center gap-x-[clamp(20px,3vw,48px)] gap-y-4 border-b border-home-fg/16 px-[clamp(4px,1.5vw,20px)] py-[clamp(24px,3vw,36px)] text-left text-home-fg transition-colors duration-300 hover:bg-home-surface"
              >
                <span className="flex-[0_0_56px] font-mono text-sm leading-none font-medium text-home-accent-text">{s.n}</span>
                <span className="flex flex-[1_1_280px] flex-col gap-2.5">
                  <span className="text-home-title font-semibold">{s.title}</span>
                  <span className="font-mono text-home-meta font-medium tracking-[0.14em] text-home-fg/60 uppercase">{s.tags}</span>
                </span>
                <span className="flex-[1.3_1_300px] text-base leading-[1.6] text-pretty text-home-fg/72">{s.desc}</span>
                <span aria-hidden="true" className="flex h-12 flex-[0_0_48px] items-center justify-center rounded-full border border-home-fg/25 text-lg leading-none font-medium">
                  →
                </span>
              </button>
            </Reveal>
          ))}
        </ul>
      </div>
    </section>
  );
}
