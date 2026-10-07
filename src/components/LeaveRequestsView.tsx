import React, { useState } from 'react';
import { Calendar, Plus, Plane, HeartPulse, Info } from 'lucide-react';
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

interface LeaveRequestsViewProps {
  leaveRequests: LeaveRequest[];
  onAddRequest: (newReq: Partial<LeaveRequest>) => void;
  userRole: UserRole;
  /** The employee record id, used to filter the calendar to one person. */
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
  const [leaveType, setLeaveType] = useState<'Annual Leave' | 'Sick Leave' | 'Personal Day' | 'Unpaid Leave'>('Annual Leave');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [reason, setReason] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<'All' | 'Pending' | 'Approved' | 'Rejected'>('All');
  const status = useDataStatus();

  const isEmployee = userRole === 'employee';

  const toast = useToast();
  const showToast = (message: string, tone: ToastTone = 'success') => toast(message, tone);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!startDate || !endDate) {
      showToast('Please enter start and end dates.', 'error');
      return;
    }
    const start = new Date(startDate);
    const end = new Date(endDate);
    const diffTime = Math.abs(end.getTime() - start.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;

    const formatDateStr = (date: Date) =>
      date.toLocaleDateString('en-US', { month: 'short', day: '2-digit' });
    const dateRangeStr = `${formatDateStr(start)} - ${formatDateStr(end)}, ${start.getFullYear()}`;
    onAddRequest({
      type: leaveType,
      dates: dateRangeStr,
      duration: diffDays,
      reason: reason,
      status: 'Pending'
    });

    setIsModalOpen(false);
    showToast('Leave request submitted successfully.');
    setStartDate('');
    setEndDate('');
    setReason('');
    setLeaveType('Annual Leave');
  };

  // A leave type is a category, not a state: one neutral colour, the icon
  // tells them apart (sick leave was in the error red).
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

  // Mock balances
  const annualLeft = 14;
  const sickLeft = 5;
  const personalLeft = 2;

  const filteredRequests = selectedStatus === 'All'
    ? leaveRequests
    : leaveRequests.filter(req => req.status === selectedStatus);

  return (
    <div className="flex-1 flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-h1 font-black text-on-surface tracking-tight md:text-display">Leave Requests</h1>
          <p className="text-body-lg text-on-surface-variant mt-1">Manage and track your time off</p>
        </div>
        {isEmployee && (
          <Button onClick={() => setIsModalOpen(true)} className="shrink-0">
            <Plus className="w-4 h-4" aria-hidden="true" />
            New request
          </Button>
        )}
      </div>

      {/* Balance cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant shadow-sm relative overflow-hidden group">
          <div className="absolute -right-4 -top-4 w-20 h-20 bg-primary/5 rounded-full transition-transform group-hover:scale-110"></div>
          <p className="text-[11px] text-on-surface-variant font-bold uppercase tracking-wider mb-1">Annual Leave</p>
          <div className="flex items-baseline gap-2">
            <span className="text-display font-black text-primary">{annualLeft}</span>
            <span className="text-body-sm text-on-surface-variant font-medium">days left</span>
          </div>
        </div>
        <div className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant shadow-sm relative overflow-hidden group">
          <div className="absolute -right-4 -top-4 w-20 h-20 bg-secondary/5 rounded-full transition-transform group-hover:scale-110"></div>
          <p className="text-[11px] text-on-surface-variant font-bold uppercase tracking-wider mb-1">Sick Leave</p>
          <div className="flex items-baseline gap-2">
            <span className="text-display font-black text-on-surface">{sickLeft}</span>
            <span className="text-body-sm text-on-surface-variant font-medium">days left</span>
          </div>
        </div>
        <div className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant shadow-sm relative overflow-hidden group">
          <div className="absolute -right-4 -top-4 w-20 h-20 bg-tertiary/5 rounded-full transition-transform group-hover:scale-110"></div>
          <p className="text-[11px] text-on-surface-variant font-bold uppercase tracking-wider mb-1">Personal Days</p>
          <div className="flex items-baseline gap-2">
            <span className="text-display font-black text-on-surface">{personalLeft}</span>
            <span className="text-body-sm text-on-surface-variant font-medium">days left</span>
          </div>
        </div>
        {/* A button, not a clickable div: it was unreachable from the keyboard. */}
        <button
          type="button"
          onClick={() => setShowCalendar(true)}
          className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant flex flex-col justify-center items-center text-center cursor-pointer hover:bg-surface-container-low transition-colors"
        >
          <Calendar className="text-on-surface mb-2 w-7 h-7" aria-hidden="true" />
          <span className="font-semibold text-body-sm text-on-surface">View Calendar</span>
        </button>
      </div>

      {/* Requests */}
      <section className="flex flex-col gap-3" aria-labelledby="recent-requests">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <h2 id="recent-requests" className="text-lg font-bold tracking-[-0.02em] text-on-surface">
            Recent requests
          </h2>
          <FilterPills
            label="Filter by status"
            options={['All', 'Pending', 'Approved', 'Rejected'] as const}
            value={selectedStatus}
            onChange={setSelectedStatus}
          />
        </div>
        <Table caption="Leave requests">
          <THead>
            <Th>Type</Th>
            <Th numeric>Dates</Th>
            <Th numeric>Duration</Th>
            <Th>Status</Th>
            <Th numeric>
              <span className="sr-only">Details</span>
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
                      <span className="font-semibold">{req.type}</span>
                    </div>
                  </Td>
                  <Td numeric muted>{req.dates}</Td>
                  <Td numeric>
                    {req.duration} {req.duration > 1 ? 'days' : 'day'}
                  </Td>
                  <Td>
                    <StatusBadge status={req.status} />
                  </Td>
                  <Td numeric>
                    <button
                      type="button"
                      onClick={() =>
                        req.rejectionReason
                          ? showToast(`Rejection reason: ${req.rejectionReason}`, 'info')
                          : showToast(`Request: ${req.type}`, 'info')
                      }
                      aria-label={`Details of the ${req.type} request, ${req.dates}`}
                      className="rounded-lg p-1.5 text-on-surface-variant transition-colors hover:bg-surface-container hover:text-on-surface cursor-pointer"
                    >
                      <Info className="w-4 h-4" aria-hidden="true" />
                    </button>
                  </Td>
                </Tr>
              ))
            ) : status.loading ? (
              <TableState kind="loading" colSpan={5} title="Loading leave requests..." />
            ) : status.error && leaveRequests.length === 0 ? (
              <TableState kind="error" colSpan={5} message={status.error} />
            ) : (
              <TableState
                kind="empty"
                colSpan={5}
                title={leaveRequests.length === 0 ? 'No leave requests yet' : `No ${selectedStatus.toLowerCase()} requests`}
                message={leaveRequests.length === 0 && isEmployee ? 'Use "New request" to ask for time off.' : undefined}
              />
            )}
          </TBody>
        </Table>
      </section>

      {/* Calendar Modal */}
      {showCalendar && (
        <CalendarView
          leaveRequests={leaveRequests}
          userRole={userRole}
          currentEmployeeId={currentEmployeeId}
          onClose={() => setShowCalendar(false)}
        />
      )}

      {/* New Request */}
      {isEmployee && (
        <Dialog
          open={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          title="New leave request"
          footer={
            <>
              <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" form="leave-request-form">
                Submit request
              </Button>
            </>
          }
        >
          <form id="leave-request-form" onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Field label="Leave type">
              {({ id }) => (
                <Select id={id} value={leaveType} onChange={(e) => setLeaveType(e.target.value as any)}>
                  <option value="Annual Leave">Annual Leave</option>
                  <option value="Sick Leave">Sick Leave</option>
                  <option value="Personal Day">Personal Day</option>
                  <option value="Unpaid Leave">Unpaid Leave</option>
                </Select>
              )}
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Start date">
                {({ id }) => <Input id={id} type="date" required value={startDate} onChange={(e) => setStartDate(e.target.value)} />}
              </Field>
              <Field label="End date">
                {({ id }) => <Input id={id} type="date" required value={endDate} onChange={(e) => setEndDate(e.target.value)} />}
              </Field>
            </div>
            <Field label="Reason (optional)">
              {({ id }) => (
                <Textarea
                  id={id}
                  rows={3}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Provide details if necessary..."
                />
              )}
            </Field>
          </form>
        </Dialog>
      )}
    </div>
  );
}
