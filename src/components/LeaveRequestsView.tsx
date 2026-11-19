import React, { useState, useEffect } from 'react';
import { Calendar, Plus, Plane, HeartPulse, Info, Loader2 } from 'lucide-react';
import { LeaveRequest, UserRole } from '../types';
import CalendarView from './CalendarView';
import StatusBadge from './StatusBadge';
import Dialog from './ui/Dialog';
import Button from './ui/Button';
import { Field, Input, Select, Textarea } from './ui/Field';
import { useToast, ToastTone } from './ui/feedback';
import { Table, THead, Th, TBody, Tr, Td, TableState } from './ui/Table';
import { FilterPills } from './ui/TableControls';
import { useDataStatus } from '../dataStatus';
import { formatDate, formatDayMonth } from '../format';
import { labelOf, useT, type MessageKey } from '../i18n';

type StatusFilter = 'All' | 'Pending' | 'Approved' | 'Rejected';
const STATUS_FILTERS: readonly StatusFilter[] = ['All', 'Pending', 'Approved', 'Rejected'];
const FILTER_LABEL: Record<StatusFilter, MessageKey> = {
  All: 'people.leave.filter.All',
  Pending: 'people.leave.filter.Pending',
  Approved: 'people.leave.filter.Approved',
  Rejected: 'people.leave.filter.Rejected',
};
const EMPTY_FILTERED: Record<StatusFilter, MessageKey> = {
  All: 'people.leave.empty.All',
  Pending: 'people.leave.empty.Pending',
  Approved: 'people.leave.empty.Approved',
  Rejected: 'people.leave.empty.Rejected',
};
// "Personal Day" has been removed as per decision on #121
const LEAVE_TYPES = ['Annual Leave', 'Sick Leave', 'Unpaid Leave'] as const;

interface LeaveBalance {
  type: string;
  entitlement: number;
  approvedDays: number;
  pendingDays: number;
  availableDays: number;
}

interface LeaveRequestsViewProps {
  leaveRequests: LeaveRequest[];
  onAddRequest: (newReq: Partial<LeaveRequest>) => void;
  userRole: UserRole;
  currentEmployeeId?: number;
}

