import React, { useEffect, useRef } from 'react';
import { LogOut, X } from 'lucide-react';
import { User } from '../types';
import { navItemsFor, ROLE_LABEL } from '../navigation';
import Wordmark from './ui/Wordmark';
import { wrapTab } from './ui/Dialog';

interface SidebarProps {
  currentUser: User;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onLogout: () => void;
  isOpenMobile: boolean;
  setIsOpenMobile: (open: boolean) => void;
  onGoHome: () => void;
}

/*
 * The "Switch to ... View" button was removed in #65 (it is #66's own issue).
 * It rewrote the signed-in user's role, id and name in the browser, so any
 * employee could render the admin screens. The server always refused the
 * admin actions, so nothing could actually be done - but the screens were
 * shown over mock data, which is a more convincing lie than a refusal.
 * The "HR Admin Mode" box that framed it went with #27: the role is shown once,
 * under the user's name.
 */
export default function Sidebar({
  currentUser,
  activeTab,
  setActiveTab,
  onLogout,
  isOpenMobile,
  setIsOpenMobile,
  onGoHome,
}: SidebarProps) {
  const navItems = navItemsFor(currentUser.role);
  const initials = `${currentUser.firstName[0] || 'U'}${currentUser.lastName[0] || ''}`;

  const go = (id: string, isHome?: boolean) => {
    if (isHome) onGoHome();
    else setActiveTab(id);
    setIsOpenMobile(false);
  };

  const content = (
    <div className="flex h-full flex-col gap-6 border-r border-outline-variant bg-surface-container-lowest px-4 py-5 select-none">
      {/* Clear space around the logo: at least the cursor's height (#27, kit rule). */}
      <div className="px-2.5 py-2.5">
        <Wordmark size="sm" />
      </div>

      <div className="flex items-center gap-3 rounded-xl border border-outline-variant bg-surface-container-low p-3">
        {currentUser.avatarUrl ? (
          <img
            alt=""
            className="h-10 w-10 shrink-0 rounded-full border border-outline-variant object-cover"
            src={currentUser.avatarUrl}
            onError={(e) => ((e.target as HTMLElement).style.display = 'none')}
          />
        ) : (
          <div
            aria-hidden="true"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-surface-container-high font-mono text-sm font-medium text-on-surface"
          >
            {initials}
          </div>
        )}
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-on-surface">
            {currentUser.firstName} {currentUser.lastName}
          </p>
          <p className="truncate font-mono text-[11px] uppercase tracking-[0.08em] text-on-surface-variant">
            {ROLE_LABEL[currentUser.role]}
          </p>
        </div>
      </div>

      <nav aria-label="Main" className="flex flex-1 flex-col gap-1">
        {navItems.map(({ id, label, icon: Icon, isHome }) => {
          const active = !isHome && activeTab === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => go(id, isHome)}
              aria-current={active ? 'page' : undefined}
              className={`relative flex items-center gap-3 rounded-lg px-4 py-2.5 text-left text-sm transition-colors cursor-pointer ${
                active
                  ? 'bg-surface-container font-semibold text-on-surface'
                  : 'font-medium text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface'
              }`}
            >
              {/*
                The active item's indicator echoes the logo's block cursor - Lime
                Deep on paper, Signal Lime on ink (the `secondary` role), exactly
                as the mark itself does. The label stays ink.
              */}
              {active && (
                <span aria-hidden="true" className="absolute left-0 top-1/2 h-5 w-1.5 -translate-y-1/2 rounded-sm bg-secondary" />
              )}
              <Icon className={`h-5 w-5 shrink-0 ${active ? '' : 'text-on-surface-variant'}`} aria-hidden="true" />
              <span className="truncate">{label}</span>
            </button>
          );
        })}
      </nav>

      <div className="border-t border-outline-variant pt-4">
        <button
          type="button"
          onClick={onLogout}
          className="flex w-full items-center gap-3 rounded-lg px-4 py-2.5 text-left text-sm font-semibold text-error transition-colors hover:bg-error-container cursor-pointer"
        >
          <LogOut className="h-5 w-5" aria-hidden="true" />
          Sign out
        </button>
      </div>
    </div>
  );

  return (
    <>
      <aside className="sticky top-0 hidden h-screen w-[248px] shrink-0 md:block">{content}</aside>
      <MobileDrawer open={isOpenMobile} onClose={() => setIsOpenMobile(false)}>
        {content}
      </MobileDrawer>
    </>
  );
}

/**
 * The navigation drawer on small screens: a native modal <dialog> anchored to
 * the left, so focus is trapped (with Tab wrapping), the page behind is inert,
 * Escape and a scrim click close it, and focus returns to the menu button.
 */
function MobileDrawer({ open, onClose, children }: { open: boolean; onClose: () => void; children: React.ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-label="Navigation"
      onCancel={(e) => {
        if (e.target !== e.currentTarget) return;
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      onKeyDown={wrapTab}
      className="m-0 h-full max-h-none w-[272px] max-w-[85vw] bg-transparent p-0 md:hidden backdrop:bg-ink/60 backdrop:backdrop-blur-sm"
    >
      {open && (
        <div className="relative h-full">
          <button
            type="button"
            onClick={onClose}
            aria-label="Close navigation"
            className="absolute right-3 top-4 z-10 rounded-lg p-2 text-on-surface-variant hover:bg-surface-container cursor-pointer"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
          {children}
        </div>
      )}
    </dialog>
  );
}
