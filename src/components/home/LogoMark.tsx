/**
 * The DI Xpertia mark, prompt and block cursor, drawn inline so it takes the
 * page's colours (design/homepage-v2/README.md, "Assets"). The stroke follows
 * the text colour; the block takes `blockClass`: accented text on the page
 * (Lime Deep on paper, lime on ink), always lime on the dark panels.
 */
export function LogoMark({ className = 'h-[22px] w-[30px]', blockClass = 'fill-home-accent-text' }: {
  className?: string;
  blockClass?: string;
}) {
  return (
    <svg viewBox="12 18 38 28" className={className} aria-hidden="true" focusable="false">
      <path d="M17 23 L27 32 L17 41" fill="none" stroke="currentColor" strokeWidth="5.5"
        strokeLinecap="round" strokeLinejoin="round" />
      <rect x="34" y="22" width="13" height="20" rx="1.5" className={blockClass} />
    </svg>
  );
}

/** The mark and "DI Xpertia", as the header and the footer show them. */
export function HomeWordmark() {
  return (
    <span className="flex items-center gap-2.5">
      <LogoMark />
      <span className="whitespace-nowrap text-[19px] font-bold leading-none tracking-[-0.02em]">
        DI{' '}
        <span className="font-mono text-[18px] font-medium tracking-[-0.03em] text-home-accent-text">Xpertia</span>
      </span>
    </span>
  );
}
