import React, { useCallback, useEffect, useState } from 'react';
import { Client, Employee, Invoice, LeaveRequest, Payslip, User } from './types';
import * as api from './api';
import Login from './components/Login';
import Homepage from './components/Homepage';
import { ThemeScope } from './theme';
import Sidebar from './components/Sidebar';
import PayslipsView from './components/PayslipsView';
import LeaveRequestsView from './components/LeaveRequestsView';
import TeamView from './components/TeamView';
import InvoicesView from './components/InvoicesView';
import DashboardView from './components/DashboardView';
import NotificationsView from './components/NotificationsView';
import SettingsView from './components/SettingsView';
import UsersView from './components/UsersView';
import ForgotPassword from './components/ForgotPassword';   // NEW
import ResetPassword from './components/ResetPassword';     // NEW
import {
  Bell,
  Menu,
  HelpCircle,
  AlertCircle,
  CheckCircle,
  X,
  User as UserIcon,
  Settings,
  LogOut
} from 'lucide-react';

interface Notification {
  id: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  read: boolean;
  timestamp: number;
  link?: string;
  targetRole?: 'admin' | 'employee';
  /**
   * When true the notification is shown for this session only and is never
   * written to localStorage. Use it for anything containing a secret - a
   * persisted notification outlives the reason it was shown.
   */
  ephemeral?: boolean;
}

interface AppUser extends User {
  isActive: boolean;
  isVerified: boolean;
  createdAt: string;
}

