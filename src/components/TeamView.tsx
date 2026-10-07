import React, { useMemo, useState } from 'react';
import { Edit, Ban, CheckCircle, Calendar, FileText } from 'lucide-react';
import { Employee, LeaveRequest, UserRole } from '../types';
import CalendarView from './CalendarView';
import StatusBadge from './StatusBadge';
import Dialog from './ui/Dialog';
import Button from './ui/Button';
import Avatar from './ui/Avatar';
import { Field, Select, Textarea } from './ui/Field';
import { useToast } from './ui/feedback';
import { Table, THead, Th, TBody, Tr, Td, TableState } from './ui/Table';
import { FilterPills, SearchField, TableToolbar } from './ui/TableControls';
import { useDataStatus } from '../dataStatus';

interface TeamViewProps {
  userRole: UserRole;
  employees: Employee[];
  leaveRequests: LeaveRequest[];
  onApproveLeave: (id: string) => void;
  onRejectLeave: (id: string, comment: string) => void;
}

/** The employment status as a label, matching the StatusBadge vocabulary. */
function employmentLabel(status: string): string {
  if (status === 'active') return 'Active';
  if (status === 'on_leave') return 'On Hold';
  return 'Inactive';
}

const STATUS_FILTERS = ['All', 'Active', 'On Hold', 'Inactive'] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];
const ALL_ROLES = 'All roles';

/** 'YYYY-MM-DD' as a local date (see CalendarView). */
function localDate(value: string | undefined): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(value ?? '');
  return m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : null;
}

