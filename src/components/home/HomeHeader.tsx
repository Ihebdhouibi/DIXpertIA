import { HomeWordmark } from './LogoMark';
import LanguageToggle from '../LanguageToggle';
import { useT, type MessageKey } from '../../i18n';

export type HomeTarget = 'home' | 'services' | 'about' | 'contact';

const NAV: { target: HomeTarget; label: MessageKey }[] = [
  { target: 'home', label: 'home.nav.home' },
  { target: 'services', label: 'home.nav.services' },
  { target: 'about', label: 'home.nav.about' },
  { target: 'contact', label: 'home.nav.contact' },
];

/**
 * Sticky, blurred header (HP-04). The navigation hides below 860px; the
 * wordmark, the FR / EN toggle and "Go to Dashboard" always stay. On a phone
 * the button takes its short label, so all three fit on a 390px screen. The
 * site has no router, so the links are buttons that scroll or switch to the
 * contact page.
 */
export default function HomeHeader({ current, onNavigate, onDashboardClick }: {
  current: 'home' | 'contact';
  onNavigate: (target: HomeTarget) => void;
  onDashboardClick: () => void;
}) {
  const t = useT();
  return (
    <header className="sticky top-0 z-30 border-b border-home-fg/10 bg-home-header backdrop-blur-md">
      <div className="mx-auto flex h-[68px] max-w-[1312px] items-center justify-between gap-3 px-[clamp(20px,5vw,48px)] sm:gap-6">
        <button type="button" onClick={() => onNavigate('home')} aria-label={t('home.nav.homeLink')} className="cursor-pointer">
          <HomeWordmark />
        </button>
        <nav aria-label={t('home.nav.primary')} className="hidden gap-8 text-sm font-medium min-[860px]:flex">
          {NAV.map(({ target, label }) => {
            const active = (target === 'home' && current === 'home') || (target === 'contact' && current === 'contact');
            return (
              <button
                key={target}
                type="button"
                onClick={() => onNavigate(target)}
                aria-current={active ? 'page' : undefined}
                className={`cursor-pointer transition-colors duration-200 ${active ? 'text-home-fg' : 'text-home-fg/66 hover:text-home-fg'}`}
              >
                {t(label)}
              </button>
            );
          })}
        </nav>
        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          <LanguageToggle tone="home" />
          <button
            type="button"
            onClick={onDashboardClick}
            // One name at every width; the short label on phones is part of it.
            aria-label={t('home.nav.dashboard')}
            className="inline-flex h-10 cursor-pointer items-center whitespace-nowrap rounded-lg bg-home-strong px-3 text-sm font-semibold text-home-on-strong transition-colors duration-200 hover:bg-home-strong-hover sm:px-[18px]"
          >
            <span className="sm:hidden">{t('home.nav.dashboardShort')}</span>
            <span className="hidden sm:inline">{t('home.nav.dashboard')}</span>
          </button>
        </div>
      </div>
    </header>
  );
}
