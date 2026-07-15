import React, { useState, useEffect } from 'react';
import { User, UserRole, Payslip, LeaveRequest, TeamMember, Invoice } from './types';
import {
  initialPayslips,
  initialLeaveRequests,
  initialTeamMembers,
  initialInvoices
} from './data';
import Registration from './components/Registration';
import Sidebar from './components/Sidebar';
import PayslipsView from './components/PayslipsView';
import LeaveRequestsView from './components/LeaveRequestsView';
import TeamView from './components/TeamView';
import InvoicesView from './components/InvoicesView';
import { 
  Bell, 
  Search, 
  Menu, 
  Info, 
  LogOut, 
  HelpCircle, 
  UserCheck, 
  AlertCircle,
  FileSpreadsheet,
  Users,
  Wallet2
} from 'lucide-react';

export default function App() {
  // --- 1. State Initialization (with localStorage hydration) ---
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

  const [activeTab, setActiveTab] = useState<string>(() => {
    const savedUser = localStorage.getItem('dixpertia_user');
    if (savedUser) {
      const parsed: User = JSON.parse(savedUser);
      return parsed.role === 'admin' ? 'reports' : 'payslips';
    }
    return 'payslips';
  });

  const [isOpenMobile, setIsOpenMobile] = useState(false);
  const [notificationCount, setNotificationCount] = useState(3);
  const [showNotificationList, setShowNotificationList] = useState(false);

  // --- 2. Persist State Changes in LocalStorage ---
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

  // --- 3. Handlers & Callbacks ---
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
    // Set appropriate starting tab based on role
    setActiveTab(role === 'admin' ? 'reports' : 'payslips');
  };

  const handleLogout = () => {
    setCurrentUser(null);
    localStorage.removeItem('dixpertia_user');
  };

  // Demo bypass/toggle to let the user preview different screens immediately
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
    setActiveTab(toggledRole === 'admin' ? 'reports' : 'payslips');
  };

  // Leave request additions
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
      reason: newReq.reason
    };
    setLeaveRequests([req, ...leaveRequests]);
  };

  // Employee additions
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

  // Admin approvals & rejections
  const handleApproveLeave = (id: string) => {
    setLeaveRequests(prev => prev.map(req => {
      if (req.id === id) {
        return { ...req, status: 'Approved' };
      }
      return req;
    }));
  };

  const handleRejectLeave = (id: string, comment: string) => {
    setLeaveRequests(prev => prev.map(req => {
      if (req.id === id) {
        return { ...req, status: 'Rejected', rejectionReason: comment };
      }
      return req;
    }));
  };

  // Invoice additions
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

  // --- 4. Render Logic Helper ---
  const renderTabContent = () => {
    if (!currentUser) return null;

    switch (activeTab) {
      case 'payslips':
        if (currentUser.role === 'admin') {
          // Admins don't view personal payslips in this scope, swap to Invoices
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

      // Simulated bento placeholders for other navigation items to make the portal feel whole and complete
      case 'dashboard':
      case 'projects':
      case 'settings':
      default:
        return (
          <div className="flex-1 flex flex-col gap-6 animate-fade-in">
            <div className="bg-white p-8 rounded-xl border border-outline-variant shadow-sm text-center max-w-2xl mx-auto flex flex-col items-center justify-center gap-4 mt-8">
              <div className="w-16 h-16 rounded-full bg-primary/10 text-primary flex items-center justify-center">
                <HelpCircle className="w-10 h-10" />
              </div>
              <h2 className="text-h2 font-black text-on-surface">Module "{activeTab.toUpperCase()}" en cours de déploiement</h2>
              <p className="text-body-sm text-on-surface-variant leading-relaxed">
                Le module interactif <strong className="text-primary">{activeTab}</strong> de DIXpertIA est actuellement en phase de test de déploiement sécurisé. 
                Toutes les spécifications visuelles du guide de style sont prêtes.
              </p>
              <div className="p-4 bg-surface-container-low rounded-lg w-full text-left space-y-2 border border-outline-variant/30">
                <p className="text-xs font-bold text-on-surface flex items-center gap-1.5">
                  <AlertCircle className="w-4 h-4 text-secondary shrink-0" /> 
                  Que pouvez-vous tester en temps réel ?
                </p>
                <ul className="list-disc list-inside text-xs text-on-surface-variant space-y-1 font-medium pl-1">
                  <li><strong>Fiches de paie (Payslips)</strong> : Filtres par année, téléchargement et cumulatifs YTD.</li>
                  <li><strong>Demandes de congés (Reports)</strong> : Soldes interactifs, demandes réelles et mise à jour du tableau.</li>
                  <li><strong>Factures (Invoices)</strong> : Filtres par statut, création de factures, et aperçu PDF Faux complet !</li>
                  <li><strong>Équipe (Team)</strong> : Ajout de collaborateurs et interface complète d'approbation RH avec refus commenté !</li>
                </ul>
              </div>
              <button
                onClick={() => setActiveTab(currentUser.role === 'admin' ? 'reports' : 'payslips')}
                className="bg-primary text-white font-bold text-body-sm px-6 py-2.5 rounded-lg hover:bg-primary/95 transition-all cursor-pointer shadow-sm mt-2"
              >
                Retourner aux Fonctionnalités Actives
              </button>
            </div>
          </div>
        );
    }
  };

  // --- 5. Unauthenticated State Render ---
  if (!currentUser) {
    return <Registration onLogin={handleLogin} />;
  }

  // --- 6. Authenticated Shell Render ---
  return (
    <div className="min-h-screen bg-background flex flex-col md:flex-row text-on-background font-sans">
      
      {/* Side Navigation panel (Drawer on mobile, stationary bar on desktop) */}
      <Sidebar
        currentUser={currentUser}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onLogout={handleLogout}
        onToggleRole={handleToggleRole}
        isOpenMobile={isOpenMobile}
        setIsOpenMobile={setIsOpenMobile}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        
        {/* Top Header Navigation bar */}
        <header className="h-16 bg-surface-container-lowest border-b border-outline-variant px-6 flex items-center justify-between sticky top-0 z-40 shrink-0">
          
          {/* Left: Mobile hamburger menu & screen contextual info */}
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

          {/* Right: Quick actions, notifications, user tag */}
          <div className="flex items-center gap-4 relative">
            
            {/* Quick Demo Role Label */}
            <div className="hidden lg:flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10 border border-primary/20">
              <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></div>
              <span className="text-[11px] font-black uppercase text-primary tracking-wider">
                Vue {currentUser.role === 'admin' ? 'Admin RH' : 'Employé'}
              </span>
            </div>

            {/* Notification Bell Badge */}
            <div className="relative">
              <button
                onClick={() => {
                  setShowNotificationList(!showNotificationList);
                  setNotificationCount(0); // Mark read on click
                }}
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

              {/* Simple Dynamic Notification Popover */}
              {showNotificationList && (
                <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-[0_4px_24px_rgba(3,34,77,0.12)] border border-outline-variant/60 py-2 z-50 animate-scale-up">
                  <div className="px-4 py-2 border-b border-outline-variant/40 flex justify-between items-center bg-surface">
                    <span className="font-bold text-caption text-on-surface">Notifications récurrentes</span>
                    <button 
                      onClick={() => setShowNotificationList(false)}
                      className="text-xs text-secondary hover:underline cursor-pointer"
                    >
                      Fermer
                    </button>
                  </div>
                  <div className="divide-y divide-outline-variant/30 max-h-64 overflow-y-auto">
                    <div className="px-4 py-2.5 hover:bg-surface transition-colors cursor-pointer">
                      <p className="text-xs font-semibold text-on-surface">💵 Votre fiche de paie de Septembre est disponible</p>
                      <p className="text-[10px] text-outline mt-1">Il y a 2 heures • Fiche de Paie</p>
                    </div>
                    <div className="px-4 py-2.5 hover:bg-surface transition-colors cursor-pointer">
                      <p className="text-xs font-semibold text-on-surface">🎉 Votre demande de congé annuel a été approuvée</p>
                      <p className="text-[10px] text-outline mt-1">Hier • Congés</p>
                    </div>
                    <div className="px-4 py-2.5 hover:bg-surface transition-colors cursor-pointer">
                      <p className="text-xs font-semibold text-on-surface">🔒 Rappel de sécurité : renforcez votre mot de passe</p>
                      <p className="text-[10px] text-outline mt-1">Il y a 3 jours • Système</p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Profile trigger backup box */}
            <div className="w-8 h-8 rounded-full bg-primary text-white font-bold text-xs flex items-center justify-center shadow-sm select-none">
              {currentUser.firstName[0]}{currentUser.lastName[0]}
            </div>

          </div>
        </header>

        {/* Primary Page Canvas */}
        <main className="flex-1 p-4 md:p-8 overflow-y-auto max-w-[1400px] w-full mx-auto">
          {renderTabContent()}
        </main>
      </div>

    </div>
  );
}