export default function TeamView({
  userRole,
  employees,
  leaveRequests,
  onApproveLeave,
  onRejectLeave,
}: TeamViewProps) {
  const isAdmin = userRole === 'admin';
  const isAccountant = userRole === 'accountant';
  const status = useDataStatus();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRole, setSelectedRole] = useState(ALL_ROLES);
  const [selectedStatus, setSelectedStatus] = useState<StatusFilter>('All');
  const [showCalendar, setShowCalendar] = useState(false);

  // Admin only
  const [activeSubTab, setActiveSubTab] = useState<'employees' | 'leave-approvals'>('employees');
  const [isRejectOpen, setIsRejectOpen] = useState(false);
  const [rejectingRequestId, setRejectingRequestId] = useState<string | null>(null);
  const [rejectionComment, setRejectionComment] = useState('');

  const toast = useToast();
  const showToast = (message: string, type: 'success' | 'error' = 'success') => toast(message, type);

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

  // --- Filters ---
  // Roles come from the employees themselves; the filter used to offer a
  // hard-coded "Developer / Manager / Administrator / Analyst" list.
  const roles = useMemo(
    () => Array.from(new Set(employees.map(e => e.role).filter(Boolean))).sort(),
    [employees]
  );

  const filteredEmployees = employees.filter(member => {
    const query = searchQuery.toLowerCase();
    const matchesSearch = member.name.toLowerCase().includes(query) || member.email.toLowerCase().includes(query);
    const matchesRole = selectedRole === ALL_ROLES || member.role === selectedRole;
    const matchesStatus = selectedStatus === 'All' || employmentLabel(member.employmentStatus) === selectedStatus;
    return matchesSearch && matchesRole && matchesStatus;
  });

  const pendingRequests = leaveRequests.filter(req => req.status === 'Pending');
  const approvedCount = leaveRequests.filter(r => r.status === 'Approved').length;
  // "On leave" was a hard-coded 0: count approved leave covering today.
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const onLeaveToday = leaveRequests.filter(r => {
    if (r.status !== 'Approved') return false;
    const start = localDate(r.startDate);
    const end = localDate(r.endDate);
    return !!start && !!end && start <= today && today <= end;
  }).length;

  // --- The employee directory, shared by the three roles ---
  const directory = (
    <>
      <TableToolbar>
        <SearchField label="Search employees" value={searchQuery} onChange={setSearchQuery} />
        <div className="flex flex-col gap-3 md:flex-row md:items-center">
          <FilterPills label="Filter by status" options={STATUS_FILTERS} value={selectedStatus} onChange={setSelectedStatus} />
          {roles.length > 1 && (
            <Select
              aria-label="Filter by role"
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value)}
              className="md:w-48"
            >
              <option value={ALL_ROLES}>{ALL_ROLES}</option>
              {roles.map(r => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </Select>
          )}
        </div>
      </TableToolbar>

      <Table
        caption="Team members"
        footer={
          employees.length > 0 && (
            <p className="border-t border-outline-variant px-5 py-3 text-sm text-on-surface-variant">
              <span className="font-mono tabular-nums text-on-surface">{filteredEmployees.length}</span> of{' '}
              <span className="font-mono tabular-nums text-on-surface">{employees.length}</span> employees
            </p>
          )
        }
      >
        <THead>
          <Th>Name</Th>
          <Th>Email</Th>
          <Th>Role</Th>
          <Th>Status</Th>
          {isAdmin && (
            <Th numeric>
              <span className="sr-only">Actions</span>
            </Th>
          )}
        </THead>
        <TBody>
          {filteredEmployees.map(member => (
            <Tr key={member.id}>
              <Td>
                <div className="flex items-center gap-3">
                  <Avatar name={member.name} />
                  <span className="font-semibold">{member.name}</span>
                </div>
              </Td>
              <Td muted>{member.email}</Td>
              <Td muted>{member.role || '-'}</Td>
              <Td>
                <StatusBadge status={employmentLabel(member.employmentStatus)} />
              </Td>
              {isAdmin && (
                <Td numeric>
                  {/* Always visible: they used to appear only on mouse hover,
                      so keyboard users never saw them. */}
                  <div className="flex justify-end gap-1">
                    <button
                      type="button"
                      onClick={() => showToast(`Edit ${member.name.split(' ')[0]} (not implemented yet)`, 'error')}
                      aria-label={`Edit ${member.name}`}
                      className="rounded-lg p-1.5 text-on-surface-variant transition-colors hover:bg-surface-container hover:text-on-surface cursor-pointer"
                    >
                      <Edit className="w-4 h-4" aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      onClick={() => showToast(`Toggle status for ${member.name.split(' ')[0]} (not implemented yet)`, 'error')}
                      aria-label={`Change the status of ${member.name}`}
                      className="rounded-lg p-1.5 text-on-surface-variant transition-colors hover:bg-error-container hover:text-error cursor-pointer"
                    >
                      <Ban className="w-4 h-4" aria-hidden="true" />
                    </button>
                  </div>
                </Td>
              )}
            </Tr>
          ))}
          {filteredEmployees.length === 0 &&
            (status.loading ? (
              <TableState kind="loading" colSpan={isAdmin ? 5 : 4} title="Loading the team..." />
            ) : status.error && employees.length === 0 ? (
              <TableState kind="error" colSpan={isAdmin ? 5 : 4} message={status.error} />
            ) : (
              <TableState
                kind="empty"
                colSpan={isAdmin ? 5 : 4}
                title={employees.length === 0 ? 'No team members yet' : 'No one matches'}
                message={employees.length === 0 ? undefined : 'Try another name, status or role.'}
              />
            ))}
        </TBody>
      </Table>
    </>
  );

  const header = (title: string, subtitle: string) => (
    <div>
      <h1 className="text-h1 font-black text-on-surface tracking-tight md:text-display">{title}</h1>
      <p className="text-body-lg text-on-surface-variant mt-1">{subtitle}</p>
    </div>
  );

  // --- Accountant and employee: read-only directory ---
  if (!isAdmin) {
    return (
      <div className="flex-1 flex flex-col gap-6 animate-fade-in">
        {isAccountant
          ? header('Team', 'View team members.')
          : header('Team Directory', 'View and connect with your colleagues.')}
        {directory}
      </div>
    );
  }

  // --- Admin: directory and leave approvals ---
  const tab = (id: 'employees' | 'leave-approvals', label: React.ReactNode) => (
    <button
      type="button"
      role="tab"
      aria-selected={activeSubTab === id}
      onClick={() => setActiveSubTab(id)}
      className={`-mb-px flex items-center gap-2 border-b-2 px-1 py-3 text-sm font-semibold transition-colors cursor-pointer ${
        activeSubTab === id
          ? 'border-primary text-on-surface'
          : 'border-transparent text-on-surface-variant hover:text-on-surface'
      }`}
    >
      {label}
    </button>
  );

  const stat = (label: string, value: number, Icon: React.ComponentType<{ className?: string }>) => (
    <div className="flex items-center gap-4 rounded-xl border border-outline-variant bg-surface-container-lowest p-5">
      <span className="flex h-11 w-11 items-center justify-center rounded-lg bg-surface-container-high">
        <Icon className="h-5 w-5 text-on-surface-variant" aria-hidden="true" />
      </span>
      <div>
        <p className="font-mono text-[11px] font-medium uppercase tracking-[0.08em] text-on-surface-variant">{label}</p>
        <p className="font-mono text-2xl font-semibold tabular-nums text-on-surface">{value}</p>
      </div>
    </div>
  );

  return (
    <div className="flex-1 flex flex-col gap-6 animate-fade-in">
      {header('Team Dashboard', 'Manage team members and leave requests.')}

      <div role="tablist" aria-label="Team sections" className="flex gap-6 border-b border-outline-variant">
        {tab('employees', 'Employee Management')}
        {tab(
          'leave-approvals',
          <>
            Leave Approvals
            {pendingRequests.length > 0 && (
              <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-danger px-1.5 font-mono text-[10px] font-medium text-on-error">
                {pendingRequests.length}
              </span>
            )}
          </>
        )}
      </div>

      {activeSubTab === 'employees' && directory}

      {activeSubTab === 'leave-approvals' && (
        <div className="flex flex-col gap-6 animate-fade-in">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {stat('Pending', pendingRequests.length, FileText)}
            {stat('Approved', approvedCount, CheckCircle)}
            {stat('On leave today', onLeaveToday, Calendar)}
          </div>

          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold tracking-[-0.02em] text-on-surface">Pending leave requests</h2>
            <Button variant="secondary" size="sm" onClick={() => setShowCalendar(true)}>
              <Calendar className="w-4 h-4" aria-hidden="true" />
              View calendar
            </Button>
          </div>

          <Table caption="Pending leave requests">
            <THead>
              <Th>Employee</Th>
              <Th numeric>Dates</Th>
              <Th>Type</Th>
              <Th>Reason</Th>
              {/* No status column: every row in this table is Pending. */}
              <Th numeric>
                <span className="sr-only">Decision</span>
              </Th>
            </THead>
            <TBody>
              {pendingRequests.map(req => (
                <Tr key={req.id}>
                  <Td>
                    <div className="flex items-center gap-3">
                      <Avatar name={req.employeeName} size="sm" />
                      <div className="whitespace-nowrap">
                        <div className="font-semibold">{req.employeeName}</div>
                        <div className="text-xs text-on-surface-variant">{req.jobTitle ?? '-'}</div>
                      </div>
                    </div>
                  </Td>
                  <Td numeric>
                    {req.dates}
                    <div className="text-xs text-on-surface-variant">
                      {req.duration} {req.duration === 1 ? 'day' : 'days'}
                    </div>
                  </Td>
                  <Td muted className="whitespace-nowrap">{req.type}</Td>
                  <Td muted className="max-w-48 truncate" title={req.reason}>
                    {req.reason || '-'}
                  </Td>
                  <Td numeric>
                    <div className="flex items-center justify-end gap-2">
                      <Button size="sm" onClick={() => handleApprove(req.id, req.employeeName)}>
                        Approve
                      </Button>
                      <Button size="sm" variant="secondary" onClick={() => triggerReject(req.id)}>
                        Reject
                      </Button>
                    </div>
                  </Td>
                </Tr>
              ))}
              {pendingRequests.length === 0 &&
                (status.loading ? (
                  <TableState kind="loading" colSpan={5} title="Loading leave requests..." />
                ) : (
                  <TableState kind="empty" colSpan={5} title="No pending leave requests" message="Every request has a decision." />
                ))}
            </TBody>
          </Table>
        </div>
      )}

      {/*
        The Add Employee modal was removed in #65. It collected a name and
        an e-mail and posted nowhere: creating a person is two steps - a
        login account, then the employee record that carries the
        employment terms (#60) - and POST /api/employees needs a userId
        that already exists. That flow belongs with #62.
      */}

      {/* Reject leave request */}
      <Dialog
        open={isRejectOpen}
        onClose={() => setIsRejectOpen(false)}
        title="Reject leave request"
        description="Give a reason for rejecting this request. The employee will see it."
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsRejectOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={handleConfirmReject}>
              Confirm rejection
            </Button>
          </>
        }
      >
        <Field label="Rejection reason">
          {({ id }) => (
            <Textarea
              id={id}
              rows={4}
              value={rejectionComment}
              onChange={(e) => setRejectionComment(e.target.value)}
              placeholder="E.g., Project deadline conflicts..."
            />
          )}
        </Field>
      </Dialog>

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
