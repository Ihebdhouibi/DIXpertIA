import { HomeWordmark } from './LogoMark';
import type { HomeTarget } from './HomeHeader';
import { useT } from '../../i18n';

const HEADING = 'mb-1 font-mono text-home-meta leading-none font-semibold tracking-[0.2em] uppercase';
const LINK = 'cursor-pointer self-start text-left text-home-fg/70 transition-colors duration-200 hover:text-home-fg';

/**
 * The footer (HP-10). Only links to pages that exist: the handoff's
 * "Leadership", "Careers" and "Case studies" are left out until they do
 * (decided on #165). The address and the legal name, DI Xpertia SUARL, are
 * the company's, confirmed by the product owner.
 */
export default function HomeFooter({ onNavigate, onDashboardClick }: {
  onNavigate: (target: HomeTarget) => void;
  onDashboardClick: () => void;
}) {
  const t = useT();
  return (
    <footer className="bg-home-bg text-home-fg">
      <div className="mx-auto grid max-w-[1312px] grid-cols-[repeat(auto-fit,minmax(min(100%,200px),1fr))] gap-x-8 gap-y-10 px-[clamp(20px,5vw,48px)] pt-14 pb-10">
        <div className="flex flex-col gap-4">
          <HomeWordmark />
          <p className="m-0 font-mono text-home-meta leading-[1.6] font-medium tracking-[0.16em] text-home-fg/66 uppercase">
            {t('home.footer.taglineLine1')}
            <br />
            {t('home.footer.taglineLine2')}
          </p>
        </div>
        <nav aria-label={t('home.footer.company')} className="flex flex-col gap-3 text-sm leading-[1.4]">
          <span className={HEADING}>{t('home.footer.company')}</span>
          <button type="button" onClick={() => onNavigate('about')} className={LINK}>{t('home.footer.aboutUs')}</button>
        </nav>
        <nav aria-label={t('home.footer.links')} className="flex flex-col gap-3 text-sm leading-[1.4]">
          <span className={HEADING}>{t('home.footer.links')}</span>
          <button type="button" onClick={() => onNavigate('services')} className={LINK}>{t('home.nav.services')}</button>
          <button type="button" onClick={onDashboardClick} className={LINK}>{t('home.nav.dashboard')}</button>
        </nav>
        <div className="flex flex-col gap-3 text-sm leading-[1.5]">
          <span className={HEADING}>{t('home.footer.contact')}</span>
          <button type="button" onClick={() => onNavigate('contact')} className={LINK}>{t('home.footer.support')}</button>
          <button type="button" onClick={() => onNavigate('contact')} className={LINK}>{t('home.footer.sales')}</button>
          <address className="text-home-fg/70 not-italic">
            Rue de Pasteur, Dar Chaabane El Fehri
            <br />
            {t('home.footer.city')}
          </address>
        </div>
      </div>
      <div className="mx-auto max-w-[1312px] border-t border-home-fg/8 px-[clamp(20px,5vw,48px)] pt-5 pb-8 text-[13px] leading-[1.4] text-home-fg/62">
        {t('home.footer.rights', { year: new Date().getFullYear() })}
      </div>
    </footer>
  );
}
