import React from 'react';
import {
  AlertCircle, ArrowRight, Calendar, CheckCircle, ChevronRight,
  Download, FileText, Info, Loader2, XCircle,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Employee, LeaveRequest, Payslip, User } from '../types';
import type { DashboardSummary } from '../api';
import { useDataStatus } from '../dataStatus';
import { formatTND } from '../format';
import StatusBadge, { TONE_CLASSES, statusTone } from './StatusBadge';
import Button from './ui/Button';
import { FormAlert } from './ui/Field';

interface Notification {
  id: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  read: boolean;
  timestamp: number;
  link?: string;
}

interface DashboardViewProps {
  user: User;
  /** The figures, computed by the server over every row (#120). */
  summary: DashboardSummary | null;
  payslips: Payslip[];
  leaveRequests: LeaveRequest[];
  employees: Employee[];
  notifications: Notification[];
  onNavigate: (tab: string) => void;
  onQuickAction: (action: string) => void;
}

const PROCESSING_STATES = ['Pending', 'Processed', 'Completed', 'Archived'] as const;
const PROCESSING_TONE = { Pending: 'warning', Processed: 'info', Completed: 'success', Archived: 'neutral' } as const;
const COMMERCIAL_STATES = ['Draft', 'Sent', 'Paid', 'Overdue', 'Cancelled'] as const;

const ROLE_INTRO: Record<User['role'], string> = {
  admin: 'Invoices waiting on the books, leave to decide and your team at a glance.',
  accountant: 'Where the invoices stand in the books, and what is waiting for you.',
  employee: 'Your leave requests, your next time off and your latest payslip.',
};

const NOTIFICATION_ICON: Record<Notification['type'], { icon: LucideIcon; className: string }> = {
  info: { icon: Info, className: 'text-info' },
  success: { icon: CheckCircle, className: 'text-success' },
  warning: { icon: AlertCircle, className: 'text-warning' },
  error: { icon: XCircle, className: 'text-danger' },
};

const CARD = 'rounded-xl border border-outline-variant bg-surface-container-lowest';
const EYEBROW = 'font-mono text-[11px] font-medium uppercase tracking-[0.08em] text-on-surface-variant';

interface Metric {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  /** Tab the card opens. */
  to?: string;
  /** The view's one Signal Lime accent: the figure this role came for. */
  highlight?: boolean;
}

function MetricCard({ metric, loading, onNavigate }: { metric: Metric; loading: boolean; onNavigate: (tab: string) => void }) {
  const body = (
    <>
      <div className="flex items-center justify-between gap-2">
        <p className={EYEBROW}>{metric.label}</p>
        {metric.highlight && <span aria-hidden="true" className="h-2 w-2 rounded-full bg-lime ring-2 ring-lime/30" />}
      </div>
      <p className="mt-3 font-mono text-3xl font-semibold tabular-nums tracking-tight text-on-surface">
        {loading ? <span className="text-on-surface-variant">–</span> : metric.value}
      </p>
      {metric.hint && !loading && (
        <p className="mt-1 font-mono text-xs tabular-nums text-on-surface-variant">{metric.hint}</p>
      )}
      {metric.to && (
        <span className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-on-surface-variant group-hover:text-on-surface">
          Open <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
        </span>
      )}
    </>
  );
  const frame = `${CARD} p-5 text-left ${metric.highlight ? 'border-on-surface/30' : ''}`;
  return metric.to ? (
    <button
      type="button"
      onClick={() => onNavigate(metric.to!)}
      className={`${frame} group cursor-pointer transition-colors hover:bg-surface-container-low`}
    >
      {body}
    </button>
  ) : (
    <div className={frame}>{body}</div>
  );
}

