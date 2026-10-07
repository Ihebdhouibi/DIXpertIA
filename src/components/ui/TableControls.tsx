import React from 'react';
import { ChevronLeft, ChevronRight, Search } from 'lucide-react';
import { Input } from './Field';

/**
 * Controls around a table (#28). All controlled - `value` / `onChange`, no
 * internal state - so a table library's state can drive them later (#113).
 */

// --------------------------------------------------------------- Filters ---

interface FilterPillsProps<T extends string> {
  /** Accessible name of the group, e.g. "Filter by status". */
  label: string;
  options: readonly T[];
  value: NoInfer<T>;
  // NoInfer: T comes from `options` only, so a state setter typed with the
  // option union is accepted instead of widening T to string.
  onChange: (value: NoInfer<T>) => void;
  /** Visible label before the pills; defaults to none. */
  showLabel?: boolean;
  renderOption?: (option: T) => React.ReactNode;
}

/** Single-choice filter: ink for the selected pill, paper with a hairline for the rest. */
export function FilterPills<T extends string>({
  label,
  options,
  value,
  onChange,
  showLabel = false,
  renderOption,
}: FilterPillsProps<T>) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {showLabel && (
        <span className="font-mono text-[11px] font-medium uppercase tracking-[0.08em] text-on-surface-variant">
          {label}
        </span>
      )}
      <div role="radiogroup" aria-label={label} className="flex flex-wrap gap-1.5">
        {options.map((option) => {
          const selected = option === value;
          return (
            <button
              key={option}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => onChange(option)}
              className={`h-8 rounded-full border px-3.5 text-xs font-semibold transition-colors cursor-pointer ${
                selected
                  ? 'border-primary bg-primary text-on-primary'
                  : 'border-outline-variant bg-surface-container-lowest text-on-surface hover:bg-surface-container-low'
              }`}
            >
              {renderOption ? renderOption(option) : option}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- Search ---

export function SearchField({
  label,
  value,
  onChange,
  placeholder,
  className = '',
}: {
  /** Accessible name; the field shows a placeholder, not a visible label. */
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}) {
  return (
    <div className={`w-full sm:w-72 ${className}`}>
      <Input
        type="search"
        icon={Search}
        aria-label={label}
        placeholder={placeholder ?? label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

// ------------------------------------------------------------ Pagination ---

interface PaginationProps {
  /** 1-based current page. */
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  /** What is being counted, e.g. "invoices". */
  noun?: string;
}

export function Pagination({ page, pageSize, total, onPageChange, noun = 'results' }: PaginationProps) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const first = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);
  const button =
    'flex h-8 min-w-8 items-center justify-center rounded-lg px-2 font-mono text-xs transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed';

  return (
    <nav
      aria-label="Pagination"
      className="flex flex-wrap items-center justify-between gap-3 border-t border-outline-variant px-5 py-3"
    >
      <p className="text-sm text-on-surface-variant">
        <span className="font-mono tabular-nums text-on-surface">
          {first}-{last}
        </span>{' '}
        of <span className="font-mono tabular-nums text-on-surface">{total}</span> {noun}
      </p>
      <div className="flex items-center gap-1">
        <button
          type="button"
          className={`${button} text-on-surface-variant hover:bg-surface-container`}
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          aria-label="Previous page"
        >
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
        </button>
        {Array.from({ length: pages }, (_, i) => i + 1).map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => onPageChange(n)}
            aria-current={n === page ? 'page' : undefined}
            aria-label={`Page ${n}`}
            className={`${button} ${
              n === page ? 'bg-primary text-on-primary' : 'text-on-surface hover:bg-surface-container'
            }`}
          >
            {n}
          </button>
        ))}
        <button
          type="button"
          className={`${button} text-on-surface-variant hover:bg-surface-container`}
          onClick={() => onPageChange(page + 1)}
          disabled={page >= pages}
          aria-label="Next page"
        >
          <ChevronRight className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </nav>
  );
}

// ---------------------------------------------------------------- Toolbar ---

/** The row above a table: filters on one side, search and actions on the other. */
export function TableToolbar({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4 md:flex-row md:items-center md:justify-between">
      {children}
    </div>
  );
}
