import React, { useState } from 'react';
import { Calendar, Plus, Filter, Plane, HeartPulse, MoreVertical, X, Check } from 'lucide-react';
import { LeaveRequest, UserRole } from '../types';

interface LeaveRequestsViewProps {
  leaveRequests: LeaveRequest[];
  onAddRequest: (newReq: Partial<LeaveRequest>) => void;
  userRole: UserRole;
}

export default function LeaveRequestsView({ leaveRequests, onAddRequest, userRole }: LeaveRequestsViewProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [leaveType, setLeaveType] = useState<'Annual Leave' | 'Sick Leave' | 'Personal Day' | 'Unpaid Leave'>('Annual Leave');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [reason, setReason] = useState('');
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [selectedStatus, setSelectedStatus] = useState<'All' | 'Pending' | 'Approved' | 'Rejected'>('All');

  // Allow both employee and accountant to create new requests
  const canCreate = userRole === 'employee' ;

  const showToast = (message: string) => {
    setToastMessage(message);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!startDate || !endDate) {
      showToast('Please enter start and end dates.');
      return;
    }
    const start = new Date(startDate);
    const end = new Date(endDate);
    const diffTime = Math.abs(end.getTime() - start.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;

    const formatDateStr = (date: Date) =>
      date.toLocaleDateString('en-US', { month: 'short', day: '2-digit' });
    const dateRangeStr = `${formatDateStr(start)} - ${formatDateStr(end)}, 2024`;

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

  const getStatusBadge = (status: 'Approved' | 'Pending' | 'Rejected') => {
    if (status === 'Approved') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-[#e6f4ea] text-[#137333]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#137333]"></span> Approved
        </span>
      );
    }
    if (status === 'Pending') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-[#fef7e0] text-[#b06000]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#b06000]"></span> Pending
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-error-container text-on-error-container border border-error/10">
        <span className="w-1.5 h-1.5 rounded-full bg-error animate-pulse"></span> Rejected
      </span>
    );
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

  const annualLeft = 14;
  const sickLeft = 5;
  const personalLeft = 2;

  const filteredRequests = selectedStatus === 'All'
    ? leaveRequests
    : leaveRequests.filter(req => req.status === selectedStatus);

  return (
    <div className="flex-1 flex flex-col gap-6">
      {toastMessage && (
        <div className="fixed bottom-4 right-4 z-50 bg-primary text-white py-3 px-5 rounded-lg shadow-lg flex items-center gap-2 animate-fade-in text-body-sm font-semibold border border-white/15">
          <Check className="w-5 h-5 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-h1 font-black text-on-surface tracking-tight md:text-display">Leave Requests</h1>
          <p className="text-body-lg text-on-surface-variant mt-1">Manage and track your time off</p>
        </div>
        {canCreate && (
          <button
            onClick={() => setIsModalOpen(true)}
            className="bg-primary text-white font-semibold text-body-sm px-6 py-2.5 rounded-lg hover:bg-primary/95 transition-all shadow-sm flex items-center gap-2 cursor-pointer"
          >
            <Plus className="w-5 h-5" />
            <span>New Request</span>
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-outline-variant shadow-sm relative overflow-hidden group">
          <div className="absolute -right-4 -top-4 w-20 h-20 bg-primary/5 rounded-full transition-transform group-hover:scale-110"></div>
          <p className="text-[11px] text-on-surface-variant font-bold uppercase tracking-wider mb-1">Annual Leave</p>
          <div className="flex items-baseline gap-2">
            <span className="text-display font-black text-primary">{annualLeft}</span>
            <span className="text-body-sm text-on-surface-variant font-medium">days left</span>
          </div>
        </div>
        <div className="bg-white p-5 rounded-xl border border-outline-variant shadow-sm relative overflow-hidden group">
          <div className="absolute -right-4 -top-4 w-20 h-20 bg-secondary/5 rounded-full transition-transform group-hover:scale-110"></div>
          <p className="text-[11px] text-on-surface-variant font-bold uppercase tracking-wider mb-1">Sick Leave</p>
          <div className="flex items-baseline gap-2">
            <span className="text-display font-black text-on-surface">{sickLeft}</span>
            <span className="text-body-sm text-on-surface-variant font-medium">days left</span>
          </div>
        </div>
        <div className="bg-white p-5 rounded-xl border border-outline-variant shadow-sm relative overflow-hidden group">
          <div className="absolute -right-4 -top-4 w-20 h-20 bg-tertiary/5 rounded-full transition-transform group-hover:scale-110"></div>
          <p className="text-[11px] text-on-surface-variant font-bold uppercase tracking-wider mb-1">Personal Days</p>
          <div className="flex items-baseline gap-2">
            <span className="text-display font-black text-on-surface">{personalLeft}</span>
            <span className="text-body-sm text-on-surface-variant font-medium">days left</span>
          </div>
        </div>
        <div
          onClick={() => showToast('Calendar view coming soon.')}
          className="bg-white p-5 rounded-xl border border-outline-variant shadow-sm flex flex-col justify-center items-center text-center cursor-pointer hover:bg-surface-container-low transition-colors select-none"
        >
          <Calendar className="text-primary mb-2 w-7 h-7" />
          <span className="font-semibold text-body-sm text-primary">View Calendar</span>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-outline-variant shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-outline-variant bg-white flex justify-between items-center">
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
                    <td className="px-6 py-4">{getStatusBadge(req.status)}</td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => req.rejectionReason ? showToast(`Rejection reason: ${req.rejectionReason}`) : showToast(`Request: ${req.type}`)}
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

      {canCreate && isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
          <div className="absolute inset-0 bg-on-background/40 backdrop-blur-sm" onClick={() => setIsModalOpen(false)}></div>
          <div className="relative w-full max-w-lg bg-white rounded-xl shadow-lg border border-outline-variant overflow-hidden flex flex-col max-h-full animate-scale-up">
            <div className="px-6 py-4 border-b border-outline-variant flex justify-between items-center bg-surface">
              <h3 className="text-h2 font-black text-on-surface">New Leave Request</h3>
              <button
                className="text-on-surface-variant hover:text-on-surface p-1 rounded-lg hover:bg-surface-container-high transition-colors cursor-pointer"
                onClick={() => setIsModalOpen(false)}
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 overflow-y-auto">
              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label className="block text-xs font-semibold text-on-surface-variant mb-1.5">Leave Type</label>
                  <select
                    value={leaveType}
                    onChange={(e) => setLeaveType(e.target.value as any)}
                    className="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-sm text-on-surface focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-all cursor-pointer font-semibold"
                  >
                    <option value="Annual Leave">Annual Leave</option>
                    <option value="Sick Leave">Sick Leave</option>
                    <option value="Personal Day">Personal Day</option>
                    <option value="Unpaid Leave">Unpaid Leave</option>
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-on-surface-variant mb-1.5">Start Date</label>
                    <input
                      type="date"
                      required
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      className="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-sm text-on-surface focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-shadow"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-on-surface-variant mb-1.5">End Date</label>
                    <input
                      type="date"
                      required
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      className="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-sm text-on-surface focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-shadow"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-on-surface-variant mb-1.5">Reason (Optional)</label>
                  <textarea
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    className="w-full bg-surface border border-outline-variant rounded-lg px-3 py-2 text-body-sm text-on-surface focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-shadow resize-none"
                    placeholder="Provide details if necessary..."
                    rows={3}
                  ></textarea>
                </div>

                <div className="pt-4 border-t border-outline-variant/30 flex justify-end gap-3 shrink-0">
                  <button
                    type="button"
                    className="px-4 py-2 rounded-lg border border-primary text-primary font-bold text-body-sm hover:bg-primary/5 transition-colors cursor-pointer"
                    onClick={() => setIsModalOpen(false)}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-lg bg-primary text-white font-bold text-body-sm hover:bg-primary/95 transition-colors shadow-sm cursor-pointer"
                  >
                    Submit Request
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}