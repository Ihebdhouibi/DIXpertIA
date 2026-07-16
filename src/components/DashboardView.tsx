import React from 'react';
import { 
  FolderOpen, FileText, Clock, Users, 
  CheckCircle, AlertCircle, XCircle, Calendar, 
  Download, Plus, ChevronRight
} from 'lucide-react';
import { User, Project, Invoice, LeaveRequest, TeamMember } from '../types';

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
  projects: Project[];
  invoices: Invoice[];
  leaveRequests: LeaveRequest[];
  teamMembers: TeamMember[];
  notifications: Notification[];
  onNavigate: (tab: string) => void;
  onQuickAction: (action: string) => void;
}

export default function DashboardView({
  user,
  projects,
  invoices,
  leaveRequests,
  teamMembers,
  notifications,
  onNavigate,
  onQuickAction,
}: DashboardViewProps) {
  // --- Statistics ---
  const totalProjects = projects.length;
  const totalInvoices = invoices.length;
  const totalInvoiceAmount = invoices.reduce((sum, inv) => sum + inv.amount, 0);
  const pendingLeaves = leaveRequests.filter(r => r.status === 'Pending').length;
  const activeTeam = teamMembers.filter(m => m.status === 'Active').length;

  // Project status breakdown
  const statusCounts = {
    Active: projects.filter(p => p.status === 'Active').length,
    'In Progress': projects.filter(p => p.status === 'In Progress').length,
    Completed: projects.filter(p => p.status === 'Completed').length,
    'On Hold': projects.filter(p => p.status === 'On Hold').length,
  };
  const maxStatusCount = Math.max(...Object.values(statusCounts), 1);

  // Invoice status breakdown
  const invoiceStats = {
    Paid: invoices.filter(i => i.status === 'Paid'),
    Sent: invoices.filter(i => i.status === 'Sent'),
    Overdue: invoices.filter(i => i.status === 'Overdue'),
    Draft: invoices.filter(i => i.status === 'Draft'),
  };

  // Recent notifications (last 5)
  const recentNotifications = notifications.slice(0, 5);

  // Employee-specific: leave balance
  const employeeLeaveRequests = leaveRequests.filter(r => r.employeeId === user.id);
  const approvedLeaves = employeeLeaveRequests.filter(r => r.status === 'Approved');
  const upcomingLeave = employeeLeaveRequests
    .filter(r => r.status === 'Approved')
    .sort((a, b) => new Date(a.dates.split('-')[0].trim()).getTime() - new Date(b.dates.split('-')[0].trim()).getTime())[0];

  // Latest payslip
  const latestPayslip = user.role === 'employee' 
    ? JSON.parse(localStorage.getItem('dixpertia_payslips') || '[]')[0] 
    : null;

  return (
    <div className="flex-1 flex flex-col gap-6 animate-fade-in">
      {/* Welcome header */}
      <div>
        <h1 className="text-h1 font-black text-on-surface tracking-tight md:text-display">
          Welcome back, {user.firstName}!
        </h1>
        <p className="text-body-lg text-on-surface-variant mt-1">
          Here's what's happening with your projects and team.
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-outline-variant shadow-sm flex items-center gap-4">
          <div className="p-3 rounded-full bg-primary/10 text-primary">
            <FolderOpen className="w-6 h-6" />
          </div>
          <div>
            <p className="text-caption font-semibold text-on-surface-variant">Total Projects</p>
            <p className="text-h2 font-black text-on-surface">{totalProjects}</p>
          </div>
        </div>
        <div className="bg-white p-5 rounded-xl border border-outline-variant shadow-sm flex items-center gap-4">
          <div className="p-3 rounded-full bg-secondary/10 text-secondary">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <p className="text-caption font-semibold text-on-surface-variant">Invoices</p>
            <p className="text-h2 font-black text-on-surface">
              {totalInvoices}
              <span className="text-body-sm font-medium text-on-surface-variant ml-1">
                (${totalInvoiceAmount.toLocaleString()})
              </span>
            </p>
          </div>
        </div>
        <div className="bg-white p-5 rounded-xl border border-outline-variant shadow-sm flex items-center gap-4">
          <div className="p-3 rounded-full bg-amber-50 text-amber-600">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <p className="text-caption font-semibold text-on-surface-variant">Pending Leaves</p>
            <p className="text-h2 font-black text-on-surface">{pendingLeaves}</p>
          </div>
        </div>
        <div className="bg-white p-5 rounded-xl border border-outline-variant shadow-sm flex items-center gap-4">
          <div className="p-3 rounded-full bg-emerald-50 text-emerald-600">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <p className="text-caption font-semibold text-on-surface-variant">Active Team</p>
            <p className="text-h2 font-black text-on-surface">{activeTeam}</p>
          </div>
        </div>
      </div>

      {/* Two‑column layout: Charts + Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column (2/3): charts */}
        <div className="lg:col-span-2 space-y-6">
          {/* Project Status Bar Chart */}
          <div className="bg-white p-6 rounded-xl border border-outline-variant shadow-sm">
            <h3 className="font-bold text-body-lg text-on-surface mb-4">Projects by Status</h3>
            <div className="space-y-3">
              {Object.entries(statusCounts).map(([status, count]) => (
                <div key={status} className="flex items-center gap-3">
                  <span className="text-caption font-semibold text-on-surface-variant w-24">{status}</span>
                  <div className="flex-1 h-3 bg-surface-variant rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        status === 'Active' ? 'bg-blue-500' :
                        status === 'In Progress' ? 'bg-amber-500' :
                        status === 'Completed' ? 'bg-emerald-500' :
                        'bg-gray-400'
                      } transition-all duration-500`}
                      style={{ width: `${(count / maxStatusCount) * 100}%` }}
                    />
                  </div>
                  <span className="text-caption font-bold text-on-surface w-8 text-right">{count}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Invoice Status Breakdown */}
          <div className="bg-white p-6 rounded-xl border border-outline-variant shadow-sm">
            <h3 className="font-bold text-body-lg text-on-surface mb-4">Invoices by Status</h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {Object.entries(invoiceStats).map(([status, items]) => (
                <div key={status} className="p-3 rounded-lg bg-surface-container-low border border-outline-variant/30 text-center">
                  <p className="text-caption font-semibold text-on-surface-variant">{status}</p>
                  <p className="text-h2 font-black text-on-surface">{items.length}</p>
                  <p className="text-caption font-medium text-on-surface-variant">
                    ${items.reduce((sum, i) => sum + i.amount, 0).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Admin Quick Actions */}
          {user.role === 'admin' && (
            <div className="bg-white p-6 rounded-xl border border-outline-variant shadow-sm">
              <h3 className="font-bold text-body-lg text-on-surface mb-4">Quick Actions</h3>
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={() => onQuickAction('approve-leaves')}
                  className="px-4 py-2 bg-amber-50 text-amber-700 border border-amber-200 rounded-lg font-semibold text-caption hover:bg-amber-100 transition-colors flex items-center gap-2"
                >
                  <Clock className="w-4 h-4" />
                  Approve Leaves
                </button>
                <button
                  onClick={() => onQuickAction('create-invoice')}
                  className="px-4 py-2 bg-primary/10 text-primary border border-primary/20 rounded-lg font-semibold text-caption hover:bg-primary/20 transition-colors flex items-center gap-2"
                >
                  <FileText className="w-4 h-4" />
                  Create Invoice
                </button>
                <button
                  onClick={() => onQuickAction('add-project')}
                  className="px-4 py-2 bg-secondary/10 text-secondary border border-secondary/20 rounded-lg font-semibold text-caption hover:bg-secondary/20 transition-colors flex items-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  Add Project
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right column (1/3): Recent Activity & Employee Widgets */}
        <div className="space-y-6">
          {/* Employee-specific widgets */}
          {user.role === 'employee' && (
            <div className="bg-white p-6 rounded-xl border border-outline-variant shadow-sm">
              <h3 className="font-bold text-body-lg text-on-surface mb-4">Your Leave Balance</h3>
              <div className="space-y-2 text-caption">
                <div className="flex justify-between">
                  <span className="text-on-surface-variant">Annual Leave</span>
                  <span className="font-bold text-on-surface">14 days left</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-on-surface-variant">Sick Leave</span>
                  <span className="font-bold text-on-surface">5 days left</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-on-surface-variant">Personal Days</span>
                  <span className="font-bold text-on-surface">2 days left</span>
                </div>
                {upcomingLeave && (
                  <div className="mt-4 pt-4 border-t border-outline-variant/30">
                    <p className="text-caption font-semibold text-on-surface-variant">Upcoming Leave</p>
                    <p className="text-body-sm font-bold text-on-surface">{upcomingLeave.type}</p>
                    <p className="text-caption text-on-surface-variant">{upcomingLeave.dates}</p>
                  </div>
                )}
                {latestPayslip && (
                  <div className="mt-4 pt-4 border-t border-outline-variant/30">
                    <p className="text-caption font-semibold text-on-surface-variant">Latest Payslip</p>
                    <button
                      onClick={() => onQuickAction('download-payslip')}
                      className="mt-1 text-primary font-semibold text-caption hover:underline flex items-center gap-1"
                    >
                      <Download className="w-3 h-3" />
                      {latestPayslip.period}
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Recent Notifications */}
          <div className="bg-white p-6 rounded-xl border border-outline-variant shadow-sm">
            <h3 className="font-bold text-body-lg text-on-surface mb-4">Recent Activity</h3>
            {recentNotifications.length === 0 ? (
              <p className="text-caption text-on-surface-variant">No recent activity</p>
            ) : (
              <ul className="divide-y divide-outline-variant/30 -mx-2">
                {recentNotifications.map((notif) => (
                  <li
                    key={notif.id}
                    className={`px-2 py-2.5 hover:bg-surface-container-low rounded-lg transition-colors cursor-pointer ${!notif.read ? 'bg-primary/5' : ''}`}
                    onClick={() => {
                      if (notif.link) {
                        onNavigate(notif.link);
                      }
                    }}
                  >
                    <div className="flex items-start gap-2">
                      {notif.type === 'warning' && <AlertCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />}
                      {notif.type === 'success' && <CheckCircle className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />}
                      {notif.type === 'error' && <XCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />}
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-on-surface truncate">{notif.message}</p>
                        <p className="text-[10px] text-outline mt-0.5">
                          {new Date(notif.timestamp).toLocaleString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </p>
                      </div>
                      {notif.link && (
                        <ChevronRight className="w-4 h-4 text-outline shrink-0 mt-1" />
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
            <button
              onClick={() => onNavigate('notifications')}
              className="mt-3 text-caption text-primary font-semibold hover:underline flex items-center gap-1"
            >
              View all
              <ChevronRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}