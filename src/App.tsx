import React, { useState, useEffect } from 'react';
import { User, UserRole, Payslip, LeaveRequest, TeamMember, Invoice, Project } from './types';
import {
  initialPayslips,
  initialLeaveRequests,
  initialTeamMembers,
  initialInvoices,
  initialProjects
} from './data';
import Registration from './components/Registration';
import Homepage from './components/Homepage';
import Sidebar from './components/Sidebar';
import PayslipsView from './components/PayslipsView';
import LeaveRequestsView from './components/LeaveRequestsView';
import TeamView from './components/TeamView';
import InvoicesView from './components/InvoicesView';
import ProjectsView from './components/ProjectsView';
import DashboardView from './components/DashboardView'; // NEW
import { 
  Bell, 
  Menu, 
  HelpCircle, 
  AlertCircle,
  CheckCircle,
  X
} from 'lucide-react';

// --- Notification type ---
interface Notification {
  id: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  read: boolean;
  timestamp: number;
  link?: string;
  targetRole?: 'admin' | 'employee';
}

export default function App() {
  // --- State ---
  const [currentUser, setCurrentUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('dixpertia_user');
    return saved ? JSON.parse(saved) : null;
  });

  const [payslips, setPayslips] = useState<Payslip[]>(() => {
    const saved = localStorage.getItem('dixpertia_payslips');
    return saved ? JSON.parse(saved) : initialPayslips;
  });

  const [leaveRequests, setLeaveRequests] = useState<LeaveRequest[]>(() => {
    const saved = localStorage.getItem('dixpertia_leave_requests');
    return saved ? JSON.parse(saved) : initialLeaveRequests;
  });

  const [teamMembers, setTeamMembers] = useState<TeamMember[]>(() => {
    const saved = localStorage.getItem('dixpertia_team_members');
    return saved ? JSON.parse(saved) : initialTeamMembers;
  });

  const [invoices, setInvoices] = useState<Invoice[]>(() => {
    const saved = localStorage.getItem('dixpertia_invoices');
    return saved ? JSON.parse(saved) : initialInvoices;
  });

  const [projects, setProjects] = useState<Project[]>(() => {
    const saved = localStorage.getItem('dixpertia_projects');
    return saved ? JSON.parse(saved) : initialProjects;
  });

  // Default active tab: dashboard
  const [activeTab, setActiveTab] = useState<string>(() => {
    const savedUser = localStorage.getItem('dixpertia_user');
    if (savedUser) {
      const parsed: User = JSON.parse(savedUser);
      // Use dashboard as default for all users
      return 'dashboard';
    }
    return 'dashboard';
  });

  const [isOpenMobile, setIsOpenMobile] = useState(false);
  const [notificationCount, setNotificationCount] = useState(0);
  const [showNotificationList, setShowNotificationList] = useState(false);
  const [showAuth, setShowAuth] = useState(false);
  const [showHomepage, setShowHomepage] = useState(false);

  // --- Notifications state ---
  const [notifications, setNotifications] = useState<Notification[]>(() => {
    const saved = localStorage.getItem('dixpertia_notifications');
    if (saved) {
      const parsed = JSON.parse(saved);
      const unread = parsed.filter((n: Notification) => !n.read).length;
      setNotificationCount(unread);
      return parsed;
    }
    return [];
  });

  // --- Persist notifications ---
  useEffect(() => {
    localStorage.setItem('dixpertia_notifications', JSON.stringify(notifications));
    const unread = notifications.filter(n => !n.read).length;
    setNotificationCount(unread);
  }, [notifications]);

  // --- Helper: add notification with target role ---
  const addNotification = (
    message: string,
    type: Notification['type'] = 'info',
    link?: string,
    targetRole?: 'admin' | 'employee'
  ) => {
    const newNotif: Notification = {
      id: `notif-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`,
      message,
      type,
      read: false,
      timestamp: Date.now(),
      link,
      targetRole,
    };
    setNotifications(prev => [newNotif, ...prev]);
  };

  // --- Persist other state ---
  useEffect(() => {
    if (currentUser) {
      localStorage.setItem('dixpertia_user', JSON.stringify(currentUser));
    } else {
      localStorage.removeItem('dixpertia_user');
    }
  }, [currentUser]);

  useEffect(() => {
    localStorage.setItem('dixpertia_payslips', JSON.stringify(payslips));
  }, [payslips]);

  useEffect(() => {
    localStorage.setItem('dixpertia_leave_requests', JSON.stringify(leaveRequests));
  }, [leaveRequests]);

  useEffect(() => {
    localStorage.setItem('dixpertia_team_members', JSON.stringify(teamMembers));
  }, [teamMembers]);

  useEffect(() => {
    localStorage.setItem('dixpertia_invoices', JSON.stringify(invoices));
  }, [invoices]);

  useEffect(() => {
    localStorage.setItem('dixpertia_projects', JSON.stringify(projects));
  }, [projects]);

  // --- Handlers ---
  const handleLogin = (role: UserRole, email: string, firstName: string, lastName: string) => {
    const newUser: User = {
      id: role === 'admin' ? 'ADMIN-01' : 'EMP-102',
      firstName,
      lastName,
      email,
      role,
      department: role === 'admin' ? 'Human Resources' : 'Engineering',
      avatarUrl: role === 'admin' 
        ? 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=150&auto=format&fit=crop'
        : 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?q=80&w=150&auto=format&fit=crop'
    };
    setCurrentUser(newUser);
    setActiveTab('dashboard'); // default to dashboard
    setShowAuth(false);
  };

  const handleLogout = () => {
    setCurrentUser(null);
    localStorage.removeItem('dixpertia_user');
    setShowAuth(false);
  };

  const handleToggleRole = () => {
    if (!currentUser) return;
    const toggledRole: UserRole = currentUser.role === 'admin' ? 'employee' : 'admin';
    const updatedUser: User = {
      ...currentUser,
      role: toggledRole,
      id: toggledRole === 'admin' ? 'ADMIN-01' : 'EMP-102',
      firstName: toggledRole === 'admin' ? 'David' : 'John',
      lastName: toggledRole === 'admin' ? 'Admin' : 'Doe',
      department: toggledRole === 'admin' ? 'Human Resources' : 'Engineering',
      avatarUrl: toggledRole === 'admin'
        ? 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?q=80&w=150&auto=format&fit=crop'
        : 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?q=80&w=150&auto=format&fit=crop'
    };
    setCurrentUser(updatedUser);
    setActiveTab('dashboard');
  };

  // --- Leave request handlers ---
  const handleAddLeaveRequest = (newReq: Partial<LeaveRequest>) => {
    if (!currentUser) return;
    const req: LeaveRequest = {
      id: `LR-00${leaveRequests.length + 1}`,
      employeeId: currentUser.id,
      employeeName: `${currentUser.firstName} ${currentUser.lastName}`,
      department: currentUser.department || 'Operations',
      type: newReq.type || 'Annual Leave',
      dates: newReq.dates || 'Oct 20, 2024',
      duration: newReq.duration || 1,
      status: 'Pending',
      reason: newReq.reason || ''
    };
    setLeaveRequests([req, ...leaveRequests]);

    const employeeName = `${currentUser.firstName} ${currentUser.lastName}`;
    addNotification(
      `New leave request from ${employeeName} (${req.type})`,
      'warning',
      'team',
      'admin'
    );
  };

  const handleApproveLeave = (id: string) => {
    setLeaveRequests(prev =>
      prev.map(req =>
        req.id === id ? { ...req, status: 'Approved' as const } : req
      )
    );
    if (currentUser && currentUser.role === 'admin') {
      const req = leaveRequests.find(r => r.id === id);
      if (req) {
        addNotification(
          `Your leave request (${req.type}) has been approved`,
          'success',
          undefined,
          'employee'
        );
      }
    }
  };

  const handleRejectLeave = (id: string, comment: string) => {
    setLeaveRequests(prev =>
      prev.map(req =>
        req.id === id ? { ...req, status: 'Rejected' as const, rejectionReason: comment } : req
      )
    );
    if (currentUser && currentUser.role === 'admin') {
      const req = leaveRequests.find(r => r.id === id);
      if (req) {
        addNotification(
          `Your leave request (${req.type}) has been rejected`,
          'error',
          undefined,
          'employee'
        );
      }
    }
  };

  // --- Employee & Invoice handlers (unchanged) ---
  const handleAddEmployee = (newEmp: Partial<TeamMember>) => {
    const emp: TeamMember = {
      id: `TM-00${teamMembers.length + 1}`,
      firstName: newEmp.firstName || 'Jane',
      lastName: newEmp.lastName || 'Doe',
      email: newEmp.email || 'jane.doe@dixpertia.com',
      role: newEmp.role || 'Contributor',
      status: 'Active',
      initials: newEmp.initials || 'JD'
    };
    setTeamMembers([emp, ...teamMembers]);
  };

  const handleAddInvoice = (newInv: Partial<Invoice>) => {
    const inv: Invoice = {
      id: newInv.id || `INV-2024-00${invoices.length + 1}`,
      client: newInv.client || 'Faux Client',
      clientInitials: newInv.clientInitials || 'FC',
      amount: newInv.amount || 1000.00,
      dateIssued: newInv.dateIssued || 'Oct 20, 2024',
      dueDate: newInv.dueDate || 'Nov 20, 2024',
      status: newInv.status || 'Sent',
      items: newInv.items || []
    };
    setInvoices([inv, ...invoices]);
  };

  // --- Projects handlers ---
  const handleAddProject = (project: Partial<Project>) => {
    const newProject: Project = {
      id: `PRJ-00${projects.length + 1}`,
      name: project.name || 'Untitled',
      client: project.client || 'Unknown',
      description: project.description || '',
      status: project.status || 'Active',
      deadline: project.deadline || new Date().toISOString().split('T')[0],
      teamMembers: project.teamMembers || [],
      createdAt: new Date().toISOString(),
    };
    setProjects([newProject, ...projects]);
    addNotification(
      `New project "${newProject.name}" created`,
      'success',
      'projects',
      'admin'
    );
  };

  const handleEditProject = (id: string, updates: Partial<Project>) => {
    setProjects(prev => prev.map(p => (p.id === id ? { ...p, ...updates } : p)));
    const proj = projects.find(p => p.id === id);
    if (proj) {
      addNotification(
        `Project "${proj.name}" updated`,
        'info',
        'projects',
        'admin'
      );
    }
  };

  const handleDeleteProject = (id: string) => {
    const proj = projects.find(p => p.id === id);
    setProjects(prev => prev.filter(p => p.id !== id));
    if (proj) {
      addNotification(
        `Project "${proj.name}" deleted`,
        'error',
        undefined,
        'admin'
      );
    }
  };

  // --- Dashboard quick actions ---
  const handleQuickAction = (action: string) => {
    switch (action) {
      case 'approve-leaves':
        setActiveTab('team');
        break;
      case 'create-invoice':
        setActiveTab('reports');
        break;
      case 'add-project':
        setActiveTab('projects');
        break;
      case 'download-payslip':
        setActiveTab('payslips');
        break;
      default:
        break;
    }
  };

  const handleGoHome = () => setShowHomepage(true);
  const handleGoToDashboard = () => setShowHomepage(false);

  // --- Render content helper ---
  const renderTabContent = () => {
    if (!currentUser) return null;

    switch (activeTab) {
      case 'dashboard':
        return (
          <DashboardView
            user={currentUser}
            projects={projects}
            invoices={invoices}
            leaveRequests={leaveRequests}
            teamMembers={teamMembers}
            notifications={notifications}
            onNavigate={(tab: string) => {
              setActiveTab(tab);
              setShowNotificationList(false);
            }}
            onQuickAction={handleQuickAction}
          />
        );

      case 'payslips':
        if (currentUser.role === 'admin') {
          return <InvoicesView invoices={invoices} onAddInvoice={handleAddInvoice} />;
        }
        return <PayslipsView payslips={payslips} />;
      
      case 'reports':
        if (currentUser.role === 'admin') {
          return <InvoicesView invoices={invoices} onAddInvoice={handleAddInvoice} />;
        }
        return (
          <LeaveRequestsView 
            leaveRequests={leaveRequests.filter(req => req.employeeId === currentUser.id)} 
            onAddRequest={handleAddLeaveRequest} 
          />
        );
      
      case 'team':
        return (
          <TeamView
            userRole={currentUser.role}
            teamMembers={teamMembers}
            leaveRequests={leaveRequests}
            onAddEmployee={handleAddEmployee}
            onApproveLeave={handleApproveLeave}
            onRejectLeave={handleRejectLeave}
          />
        );
      
      case 'projects':
        return (
          <ProjectsView
            projects={projects}
            onAddProject={handleAddProject}
            onEditProject={handleEditProject}
            onDeleteProject={handleDeleteProject}
            userRole={currentUser.role}
            teamMembers={teamMembers}
          />
        );

      default:
        return (
          <div className="flex-1 flex flex-col gap-6 animate-fade-in">
            <div className="bg-white p-8 rounded-xl border border-outline-variant shadow-sm text-center max-w-2xl mx-auto flex flex-col items-center justify-center gap-4 mt-8">
              <div className="w-16 h-16 rounded-full bg-primary/10 text-primary flex items-center justify-center">
                <HelpCircle className="w-10 h-10" />
              </div>
              <h2 className="text-h2 font-black text-on-surface">Module "{activeTab.toUpperCase()}" is being deployed</h2>
              <p className="text-body-sm text-on-surface-variant leading-relaxed">
                The interactive module <strong className="text-primary">{activeTab}</strong> is currently in secure deployment testing.
              </p>
              <button
                onClick={() => setActiveTab('dashboard')}
                className="bg-primary text-white font-bold text-body-sm px-6 py-2.5 rounded-lg hover:bg-primary/95 transition-all cursor-pointer shadow-sm mt-2"
              >
                Back to Dashboard
              </button>
            </div>
          </div>
        );
    }
  };

  // --- Unauthenticated render ---
  if (!currentUser) {
    if (showAuth) {
      return <Registration onLogin={handleLogin} onBackHome={() => setShowAuth(false)} />;
    }
    return <Homepage onLoginClick={() => setShowAuth(true)} />;
  }

  if (showHomepage) {
    return <Homepage onLoginClick={handleGoToDashboard} showDashboardButton={true} />;
  }

  // --- Filter notifications by role ---
  const visibleNotifications = notifications.filter(n => {
    if (!n.targetRole) return true;
    return n.targetRole === currentUser.role;
  });

  // --- Authenticated Dashboard ---
  return (
    <div className="min-h-screen bg-background flex flex-col md:flex-row text-on-background font-sans">
      
      <Sidebar
        currentUser={currentUser}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onLogout={handleLogout}
        onToggleRole={handleToggleRole}
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
                {currentUser.role === 'admin' ? 'HR Admin' : 'Employee'} View
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
                  <span className="absolute top-1 right-1 w-4 h-4 bg-error text-white font-black text-[9px] rounded-full flex items-center justify-center animate-bounce shadow-sm">
                    {notificationCount}
                  </span>
                )}
              </button>

              {/* Notification Popover */}
              {showNotificationList && (
                <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-[0_4px_24px_rgba(3,34,77,0.12)] border border-outline-variant/60 py-2 z-50 animate-scale-up">
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
                            if (notif.link === 'team') {
                              setActiveTab('team');
                              setShowNotificationList(false);
                            } else if (notif.link === 'projects') {
                              setActiveTab('projects');
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

            <div className="w-8 h-8 rounded-full bg-primary text-white font-bold text-xs flex items-center justify-center shadow-sm select-none">
              {currentUser.firstName[0]}{currentUser.lastName[0]}
            </div>
          </div>
        </header>

        <main className="flex-1 p-4 md:p-8 overflow-y-auto max-w-[1400px] w-full mx-auto">
          {renderTabContent()}
        </main>
      </div>
    </div>
  );
}