import React from 'react';
import {
  LayoutDashboard,
  Briefcase,
  FileText,
  Calendar,
  Users,
  Settings,
  LogOut,
  ShieldAlert,
  UserCheck,
  Home,
  Bell,
  Receipt,
  UserCog
} from 'lucide-react';
import { User } from '../types';

interface SidebarProps {
  currentUser: User;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onLogout: () => void;
  onToggleRole: () => void;
  isOpenMobile: boolean;
  setIsOpenMobile: (open: boolean) => void;
  onGoHome: () => void;
}

export default function Sidebar({
  currentUser,
  activeTab,
  setActiveTab,
  onLogout,
  onToggleRole,
  isOpenMobile,
  setIsOpenMobile,
  onGoHome,
}: SidebarProps) {
  const handleTabClick = (tabId: string) => {
    setActiveTab(tabId);
    setIsOpenMobile(false);
  };

  const initials = `${currentUser.firstName[0] || 'U'}${currentUser.lastName[0] || 'D'}`;

  // Define all possible items with visibility rules
  const allNavItems = [
    { id: 'home', label: 'Home', icon: Home, isMock: false, isHome: true },
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, isMock: false },
    // Invoices: visible to admin and accountant
    { id: 'invoices', label: 'Invoices', icon: FileText, isMock: false, showFor: ['admin', 'accountant'] },
    // Leave Requests: only employee. Accountants are deliberately excluded -
    // they do not manage HR processes (see #10).
    { id: 'leave-requests', label: 'Leave Requests', icon: Calendar, isMock: false, showFor: ['employee'] },
    // Projects: only admin
    { id: 'projects', label: 'Projects', icon: Briefcase, isMock: false, showFor: ['admin'] },
    // Payslips: employee and accountant. The accountant access is intentional -
    // #12 deliberately superseded the employee-only rule in #10. Do not revert.
    { id: 'payslips', label: 'Payslips', icon: Receipt, isMock: false, showFor: ['employee' , 'accountant'] },
    // Team: admin and employee (not accountant)
    { id: 'team', label: currentUser.role === 'admin' ? 'Team Management' : 'Team', icon: Users, isMock: false, showFor: ['admin', 'employee'] },
    // Users: admin and accountant (read‑only for accountant)
    { id: 'users', label: 'Users', icon: UserCog, isMock: false, showFor: ['admin', 'accountant'] },
    // Notifications and Settings: everyone
    { id: 'notifications', label: 'Notifications', icon: Bell, isMock: false },
    { id: 'settings', label: 'Settings', icon: Settings, isMock: false },
  ];

  // Filter items based on role
  const navItems = allNavItems.filter(item => {
    if (item.isHome) return true;
    if (!item.showFor) return true; // dashboard, notifications, settings
    return item.showFor.includes(currentUser.role);
  });

  const sidebarContent = (
    <div className="flex flex-col h-full py-4 gap-2 px-4 bg-surface-container-lowest border-r border-outline-variant select-none">
      <div className="mb-6 pt-2 px-2 flex flex-col gap-1">
        <div className="text-primary font-black text-h1 tracking-tight">DIXpertIA</div>
        <div className="text-[11px] text-outline font-semibold tracking-widest uppercase">
              {currentUser.role === 'admin' ? 'HR Portal' : currentUser.role === 'accountant' ? 'Accountant Portal' : 'Employee Portal'}
        </div>
        </div>

      <div className="mb-6 p-3 rounded-xl bg-surface-container-low border border-outline-variant/30 flex items-center gap-3">
        {currentUser.avatarUrl ? (
          <img
            alt="User Profile"
            className="w-11 h-11 rounded-full object-cover border border-outline-variant shadow-sm"
            src={currentUser.avatarUrl}
            onError={(e) => (e.target as HTMLElement).style.display = 'none'}
          />
        ) : (
          <div className="w-11 h-11 rounded-full bg-primary-container text-primary font-bold flex items-center justify-center border border-outline-variant text-sm shadow-sm shrink-0">
            {initials}
          </div>
        )}
        <div className="min-w-0">
          <p className="font-semibold text-body-sm text-on-surface truncate">{currentUser.firstName} {currentUser.lastName}</p>
          <p className="text-[11px] text-on-surface-variant truncate font-medium">
            DIXpertIA {currentUser.role === 'admin' ? 'Admin' : currentUser.role === 'accountant' ? 'Accountant' : 'Operations'}
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-1.5 flex-1">
        {navItems.map((item) => {
          if (item.isHome) {
            return (
              <button
                key={item.id}
                onClick={() => { onGoHome(); setIsOpenMobile(false); }}
                className="flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-all text-body-sm cursor-pointer select-none font-medium text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
              >
                <Home className="w-5 h-5 text-outline" />
                <span>Home</span>
              </button>
            );
          }
          const isActive = activeTab === item.id;
          const IconComponent = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => handleTabClick(item.id)}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-all text-body-sm cursor-pointer select-none font-medium ${
                isActive
                  ? 'bg-tertiary-fixed text-on-tertiary-fixed-variant font-bold shadow-sm scale-98'
                  : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface scale-95 active:scale-100'
              }`}
            >
              <IconComponent className={`w-5 h-5 ${isActive ? 'stroke-[2.5px]' : 'text-outline'}`} />
              <span className="truncate">{item.label}</span>
              {item.isMock && (
                <span className="ml-auto text-[9px] bg-outline-variant/50 text-on-surface-variant px-1.5 py-0.5 rounded font-bold uppercase tracking-wider scale-90">Mock</span>
              )}
            </button>
          );
        })}
      </div>

      <div className="mt-auto pt-4 border-t border-outline-variant/30 flex flex-col gap-2">
        <div className="bg-primary-container/40 p-3 rounded-lg border border-primary/10 flex flex-col gap-2 text-center">
          <div className="flex items-center justify-center gap-1.5 text-xs font-semibold text-primary">
            {currentUser.role === 'admin' ? (
              <><ShieldAlert className="w-4 h-4" /> HR Admin Mode</>
            ) : currentUser.role === 'accountant' ? (
              <><ShieldAlert className="w-4 h-4" /> Accountant Mode</>
            ) : (
              <><UserCheck className="w-4 h-4" /> Employee Mode</>
            )}
          </div>
          <button
            onClick={onToggleRole}
            className="w-full text-[11px] bg-primary text-white py-1.5 rounded font-bold hover:bg-primary/90 transition-colors shadow-sm cursor-pointer"
          >
            Switch to {currentUser.role === 'admin' ? 'Employee' : currentUser.role === 'accountant' ? 'Employee' : 'Admin'} View
          </button>
        </div>

        <button
          onClick={onLogout}
          className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-error hover:bg-error-container/40 transition-all text-body-sm font-semibold cursor-pointer text-left w-full"
        >
          <LogOut className="w-5 h-5 text-error" />
          <span>Sign Out</span>
        </button>
      </div>
    </div>
  );

  return (
    <>
      <aside className="hidden md:block w-[240px] h-screen shrink-0 sticky top-0">
        {sidebarContent}
      </aside>
      {isOpenMobile && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setIsOpenMobile(false)}></div>
          <div className="relative w-[240px] max-w-xs h-full bg-white z-10 shadow-xl animate-slide-in">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
}
