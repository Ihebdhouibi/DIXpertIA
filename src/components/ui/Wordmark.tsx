import React from 'react';

/**
 * The DI Xpertia wordmark: the mark (prompt + block cursor) and "DI Xpertia",
 * as on the brand palette sheet (#27). One component for the homepage, the
 * auth screens and the sidebar, which each used to re-code it.
 *
 * Follows the theme: the mark for paper grounds in light, the mark for ink
 * grounds in dark, and "Xpertia" in Lime Deep on paper / Signal Lime on ink
 * (the `secondary` role). On the unthemed public homepage it stays on paper.
 *
 * Clear space: the kit asks for at least the cursor's height around the logo,
 * which is 20/64 of the mark - give the wrapper that much padding.
 */
interface WordmarkProps {
  size?: 'sm' | 'md';
  className?: string;
}

const SIZES = {
  sm: { mark: 'w-7 h-7', text: 'text-lg' },
  md: { mark: 'w-8 h-8', text: 'text-xl' },
};

export default function Wordmark({ size = 'md', className = '' }: WordmarkProps) {
  const s = SIZES[size];
  return (
    <span className={`inline-flex items-center gap-2 ${className}`} role="img" aria-label="DI Xpertia">
      <img src="/brand/mark-dark.svg" alt="" className={`${s.mark} dark:hidden`} />
      <img src="/brand/mark-light.svg" alt="" className={`${s.mark} hidden dark:block`} />
      <span className={`${s.text} font-bold tracking-[-0.02em] text-on-surface`} aria-hidden="true">
        DI <span className="font-mono font-medium text-secondary">Xpertia</span>
      </span>
    </span>
  );
}
