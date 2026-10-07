import React, { useCallback, useRef, useState } from 'react';
import { AlertCircle, Bell, CheckCircle, Info, LogOut, Menu, Settings, User as UserIcon, XCircle } from 'lucide-react';
import { User } from '../types';
import { tabLabel } from '../navigation';
import { useDismiss } from './ui/useDismiss';

/** The fields of App's notifications the header needs. */
export interface HeaderNotification {
  id: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  read: boolean;
  timestamp: number;
  link?: string;
}

interface AppHeaderProps {
  currentUser: User;
  activeTab: string;
  notifications: HeaderNotification[];
  unreadCount: number;
  onOpenNavigation: () => void;
  onMarkAllRead: () => void;
  onOpenNotification: (notification: HeaderNotification) => void;
  onOpenSettings: () => void;
  onLogout: () => void;
}

const TYPE_ICON: Record<HeaderNotification['type'], { icon: React.ComponentType<{ className?: string }>; tone: string }> = {
  info: { icon: Info, tone: 'text-info' },
  success: { icon: CheckCircle, tone: 'text-success' },
  warning: { icon: AlertCircle, tone: 'text-warning' },
  error: { icon: XCircle, tone: 'text-danger' },
};

const MENU_ITEM =
  'flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-on-surface transition-colors hover:bg-surface-container-low cursor-pointer';

/**
 * The app's top bar (#27), moved out of App.tsx: breadcrumb, notification
 * menu and user menu. Both menus close on Escape (focus back on their button)
 * and on a click outside.
 */
