import { useState, useRef } from 'react';
import { Menu, X } from 'lucide-react';
import { HomeWordmark } from './LogoMark';
import LanguageToggle from '../LanguageToggle';
import { useT, type MessageKey } from '../../i18n';
import { useDismiss } from '../ui/useDismiss';

export type HomeTarget = 'home' | 'services' | 'about' | 'contact';

const NAV: { target: HomeTarget; label: MessageKey }[] = [
  { target: 'home', label: 'home.nav.home' },
  { target: 'services', label: 'home.nav.services' },
  { target: 'about', label: 'home.nav.about' },
  { target: 'contact', label: 'home.nav.contact' },
];

/**
 * Sticky, blurred header (HP-04). The navigation moves into a hamburger menu
 * below 860px. On mobile, the FR/EN toggle is moved inside the menu to save
 * space and prevent horizontal scrolling. The site has no router, so the links
 * are buttons that scroll or switch to the contact page.
 */
export default function HomeHeader({ current, onNavigate, onDashboardClick }: {
  current: 'home' | 'contact';
  onNavigate: (target: HomeTarget) => void;
  onDashboardClick: () => void;
}) {
  const t = useT();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Reuse the app's useDismiss hook for Escape, click-outside, and focus return
  useDismiss(menuRef, isMenuOpen, () => {
    setIsMenuOpen(false);
    menuButtonRef.current?.focus();
  });

  const handleNavigate = (target: HomeTarget) => {
    onNavigate(target);
    setIsMenuOpen(false);
  };

  return (
    <header className="sticky top-0 z-30 border-b border-home-fg/10 bg-home-header backdrop-blur-md">
      <div className="mx-auto flex h-[68px] max-w-[1312px] items-center justify-between gap-3 px-[clamp(20px,5vw,48px)] sm:gap-6">

        <button type="button" onClick={() => handleNavigate('home')} aria-label={t('home.nav.homeLink')} className="cursor-pointer">
          <HomeWordmark />
        </button>

        {/* Desktop Navigation */}
        <nav aria-label={t('home.nav.primary')} className="hidden gap-8 text-sm font-medium min-[860px]:flex">
          {NAV.map(({ target, label }) => {
            const active = (target === 'home' && current === 'home') || (target === 'contact' && current === 'contact');
            return (
              <button
                key={target}
                type="button"
                onClick={() => handleNavigate(target)}
                aria-current={active ? 'page' : undefined}
                className={`cursor-pointer transition-colors duration-200 ${active ? 'text-home-fg' : 'text-home-fg/66 hover:text-home-fg'}`}
              >
                {t(label)}
              </button>
            );
          })}
        </nav>

        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          {/* Hide LanguageToggle on mobile to save space; it goes in the menu */}
          <div className="hidden min-[860px]:block">
            <LanguageToggle tone="home" />
          </div>

          <button
            type="button"
            onClick={onDashboardClick}
            aria-label={t('home.nav.dashboard')}
            className="inline-flex h-10 cursor-pointer items-center whitespace-nowrap rounded-lg bg-home-strong px-3 text-sm font-semibold text-home-on-strong transition-colors duration-200 hover:bg-home-strong-hover sm:px-[18px]"
          >
            <span className="sm:hidden">{t('home.nav.dashboardShort')}</span>
            <span className="hidden sm:inline">{t('home.nav.dashboard')}</span>
          </button>

          {/* Mobile Menu Button */}
          <button
            ref={menuButtonRef}
            type="button"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            aria-expanded={isMenuOpen}
            aria-controls="mobile-menu"
            aria-label={isMenuOpen ? t('common.nav.close') : t('common.nav.open')}
            className="flex h-10 w-10 cursor-pointer items-center justify-center rounded-lg text-home-fg hover:bg-home-fg/5 min-[860px]:hidden"
          >
            {isMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {isMenuOpen && (
        <div
          id="mobile-menu"
          ref={menuRef}
          className="absolute left-0 top-full w-full border-b border-home-fg/10 bg-home-header shadow-lg backdrop-blur-md min-[860px]:hidden"
        >
          <nav aria-label={t('home.nav.primary')} className="flex flex-col px-[clamp(20px,5vw,48px)] py-4 gap-4 text-base font-medium">
            {NAV.map(({ target, label }) => {
              const active = (target === 'home' && current === 'home') || (target === 'contact' && current === 'contact');
              return (
                <button
                  key={target}
                  type="button"
                  onClick={() => handleNavigate(target)}
                  aria-current={active ? 'page' : undefined}
                  className={`text-left cursor-pointer transition-colors duration-200 ${
                    active ? 'text-home-fg font-bold' : 'text-home-fg/66 hover:text-home-fg'
                  }`}
                >
                  {t(label)}
                </button>
              );
            })}
          </nav>
          {/* Language Toggle moved into the mobile menu */}
          <div className="px-[clamp(20px,5vw,48px)] pb-4">
            <LanguageToggle tone="home" />
          </div>
        </div>
      )}
    </header>
  );
}
