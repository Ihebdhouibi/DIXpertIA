import { Bell, Calendar, FileText, Home, Inbox, LayoutDashboard, Settings, UserCog, Users, Wallet } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { UserRole } from './types';
import type { MessageKey, Params } from './i18n';

/**
 * The app's navigation, one source for the sidebar and the topbar breadcrumb
 * (#27). `showFor` omitted means every role. `label` is a message key,
 * translated where it is shown (#135).
 */
export interface NavItem {
  id: string;
  label: MessageKey;
  icon: LucideIcon;
  showFor?: UserRole[];
  /** Leaves the app for the public homepage instead of switching tab. */
  isHome?: boolean;
}

const ITEMS: NavItem[] = [
  { id: 'home', label: 'common.nav.home', icon: Home, isHome: true },
  { id: 'dashboard', label: 'common.nav.dashboard', icon: LayoutDashboard },
  // Invoices: admin and accountant.
  { id: 'invoices', label: 'common.nav.invoices', icon: FileText, showFor: ['admin', 'accountant'] },
  // Leave Requests: employees only. Accountants are deliberately excluded -
  // they do not manage HR processes (see #10).
  { id: 'leave-requests', label: 'common.nav.leaveRequests', icon: Calendar, showFor: ['employee'] },
  // Payslips: employee and accountant. The accountant access is intentional -
  // #12 deliberately superseded the employee-only rule in #10. Do not revert.
  { id: 'payslips', label: 'common.nav.payslips', icon: Wallet, showFor: ['employee', 'accountant'] },
  // Team: admin and employee (not accountant).
  { id: 'team', label: 'common.nav.team', icon: Users, showFor: ['admin', 'employee'] },
  // Users: admin and accountant (read-only for accountant).
  { id: 'users', label: 'common.nav.users', icon: UserCog, showFor: ['admin', 'accountant'] },
  // Enquiries from the website's contact form (#98): admin only.
  { id: 'enquiries', label: 'common.nav.enquiries', icon: Inbox, showFor: ['admin'] },
  { id: 'notifications', label: 'common.nav.notifications', icon: Bell },
  { id: 'settings', label: 'common.nav.settings', icon: Settings },
];

export function navItemsFor(role: UserRole): NavItem[] {
  return ITEMS.filter((item) => !item.showFor || item.showFor.includes(role)).map((item) =>
    item.id === 'team' && role === 'admin' ? { ...item, label: 'common.nav.teamManagement' } : item
  );
}

/**
 * Translated label for a tab id. An id with no nav item falls back to the id
 * itself: "leave-requests" -> "Leave requests".
 */
export function tabLabel(id: string, role: UserRole, t: (key: MessageKey, params?: Params) => string): string {
  const item = navItemsFor(role).find((i) => i.id === id);
  if (item) return t(item.label);
  const words = id.replace(/-/g, ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** The role's name, as a message key: render it with t(ROLE_LABEL[role]). */
export const ROLE_LABEL: Record<UserRole, MessageKey> = {
  admin: 'common.role.admin',
  accountant: 'common.role.accountant',
  employee: 'common.role.employee',
};