export default function LeaveRequestsView({
  leaveRequests,
  onAddRequest,
  userRole,
  currentEmployeeId
}: LeaveRequestsViewProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [showCalendar, setShowCalendar] = useState(false);
  const [leaveType, setLeaveType] = useState<'Annual Leave' | 'Sick Leave' | 'Unpaid Leave'>('Annual Leave');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [reason, setReason] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<StatusFilter>('All');

  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [loadingBalances, setLoadingBalances] = useState(true);

  const status = useDataStatus();
  const t = useT();
  const isEmployee = userRole === 'employee';
  const toast = useToast();
  const showToast = (message: string, tone: ToastTone = 'success') => toast(message, tone);

  // Fetch real balances (#121)
  useEffect(() => {
    const fetchBalances = async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await fetch('/api/leaves/balances', {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setBalances(data.balances);
        }
      } catch (err) {
        console.error('Failed to fetch leave balances', err);
      } finally {
        setLoadingBalances(false);
      }
    };
    if (isEmployee) fetchBalances();
    else setLoadingBalances(false);
  }, [isEmployee]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!startDate || !endDate) {
      showToast(t('people.leave.enterDates'), 'error');
      return;
    }
    const start = new Date(`${startDate}T00:00`);
    const end = new Date(`${endDate}T00:00`);
    const diffTime = Math.abs(end.getTime() - start.getTime());
    const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24)) + 1;

    const dateRangeStr = `${formatDayMonth(start)} - ${formatDate(end)}`;
    onAddRequest({
      type: leaveType,
      startDate,
      endDate,
      dates: dateRangeStr,
      duration: diffDays,
      reason: reason,
      status: 'Pending'
    });

    setIsModalOpen(false);
    showToast(t('people.leave.submitted'));
    setStartDate('');
    setEndDate('');
    setReason('');
    setLeaveType('Annual Leave');
  };

  const getLeaveIcon = (type: string) => {
    const icon = 'w-4 h-4 text-on-surface-variant';
    switch (type) {
      case 'Annual Leave':
        return <Plane className={icon} aria-hidden="true" />;
      case 'Sick Leave':
        return <HeartPulse className={icon} aria-hidden="true" />;
      default:
        return <Calendar className={icon} aria-hidden="true" />;
    }
  };

  // Helpers to get specific balances
  const getBalance = (type: string) => balances.find(b => b.type === type);

  const filteredRequests = selectedStatus === 'All'
    ? leaveRequests
    : leaveRequests.filter(req => req.status === selectedStatus);

  return (
    <div className="flex-1 flex flex-col gap-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-h1 font-black text-on-surface tracking-tight md:text-display">{t('people.leave.title')}</h1>
          <p className="text-body-lg text-on-surface-variant mt-1">{t('people.leave.subtitle')}</p>
        </div>
        {isEmployee && (
          <Button onClick={() => setIsModalOpen(true)} className="shrink-0">
            <Plus className="w-4 h-4" aria-hidden="true" />
            {t('people.leave.newRequest')}
          </Button>
        )}
      </div>

      {/* Real Balance cards (#121) */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant shadow-sm relative overflow-hidden group">
          <div className="absolute -right-4 -top-4 w-20 h-20 bg-primary/5 rounded-full transition-transform group-hover:scale-110"></div>
          <p className="text-[11px] text-on-surface-variant font-bold uppercase tracking-wider mb-1">{labelOf(t, 'common.leaveType', 'Annual Leave')}</p>
          <div className="flex items-baseline gap-2">
            {loadingBalances ? <Loader2 className="w-5 h-5 animate-spin text-primary" /> : (
              <>
                <span className="text-display font-black text-primary">{getBalance('paye')?.availableDays ?? 0}</span>
                <span className="text-body-sm text-on-surface-variant font-medium">{t('people.leave.daysLeft', { count: getBalance('paye')?.availableDays ?? 0 })}</span>
              </>
            )}
          </div>
        </div>

        <div className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant shadow-sm relative overflow-hidden group">
          <div className="absolute -right-4 -top-4 w-20 h-20 bg-secondary/5 rounded-full transition-transform group-hover:scale-110"></div>
          <p className="text-[11px] text-on-surface-variant font-bold uppercase tracking-wider mb-1">{labelOf(t, 'common.leaveType', 'Sick Leave')}</p>
          <div className="flex items-baseline gap-2">
            {loadingBalances ? <Loader2 className="w-5 h-5 animate-spin" /> : (
              <>
                <span className="text-display font-black text-on-surface">{getBalance('maladie')?.approvedDays ?? 0}</span>
                <span className="text-body-sm text-on-surface-variant font-medium">{t('people.days', { count: getBalance('maladie')?.approvedDays ?? 0 })}</span>
              </>
            )}
          </div>
        </div>

        <div className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant shadow-sm relative overflow-hidden group">
          <div className="absolute -right-4 -top-4 w-20 h-20 bg-tertiary/5 rounded-full transition-transform group-hover:scale-110"></div>
          <p className="text-[11px] text-on-surface-variant font-bold uppercase tracking-wider mb-1">{labelOf(t, 'common.leaveType', 'Unpaid Leave')}</p>
          <div className="flex items-baseline gap-2">
            {loadingBalances ? <Loader2 className="w-5 h-5 animate-spin" /> : (
              <>
                <span className="text-display font-black text-on-surface">{getBalance('sans_solde')?.approvedDays ?? 0}</span>
                <span className="text-body-sm text-on-surface-variant font-medium">{t('people.days', { count: getBalance('sans_solde')?.approvedDays ?? 0 })}</span>
              </>
            )}
          </div>
        </div>
      </div>

      <section className="flex flex-col gap-3" aria-labelledby="recent-requests">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <h2 id="recent-requests" className="text-lg font-bold tracking-[-0.02em] text-on-surface">
            {t('people.leave.recent')}
          </h2>
          <div className="flex items-center gap-2">
            <FilterPills
              label={t('people.filterByStatus')}
              options={STATUS_FILTERS}
              value={selectedStatus}
              onChange={setSelectedStatus}
              renderOption={(option) => t(FILTER_LABEL[option])}
            />
            <Button variant="secondary" size="sm" onClick={() => setShowCalendar(true)}>
              <Calendar className="w-4 h-4 mr-1" aria-hidden="true" /> {t('people.viewCalendar')}
            </Button>
          </div>
        </div>

        <Table caption={t('people.leave.caption')}>
          <THead>
            <Th>{t('people.col.type')}</Th>
            <Th numeric>{t('people.col.dates')}</Th>
            <Th numeric>{t('people.col.duration')}</Th>
            <Th>{t('people.col.status')}</Th>
            <Th numeric>
              <span className="sr-only">{t('people.leave.details')}</span>
            </Th>
          </THead>
          <TBody>
            {filteredRequests.length > 0 ? (
              filteredRequests.map((req) => (
                <Tr key={req.id}>
                  <Td>
                    <div className="flex items-center gap-3">
                      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-surface-container-high">
                        {getLeaveIcon(req.type)}
                      </span>
                      <span className="font-semibold">{labelOf(t, 'common.leaveType', req.type)}</span>
                    </div>
                  </Td>
                  <Td numeric muted>{req.dates}</Td>
                  <Td numeric>
                    {t('people.days', { count: req.duration })}
                  </Td>
                  <Td>
                    <StatusBadge status={req.status} />
                  </Td>
                  <Td numeric>
                    <button
                      type="button"
                      onClick={() =>
                        req.rejectionReason
                          ? showToast(t('people.leave.rejectionReason', { reason: req.rejectionReason }), 'info')
                          : showToast(t('people.leave.requestOf', { type: labelOf(t, 'common.leaveType', req.type) }), 'info')
                      }
                      aria-label={t('people.leave.detailsOf', { type: labelOf(t, 'common.leaveType', req.type), dates: req.dates })}
                      className="rounded-lg p-1.5 text-on-surface-variant transition-colors hover:bg-surface-container hover:text-on-surface cursor-pointer"
                    >
                      <Info className="w-4 h-4" aria-hidden="true" />
                    </button>
                  </Td>
                </Tr>
              ))
            ) : status.loading ? (
              <TableState kind="loading" colSpan={5} title={t('people.loadingLeave')} />
            ) : status.error && leaveRequests.length === 0 ? (
              <TableState kind="error" colSpan={5} message={status.error} />
            ) : (
              <TableState
                kind="empty"
                colSpan={5}
                title={leaveRequests.length === 0 ? t('people.leave.emptyNone') : t(EMPTY_FILTERED[selectedStatus])}
                message={leaveRequests.length === 0 && isEmployee ? t('people.leave.emptyHint') : undefined}
              />
            )}
          </TBody>
        </Table>
      </section>

      {showCalendar && (
        <CalendarView
          leaveRequests={leaveRequests}
          userRole={userRole}
          currentEmployeeId={currentEmployeeId}
          onClose={() => setShowCalendar(false)}
        />
      )}

      {isEmployee && (
        <Dialog
          open={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          title={t('people.leave.newTitle')}
          footer={
            <>
              <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
                {t('people.cancel')}
              </Button>
              <Button type="submit" form="leave-request-form">
                {t('people.leave.submit')}
              </Button>
            </>
          }
        >
          <form id="leave-request-form" onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Field label={t('people.leave.type')}>
              {({ id }) => (
                <Select id={id} value={leaveType} onChange={(e) => setLeaveType(e.target.value as any)}>
                  {LEAVE_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {labelOf(t, 'common.leaveType', type)}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label={t('people.leave.startDate')}>
                {({ id }) => <Input id={id} type="date" required value={startDate} onChange={(e) => setStartDate(e.target.value)} />}
              </Field>
              <Field label={t('people.leave.endDate')}>
                {({ id }) => <Input id={id} type="date" required value={endDate} onChange={(e) => setEndDate(e.target.value)} />}
              </Field>
            </div>
            <Field label={t('people.leave.reasonOptional')}>
              {({ id }) => (
                <Textarea
                  id={id}
                  rows={3}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder={t('people.leave.reasonPlaceholder')}
                />
              )}
            </Field>
          </form>
        </Dialog>
      )}
    </div>
  );
}
