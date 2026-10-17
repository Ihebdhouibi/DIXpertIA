import { useEffect, useState } from 'react';
import { LogoMark } from './LogoMark';
import { useReducedMotion } from './motion';
import { useT, type MessageKey } from '../../i18n';

/**
 * An illustrative console beside the hero (HP-06): three disciplines fill in
 * turn while the log walks through how we work. It reads nothing: it is a
 * loop. That is why it says "how we work" with no clock. The handoff's
 * "ops / live" and a live clock could pass for real telemetry of our systems
 * (decided on #165). Always dark, in both themes. Its words follow the
 * language; the loop only counts ticks, so a switch carries on in the new
 * language at the same step, never mixing the two.
 */

const TICK_MS = 1100;
const TICKS = 10;
/** The finished picture: every row done, the last log lines shown. */
const FINISHED = TICKS - 1;

const ROWS: { label: MessageKey; working: MessageKey; done: MessageKey }[] = [
  { label: 'home.console.cloud', working: 'home.console.cloudWorking', done: 'home.console.cloudDone' },
  { label: 'home.console.security', working: 'home.console.securityWorking', done: 'home.console.securityDone' },
  { label: 'home.console.software', working: 'home.console.softwareWorking', done: 'home.console.softwareDone' },
];
const LOG: MessageKey[] = [
  'home.console.log1',
  'home.console.log2',
  'home.console.log3',
  'home.console.log4',
  'home.console.log5',
  'home.console.log6',
];

/** The tick, advancing while the page is visible; frozen at FINISHED under reduced motion. */
function useTick(reduced: boolean) {
  const [tick, setTick] = useState(reduced ? FINISHED : 0);
  useEffect(() => {
    if (reduced) {
      setTick(FINISHED);
      return;
    }
    let timer: number | undefined;
    const start = () => {
      if (timer === undefined) timer = window.setInterval(() => setTick((t) => (t + 1) % TICKS), TICK_MS);
    };
    const stop = () => {
      window.clearInterval(timer);
      timer = undefined;
    };
    // A hidden tab does not need a running loop.
    const onVisibility = () => (document.hidden ? stop() : start());
    onVisibility();
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      stop();
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [reduced]);
  return tick;
}

export default function HowWeWorkConsole() {
  const t = useT();
  const reduced = useReducedMotion();
  const tick = useTick(reduced);
  const shown = LOG.slice(0, Math.max(1, Math.min(LOG.length, tick))).slice(-4);

  return (
    <div
      role="img"
      aria-label={t('home.console.label')}
      className="flex flex-col gap-[18px] rounded-2xl border border-home-panel-border bg-home-panel px-[22px] pt-5 pb-[22px] text-paper shadow-[0_30px_60px_-30px_var(--color-home-panel-shadow)]"
    >
      <div className="flex items-center gap-2 font-mono text-home-meta leading-none font-medium tracking-[0.14em] text-paper/60 uppercase">
        <LogoMark className="h-[13px] w-[18px]" blockClass="fill-lime" />
        {t('home.console.title')}
      </div>

      <div className="flex flex-col gap-3.5">
        {ROWS.map((row, i) => {
          const progress = Math.max(0, Math.min(1, (tick - i * 2) / 2));
          const done = progress >= 1;
          return (
            <div key={row.label} className="grid grid-cols-[92px_minmax(0,1fr)_96px] items-center gap-3.5 font-mono text-caption leading-none font-medium">
              <span className="tracking-[0.12em] text-paper uppercase">{t(row.label)}</span>
              <span className="h-1 overflow-hidden rounded-[2px] bg-paper/12">
                <span
                  className="block h-full origin-left bg-lime transition-transform duration-900 ease-home-out"
                  style={{ transform: `scaleX(${progress})` }}
                />
              </span>
              <span className={`text-right ${done ? 'text-lime' : 'text-paper/60'}`}>
                {done ? `● ${t(row.done)}` : `○ ${t(progress > 0 ? row.working : 'home.console.queued')}`}
              </span>
            </div>
          );
        })}
      </div>

      <div className="flex min-h-[104px] flex-col gap-2 border-t border-paper/10 pt-3.5 font-mono text-caption leading-[1.4] text-paper/70">
        {shown.map((line) => (
          <span key={line}>{t(line)}</span>
        ))}
      </div>
    </div>
  );
}
