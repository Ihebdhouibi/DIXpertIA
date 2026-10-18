import React from 'react';
import { Loader2 } from 'lucide-react';

/**
 * The app's button vocabulary (#29).
 *
 * - primary   ink fill (paper in dark). The workhorse.
 * - accent    Signal Lime fill, ink label. At most one per view: the single
 *             most important action. Lime never carries light text.
 * - secondary surface fill, hairline border.
 * - ghost     no fill, for tertiary actions.
 * - danger    the danger tone, for destructive actions.
 *
 * Focus uses the global :focus-visible ring from index.css.
 */
export type ButtonVariant = 'primary' | 'accent' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

const VARIANTS: Record<ButtonVariant, string> = {
  primary: 'bg-primary text-on-primary hover:bg-primary/90 active:bg-primary/80',
  accent: 'bg-lime text-ink hover:brightness-95 active:brightness-90',
  secondary:
    'bg-surface-container-lowest text-on-surface border border-outline-variant hover:bg-surface-container active:bg-surface-container-high',
  ghost: 'text-on-surface hover:bg-surface-container active:bg-surface-container-high',
  danger: 'bg-error text-on-error hover:bg-error/90 active:bg-error/80',
};

const SIZES: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-xs gap-1.5',
  md: 'h-10 px-4 text-sm gap-2',
  lg: 'h-12 px-6 text-sm gap-2',
};

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Shows a spinner, disables the button and sets aria-busy. */
  loading?: boolean;
  fullWidth?: boolean;
}

export default function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  fullWidth = false,
  disabled,
  type = 'button',
  className = '',
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`inline-flex items-center justify-center rounded-lg font-semibold whitespace-nowrap transition-colors select-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${VARIANTS[variant]} ${SIZES[size]} ${fullWidth ? 'w-full' : ''} ${className}`}
      {...rest}
    >
      {loading && <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />}
      {children}
    </button>
  );
}
