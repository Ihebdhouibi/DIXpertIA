import { useT } from '../../i18n';

/**
 * "Skip to content" (#31, WCAG 2.4.1): the first stop of the tab order, shown
 * only when focused. Without it a keyboard user crossed the whole sidebar,
 * the bell and the user menu (8 to 10 stops) on every screen before reaching
 * the content. It moves focus to the element with id `targetId`, which needs
 * tabIndex={-1}. It focuses instead of following "#id", so the URL does not
 * change.
 */
export default function SkipLink({ targetId = 'main-content' }: { targetId?: string }) {
  const t = useT();
  return (
    <a
      href={`#${targetId}`}
      onClick={(e) => {
        const target = document.getElementById(targetId);
        if (!target) return;
        e.preventDefault();
        target.focus();
        target.scrollIntoView({ block: 'start' });
      }}
      className="sr-only rounded-lg bg-primary text-sm font-semibold text-on-primary shadow-lg focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[100] focus:px-4 focus:py-2.5"
    >
      {t('common.skipToContent')}
    </a>
  );
}
