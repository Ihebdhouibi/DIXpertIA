import { useEffect, useState } from 'react';
import { LogoMark } from './LogoMark';
import { useReducedMotion } from './motion';

/**
 * An illustrative console beside the hero (HP-06): three disciplines fill in
 * turn while the log walks through how we work. It reads nothing: it is a
 * loop. That is why it says "how we work" with no clock. The handoff's
 * "ops / live" and a live clock could pass for real telemetry of our systems
 * (decided on #165). Always dark, in both themes.
 */

const TICK_MS = 1100;
const TICKS = 10;
/** The finished picture: every row done, the last log lines shown. */
const FINISHED = TICKS - 1;

const ROWS = [
  { label: 'Cloud', working: 'provisioning', done: 'healthy' },
  { label: 'Security', working: 'scanning', done: 'protected' },
  { label: 'Software', working: 'building', done: 'shipped' },
];
const LOG = [
  '› plan infrastructure',
  '› provision network … ok',
  '› harden access policies … ok',
  '› run test suite … ok',
  '› deploy release … ok',
  '› monitor · all systems nominal',
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
  const reduced = useReducedMotion();
  const tick = useTick(reduced);
  const shown = LOG.slice(0, Math.max(1, Math.min(LOG.length, tick))).slice(-4);

  return (
    <div
      role="img"
      aria-label="Illustration of how we work: plan, provision, harden, test, deploy and monitor"
      className="flex flex-col gap-[18px] rounded-2xl border border-home-panel-border bg-home-panel px-[22px] pt-5 pb-[22px] text-paper shadow-[0_30px_60px_-30px_var(--color-home-panel-shadow)]"
    >
      <div className="flex items-center gap-2 font-mono text-home-meta leading-none font-medium tracking-[0.14em] text-paper/60 uppercase">
        <LogoMark className="h-[13px] w-[18px]" blockClass="fill-lime" />
        how we work
      </div>

      <div className="flex flex-col gap-3.5">
        {ROWS.map((row, i) => {
          const progress = Math.max(0, Math.min(1, (tick - i * 2) / 2));
          const done = progress >= 1;
          return (
            <div key={row.label} className="grid grid-cols-[92px_minmax(0,1fr)_96px] items-center gap-3.5 font-mono text-caption leading-none font-medium">
              <span className="tracking-[0.12em] text-paper uppercase">{row.label}</span>
              <span className="h-1 overflow-hidden rounded-[2px] bg-paper/12">
                <span
                  className="block h-full origin-left bg-lime transition-transform duration-900 ease-home-out"
                  style={{ transform: `scaleX(${progress})` }}
                />
              </span>
              <span className={`text-right ${done ? 'text-lime' : 'text-paper/60'}`}>
                {done ? `● ${row.done}` : progress > 0 ? `○ ${row.working}` : '○ queued'}
              </span>
            </div>
          );
        })}
      </div>

      <div className="flex min-h-[104px] flex-col gap-2 border-t border-paper/10 pt-3.5 font-mono text-caption leading-[1.4] text-paper/70">
        {shown.map((line) => (
          <span key={line}>{line}</span>
        ))}
      </div>
    </div>
  );
}