export default function App() {
  // --- State ---
  // Nothing is seeded from a fixture and nothing is read back from
  // localStorage: every entity below is loaded from the API once there is a
  // signed-in user, and reloaded after any change (#65). Business data now
  // lives in one place - the database - so what the admin creates the
  // accountant sees, and clearing the browser loses nothing.
  const [currentUser, setCurrentUser] = useState<AppUser | null>(null);
  const [sessionChecked, setSessionChecked] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [payslips, setPayslips] = useState<Payslip[]>([]);
  const [leaveRequests, setLeaveRequests] = useState<LeaveRequest[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [users, setUsers] = useState<AppUser[]>([]);
  const [clients, setClients] = useState<Client[]>([]);

  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [isOpenMobile, setIsOpenMobile] = useState(false);
  const [notificationCount, setNotificationCount] = useState(0);
  const [showNotificationList, setShowNotificationList] = useState(false);
  const [showHomepage, setShowHomepage] = useState(true);
  const [showUserDropdown, setShowUserDropdown] = useState(false);
  const [showLogin, setShowLogin] = useState(false);
  const [showForgotPassword, setShowForgotPassword] = useState(false);   // NEW
  const [resetToken, setResetToken] = useState<string | null>(null);    // NEW

  // --- Detect reset token from URL ---
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    if (token) {
      setResetToken(token);
      setShowForgotPassword(false);
    }
  }, []);

  // --- Notifications state ---
  // Session-only. These were persisted to localStorage, which outlived the
  // reason they were shown and could not be seen by anyone else anyway. Real,
  // server-side notifications tied to actual events belong with the accountant
  // workflow (#64).
  const [notifications, setNotifications] = useState<Notification[]>([]);

  useEffect(() => {
    setNotificationCount(notifications.filter(n => !n.read).length);
  }, [notifications]);

  const addNotification = (
    message: string,
    type: Notification['type'] = 'info',
    link?: string,
    targetRole?: 'admin' | 'employee',
    ephemeral = false
  ) => {
    const newNotif: Notification = {
      id: `notif-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`,
      message,
      type,
      read: false,
      timestamp: Date.now(),
      link,
      targetRole,
      ephemeral,
    };
    setNotifications(prev => [newNotif, ...prev]);
  };

  // --- Loading everything from the API ---

  const refresh = useCallback(async (user: AppUser) => {
    // Each call is scoped by the server: an employee's request returns their
    // own payslips and leave, an admin's returns everyone's. The row-level
    // security policies decide that, not this code, so there is no role check
    // here to drift out of step.
    const isPrivileged = user.role === 'admin' || user.role === 'accountant';
    const results = await Promise.allSettled([
      api.payslips.list(),
      api.leaveRequests.list(),
      api.employees.list(),
      isPrivileged ? api.invoices.list({ limit: 200 }) : Promise.resolve([]),
      user.role === 'admin' ? api.users.list() : Promise.resolve([]),
      isPrivileged ? api.clients.list() : Promise.resolve([]),
    ]);

    const [p, l, e, i, u, c] = results;
    if (p.status === 'fulfilled') setPayslips(p.value);
    if (l.status === 'fulfilled') setLeaveRequests(l.value);
    if (e.status === 'fulfilled') setEmployees(e.value);
    if (i.status === 'fulfilled') setInvoices(i.value as Invoice[]);
    if (u.status === 'fulfilled') setUsers(u.value as AppUser[]);
    if (c.status === 'fulfilled') setClients(c.value as Client[]);

    // allSettled rather than all: one failing list should not blank the other
    // four. The first real failure is surfaced, the rest are left to the next
    // refresh.
    const failed = results.find(r => r.status === 'rejected');
    setLoadError(failed ? (failed as PromiseRejectedResult).reason?.message ?? 'Could not load data' : null);
  }, []);

  // Restore the session from the token alone. The user is never read from
  // localStorage: the client would then be deciding its own role.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!api.getToken()) {
        setSessionChecked(true);
        return;
      }
      try {
        const me = await api.auth.me();
        if (cancelled) return;
        setCurrentUser(me);
        setShowHomepage(false);
        await refresh(me);
      } catch {
        // An expired or invalid token: fall back to the public site.
        api.setToken(null);
      } finally {
        if (!cancelled) setSessionChecked(true);
      }
    })();
    return () => { cancelled = true; };
  }, [refresh]);

  // Send the user back to the public site when the API rejects the token.
  useEffect(() => {
    api.setUnauthorizedHandler(() => {
      setCurrentUser(null);
      setShowHomepage(true);
    });
  }, []);

  // --- Handlers with real API calls ---

  // Authentication goes through POST /api/login only. The role, and every other
  // user attribute, comes from the server's response - never from the client.
  const handleLogin = async (email: string, password: string) => {
    try {
      const data = await api.auth.login(email, password);
      api.setToken(data.access_token);
      const appUser = data.user as AppUser;
      setCurrentUser(appUser);
      setActiveTab('dashboard');
      setShowHomepage(false);
      setShowLogin(false);
      addNotification(`Welcome back, ${appUser.firstName}!`, 'success');
      await refresh(appUser);
    } catch (error) {
      const message = error instanceof api.ApiError ? error.message : 'Network error during login';
      addNotification(`Login failed: ${message}`, 'error');
    }
  };

  const handleLogout = () => {
    setCurrentUser(null);
    api.setToken(null);
    // Business data is dropped with the session rather than left in memory for
    // whoever signs in next on this browser.
    setPayslips([]);
    setLeaveRequests([]);
    setEmployees([]);
    setInvoices([]);
    setUsers([]);
    setClients([]);
    setNotifications([]);
    setShowHomepage(true);
    setShowUserDropdown(false);
    setShowLogin(false);
  };

  // handleToggleRole is gone (#66). It rewrote the signed-in user's role, name
  // and id in the browser and re-rendered the admin screens on top of mock
  // data. The server always refused the admin actions, so nothing could be
  // done with it - but it showed every employee an admin view of fictional
  // numbers, which is worse than refusing outright.

  // --- Leave handlers ---
  //
  // Each one calls the API and then reloads from it, rather than editing local
  // state and hoping the two agree. The server applies the rules - who may
  // approve, that nobody validates their own request - so the reloaded list is
  // the truth, including any change someone else made meanwhile.

  const withRefresh = async (action: () => Promise<unknown>, failure: string) => {
    if (!currentUser) return;
    try {
      await action();
      await refresh(currentUser);
    } catch (error) {
      const message = error instanceof api.ApiError ? error.message : failure;
      addNotification(message, 'error');
    }
  };

  const handleAddLeaveRequest = (newReq: Partial<LeaveRequest>) =>
    withRefresh(
      () => api.leaveRequests.create({
        type: newReq.type ?? 'Annual Leave',
        startDate: newReq.startDate,
        endDate: newReq.endDate,
        reason: newReq.reason ?? '',
      }),
      'Could not submit the leave request',
    );

  const handleApproveLeave = (id: string) =>
    withRefresh(() => api.leaveRequests.approve(id), 'Could not approve the request');

  const handleRejectLeave = (id: string, comment: string) =>
    withRefresh(() => api.leaveRequests.reject(id, comment), 'Could not reject the request');

  const handleAddInvoice = (newInv: { client_id: number; date_echeance: string; items: unknown[] }) =>
    withRefresh(() => api.invoices.create(newInv), 'Could not create the invoice');

  const handleAddUser = (body: unknown) =>
    withRefresh(() => api.users.create(body), 'Could not create the account');

  // --- Quick actions ---
  const handleQuickAction = (action: string) => {
    switch (action) {
      case 'approve-leaves': setActiveTab('team'); break;
      case 'create-invoice': setActiveTab('reports'); break;
      case 'download-payslip': setActiveTab('payslips'); break;
      case 'view-notifications': setActiveTab('notifications'); break;
      default: break;
    }
  };

  const handleGoHome = () => {
    setShowHomepage(true);
    setShowUserDropdown(false);
    setShowLogin(false);
  };

  const handleGoToDashboard = () => {
    setShowHomepage(false);
    setShowLogin(false);
  };

  // Leave and payroll belong to the employee record, not the login account
  // (#60), so "mine" means this id. An admin account with no employee record
  // has no leave of its own, which is correct.
  const myEmployeeId = employees.find(e => e.userId === currentUser?.id)?.id;

  // --- Notification filter ---
  const visibleNotifications = notifications.filter(n => {
    if (!n.targetRole) return true;
    return n.targetRole === currentUser?.role;
  });

  const renderTabContent = () => {
    if (!currentUser) return null;

    switch (activeTab) {
      case 'dashboard':
        return (
          <DashboardView
            user={currentUser}
            invoices={invoices}
            payslips={payslips}
            leaveRequests={leaveRequests}
            employees={employees}
            notifications={visibleNotifications}
            onNavigate={(tab: string) => {
              setActiveTab(tab);
              setShowNotificationList(false);
            }}
            onQuickAction={handleQuickAction}
          />
        );

      case 'notifications':
        return (
          <NotificationsView
            notifications={visibleNotifications}
            onMarkRead={(id) => {
              setNotifications(prev =>
                prev.map(n => n.id === id ? { ...n, read: true } : n)
              );
            }}
            onMarkAllRead={() => {
              setNotifications(prev =>
                prev.map(n => ({ ...n, read: true }))
              );
            }}
            onClearAll={() => {
              if (window.confirm('Delete all notifications?')) {
                setNotifications([]);
              }
            }}
            onNavigate={(link) => {
              setActiveTab(link);
              setShowNotificationList(false);
            }}
            userRole={currentUser.role}
          />
        );

      case 'settings':
        return <SettingsView user={currentUser} onLogout={handleLogout} />;

      case 'invoices':
        return <InvoicesView invoices={invoices} clients={clients} onAddInvoice={handleAddInvoice} userRole={currentUser.role} />;

      case 'leave-requests':
        // Employees only. Hiding the sidebar entry is not enough on its own -
        // activeTab can be reached by other paths, so the view guards too (#10).
        if (currentUser.role !== 'employee') {
          return (
            <div className="flex-1 flex flex-col gap-6 animate-fade-in">
              <div className="bg-surface-container-lowest p-8 rounded-xl border border-outline-variant shadow-sm text-center max-w-2xl mx-auto">
                <h2 className="text-h2 font-black text-on-surface">Access Denied</h2>
                <p className="text-body-sm text-on-surface-variant mt-2">You do not have permission to view leave requests.</p>
              </div>
            </div>
          );
        }
        return (
          <LeaveRequestsView
            leaveRequests={leaveRequests.filter(req => req.employeeId === myEmployeeId)}
            onAddRequest={handleAddLeaveRequest}
            userRole={currentUser.role}
            currentEmployeeId={myEmployeeId}
          />
        );

      case 'users':
        if (currentUser.role !== 'admin' && currentUser.role !== 'accountant') {
          return (
            <div className="flex-1 flex flex-col gap-6 animate-fade-in">
              <div className="bg-surface-container-lowest p-8 rounded-xl border border-outline-variant shadow-sm text-center max-w-2xl mx-auto">
                <h2 className="text-h2 font-black text-on-surface">Access Denied</h2>
                <p className="text-body-sm text-on-surface-variant mt-2">You do not have permission to view this page.</p>
              </div>
            </div>
          );
        }
        const isAdmin = currentUser.role === 'admin';
        // onEditUser and onDeleteUser are deliberately not passed: the API has
        // no endpoint for either, and the buttons previously only changed the
        // browser. Server-side account lifecycle is #62.
        return (
          <UsersView
            users={users}
            onAddUser={isAdmin ? handleAddUser : undefined}
            userRole={currentUser.role}
          />
        );

      case 'payslips':
        if (currentUser.role === 'admin') {
          return <InvoicesView invoices={invoices} clients={clients} onAddInvoice={handleAddInvoice} userRole={currentUser.role} />;
        }
        return <PayslipsView payslips={payslips} userRole={currentUser.role} />;

      case 'reports':
        if (currentUser.role === 'admin') {
          return <InvoicesView invoices={invoices} clients={clients} onAddInvoice={handleAddInvoice} userRole={currentUser.role} />;
        }
        return (
          <LeaveRequestsView
            leaveRequests={leaveRequests.filter(req => req.employeeId === myEmployeeId)}
            onAddRequest={handleAddLeaveRequest}
            userRole={currentUser.role}
          />
        );

      case 'team':
        return (
          <TeamView
            userRole={currentUser.role}
            employees={employees}
            leaveRequests={leaveRequests}
            onApproveLeave={handleApproveLeave}
            onRejectLeave={handleRejectLeave}
          />
        );

      default:
        return (
          <div className="flex-1 flex flex-col gap-6 animate-fade-in">
            <div className="bg-surface-container-lowest p-8 rounded-xl border border-outline-variant shadow-sm text-center max-w-2xl mx-auto flex flex-col items-center justify-center gap-4 mt-8">
              <div className="w-16 h-16 rounded-full bg-primary/10 text-primary flex items-center justify-center">
                <HelpCircle className="w-10 h-10" />
              </div>
              <h2 className="text-h2 font-black text-on-surface">Module "{activeTab.toUpperCase()}" is being deployed</h2>
              <p className="text-body-sm text-on-surface-variant leading-relaxed">
                The interactive module <strong className="text-primary">{activeTab}</strong> is currently in secure deployment testing.
              </p>
              <button
                onClick={() => setActiveTab('dashboard')}
                className="bg-primary text-on-primary font-bold text-body-sm px-6 py-2.5 rounded-lg hover:bg-primary/95 transition-all cursor-pointer shadow-sm mt-2"
              >
                Back to Dashboard
              </button>
            </div>
          </div>
        );
    }
  };

  // --- RENDERING LOGIC (NEW ORDER) ---

  // 0. Hold the first paint until the token has been checked.
  //
  // Without this a signed-in user sees the public homepage for a moment on
  // every reload, because the session is restored asynchronously and
  // showHomepage starts true. A password-reset link is exempt: it carries its
  // own token in the URL and does not need a session.
  if (!sessionChecked && !resetToken) {
    return (
      <ThemeScope>
        <div className="min-h-screen bg-background flex items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 rounded-full border-2 border-outline-variant border-t-primary animate-spin" />
            <p className="text-body-sm text-on-surface-variant">Signing you in...</p>
          </div>
        </div>
      </ThemeScope>
    );
  }

  // 1. If resetToken is present, show ResetPassword
  if (resetToken) {
    return (
      <ThemeScope>
      <ResetPassword
        token={resetToken}
        onComplete={() => {
          setResetToken(null);
          window.history.replaceState({}, document.title, window.location.pathname);
          setShowLogin(true);
        }}
      />
      </ThemeScope>
    );
  }

  // 2. If showForgotPassword is true, show ForgotPassword
  if (showForgotPassword) {
    return (
      <ThemeScope>
        <ForgotPassword onBack={() => setShowForgotPassword(false)} />
      </ThemeScope>
    );
  }

  // 3. If showLogin is true, show Login
  if (showLogin) {
    return (
      <ThemeScope>
      <Login
        onLogin={handleLogin}
        onBackHome={() => { setShowLogin(false); setShowHomepage(true); }}
        onForgotPassword={() => setShowForgotPassword(true)}
      />
      </ThemeScope>
    );
  }

  // 4. Public site: always for visitors, and for a signed-in user who went
  // back to it. Its single "Go to Dashboard" button opens the app when signed
  // in and the login form otherwise.
  if (!currentUser || showHomepage) {
    return (
      <Homepage onDashboardClick={currentUser ? handleGoToDashboard : () => setShowLogin(true)} />
    );
  }

  // 5. Otherwise, show the dashboard
  return (
    <ThemeScope><div className="min-h-screen bg-background flex flex-col md:flex-row text-on-background font-sans">
      <Sidebar
        currentUser={currentUser}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onLogout={handleLogout}
        isOpenMobile={isOpenMobile}
        setIsOpenMobile={setIsOpenMobile}
        onGoHome={handleGoHome}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 bg-surface-container-lowest border-b border-outline-variant px-6 flex items-center justify-between sticky top-0 z-40 shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsOpenMobile(true)}
              className="p-1.5 hover:bg-surface-container rounded-lg md:hidden text-on-surface-variant transition-colors cursor-pointer"
              title="Menu"
            >
              <Menu className="w-6 h-6" />
            </button>
            <div className="hidden sm:flex items-center gap-2">
              <span className="text-caption font-bold text-outline uppercase tracking-wider">DIXpertIA</span>
              <span className="text-caption text-outline-variant">/</span>
              <span className="text-caption font-bold text-primary capitalize">{activeTab}</span>
            </div>
          </div>

          <div className="flex items-center gap-4 relative">
            <div className="hidden lg:flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10 border border-primary/20">
              <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></div>
              <span className="text-[11px] font-black uppercase text-primary tracking-wider">
                {currentUser.role === 'admin' ? 'HR Admin' : currentUser.role === 'accountant' ? 'Accountant' : 'Employee'} View
              </span>
            </div>

            {/* Notification Bell */}
            <div className="relative">
              <button
                onClick={() => setShowNotificationList(!showNotificationList)}
                className="p-1.5 hover:bg-surface-container text-on-surface-variant hover:text-on-surface rounded-full transition-all relative cursor-pointer"
                title="Notifications"
              >
                <Bell className="w-5 h-5" />
                {notificationCount > 0 && (
                  <span className="absolute top-1 right-1 w-4 h-4 bg-error text-on-error font-black text-[9px] rounded-full flex items-center justify-center animate-bounce shadow-sm">
                    {notificationCount}
                  </span>
                )}
              </button>

              {showNotificationList && (
                <div className="absolute right-0 mt-2 w-80 bg-surface-container-lowest rounded-xl shadow-[0_4px_24px_rgba(3,34,77,0.12)] border border-outline-variant/60 py-2 z-50 animate-scale-up">
                  <div className="px-4 py-2 border-b border-outline-variant/40 flex justify-between items-center bg-surface">
                    <span className="font-bold text-caption text-on-surface">Notifications</span>
                    <div className="flex gap-2">
                      {visibleNotifications.some(n => !n.read) && (
                        <button
                          onClick={() => {
                            setNotifications(prev =>
                              prev.map(n =>
                                !n.targetRole || n.targetRole === currentUser.role
                                  ? { ...n, read: true }
                                  : n
                              )
                            );
                          }}
                          className="text-xs text-secondary hover:underline cursor-pointer"
                        >
                          Mark all read
                        </button>
                      )}
                      <button
                        onClick={() => setShowNotificationList(false)}
                        className="text-xs text-secondary hover:underline cursor-pointer"
                      >
                        Close
                      </button>
                    </div>
                  </div>
                  <div className="divide-y divide-outline-variant/30 max-h-64 overflow-y-auto">
                    {visibleNotifications.length === 0 ? (
                      <div className="px-4 py-6 text-center text-xs text-on-surface-variant">
                        No notifications
                      </div>
                    ) : (
                      visibleNotifications.slice(0, 10).map((notif) => (
                        <div
                          key={notif.id}
                          className={`px-4 py-2.5 hover:bg-surface transition-colors cursor-pointer ${
                            !notif.read ? 'bg-primary/5' : ''
                          }`}
                          onClick={() => {
                            setNotifications(prev =>
                              prev.map(n => n.id === notif.id ? { ...n, read: true } : n)
                            );
                            if (notif.link) {
                              setActiveTab(notif.link);
                              setShowNotificationList(false);
                            }
                          }}
                        >
                          <div className="flex items-start gap-2">
                            {notif.type === 'warning' && <AlertCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />}
                            {notif.type === 'success' && <CheckCircle className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />}
                            {notif.type === 'error' && <X className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />}
                            <div className="flex-1">
                              <p className="text-xs font-semibold text-on-surface">{notif.message}</p>
                              <p className="text-[10px] text-outline mt-1">
                                {new Date(notif.timestamp).toLocaleString('en-US', {
                                  month: 'short',
                                  day: 'numeric',
                                  hour: '2-digit',
                                  minute: '2-digit',
                                })}
                              </p>
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* User Avatar with Dropdown */}
            <div className="relative">
              <button
                onClick={() => setShowUserDropdown(!showUserDropdown)}
                className="w-8 h-8 rounded-full bg-primary text-on-primary font-bold text-xs flex items-center justify-center shadow-sm hover:opacity-80 transition cursor-pointer select-none"
                title="User menu"
              >
                {currentUser.firstName[0]}{currentUser.lastName[0]}
              </button>

              {showUserDropdown && (
                <div className="absolute right-0 mt-2 w-48 bg-surface-container-lowest rounded-xl shadow-[0_4px_24px_rgba(3,34,77,0.12)] border border-outline-variant/60 py-1 z-50 animate-scale-up">
                  <div className="px-4 py-2 border-b border-outline-variant/30">
                    <p className="text-xs font-bold text-on-surface">{currentUser.firstName} {currentUser.lastName}</p>
                    <p className="text-[10px] text-on-surface-variant">{currentUser.email}</p>
                  </div>
                  <button
                    onClick={() => {
                      setActiveTab('settings');
                      setShowUserDropdown(false);
                    }}
                    className="w-full text-left px-4 py-2 text-body-sm hover:bg-surface-container-low transition-colors flex items-center gap-2 cursor-pointer"
                  >
                    <UserIcon className="w-4 h-4" />
                    Profile
                  </button>
                  <button
                    onClick={() => {
                      setActiveTab('settings');
                      setShowUserDropdown(false);
                    }}
                    className="w-full text-left px-4 py-2 text-body-sm hover:bg-surface-container-low transition-colors flex items-center gap-2 cursor-pointer"
                  >
                    <Settings className="w-4 h-4" />
                    Settings
                  </button>
                  <hr className="border-outline-variant/30 my-1" />
                  <button
                    onClick={() => {
                      handleLogout();
                      setShowUserDropdown(false);
                    }}
                    className="w-full text-left px-4 py-2 text-body-sm text-error hover:bg-error-container/30 transition-colors flex items-center gap-2 cursor-pointer"
                  >
                    <LogOut className="w-4 h-4" />
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        <main className="flex-1 p-4 md:p-8 overflow-y-auto max-w-[1400px] w-full mx-auto">
          {loadError && (
            <div
              role="alert"
              className="mb-4 flex items-start gap-3 rounded-lg border border-danger/40 bg-danger-container px-4 py-3"
            >
              <AlertCircle className="w-5 h-5 text-danger shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-body-sm font-semibold text-danger">Some data could not be loaded</p>
                <p className="text-caption text-on-surface-variant mt-0.5">{loadError}</p>
              </div>
              <button
                onClick={() => currentUser && refresh(currentUser)}
                className="text-caption font-bold text-danger hover:underline cursor-pointer shrink-0"
              >
                Retry
              </button>
            </div>
          )}
          {renderTabContent()}
        </main>
      </div>
    </div></ThemeScope>
  );
}
