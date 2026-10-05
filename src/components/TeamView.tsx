import React, { useState } from 'react';
import { Plus, Search, Edit, Ban, CheckCircle, X, Calendar, User, FileText, Check, AlertCircle } from 'lucide-react';
import { Employee, LeaveRequest, UserRole } from '../types';
import CalendarView from './CalendarView';
import StatusBadge from './StatusBadge';

interface TeamViewProps {
  userRole: UserRole;
  employees: Employee[];
  leaveRequests: LeaveRequest[];
  onApproveLeave: (id: string) => void;
  onRejectLeave: (id: string, comment: string) => void;
}


/** Two initials from a display name, for the avatar circle. */
function initialsOf(name: string): string {
  return name.split(' ').filter(Boolean).slice(0, 2).map(w => w[0]).join('').toUpperCase() || '?';
}

/** The employment status as a label, matching the StatusBadge vocabulary. */
function employmentLabel(status: string): string {
  if (status === 'active') return 'Active';
  if (status === 'on_leave') return 'On Hold';
  return 'Inactive';
}

export default function TeamView({
  userRole,
  employees,
  leaveRequests,
  onApproveLeave,
  onRejectLeave,
}: TeamViewProps) {
  const isAdmin = userRole === 'admin';
  const isEmployee = userRole === 'employee';
  const isAccountant = userRole === 'accountant';

  // Shared state
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRole, setSelectedRole] = useState('All Roles');
  const [selectedStatus, setSelectedStatus] = useState('All Status');
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [showCalendar, setShowCalendar] = useState(false);

  // Admin-only states
  const [activeSubTab, setActiveSubTab] = useState<'employees' | 'leave-approvals'>('employees');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('');
  const [sendInvitation, setSendInvitation] = useState(true);
  const [isRejectOpen, setIsRejectOpen] = useState(false);
  const [rejectingRequestId, setRejectingRequestId] = useState<string | null>(null);
  const [rejectionComment, setRejectionComment] = useState('');

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  // --- Handlers (admin only) ---
  const handleApprove = (id: string, name: string) => {
    onApproveLeave(id);
    showToast(`Leave request from ${name} approved.`);
  };

  const triggerReject = (id: string) => {
    setRejectingRequestId(id);
    setIsRejectOpen(true);
  };

  const handleConfirmReject = () => {
    if (!rejectingRequestId) return;
    const req = leaveRequests.find(r => r.id === rejectingRequestId);
    onRejectLeave(rejectingRequestId, rejectionComment);
    setIsRejectOpen(false);
    setRejectionComment('');
    setRejectingRequestId(null);
    showToast(`Leave request from ${req?.employeeName || 'employee'} rejected.`);
  };

  // --- Filtered employees ---
  const filteredEmployees = employees.filter(member => {
    const fullName = `${member.name.split(' ')[0]} ${member.name.split(' ').slice(1).join(' ')}`.toLowerCase();
    const query = searchQuery.toLowerCase();
    const matchesSearch = fullName.includes(query) || member.email.toLowerCase().includes(query);
    const matchesRole = selectedRole === 'All Roles' || member.role.toLowerCase().includes(selectedRole.toLowerCase());
    const matchesStatus = selectedStatus === 'All Status' || employmentLabel(member.employmentStatus) === selectedStatus;
    return matchesSearch && matchesRole && matchesStatus;
  });

  const pendingRequests = leaveRequests.filter(req => req.status === 'Pending');

  // --- Render: Accountant (read-only) ---
  if (isAccountant) {
    return (
      <div className="flex-1 flex flex-col gap-6 animate-fade-in">
        {toast && (
          <div
            className={`fixed bottom-4 right-4 z-50 py-3 px-5 rounded-lg shadow-lg flex items-center gap-2 animate-fade-in text-body-sm font-semibold border ${
              toast.type === 'success'
                ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                : 'bg-red-50 text-red-800 border-red-200'
            }`}
          >
            {toast.type === 'success' ? <Check className="w-5 h-5 shrink-0" /> : <AlertCircle className="w-5 h-5 shrink-0" />}
            <span>{toast.message}</span>
          </div>
        )}
        <div>
          <h1 className="text-h1 font-black text-on-surface tracking-tight md:text-display">Team</h1>
          <p className="text-body-lg text-on-surface-variant mt-1">View team members.</p>
        </div>
        <div className="bg-surface-container-lowest rounded-xl shadow-sm border border-outline-variant/30 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[700px]">
              <thead>
                <tr className="border-b border-outline-variant bg-surface-container-lowest">
                  <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Name</th>
                  <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Email</th>
                  <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Role</th>
                  <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/40">
                {filteredEmployees.map((member) => (
                  <tr key={member.id} className="hover:bg-surface-container/50 transition-colors">
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center font-bold text-body-sm shrink-0">
                          {initialsOf(member.name)}
                        </div>
                        <div>
                          <div className="font-bold text-body-sm text-on-surface">{member.name}</div>
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-6 text-body-sm text-on-surface-variant font-medium">{member.email}</td>
                    <td className="py-4 px-6">
                      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border bg-surface-variant text-on-surface-variant border-outline-variant">
                        {member.role}
                      </span>
                    </td>
                    <td className="py-4 px-6">
                      <StatusBadge status={employmentLabel(member.employmentStatus)} />
                    </td>
                  </tr>
                ))}
                {filteredEmployees.length === 0 && (
                  <tr>
                    <td colSpan={4} className="py-12 px-6 text-center text-on-surface-variant font-medium">
                      No team members found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  }

  // --- Render: Admin (full control) ---
  if (isAdmin) {
    return (
      <div className="flex-1 flex flex-col gap-6 animate-fade-in">
        {toast && (
          <div
            className={`fixed bottom-4 right-4 z-50 py-3 px-5 rounded-lg shadow-lg flex items-center gap-2 animate-fade-in text-body-sm font-semibold border ${
              toast.type === 'success'
                ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                : 'bg-red-50 text-red-800 border-red-200'
            }`}
          >
            {toast.type === 'success' ? <Check className="w-5 h-5 shrink-0" /> : <AlertCircle className="w-5 h-5 shrink-0" />}
            <span>{toast.message}</span>
          </div>
        )}

        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-h1 font-black text-on-surface tracking-tight md:text-display">Team Dashboard</h1>
            <p className="text-body-lg text-on-surface-variant mt-1">Manage team members and leave requests.</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-outline-variant flex gap-4 select-none">
          <button
            onClick={() => setActiveSubTab('employees')}
            className={`py-3 px-1 font-bold text-body-sm border-b-2 transition-all cursor-pointer ${
              activeSubTab === 'employees'
                ? 'border-primary text-primary'
                : 'border-transparent text-on-surface-variant hover:text-on-surface'
            }`}
          >
            Employee Management
          </button>
          <button
            onClick={() => setActiveSubTab('leave-approvals')}
            className={`py-3 px-1 font-bold text-body-sm border-b-2 transition-all cursor-pointer flex items-center gap-2 ${
              activeSubTab === 'leave-approvals'
                ? 'border-primary text-primary'
                : 'border-transparent text-on-surface-variant hover:text-on-surface'
            }`}
          >
            Leave Approvals
            {pendingRequests.length > 0 && (
              <span className="bg-error text-on-error font-black text-[10px] w-5 h-5 rounded-full flex items-center justify-center animate-pulse">
                {pendingRequests.length}
              </span>
            )}
          </button>
        </div>

        {/* Employees Tab */}
        {activeSubTab === 'employees' && (
          <>
            <div className="bg-surface-container-lowest rounded-xl shadow-sm border border-outline-variant/30 p-4 flex flex-col md:flex-row gap-4 items-center justify-between">
              <div className="relative w-full md:max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-outline w-5 h-5" />
                <input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-surface border border-outline-variant rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all text-body-sm text-on-surface placeholder:text-outline"
                  placeholder="Search employees..."
                  type="text"
                />
              </div>
              <div className="flex items-center gap-3 w-full md:w-auto">
                <select
                  value={selectedRole}
                  onChange={(e) => setSelectedRole(e.target.value)}
                  className="w-full md:w-auto px-4 py-2 bg-surface border border-outline-variant rounded-lg focus:outline-none focus:border-primary text-body-sm text-on-surface cursor-pointer font-medium"
                >
                  <option value="All Roles">All Roles</option>
                  <option value="Developer">Developer</option>
                  <option value="Manager">Manager</option>
                  <option value="Administrator">Administrator</option>
                  <option value="Analyst">Analyst</option>
                </select>
                <select
                  value={selectedStatus}
                  onChange={(e) => setSelectedStatus(e.target.value)}
                  className="w-full md:w-auto px-4 py-2 bg-surface border border-outline-variant rounded-lg focus:outline-none focus:border-primary text-body-sm text-on-surface cursor-pointer font-medium"
                >
                  <option value="All Status">All Status</option>
                  <option value="Active">Active</option>
                  <option value="Inactive">Inactive</option>
                </select>
              </div>
            </div>

            <div className="bg-surface-container-lowest rounded-xl shadow-sm border border-outline-variant/30 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse min-w-[800px]">
                  <thead>
                    <tr className="border-b border-outline-variant bg-surface-container-lowest">
                      <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Name</th>
                      <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Email</th>
                      <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Role</th>
                      <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Status</th>
                      <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant/40">
                    {filteredEmployees.map((member) => (
                      <tr key={member.id} className="hover:bg-surface-container/50 transition-colors group">
                        <td className="py-4 px-6">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center font-bold text-body-sm shrink-0">
                              {initialsOf(member.name)}
                            </div>
                            <div>
                              <div className="font-bold text-body-sm text-on-surface">{member.name}</div>
                            </div>
                          </div>
                        </td>
                        <td className="py-4 px-6 text-body-sm text-on-surface-variant font-medium">{member.email}</td>
                        <td className="py-4 px-6">
                          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border bg-surface-variant text-on-surface-variant border-outline-variant">
                            {member.role}
                          </span>
                        </td>
                        <td className="py-4 px-6">
                          <StatusBadge status={employmentLabel(member.employmentStatus)} />
                        </td>
                        <td className="py-4 px-6 text-right">
                          <div className="flex justify-end gap-2 md:opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={() => showToast(`Edit ${member.name.split(' ')[0]} (not implemented yet)`, 'error')}
                              className="p-1.5 text-on-surface-variant hover:text-primary hover:bg-primary/10 rounded transition-colors cursor-pointer"
                              title="Edit Profile"
                            >
                              <Edit className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => showToast(`Toggle status for ${member.name.split(' ')[0]} (not implemented yet)`, 'error')}
                              className="p-1.5 text-on-surface-variant hover:text-error hover:bg-error-container/50 rounded transition-colors cursor-pointer"
                              title="Toggle Status"
                            >
                              <Ban className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {filteredEmployees.length === 0 && (
                      <tr>
                        <td colSpan={5} className="py-12 px-6 text-center text-on-surface-variant font-medium">
                          No employees found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              <div className="border-t border-outline-variant bg-surface-container-lowest px-6 py-4 flex items-center justify-between">
                <span className="text-body-sm text-on-surface-variant font-medium">
                  Showing {filteredEmployees.length} of {employees.length} employees
                </span>
              </div>
            </div>
          </>
        )}

        {/* Leave Approvals Tab */}
        {activeSubTab === 'leave-approvals' && (
          <div className="flex flex-col gap-6 animate-fade-in">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="glass-card rounded-xl p-6 flex items-center gap-4 border border-outline-variant/50 shadow-sm">
                <div className="w-12 h-12 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container shadow-sm">
                  <FileText className="w-6 h-6 text-[#00477b]" />
                </div>
                <div>
                  <div className="text-[11px] text-on-surface-variant font-bold uppercase tracking-wider mb-1">Pending Requests</div>
                  <div className="text-h1 font-black text-on-surface">{pendingRequests.length}</div>
                </div>
              </div>
              <div className="glass-card rounded-xl p-6 flex items-center gap-4 border border-outline-variant/50 shadow-sm">
                <div className="w-12 h-12 rounded-full bg-primary-fixed text-primary flex items-center justify-center shadow-sm">
                  <CheckCircle className="w-6 h-6 text-[#137333]" />
                </div>
                <div>
                  <div className="text-[11px] text-on-surface-variant font-bold uppercase tracking-wider mb-1">Approved Today</div>
                  <div className="text-h1 font-black text-on-surface">
                    {leaveRequests.filter(r => r.status === 'Approved').length}
                  </div>
                </div>
              </div>
              <div className="glass-card rounded-xl p-6 flex items-center gap-4 border border-outline-variant/50 shadow-sm">
                <div className="w-12 h-12 rounded-full bg-error-container text-on-error-container flex items-center justify-center shadow-sm">
                  <Calendar className="w-6 h-6 text-error" />
                </div>
                <div>
                  <div className="text-[11px] text-on-surface-variant font-bold uppercase tracking-wider mb-1">On Leave</div>
                  <div className="text-h1 font-black text-on-surface">0</div>
                </div>
              </div>
            </div>

            {/* Calendar Button */}
            <div className="flex justify-between items-center">
              <h2 className="text-body-lg font-bold text-on-surface">Pending Leave Requests</h2>
              <button
                onClick={() => setShowCalendar(true)}
                className="px-4 py-2 bg-primary/10 text-primary border border-primary/20 rounded-lg font-semibold text-caption hover:bg-primary/20 transition-colors flex items-center gap-2"
              >
                <Calendar className="w-4 h-4" />
                View Calendar
              </button>
            </div>

            <div className="glass-card rounded-xl overflow-hidden border border-outline-variant/50 bg-surface-container-lowest shadow-sm">
              <div className="overflow-x-auto w-full">
                <table className="w-full text-left border-collapse">
                  <thead className="bg-surface-container-low border-b border-outline-variant font-semibold text-caption text-on-surface-variant">
                    <tr>
                      <th className="px-6 py-4 uppercase tracking-wider">Employee</th>
                      <th className="px-6 py-4 uppercase tracking-wider">Dates</th>
                      <th className="px-6 py-4 uppercase tracking-wider">Type</th>
                      <th className="px-6 py-4 uppercase tracking-wider">Reason</th>
                      <th className="px-6 py-4 uppercase tracking-wider">Status</th>
                      <th className="px-6 py-4 uppercase tracking-wider text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="text-body-sm divide-y divide-outline-variant/40">
                    {pendingRequests.map((req) => (
                      <tr key={req.id} className="hover:bg-surface-container-low/50 transition-colors">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-9 h-9 rounded-full bg-secondary-fixed flex items-center justify-center text-on-secondary-fixed font-bold text-xs shadow-sm">
                              {req.employeeName.split(' ').map(n => n[0]).join('')}
                            </div>
                            <div>
                              <div className="font-bold text-on-surface">{req.employeeName}</div>
                              <div className="text-caption text-on-surface-variant font-medium">{req.jobTitle ?? '-'}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-on-surface font-semibold whitespace-nowrap">
                          {req.dates}
                          <br />
                          <span className="text-caption text-on-surface-variant font-medium">{req.duration} Days</span>
                        </td>
                        <td className="px-6 py-4">
                          <span className="px-2.5 py-1 rounded-full bg-surface-variant text-on-surface-variant text-xs font-semibold">
                            {req.type}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-on-surface font-medium max-w-xs truncate" title={req.reason}>
                          {req.reason || 'N/A'}
                        </td>
                        <td className="px-6 py-4">
                          <span className="px-2.5 py-1 rounded-full bg-tertiary-fixed text-on-tertiary-fixed-variant text-xs font-semibold flex items-center w-fit gap-1 shadow-sm">
                            <Calendar className="w-3.5 h-3.5" />
                            Pending
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right whitespace-nowrap">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => handleApprove(req.id, req.employeeName)}
                              className="px-3 py-1.5 rounded-lg bg-primary text-on-primary font-bold text-xs hover:bg-primary/90 transition-colors shadow-sm cursor-pointer"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => triggerReject(req.id)}
                              className="px-3 py-1.5 rounded-lg bg-error-container text-on-error-container font-bold text-xs hover:bg-error-container/85 transition-colors cursor-pointer border border-error/10"
                            >
                              Reject
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {pendingRequests.length === 0 && (
                      <tr>
                        <td colSpan={6} className="py-12 px-6 text-center text-on-surface-variant font-semibold">
                          No pending leave requests. ✨
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/*
          The Add Employee modal was removed in #65. It collected a name and
          an e-mail and posted nowhere: creating a person is two steps - a
          login account, then the employee record that carries the
          employment terms (#60) - and POST /api/employees needs a userId
          that already exists. That flow belongs with #62.
        */}

        {/* Reject Modal */}
        {isRejectOpen && (
          <div className="fixed inset-0 bg-on-background/50 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
            <div className="relative bg-surface-container-lowest rounded-xl shadow-[0_8px_32px_rgba(3,34,77,0.15)] w-full max-w-md p-6 border border-outline-variant animate-scale-up">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-h2 text-on-surface font-black m-0">Reject Leave Request</h2>
                <button className="text-on-surface-variant hover:text-on-surface p-1 rounded-full hover:bg-surface-variant transition-colors cursor-pointer" onClick={() => setIsRejectOpen(false)}>
                  <X className="w-5 h-5" />
                </button>
              </div>
              <p className="text-body-sm text-on-surface-variant mb-6">
                Please provide a reason for rejecting this leave request. This will be visible to the employee.
              </p>
              <div className="mb-6">
                <label className="block text-xs font-semibold text-on-surface mb-2" htmlFor="rejectComment">Rejection Reason</label>
                <textarea
                  value={rejectionComment}
                  onChange={(e) => setRejectionComment(e.target.value)}
                  className="w-full rounded-lg border border-outline-variant bg-surface px-3 py-2 text-body-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-primary focus:outline-none placeholder:text-outline/50 transition-shadow resize-none"
                  id="rejectComment"
                  placeholder="E.g., Project deadline conflicts..."
                  rows={4}
                ></textarea>
              </div>
              <div className="flex justify-end gap-3 pt-4 border-t border-outline-variant/30">
                <button
                  className="px-4 py-2 rounded-lg text-body-sm font-bold border border-outline text-on-surface hover:bg-surface-container-low transition-colors cursor-pointer"
                  onClick={() => setIsRejectOpen(false)}
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmReject}
                  className="px-4 py-2 rounded-lg text-body-sm font-bold bg-error text-on-error hover:bg-error/90 transition-colors cursor-pointer"
                >
                  Confirm Rejection
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Calendar Modal */}
        {showCalendar && (
          <CalendarView
            leaveRequests={leaveRequests}
            userRole={userRole}
            currentEmployeeId={undefined}
            onClose={() => setShowCalendar(false)}
          />
        )}
      </div>
    );
  }

  // --- Render: Employee (read-only directory, no actions) ---
  return (
    <div className="flex-1 flex flex-col gap-6 animate-fade-in">
      {toast && (
        <div
          className={`fixed bottom-4 right-4 z-50 py-3 px-5 rounded-lg shadow-lg flex items-center gap-2 animate-fade-in text-body-sm font-semibold border ${
            toast.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
              : 'bg-red-50 text-red-800 border-red-200'
          }`}
        >
          {toast.type === 'success' ? <Check className="w-5 h-5 shrink-0" /> : <AlertCircle className="w-5 h-5 shrink-0" />}
          <span>{toast.message}</span>
        </div>
      )}
      <div>
        <h1 className="text-h1 font-black text-on-surface tracking-tight md:text-display">Team Directory</h1>
        <p className="text-body-lg text-on-surface-variant mt-1">View and connect with your colleagues.</p>
      </div>
      <div className="bg-surface-container-lowest rounded-xl shadow-sm border border-outline-variant/30 p-4 flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="relative w-full md:max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-outline w-5 h-5" />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-surface border border-outline-variant rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all text-body-sm text-on-surface placeholder:text-outline"
            placeholder="Search employees..."
            type="text"
          />
        </div>
        <div className="flex items-center gap-3 w-full md:w-auto">
          <select
            value={selectedRole}
            onChange={(e) => setSelectedRole(e.target.value)}
            className="w-full md:w-auto px-4 py-2 bg-surface border border-outline-variant rounded-lg focus:outline-none focus:border-primary text-body-sm text-on-surface cursor-pointer font-medium"
          >
            <option value="All Roles">All Roles</option>
            <option value="Developer">Developer</option>
            <option value="Manager">Manager</option>
            <option value="Administrator">Administrator</option>
            <option value="Analyst">Analyst</option>
          </select>
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="w-full md:w-auto px-4 py-2 bg-surface border border-outline-variant rounded-lg focus:outline-none focus:border-primary text-body-sm text-on-surface cursor-pointer font-medium"
          >
            <option value="All Status">All Status</option>
            <option value="Active">Active</option>
            <option value="Inactive">Inactive</option>
          </select>
        </div>
      </div>
      <div className="bg-surface-container-lowest rounded-xl shadow-sm border border-outline-variant/30 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[800px]">
            <thead>
              <tr className="border-b border-outline-variant bg-surface-container-lowest">
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Name</th>
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Email</th>
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Role</th>
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/40">
              {filteredEmployees.map((member) => (
                <tr key={member.id} className="hover:bg-surface-container/50 transition-colors">
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center font-bold text-body-sm shrink-0">
                        {initialsOf(member.name)}
                      </div>
                      <div>
                        <div className="font-bold text-body-sm text-on-surface">{member.name}</div>
                      </div>
                    </div>
                  </td>
                  <td className="py-4 px-6 text-body-sm text-on-surface-variant font-medium">{member.email}</td>
                  <td className="py-4 px-6">
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border bg-surface-variant text-on-surface-variant border-outline-variant">
                      {member.role}
                    </span>
                  </td>
                  <td className="py-4 px-6">
                    <StatusBadge status={employmentLabel(member.employmentStatus)} />
                  </td>
                </tr>
              ))}
              {filteredEmployees.length === 0 && (
                <tr>
                  <td colSpan={4} className="py-12 px-6 text-center text-on-surface-variant font-medium">
                    No employees found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
