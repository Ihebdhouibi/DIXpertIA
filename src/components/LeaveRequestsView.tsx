import React, { useState } from 'react';
import { Calendar, Plus, Filter, Plane, HeartPulse, MoreVertical, X, Check } from 'lucide-react';
import { LeaveRequest, UserRole } from '../types';
import CalendarView from './CalendarView';
import StatusBadge from './StatusBadge';
import Dialog from './ui/Dialog';
import Button from './ui/Button';
import { Field, Input, Select, Textarea } from './ui/Field';
import { useToast, ToastTone } from './ui/feedback';

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

  const getLeaveIcon = (type: string) => {
    switch (type) {
      case 'Annual Leave':
        return <Plane className="w-4 h-4 text-primary" />;
      case 'Sick Leave':
        return <HeartPulse className="w-4 h-4 text-error" />;
      default:
        return <Calendar className="w-4 h-4 text-secondary" />;
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
          <button
            onClick={() => setIsModalOpen(true)}
            className="bg-primary text-on-primary font-semibold text-body-sm px-6 py-2.5 rounded-lg hover:bg-primary/95 transition-all shadow-sm flex items-center gap-2 cursor-pointer"
          >
            <Plus className="w-5 h-5" />
            <span>New Request</span>
          </button>
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
        <div
          onClick={() => setShowCalendar(true)}
          className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant shadow-sm flex flex-col justify-center items-center text-center cursor-pointer hover:bg-surface-container-low transition-colors select-none"
        >
          <Calendar className="text-primary mb-2 w-7 h-7" />
          <span className="font-semibold text-body-sm text-primary">View Calendar</span>
        </div>
      </div>

      {/* Table */}
      <div className="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-outline-variant bg-surface-container-lowest flex justify-between items-center">
          <h2 className="font-bold text-body-lg text-on-surface">Recent Requests</h2>
          <div className="flex gap-2">
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value as any)}
              className="px-3 py-1.5 border border-outline-variant rounded-lg text-caption font-medium bg-surface focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="All">All</option>
              <option value="Pending">Pending</option>
              <option value="Approved">Approved</option>
              <option value="Rejected">Rejected</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-outline-variant bg-surface">
                <th className="px-6 py-3 text-caption text-on-surface-variant uppercase tracking-wider font-semibold">Type</th>
                <th className="px-6 py-3 text-caption text-on-surface-variant uppercase tracking-wider font-semibold">Dates</th>
                <th className="px-6 py-3 text-caption text-on-surface-variant uppercase tracking-wider font-semibold">Duration</th>
                <th className="px-6 py-3 text-caption text-on-surface-variant uppercase tracking-wider font-semibold">Status</th>
                <th className="px-6 py-3 text-caption text-on-surface-variant uppercase tracking-wider font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="text-body-sm text-on-surface divide-y divide-outline-variant">
              {filteredRequests.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-on-surface-variant font-medium">
                    No leave requests found.
                  </td>
                </tr>
              ) : (
                filteredRequests.map((req) => (
                  <tr key={req.id} className="hover:bg-surface-container-lowest transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                          {getLeaveIcon(req.type)}
                        </div>
                        <span className="font-semibold text-on-surface">{req.type}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-on-surface-variant font-medium">{req.dates}</td>
                    <td className="px-6 py-4 font-medium">{req.duration} {req.duration > 1 ? 'days' : 'day'}</td>
                    <td className="px-6 py-4"><StatusBadge status={req.status} /></td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => req.rejectionReason ? showToast(`Rejection reason: ${req.rejectionReason}`, 'info') : showToast(`Request: ${req.type}`, 'info')}
                        className="text-on-surface-variant hover:text-primary transition-colors cursor-pointer p-1"
                      >
                        <MoreVertical className="w-5 h-5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

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
