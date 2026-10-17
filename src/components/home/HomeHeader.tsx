import { HomeWordmark } from './LogoMark';

export type HomeTarget = 'home' | 'services' | 'about' | 'contact';

const NAV: { target: HomeTarget; label: string }[] = [
  { target: 'home', label: 'Home' },
  { target: 'services', label: 'Services' },
  { target: 'about', label: 'About' },
  { target: 'contact', label: 'Contact' },
];

/**
 * Sticky, blurred header (HP-04). The navigation hides below 860px; the
 * wordmark and "Go to Dashboard" always stay. The site has no router, so the
 * links are buttons that scroll or switch to the contact page.
 */
export default function HomeHeader({ current, onNavigate, onDashboardClick }: {
  current: 'home' | 'contact';
  onNavigate: (target: HomeTarget) => void;
  onDashboardClick: () => void;
}) {
  return (
    <header className="sticky top-0 z-30 border-b border-home-fg/10 bg-home-header backdrop-blur-md">
      <div className="mx-auto flex h-[68px] max-w-[1312px] items-center justify-between gap-6 px-[clamp(20px,5vw,48px)]">
        <button type="button" onClick={() => onNavigate('home')} aria-label="DI Xpertia, home" className="cursor-pointer">
          <HomeWordmark />
        </button>
        <nav aria-label="Primary" className="hidden gap-8 text-sm font-medium min-[860px]:flex">
          {NAV.map(({ target, label }) => {
            const active = (target === 'home' && current === 'home') || (target === 'contact' && current === 'contact');
            return (
              <button
                key={target}
                type="button"
                onClick={() => onNavigate(target)}
                aria-current={active ? 'page' : undefined}
                className={`cursor-pointer transition-colors duration-200 ${active ? 'text-home-fg' : 'text-home-fg/65 hover:text-home-fg'}`}
              >
                {label}
              </button>
            );
          })}
        </nav>
        <button
          type="button"
          onClick={onDashboardClick}
          className="inline-flex h-10 cursor-pointer items-center whitespace-nowrap rounded-lg bg-home-strong px-[18px] text-sm font-semibold text-home-on-strong transition-colors duration-200 hover:bg-home-strong-hover"
        >
          Go to Dashboard
        </button>
      </div>
    </header>
  );
}
