import React, { useId } from 'react';
import { AlertCircle } from 'lucide-react';

/**
 * Form fields (#29): a label in mono micro-copy, the control, then a hint or
 * an error. The label, hint and error are wired to the control with
 * htmlFor / aria-describedby / aria-invalid, so screen readers announce them.
 */

const CONTROL =
  'w-full bg-surface-container-lowest text-on-surface text-sm border rounded-lg ' +
  'placeholder:text-on-surface-variant transition-colors hover:border-outline ' +
  'disabled:opacity-50 disabled:cursor-not-allowed';

interface FieldProps {
  label: string;
  hint?: string;
  error?: string;
  /** Element shown at the right of the label, e.g. a "Forgot?" link. */
  labelAside?: React.ReactNode;
  className?: string;
  children: (control: { id: string; describedBy?: string; invalid: boolean }) => React.ReactNode;
}

export function Field({ label, hint, error, labelAside, className = '', children }: FieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [errorId, hintId].filter(Boolean).join(' ') || undefined;

  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <div className="flex items-center justify-between gap-2">
        <label
          htmlFor={id}
          className="font-mono text-[11px] font-medium uppercase tracking-[0.08em] text-on-surface-variant"
        >
          {label}
        </label>
        {labelAside}
      </div>
      {children({ id, describedBy, invalid: Boolean(error) })}
      {error ? (
        <p id={errorId} className="flex items-center gap-1.5 text-xs font-medium text-error">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
          {error}
        </p>
      ) : (
        hint && (
          <p id={hintId} className="text-xs text-on-surface-variant">
            {hint}
          </p>
        )
      )}
    </div>
  );
}

function borderFor(invalid?: boolean) {
  return invalid ? 'border-error' : 'border-outline-variant';
}

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
  /** Icon shown inside the field, on the left. */
  icon?: React.ComponentType<{ className?: string }>;
}

export function Input({ invalid, icon: Icon, className = '', ...rest }: InputProps) {
  const input = (
    <input
      aria-invalid={invalid || undefined}
      className={`${CONTROL} ${borderFor(invalid)} h-10 ${Icon ? 'pl-10 pr-3' : 'px-3'} ${className}`}
      {...rest}
    />
  );
  if (!Icon) return input;
  return (
    <div className="relative">
      <Icon className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-on-surface-variant" />
      {input}
    </div>
  );
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  invalid?: boolean;
}

export function Select({ invalid, className = '', children, ...rest }: SelectProps) {
  return (
    <select
      aria-invalid={invalid || undefined}
      className={`${CONTROL} ${borderFor(invalid)} h-10 px-3 cursor-pointer ${className}`}
      {...rest}
    >
      {children}
    </select>
  );
}

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean;
}

export function Textarea({ invalid, className = '', ...rest }: TextareaProps) {
  return (
    <textarea
      aria-invalid={invalid || undefined}
      className={`${CONTROL} ${borderFor(invalid)} px-3 py-2.5 resize-y ${className}`}
      {...rest}
    />
  );
}

/** Form-level message (e.g. a failed request), above the fields. */
export function FormAlert({ children }: { children: React.ReactNode }) {
  return (
    <div
      role="alert"
      className="flex items-start gap-2 rounded-lg border border-error/20 bg-error-container px-3 py-2.5 text-sm font-medium text-on-error-container"
    >
      <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" aria-hidden="true" />
      <span>{children}</span>
    </div>
  );
}
