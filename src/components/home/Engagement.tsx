import React, { useRef, useState } from 'react';
import { Reveal, useReducedMotion } from './motion';
import { SectionHeading } from './Services';
import { useT, type MessageKey } from '../../i18n';

/** Who leads a phase: 0 your team, 0.5 joint, 1 DI Xpertia. */
type Lead = 0 | 0.5 | 1;
const LEAD_LABEL: Record<Lead, MessageKey> = {
  0: 'home.engage.lead.team',
  0.5: 'home.engage.lead.joint',
  1: 'home.engage.lead.us',
};

type Phase = 'scope' | 'build' | 'launch' | 'run';
const PHASE_LABEL: Record<Phase, MessageKey> = {
  scope: 'home.engage.phase.scope',
  build: 'home.engage.phase.build',
  launch: 'home.engage.phase.launch',
  run: 'home.engage.phase.run',
};

/** Each model's words live under home.engage.<id>.* in ../../i18n/messages/home.ts. */
const MODELS: {
  n: string;
  id: 'project' | 'extension' | 'managed';
  phases: [Phase, Lead][];
}[] = [
  { n: '01', id: 'project', phases: [['scope', 0.5], ['build', 1], ['launch', 1], ['run', 0]] },
  { n: '02', id: 'extension', phases: [['scope', 0], ['build', 0.5], ['launch', 0.5], ['run', 0]] },
  { n: '03', id: 'managed', phases: [['scope', 0.5], ['build', 0.5], ['launch', 1], ['run', 1]] },
];

const ITEMS = ['item1', 'item2', 'item3', 'item4'] as const;
type ModelText = 'name' | 'headline' | 'desc' | 'fit' | 'footnote' | (typeof ITEMS)[number];
/** Typed: every model x part combination must exist in the catalog, or tsc fails. */
const textKey = (id: (typeof MODELS)[number]['id'], part: ModelText): MessageKey => `home.engage.${id}.${part}` as const;

const tabId = (i: number) => `engage-tab-${i}`;

/**
 * "Ways to work with us" (HP-08): three engagement models as WAI-ARIA tabs.
 * Arrow keys move between them, Home and End jump, and only the active tab
 * is in the tab order (roving tabindex). The panel fades in on a change and
 * the phase bars slide to the new split; both stay still under reduced
 * motion.
 */