function Section({ title, aside, children }: { title: string; aside?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className={`${CARD} p-6`}>
      <div className="mb-4 flex items-baseline justify-between gap-3">
        <h2 className="text-base font-semibold text-on-surface">{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  );
}

export default function DashboardView({
  user,
  summary,
  payslips,
  leaveRequests,
  employees,
  notifications,
  onNavigate,
  onQuickAction,
}: DashboardViewProps) {
  const { loading, error, retry } = useDataStatus();
  const seesInvoices = user.role === 'admin' || user.role === 'accountant';

  // --- Invoices (admin and accountant) ---
  // Counted and summed by the server over every invoice (#120): the browser no
  // longer adds up a list capped at the API's page size.
  const figures = summary?.invoices;
  const invoiceCount = figures?.count ?? 0;
  const totalAmount = figures?.amount ?? 0;
  // Where the invoices have got to in the accountant's workflow (#41). A
  // separate axis from the commercial status: an invoice is routinely Paid and
  // still Pending here, because the client has paid and nobody has booked it yet.
  const processingCounts = PROCESSING_STATES.map((state) => ({
    state,
    count: figures?.byProcessing.find((p) => p.status === state)?.count ?? 0,
  }));
  const countOf = (state: (typeof PROCESSING_STATES)[number]) =>
    processingCounts.find((p) => p.state === state)?.count ?? 0;
  const commercialStats = COMMERCIAL_STATES.map((status) => {
    const figure = figures?.byStatus.find((s) => s.status === status);
    return { status, count: figure?.count ?? 0, amount: figure?.amount ?? 0 };
  });

  // --- Leave and team ---
  // The caller's own pending requests, or everyone's for the admin: the
  // server's row-level security decides, as for the leave list.
  const pendingLeaves = summary?.leave.pending ?? 0;
  const activeTeam = summary?.team?.active ?? 0;
  const teamTotal = summary?.team?.total ?? 0;

  // --- Employee: their own records ---
  // Resolved through the employee record: leave belongs to the employee, not
  // the login account (#60).
  const myEmployeeId = employees.find((e) => e.userId === user.id)?.id;
  const myLeave = leaveRequests.filter((r) => r.employeeId === myEmployeeId);
  // The next approved leave that has not ended yet, by its real start date.
  const today = new Date().toISOString().slice(0, 10);
  const upcomingLeave = myLeave
    .filter((r) => r.status === 'Approved' && r.endDate >= today)
    .sort((a, b) => a.startDate.localeCompare(b.startDate))[0];
  const latestPayslip = user.role === 'employee' ? payslips[0] ?? null : null;
  const unread = notifications.filter((n) => !n.read).length;

  const metrics: Metric[] =
    user.role === 'admin'
      ? [
          { label: 'Awaiting booking', value: countOf('Pending'), hint: 'invoices in Pending', to: 'invoices', highlight: true },
          { label: 'Invoices', value: invoiceCount, hint: formatTND(totalAmount), to: 'invoices' },
          { label: 'Leave to decide', value: pendingLeaves, hint: 'pending requests', to: 'team' },
          { label: 'Active team', value: activeTeam, hint: `${teamTotal} employees in total`, to: 'team' },
        ]
      : user.role === 'accountant'
        ? [
            { label: 'Awaiting booking', value: countOf('Pending'), hint: 'invoices in Pending', to: 'invoices', highlight: true },
            { label: 'To complete', value: countOf('Processed'), hint: 'invoices in Processed', to: 'invoices' },
            { label: 'Completed', value: countOf('Completed'), hint: 'ready for the month close', to: 'invoices' },
            { label: 'Invoiced', value: invoiceCount, hint: formatTND(totalAmount), to: 'invoices' },
          ]
        : [
            {
              label: 'Pending requests',
              value: pendingLeaves,
              hint: 'waiting for a decision',
              to: 'leave-requests',
              highlight: true,
            },
            {
              label: 'Next leave',
              value: upcomingLeave ? upcomingLeave.startDate : 'None',
              hint: upcomingLeave ? `${upcomingLeave.type} · ${upcomingLeave.duration} days` : 'nothing approved ahead',
              to: 'leave-requests',
            },
            {
              label: 'Latest payslip',
              value: latestPayslip ? latestPayslip.period : 'None',
              hint: latestPayslip ? `net ${formatTND(latestPayslip.netPay)}` : 'none issued yet',
              to: 'payslips',
            },
            { label: 'Unread', value: unread, hint: 'notifications', to: 'notifications' },
          ];

  const maxProcessing = Math.max(...processingCounts.map((p) => p.count), 1);
  const recentNotifications = notifications.slice(0, 5);

  return (
    <div className="flex-1 flex flex-col gap-6 animate-fade-in">
      <div>
        <h1 className="text-h1 font-black text-on-surface tracking-tight md:text-display">
          Welcome back, {user.firstName}
        </h1>
        <p className="text-body-lg text-on-surface-variant mt-1">{ROLE_INTRO[user.role]}</p>
      </div>

      {error && (
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex-1">
            <FormAlert>Some figures could not be loaded: {error}</FormAlert>
          </div>
          <Button variant="secondary" size="sm" onClick={retry}>
            Retry
          </Button>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4" aria-busy={loading || undefined}>
        {metrics.map((m) => (
          <MetricCard key={m.label} metric={m} loading={loading} onNavigate={onNavigate} />
        ))}
      </div>

      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          {seesInvoices && (
            <Section
              title="Invoices by processing state"
              aside={<span className={EYEBROW}>{invoiceCount} invoices</span>}
            >
              {loading ? (
                <LoadingRow />
              ) : invoiceCount === 0 ? (
                <p className="text-sm text-on-surface-variant">No invoices yet.</p>
              ) : (
                // Each bar carries its label and its count, so no value relies on colour.
                <ul className="space-y-3">
                  {processingCounts.map(({ state, count }) => (
                    <li key={state} className="grid grid-cols-[6.5rem_1fr_3rem] items-center gap-3">
                      <span className="text-sm text-on-surface-variant">{state}</span>
                      <div className="h-2.5 overflow-hidden rounded-full bg-surface-container-high">
                        <div
                          className={`h-full rounded-full ${TONE_CLASSES[PROCESSING_TONE[state]].dot} transition-all duration-500`}
                          style={{ width: `${(count / maxProcessing) * 100}%` }}
                        />
                      </div>
                      <span className="text-right font-mono text-sm font-semibold tabular-nums text-on-surface">
                        {count}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Section>
          )}

          {seesInvoices && (
            <Section title="Invoices by status">
              {loading ? (
                <LoadingRow />
              ) : (
                <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
                  {commercialStats.map(({ status, count, amount }) => (
                    <li key={status} className="rounded-lg border border-outline-variant p-3">
                      <StatusBadge status={status} tone={statusTone(status)} />
                      <p className="mt-3 font-mono text-2xl font-semibold tabular-nums text-on-surface">{count}</p>
                      <p className="mt-0.5 truncate font-mono text-xs tabular-nums text-on-surface-variant" title={formatTND(amount)}>
                        {formatTND(amount)}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </Section>
          )}

          {user.role === 'admin' && (
            <Section title="Quick actions">
              <div className="flex flex-wrap gap-3">
                <Button variant="secondary" size="sm" onClick={() => onQuickAction('approve-leaves')}>
                  <Calendar className="h-4 w-4" aria-hidden="true" />
                  Review leave requests
                </Button>
                <Button variant="secondary" size="sm" onClick={() => onQuickAction('create-invoice')}>
                  <FileText className="h-4 w-4" aria-hidden="true" />
                  Create an invoice
                </Button>
              </div>
            </Section>
          )}

          {user.role === 'employee' && (
            <Section title="Your leave">
              <dl className="space-y-4 text-sm">
                <div>
                  <dt className={EYEBROW}>Balance</dt>
                  {/* The balance used to be three invented figures. Until the
                      server holds entitlements (#121), say so instead. */}
                  <dd className="mt-1 text-on-surface-variant">Leave balances are not available yet.</dd>
                </div>
                <div>
                  <dt className={EYEBROW}>Next approved leave</dt>
                  <dd className="mt-1 text-on-surface">
                    {upcomingLeave ? (
                      <>
                        <span className="font-semibold">{upcomingLeave.type}</span>{' '}
                        <span className="font-mono tabular-nums text-on-surface-variant">{upcomingLeave.dates}</span>
                      </>
                    ) : (
                      <span className="text-on-surface-variant">None scheduled.</span>
                    )}
                  </dd>
                </div>
                {latestPayslip && (
                  <div>
                    <dt className={EYEBROW}>Latest payslip</dt>
                    <dd className="mt-1">
                      <Button variant="ghost" size="sm" onClick={() => onQuickAction('download-payslip')}>
                        <Download className="h-4 w-4" aria-hidden="true" />
                        {latestPayslip.period}
                      </Button>
                    </dd>
                  </div>
                )}
              </dl>
            </Section>
          )}
        </div>

        <Section
          title="Recent activity"
          aside={
            <button
              type="button"
              onClick={() => onNavigate('notifications')}
              className="inline-flex items-center gap-1 rounded text-xs font-semibold text-on-surface-variant hover:text-on-surface cursor-pointer"
            >
              View all <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          }
        >
          {recentNotifications.length === 0 ? (
            <p className="text-sm text-on-surface-variant">No recent activity.</p>
          ) : (
            <ul className="-mx-2 divide-y divide-outline-variant">
              {recentNotifications.map((notif) => {
                const { icon: Icon, className } = NOTIFICATION_ICON[notif.type];
                const content = (
                  <>
                    <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${className}`} aria-hidden="true" />
                    <span className="min-w-0 flex-1">
                      <span className={`block truncate text-sm ${notif.read ? 'text-on-surface-variant' : 'font-semibold text-on-surface'}`}>
                        {!notif.read && <span className="sr-only">Unread: </span>}
                        {notif.message}
                      </span>
                      <span className="mt-0.5 block font-mono text-[11px] tabular-nums text-on-surface-variant">
                        {new Date(notif.timestamp).toLocaleString('en-US', {
                          month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                        })}
                      </span>
                    </span>
                    {!notif.read && <span aria-hidden="true" className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-on-surface" />}
                    {notif.link && <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-on-surface-variant" aria-hidden="true" />}
                  </>
                );
                const row = 'flex w-full items-start gap-2.5 rounded-lg px-2 py-2.5 text-left';
                return (
                  <li key={notif.id}>
                    {notif.link ? (
                      <button
                        type="button"
                        onClick={() => onNavigate(notif.link!)}
                        className={`${row} cursor-pointer transition-colors hover:bg-surface-container-low`}
                      >
                        {content}
                      </button>
                    ) : (
                      <div className={row}>{content}</div>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </Section>
      </div>
    </div>
  );
}

function LoadingRow() {
  return (
    <p className="flex items-center gap-2 text-sm text-on-surface-variant" role="status">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Loading…
    </p>
  );
}
