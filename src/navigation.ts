import { Bell, Calendar, FileText, Home, LayoutDashboard, Receipt, Settings, UserCog, Users } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { UserRole } from './types';

/**
 * The app's navigation, one source for the sidebar and the topbar breadcrumb
 * (#27). `showFor` omitted means every role.
 */
export interface NavItem {
  id: string;
  label: string;
  icon: LucideIcon;
  showFor?: UserRole[];
  /** Leaves the app for the public homepage instead of switching tab. */
  isHome?: boolean;
}

const ITEMS: NavItem[] = [
  { id: 'home', label: 'Home', icon: Home, isHome: true },
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  // Invoices: admin and accountant.
  { id: 'invoices', label: 'Invoices', icon: FileText, showFor: ['admin', 'accountant'] },
  // Leave Requests: employees only. Accountants are deliberately excluded -
  // they do not manage HR processes (see #10).
  { id: 'leave-requests', label: 'Leave Requests', icon: Calendar, showFor: ['employee'] },
  // Payslips: employee and accountant. The accountant access is intentional -
  // #12 deliberately superseded the employee-only rule in #10. Do not revert.
  { id: 'payslips', label: 'Payslips', icon: Receipt, showFor: ['employee', 'accountant'] },
  // Team: admin and employee (not accountant).
  { id: 'team', label: 'Team', icon: Users, showFor: ['admin', 'employee'] },
  // Users: admin and accountant (read-only for accountant).
  { id: 'users', label: 'Users', icon: UserCog, showFor: ['admin', 'accountant'] },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export function navItemsFor(role: UserRole): NavItem[] {
  return ITEMS.filter((item) => !item.showFor || item.showFor.includes(role)).map((item) =>
    item.id === 'team' && role === 'admin' ? { ...item, label: 'Team Management' } : item
  );
}

/** Human label for a tab id: "leave-requests" -> "Leave Requests". */
export function tabLabel(id: string, role: UserRole): string {
  const item = navItemsFor(role).find((i) => i.id === id);
  if (item) return item.label;
  const words = id.replace(/-/g, ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export const ROLE_LABEL: Record<UserRole, string> = {
  admin: 'HR Admin',
  accountant: 'Accountant',
  employee: 'Employee',
};