export default function Engagement() {
  const t = useT();
  const [active, setActive] = useState(0);
  const reduced = useReducedMotion();
  const panel = useRef<HTMLDivElement>(null);
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  const model = MODELS[active];
  const text = (part: ModelText) => t(textKey(model.id, part));

  const select = (i: number, focus = false) => {
    if (focus) tabs.current[i]?.focus();
    if (i === active) return;
    setActive(i);
    if (!reduced) {
      panel.current?.animate(
        [{ opacity: 0, transform: 'translateY(10px)' }, { opacity: 1, transform: 'none' }],
        { duration: 450, easing: 'cubic-bezier(0.2, 0.7, 0.2, 1)' },
      );
    }
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    const last = MODELS.length - 1;
    const keys: Record<string, number> = {
      ArrowRight: active === last ? 0 : active + 1,
      ArrowDown: active === last ? 0 : active + 1,
      ArrowLeft: active === 0 ? last : active - 1,
      ArrowUp: active === 0 ? last : active - 1,
      Home: 0,
      End: last,
    };
    const next = keys[e.key];
    if (next === undefined) return;
    e.preventDefault();
    select(next, true);
  };

  return (
    <section id="engage" aria-labelledby="engage-title" className="border-y border-home-fg/10 bg-home-surface">
      <div className="mx-auto flex max-w-[1312px] flex-col gap-[clamp(32px,4vw,48px)] px-[clamp(20px,5vw,48px)] py-[clamp(72px,9vw,120px)]">
        <SectionHeading
          eyebrow={t('home.engage.eyebrow')}
          title={t('home.engage.title')}
          id="engage-title"
          note={t('home.engage.note')}
        />

        <Reveal index={1}>
          <div
            role="tablist"
            aria-label={t('home.engage.tablist')}
            onKeyDown={onKeyDown}
            className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,220px),1fr))] gap-2 rounded-[14px] border border-home-fg/10 bg-home-bg p-1.5"
          >
            {MODELS.map((m, i) => {
              const selected = i === active;
              return (
                <button
                  key={m.n}
                  ref={(el) => {
                    tabs.current[i] = el;
                  }}
                  type="button"
                  role="tab"
                  id={tabId(i)}
                  aria-selected={selected}
                  aria-controls="engage-panel"
                  tabIndex={selected ? 0 : -1}
                  onClick={() => select(i)}
                  className={`flex min-h-14 cursor-pointer items-center gap-3 rounded-[10px] px-[18px] py-3 text-left text-base leading-[1.2] font-semibold transition-colors duration-250 ${
                    selected ? 'bg-home-tab text-home-on-tab' : 'bg-transparent text-home-fg'
                  }`}
                >
                  <span className={`font-mono text-caption leading-none font-medium ${selected ? 'text-home-tab-number' : 'text-home-accent-text'}`}>
                    {m.n}
                  </span>
                  {t(textKey(m.id, 'name'))}
                </button>
              );
            })}
          </div>
        </Reveal>

        <div
          ref={panel}
          id="engage-panel"
          role="tabpanel"
          aria-labelledby={tabId(active)}
          className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,420px),1fr))] items-start gap-[clamp(28px,4vw,64px)]"
        >
          <div className="flex flex-col gap-[22px]">
            <h3 className="m-0 text-home-subhead font-semibold text-balance">{text('headline')}</h3>
            <p className="m-0 max-w-[33.33em] text-[17px] leading-[1.6] text-pretty text-home-fg/72">{text('desc')}</p>
            <ul className="m-0 flex list-none flex-col border-t border-home-fg/14 p-0">
              {ITEMS.map((item) => (
                <li key={item} className="flex items-baseline gap-3.5 border-b border-home-fg/10 py-3.5 text-[15px] leading-[1.5]">
                  <span aria-hidden="true" className="h-2.5 w-1.5 flex-none -translate-y-px rounded-[1px] bg-home-accent-text" />
                  {text(item)}
                </li>
              ))}
            </ul>
            <p className="m-0 font-mono text-caption leading-[1.6] font-medium tracking-[0.06em] text-home-fg/70">
              <span className="tracking-[0.16em] text-home-accent-text">{t('home.engage.bestFor')}</span>
              {text('fit')}
            </p>
          </div>

          <div
            role="img"
            aria-label={t('home.engage.chartLabel', {
              model: text('name'),
              phases: model.phases.map(([phase, lead]) => `${t(PHASE_LABEL[phase])}, ${t(LEAD_LABEL[lead])}`).join('; '),
              footnote: text('footnote'),
            })}
            className="flex flex-col gap-5 rounded-2xl border border-home-panel-border bg-home-panel p-6 text-paper"
          >
            <div className="flex justify-between gap-3 font-mono text-home-meta leading-none font-medium tracking-[0.14em] text-paper/60 uppercase">
              <span>{t('home.engage.whoLeads')}</span>
              <span className="flex gap-3.5">
                <span className="flex items-center gap-1.5">
                  <span className="size-2.5 rounded-[2px] bg-lime" />
                  DI Xpertia
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="size-2.5 rounded-[2px] border border-paper/60" />
                  {t('home.engage.legendTeam')}
                </span>
              </span>
            </div>
            <div className="flex flex-col gap-3.5">
              {model.phases.map(([phase, lead]) => (
                <div key={phase} className="grid grid-cols-[96px_minmax(0,1fr)] items-center gap-3.5 font-mono text-caption leading-none font-medium">
                  <span className="tracking-[0.12em] uppercase">{t(PHASE_LABEL[phase])}</span>
                  <span className="relative h-7 overflow-hidden rounded-md border border-paper/22">
                    <span
                      className="absolute inset-0 origin-left bg-lime transition-transform duration-700 ease-home-out"
                      style={{ transform: `scaleX(${lead})` }}
                    />
                    {/* Ink on lime, paper on the empty bar: each label stays AA. */}
                    <span className={`absolute inset-0 flex items-center px-2.5 text-home-meta leading-none ${lead > 0 ? 'text-ink' : 'text-paper'}`}>
                      {t(LEAD_LABEL[lead])}
                    </span>
                  </span>
                </div>
              ))}
            </div>
            <p className="m-0 border-t border-paper/10 pt-3.5 text-[13px] leading-[1.5] text-paper/72">{text('footnote')}</p>
          </div>
        </div>
      </div>
    </section>
  );
}