export default function AppHeader({
  currentUser,
  activeTab,
  notifications,
  unreadCount,
  onOpenNavigation,
  onMarkAllRead,
  onOpenNotification,
  onOpenSettings,
  onLogout,
}: AppHeaderProps) {
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const notificationsRef = useRef<HTMLDivElement>(null);
  const notificationsButton = useRef<HTMLButtonElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const userMenuButton = useRef<HTMLButtonElement>(null);

  const closeNotifications = useCallback(() => setNotificationsOpen(false), []);
  const closeUserMenu = useCallback(() => setUserMenuOpen(false), []);
  useDismiss(notificationsRef, notificationsOpen, closeNotifications, notificationsButton);
  useDismiss(userMenuRef, userMenuOpen, closeUserMenu, userMenuButton);

  const initials = `${currentUser.firstName[0] || ''}${currentUser.lastName[0] || ''}`;

  return (
    <header className="sticky top-0 z-40 flex h-16 shrink-0 items-center justify-between border-b border-outline-variant bg-surface-container-lowest px-4 md:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          onClick={onOpenNavigation}
          aria-label="Open navigation"
          className="rounded-lg p-1.5 text-on-surface-variant transition-colors hover:bg-surface-container md:hidden cursor-pointer"
        >
          <Menu className="h-6 w-6" aria-hidden="true" />
        </button>
        <nav aria-label="Breadcrumb" className="hidden min-w-0 items-center gap-2 sm:flex">
          <span className="font-mono text-[11px] uppercase tracking-[0.08em] text-on-surface-variant">DI Xpertia</span>
          <span className="text-on-surface-variant" aria-hidden="true">
            /
          </span>
          <span aria-current="page" className="truncate text-sm font-semibold text-on-surface">
            {tabLabel(activeTab, currentUser.role)}
          </span>
        </nav>
      </div>

      <div className="flex items-center gap-2">
        {/* Notifications */}
        <div className="relative" ref={notificationsRef}>
          <button
            ref={notificationsButton}
            type="button"
            onClick={() => {
              setNotificationsOpen((v) => !v);
              setUserMenuOpen(false);
            }}
            aria-label={unreadCount > 0 ? `Notifications, ${unreadCount} unread` : 'Notifications'}
            aria-haspopup="true"
            aria-expanded={notificationsOpen}
            className="relative rounded-full p-2 text-on-surface-variant transition-colors hover:bg-surface-container hover:text-on-surface cursor-pointer"
          >
            <Bell className="h-5 w-5" aria-hidden="true" />
            {unreadCount > 0 && (
              <span
                aria-hidden="true"
                className="absolute right-0.5 top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 font-mono text-[10px] font-medium text-on-error"
              >
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {notificationsOpen && (
            <div className="absolute right-0 z-50 mt-2 w-80 overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest shadow-lg">
              <div className="flex items-center justify-between border-b border-outline-variant px-4 py-2.5">
                <span className="text-sm font-semibold text-on-surface">Notifications</span>
                {notifications.some((n) => !n.read) && (
                  <button
                    type="button"
                    onClick={onMarkAllRead}
                    className="rounded text-xs font-semibold text-secondary hover:underline cursor-pointer"
                  >
                    Mark all read
                  </button>
                )}
              </div>
              <ul className="max-h-72 divide-y divide-outline-variant overflow-y-auto">
                {notifications.length === 0 ? (
                  <li className="px-4 py-6 text-center text-sm text-on-surface-variant">No notifications</li>
                ) : (
                  notifications.slice(0, 10).map((n) => {
                    const { icon: Icon, tone } = TYPE_ICON[n.type];
                    return (
                      <li key={n.id}>
                        <button
                          type="button"
                          onClick={() => {
                            onOpenNotification(n);
                            if (n.link) setNotificationsOpen(false);
                          }}
                          className={`flex w-full items-start gap-2.5 px-4 py-3 text-left transition-colors hover:bg-surface-container-low cursor-pointer ${
                            n.read ? '' : 'bg-surface-container-low'
                          }`}
                        >
                          <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${tone}`} aria-hidden="true" />
                          <span className="min-w-0 flex-1">
                            <span className={`block text-sm text-on-surface ${n.read ? '' : 'font-semibold'}`}>
                              {n.message}
                            </span>
                            <span className="mt-1 block font-mono text-[11px] text-on-surface-variant">
                              {new Date(n.timestamp).toLocaleString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </span>
                          </span>
                        </button>
                      </li>
                    );
                  })
                )}
              </ul>
            </div>
          )}
        </div>

        {/* User menu */}
        <div className="relative" ref={userMenuRef}>
          <button
            ref={userMenuButton}
            type="button"
            onClick={() => {
              setUserMenuOpen((v) => !v);
              setNotificationsOpen(false);
            }}
            aria-label="User menu"
            aria-haspopup="true"
            aria-expanded={userMenuOpen}
            className="flex h-9 w-9 items-center justify-center rounded-full bg-surface-container-high font-mono text-xs font-medium text-on-surface transition-colors hover:bg-surface-container-highest cursor-pointer select-none"
          >
            {initials}
          </button>

          {userMenuOpen && (
            <div className="absolute right-0 z-50 mt-2 w-56 overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest py-1 shadow-lg">
              <div className="border-b border-outline-variant px-4 py-2.5">
                <p className="truncate text-sm font-semibold text-on-surface">
                  {currentUser.firstName} {currentUser.lastName}
                </p>
                <p className="truncate text-xs text-on-surface-variant">{currentUser.email}</p>
              </div>
              <button
                type="button"
                className={MENU_ITEM}
                onClick={() => {
                  onOpenSettings();
                  setUserMenuOpen(false);
                }}
              >
                <UserIcon className="h-4 w-4" aria-hidden="true" />
                Profile
              </button>
              <button
                type="button"
                className={MENU_ITEM}
                onClick={() => {
                  onOpenSettings();
                  setUserMenuOpen(false);
                }}
              >
                <Settings className="h-4 w-4" aria-hidden="true" />
                Settings
              </button>
              <div className="my-1 border-t border-outline-variant" />
              <button
                type="button"
                className={`${MENU_ITEM} text-error hover:bg-error-container`}
                onClick={() => {
                  setUserMenuOpen(false);
                  onLogout();
                }}
              >
                <LogOut className="h-4 w-4" aria-hidden="true" />
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
