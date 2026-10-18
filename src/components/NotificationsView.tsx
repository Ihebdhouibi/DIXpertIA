import React, { useState } from 'react';
import { UserRole } from '../types';
import { useConfirm } from './ui/feedback';
import Button from './ui/Button';

import { Bell, CheckCircle, AlertCircle, XCircle, Info, Check, Trash2 } from 'lucide-react';
import { FilterPills } from './ui/TableControls';
import { formatDateTime } from '../format';
import { useT, type MessageKey } from '../i18n';

interface Notification {
  id: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  read: boolean;
  timestamp: number;
  link?: string;
}

interface NotificationsViewProps {
  notifications: Notification[];
  onMarkRead: (id: string) => void;
  onMarkAllRead: () => void;
  onClearAll: () => void;
  onClearSelected: (ids: string[]) => void;
  onNavigate: (link: string) => void;
  userRole: UserRole;
}

export default function NotificationsView({
  notifications,
  onMarkRead,
  onMarkAllRead,
  onClearAll,
  onClearSelected,
  onNavigate,
  userRole,
}: NotificationsViewProps) {
  const t = useT();
  const confirm = useConfirm();
  const [filterType, setFilterType] = useState<'all' | 'info' | 'success' | 'warning' | 'error'>('all');
  const [filterRead, setFilterRead] = useState<'all' | 'read' | 'unread'>('all');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // Filter notifications
  const filtered = notifications.filter(n => {
    const matchType = filterType === 'all' || n.type === filterType;
    const matchRead = filterRead === 'all' || (filterRead === 'read' ? n.read : !n.read);
    return matchType && matchRead;
  });

  const toggleSelect = (id: string) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === filtered.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filtered.map(n => n.id));
    }
  };

  const handleMarkSelectedRead = () => {
    selectedIds.forEach(id => onMarkRead(id));
    setSelectedIds([]);
  };

  // Deletes only the selected notifications. It used to call onClearAll once
  // per selected item, which wiped every notification (#106).
  const handleClearSelected = async () => {
    const count = selectedIds.length;
    const ok = await confirm({
      title: t('common.notifications.deleteSelected', { count }),
      message: t('common.cannotBeUndone'),
      confirmLabel: t('common.delete'),
      tone: 'danger',
    });
    if (ok) {
      onClearSelected(selectedIds);
      setSelectedIds([]);
    }
  };

  const handleClearAll = async () => {
    const ok = await confirm({
      title: t('common.notifications.deleteAll'),
      message: t('common.cannotBeUndone'),
      confirmLabel: t('common.notifications.deleteAllConfirm'),
      tone: 'danger',
    });
    if (ok) onClearAll();
  };

  const getIcon = (type: Notification['type']) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-success" />;
      case 'warning':
        return <AlertCircle className="w-5 h-5 text-warning" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-danger" />;
      default:
        return <Info className="w-5 h-5 text-info" />;
    }
  };

  const TYPE_LABEL: Record<typeof filterType, MessageKey> = {
    all: 'common.notifications.filter.all',
    info: 'common.notifications.filter.info',
    success: 'common.notifications.filter.success',
    warning: 'common.notifications.filter.warning',
    error: 'common.notifications.filter.error',
  };
  const READ_LABEL: Record<typeof filterRead, MessageKey> = {
    all: 'common.notifications.filter.all',
    unread: 'common.notifications.filter.unread',
    read: 'common.notifications.filter.read',
  };

  return (
    <div className="flex-1 flex flex-col gap-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-h1 font-black text-on-surface tracking-tight md:text-display">{t('common.notifications.title')}</h1>
          <p className="text-body-lg text-on-surface-variant mt-1">
            {t('common.notifications.subtitle')}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={onMarkAllRead}>
            <Check className="w-4 h-4" aria-hidden="true" />
            {t('common.notifications.markAllRead')}
          </Button>
          <Button variant="ghost" onClick={handleClearAll} className="text-error hover:bg-error-container">
            <Trash2 className="w-4 h-4" aria-hidden="true" />
            {t('common.notifications.clearAll')}
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4 lg:flex-row lg:items-center">
        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:gap-6">
          <FilterPills
            label={t('common.notifications.type')}
            showLabel
            options={['all', 'info', 'success', 'warning', 'error'] as const}
            value={filterType}
            onChange={setFilterType}
            renderOption={(o) => t(TYPE_LABEL[o])}
          />
          <FilterPills
            label={t('common.notifications.status')}
            showLabel
            options={['all', 'unread', 'read'] as const}
            value={filterRead}
            onChange={setFilterRead}
            renderOption={(o) => t(READ_LABEL[o])}
          />
        </div>
        {selectedIds.length > 0 && (
          <div className="flex items-center gap-2 lg:ml-auto">
            <span className="text-sm text-on-surface-variant">
              <span className="font-mono tabular-nums text-on-surface">{selectedIds.length}</span>{' '}
              {t('common.notifications.selected', { count: selectedIds.length })}
            </span>
            <Button size="sm" onClick={handleMarkSelectedRead}>
              {t('common.notifications.markRead')}
            </Button>
            {/* handleClearSelected existed but no control called it (#106). */}
            <Button variant="danger" size="sm" onClick={handleClearSelected}>
              <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
              {t('common.delete')}
            </Button>
          </div>
        )}
      </div>

      {/* Notification list */}
      <div className="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest">
        {filtered.length === 0 ? (
          <div role="status" className="flex flex-col items-center gap-2 px-5 py-12 text-center">
            <Bell className="h-6 w-6 text-on-surface-variant" aria-hidden="true" />
            <p className="text-sm font-semibold text-on-surface">
              {notifications.length === 0 ? t('common.notifications.allCaughtUp') : t('common.notifications.noMatch')}
            </p>
            {notifications.length > 0 && (
              <p className="text-sm text-on-surface-variant">{t('common.notifications.tryAnother')}</p>
            )}
          </div>
        ) : (
          <>
            <label className="flex items-center gap-3 border-b border-outline-variant bg-surface-container-low px-5 py-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedIds.length === filtered.length && filtered.length > 0}
                onChange={toggleSelectAll}
                className="h-4 w-4 accent-primary cursor-pointer"
              />
              <span className="font-mono text-[11px] font-medium uppercase tracking-[0.08em] text-on-surface-variant">
                {t('common.notifications.selectAll')}
              </span>
            </label>

            <ul className="divide-y divide-outline-variant">
              {filtered.map((notif) => (
                <li
                  key={notif.id}
                  className={`flex items-start gap-3 px-5 py-3.5 transition-colors ${
                    notif.read ? '' : 'bg-surface-container-low'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(notif.id)}
                    onChange={() => toggleSelect(notif.id)}
                    aria-label={t('common.notifications.selectOne', { message: notif.message })}
                    className="mt-1 h-4 w-4 shrink-0 accent-primary cursor-pointer"
                  />
                  <div className="mt-0.5 shrink-0">{getIcon(notif.type)}</div>
                  <div className="min-w-0 flex-1">
                    {/* A button when the notification leads somewhere, so the
                        keyboard can reach it (it was a clickable div). */}
                    {notif.link ? (
                      <button
                        type="button"
                        onClick={() => onNavigate(notif.link!)}
                        className={`rounded text-left text-sm text-on-surface hover:underline cursor-pointer ${notif.read ? '' : 'font-semibold'}`}
                      >
                        {notif.message}
                      </button>
                    ) : (
                      <p className={`text-sm text-on-surface ${notif.read ? '' : 'font-semibold'}`}>{notif.message}</p>
                    )}
                    <p className="mt-0.5 font-mono text-[11px] text-on-surface-variant">{formatDateTime(notif.timestamp)}</p>
                  </div>
                  {notif.read ? (
                    <span className="shrink-0 font-mono text-[11px] uppercase tracking-[0.08em] text-on-surface-variant">{t('common.notifications.read')}</span>
                  ) : (
                    <button
                      type="button"
                      onClick={() => onMarkRead(notif.id)}
                      className="shrink-0 rounded text-xs font-semibold text-secondary hover:underline cursor-pointer"
                    >
                      {t('common.notifications.markRead')}
                    </button>
                  )}
                </li>
              ))}
            </ul>
            {/* The old footer had two pagination buttons that were always
                disabled; the count stays, the dead controls go. */}
            <p className="border-t border-outline-variant px-5 py-3 text-sm text-on-surface-variant">
              <span className="font-mono tabular-nums text-on-surface">{filtered.length}</span> {t('common.pagination.of')}{' '}
              <span className="font-mono tabular-nums text-on-surface">{notifications.length}</span>{' '}
              {t('common.notifications.noun', { count: notifications.length })}
            </p>
          </>
        )}
      </div>
    </div>
  );
}
