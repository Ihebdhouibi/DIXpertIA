import React from 'react';

/**
 * Initials avatar (#28): mono initials on a neutral ground. Replaces the lime
 * circles in the team and invoice tables - lime is the one accent per view,
 * not a decoration for every row.
 */
const SIZES = {
  sm: 'h-8 w-8 text-[11px]',
  md: 'h-10 w-10 text-xs',
  lg: 'h-12 w-12 text-sm',
};

export default function Avatar({
  name,
  size = 'md',
  shape = 'circle',
}: {
  /** Full name (or company name); the first letters of the first two words are shown. */
  name: string;
  size?: keyof typeof SIZES;
  /** Square for companies (clients), circle for people. */
  shape?: 'circle' | 'square';
}) {
  const initials =
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((w) => w[0]?.toUpperCase())
      .join('') || '?';
  return (
    <span
      aria-hidden="true"
      className={`inline-flex shrink-0 items-center justify-center bg-surface-container-high font-mono font-medium text-on-surface ${
        SIZES[size]
      } ${shape === 'circle' ? 'rounded-full' : 'rounded-md'}`}
    >
      {initials}
    </span>
  );
}
