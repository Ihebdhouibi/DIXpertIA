import React from 'react';

export type StatusTone = 'success' | 'warning' | 'danger' | 'info' | 'neutral';

// The single place a business status is given a colour. Add new statuses here,
// never as colour classes in a view.
const STATUS_TONES: Record<string, StatusTone> = {
  // Invoices
  Draft: 'neutral',
  Sent: 'info',
  Paid: 'success',
  Overdue: 'danger',
  // Danger, not neutral: a void invoice must not look like a Draft.
  Cancelled: 'danger',
  // Leave requests
  Pending: 'warning',
  Approved: 'success',
  Rejected: 'danger',
  // Projects
  'In Progress': 'info',
  Completed: 'neutral',
  'On Hold': 'warning',
  // Team members and user accounts
  Active: 'success',
  Inactive: 'neutral',
};

/** Tone for a business status; charts and calendars reuse it so colours agree everywhere. */
export function statusTone(status: string): StatusTone {
  return STATUS_TONES[status] ?? 'neutral';
}

// Full class names so Tailwind can see them at build time.
export const TONE_CLASSES: Record<StatusTone, { badge: string; dot: string }> = {
  success: { badge: 'bg-success-container text-success', dot: 'bg-success' },
  warning: { badge: 'bg-warning-container text-warning', dot: 'bg-warning' },
  danger: { badge: 'bg-danger-container text-danger', dot: 'bg-danger' },
  info: { badge: 'bg-info-container text-info', dot: 'bg-info' },
  neutral: { badge: 'bg-neutral-container text-neutral', dot: 'bg-neutral' },
};

interface StatusBadgeProps {
  status: string;
  /** Overrides the mapped tone, for a status that is not in STATUS_TONES. */
  tone?: StatusTone;
  className?: string;
}

/**
 * Status pill: a dot plus the status label, so the state never relies on
 * colour alone.
 */
export default function StatusBadge({ status, tone, className = '' }: StatusBadgeProps) {
  const classes = TONE_CLASSES[tone ?? statusTone(status)];
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold whitespace-nowrap ${classes.badge} ${className}`}
    >
      <span aria-hidden="true" className={`w-1.5 h-1.5 rounded-full ${classes.dot}`}></span>
      {status}
    </span>
  );
}
