import React from 'react';
import { AlertCircle, ArrowDown, ArrowUp, ArrowUpDown, Inbox, Loader2 } from 'lucide-react';

/**
 * Data tables (#28). Presentational only: these pieces render the rows they
 * are given and never filter, sort or paginate. That keeps them ready for a
 * headless table library (#113): its state drives the views, and these pieces
 * draw the result unchanged.
 *
 * - Headers in mono micro-copy, hairline row separators, no heavy borders.
 * - `numeric` cells (IDs, amounts, dates) are mono and right-aligned with
 *   tabular figures, so columns align on the numerals.
 * - Th already takes a sort direction and onSort; Tr takes `selected`. Both
 *   are unused until sorting and bulk actions arrive (#113, #64).
 */

export function Table({
  caption,
  className = '',
  children,
}: {
  /** Visually hidden table caption, read by screen readers. */
  caption?: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest ${className}`}>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left text-sm">
          {caption && <caption className="sr-only">{caption}</caption>}
          {children}
        </table>
      </div>
    </div>
  );
}

export function THead({ children }: { children: React.ReactNode }) {
  return (
    <thead className="border-b border-outline-variant bg-surface-container-low">
      <tr>{children}</tr>
    </thead>
  );
}

export type SortDirection = 'asc' | 'desc' | false;

interface ThProps {
  numeric?: boolean;
  className?: string;
  /** Sorting hook (#113): pass the current direction and a handler to make the header sortable. */
  sort?: SortDirection;
  onSort?: () => void;
  children?: React.ReactNode;
}

const TH = 'px-5 py-3 font-mono text-[11px] font-medium uppercase tracking-[0.08em] text-on-surface-variant whitespace-nowrap';

export function Th({ numeric = false, className = '', sort, onSort, children }: ThProps) {
  const align = numeric ? 'text-right' : 'text-left';
  if (!onSort) {
    return (
      <th scope="col" className={`${TH} ${align} ${className}`}>
        {children}
      </th>
    );
  }
  const Icon = sort === 'asc' ? ArrowUp : sort === 'desc' ? ArrowDown : ArrowUpDown;
  return (
    <th
      scope="col"
      aria-sort={sort === 'asc' ? 'ascending' : sort === 'desc' ? 'descending' : 'none'}
      className={`${TH} ${align} ${className}`}
    >
      <button
        type="button"
        onClick={onSort}
        className={`inline-flex items-center gap-1 rounded uppercase tracking-[0.08em] hover:text-on-surface cursor-pointer ${numeric ? 'flex-row-reverse' : ''}`}
      >
        {children}
        <Icon className={`h-3.5 w-3.5 ${sort ? 'text-on-surface' : 'opacity-50'}`} aria-hidden="true" />
      </button>
    </th>
  );
}

export function TBody({ children }: { children: React.ReactNode }) {
  return <tbody className="divide-y divide-outline-variant">{children}</tbody>;
}

interface TrProps extends React.HTMLAttributes<HTMLTableRowElement> {
  /** Row selection hook (#113, #64). */
  selected?: boolean;
  /** Makes the whole row look clickable; still pass onClick and a keyboard path. */
  interactive?: boolean;
}

export function Tr({ selected = false, interactive = false, className = '', children, ...rest }: TrProps) {
  return (
    <tr
      aria-selected={selected || undefined}
      className={`transition-colors ${selected ? 'bg-surface-container' : ''} ${
        interactive ? 'cursor-pointer hover:bg-surface-container-low' : ''
      } ${className}`}
      {...rest}
    >
      {children}
    </tr>
  );
}

interface TdProps extends React.TdHTMLAttributes<HTMLTableCellElement> {
  /** IDs, amounts, dates: mono, tabular figures, right-aligned. */
  numeric?: boolean;
  /** Mono without right alignment, e.g. a reference in the first column. */
  mono?: boolean;
  muted?: boolean;
}

export function Td({ numeric = false, mono = false, muted = false, className = '', children, ...rest }: TdProps) {
  return (
    <td
      className={`px-5 py-3.5 align-middle ${numeric ? 'text-right font-mono tabular-nums whitespace-nowrap' : ''} ${
        mono ? 'font-mono tabular-nums whitespace-nowrap' : ''
      } ${muted ? 'text-on-surface-variant' : 'text-on-surface'} ${className}`}
      {...rest}
    >
      {children}
    </td>
  );
}

/**
 * The designed empty, loading and error states of a table body (#28). Renders
 * a full-width row, so it goes inside <TBody>.
 */
export function TableState({
  kind,
  colSpan,
  title,
  message,
  action,
}: {
  kind: 'empty' | 'loading' | 'error';
  colSpan: number;
  title?: string;
  message?: string;
  action?: React.ReactNode;
}) {
  const Icon = kind === 'loading' ? Loader2 : kind === 'error' ? AlertCircle : Inbox;
  const defaults = {
    empty: 'Nothing here yet',
    loading: 'Loading...',
    error: 'Could not load this list',
  };
  return (
    <tr>
      <td colSpan={colSpan} className="px-5 py-12">
        <div
          role={kind === 'error' ? 'alert' : 'status'}
          className="flex flex-col items-center gap-2 text-center"
        >
          <Icon
            className={`h-6 w-6 ${kind === 'loading' ? 'animate-spin text-on-surface-variant' : kind === 'error' ? 'text-error' : 'text-on-surface-variant'}`}
            aria-hidden="true"
          />
          <p className={`text-sm font-semibold ${kind === 'error' ? 'text-error' : 'text-on-surface'}`}>
            {title ?? defaults[kind]}
          </p>
          {message && <p className="max-w-sm text-sm text-on-surface-variant">{message}</p>}
          {action && <div className="mt-2">{action}</div>}
        </div>
      </td>
    </tr>
  );
}
