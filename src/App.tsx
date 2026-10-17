import React, { useCallback, useEffect, useState } from 'react';
import { Client, Employee, Invoice, LeaveRequest, Payslip, User } from './types';
import * as api from './api';
import Login from './components/Login';
import Homepage from './components/Homepage';
import { ThemeScope } from './theme';
import Sidebar from './components/Sidebar';
import AppHeader from './components/AppHeader';
import { DataStatusContext } from './dataStatus';
import { useToast } from './components/ui/feedback';
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
import { HelpCircle, AlertCircle } from 'lucide-react';

interface Notification {
  id: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  read: boolean;
  timestamp: number;
  link?: string;
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
  const [loading, setLoading] = useState(false);

  const [payslips, setPayslips] = useState<Payslip[]>([]);
  const [leaveRequests, setLeaveRequests] = useState<LeaveRequest[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [users, setUsers] = useState<AppUser[]>([]);
  const [clients, setClients] = useState<Client[]>([]);

  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [isOpenMobile, setIsOpenMobile] = useState(false);
  const [notificationCount, setNotificationCount] = useState(0);
  const [showHomepage, setShowHomepage] = useState(true);
  const [showLogin, setShowLogin] = useState(false);
  const [showForgotPassword, setShowForgotPassword] = useState(false);   // NEW
  const [resetToken, setResetToken] = useState<string | null>(null);
  // A reset link carries ?token=, an activation link ?activate= (#62). Both
  // open the same "choose a password" page, against different endpoints.
  const [linkMode, setLinkMode] = useState<'reset' | 'activate'>('reset');

  // --- Detect a reset or activation link in the URL ---
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const activation = params.get('activate');
    const token = activation ?? params.get('token');
    if (token) {
      setLinkMode(activation ? 'activate' : 'reset');
      setResetToken(token);
      setShowForgotPassword(false);
    }
  }, []);

  // --- Notifications (#116) ---
  // Kept by the server, per user, and written on workflow events - an invoice
  // to verify, a rejection, an approval - so they reach the person concerned
  // and survive a reload or another device. They used to be made in this
  // browser and lived only in the session. Reloaded on sign-in, every minute,
  // and when the window regains focus; every action goes through the API and
  // reloads, so the bell and the page always show the server's state.
  const toast = useToast();
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const loadNotifications = useCallback(async () => {
    try {
      const page = await api.notifications.list();
      setNotifications(page.rows.map((n) => ({ ...n, link: n.link ?? undefined })));
      setNotificationCount(page.unread);
    } catch {
      // A failed refresh keeps what the bell already shows; the next one retries.
    }
  }, []);

  const notificationAction = (action: () => Promise<unknown>) => {
    action()
      .catch((error) => toast(error instanceof Error ? error.message : 'Could not update notifications', 'error'))
      .finally(loadNotifications);
  };

  // --- Loading everything from the API ---

  const refresh = useCallback(async (user: AppUser) => {
    // Each call is scoped by the server: an employee's request returns their
    // own payslips and leave, an admin's returns everyone's. The row-level
    // security policies decide that, not this code, so there is no role check
    // here to drift out of step.
    const isPrivileged = user.role === 'admin' || user.role === 'accountant';
    setLoading(true);
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
    setLoading(false);
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

  useEffect(() => {
    if (!currentUser) return;
    void loadNotifications();
    const timer = window.setInterval(loadNotifications, 60_000);
    window.addEventListener('focus', loadNotifications);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener('focus', loadNotifications);
    };
  }, [currentUser, loadNotifications]);

  // Authentication goes through POST /api/login only. The role, and every other
  // user attribute, comes from the server's response - never from the client.
  // Returns the error to show in the form, or null: a failed sign-in used to be
  // added to the in-app notifications, which are not on the sign-in screen, so
  // a wrong password showed nothing at all (#116).
  const handleLogin = async (email: string, password: string): Promise<string | null> => {
    try {
      const data = await api.auth.login(email, password);
      api.setToken(data.access_token);
      const appUser = data.user as AppUser;
      setCurrentUser(appUser);
      setActiveTab('dashboard');
      setShowHomepage(false);
      setShowLogin(false);
      await refresh(appUser);
      return null;
    } catch (error) {
      return error instanceof api.ApiError ? error.message : 'Network error during sign-in. Please try again.';
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
    setNotificationCount(0);
    setShowHomepage(true);
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
      toast(message, 'error');
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

  // The invoice view creates the invoice itself, so it can keep the form open
  // on a refusal and send an Idempotency-Key (#128); the app only reloads what
  // other screens show, such as the dashboard figures.
  const handleInvoiceCreated = () => {
    if (currentUser) refresh(currentUser);
  };

  // --- Quick actions ---
  const handleQuickAction = (action: string) => {
    switch (action) {
      case 'approve-leaves': setActiveTab('team'); break;
      case 'create-invoice': setActiveTab('invoices'); break;
      case 'download-payslip': setActiveTab('payslips'); break;
      case 'view-notifications': setActiveTab('notifications'); break;
      default: break;
    }
  };

  const handleGoHome = () => {
    setShowHomepage(true);
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

  // The server returns only the caller's own notifications (#116).
  const visibleNotifications = notifications;

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
            onNavigate={(tab: string) => setActiveTab(tab)}
            onQuickAction={handleQuickAction}
          />
        );

      case 'notifications':
        return (
          <NotificationsView
            notifications={visibleNotifications}
            onMarkRead={(id) => notificationAction(() => api.notifications.read(id))}
            onMarkAllRead={() => notificationAction(api.notifications.readAll)}
            // The view asks for confirmation (#106); asking here as well
            // made "Clear all" prompt twice. Clearing is a soft dismissal.
            onClearAll={() => notificationAction(api.notifications.dismissAll)}
            onClearSelected={(ids) =>
              notificationAction(() => Promise.all(ids.map((id) => api.notifications.dismiss(id))))
            }
            onNavigate={(link) => setActiveTab(link)}
            userRole={currentUser.role}
          />
        );

      case 'settings':
        return <SettingsView user={currentUser} onLogout={handleLogout} />;

      case 'invoices':
        return <InvoicesView invoices={invoices} clients={clients} onInvoiceCreated={handleInvoiceCreated} userRole={currentUser.role} />;

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
        // The view creates, edits and deactivates accounts through the API
        // itself (#62) and asks for a reload once the server has accepted.
        return (
          <UsersView
            users={users}
            userRole={currentUser.role}
            currentUserId={currentUser.id}
            onChanged={currentUser.role === 'admin' ? () => refresh(currentUser) : undefined}
          />
        );

      case 'payslips':
        if (currentUser.role === 'admin') {
          return <InvoicesView invoices={invoices} clients={clients} onInvoiceCreated={handleInvoiceCreated} userRole={currentUser.role} />;
        }
        return <PayslipsView payslips={payslips} userRole={currentUser.role} />;

      case 'reports':
        if (currentUser.role === 'admin') {
          return <InvoicesView invoices={invoices} clients={clients} onInvoiceCreated={handleInvoiceCreated} userRole={currentUser.role} />;
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
        mode={linkMode}
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
      // Themed since #165: the homepage follows the light/dark preference like the app.
      <ThemeScope>
        <Homepage onDashboardClick={currentUser ? handleGoToDashboard : () => setShowLogin(true)} />
      </ThemeScope>
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
        <AppHeader
          currentUser={currentUser}
          activeTab={activeTab}
          notifications={visibleNotifications}
          unreadCount={notificationCount}
          onOpenNavigation={() => setIsOpenMobile(true)}
          onMarkAllRead={() => notificationAction(api.notifications.readAll)}
          onOpenNotification={(notif) => {
            if (!notif.read) notificationAction(() => api.notifications.read(notif.id));
            if (notif.link) setActiveTab(notif.link);
          }}
          onOpenSettings={() => setActiveTab('settings')}
          onLogout={handleLogout}
        />

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
          <DataStatusContext.Provider
            value={{ loading, error: loadError, retry: () => { if (currentUser) refresh(currentUser); } }}
          >
            {renderTabContent()}
          </DataStatusContext.Provider>
        </main>
      </div>
    </div></ThemeScope>
  );
}
