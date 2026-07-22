import React, { useState } from 'react';
import {
  Bell,
  CheckCircle,
  AlertCircle,
  XCircle,
  Info,
  Filter,
  Check,
  X,
  Trash2,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { UserRole } from '../types';

interface Notification {
  id: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  read: boolean;
  timestamp: number;
  link?: string;
  targetRole?: 'admin' | 'employee';
}

interface NotificationsViewProps {
  notifications: Notification[];
  onMarkRead: (id: string) => void;
  onMarkAllRead: () => void;
  onClearAll: () => void;
  onNavigate: (link: string) => void;
  userRole: UserRole;
}

export default function NotificationsView({
  notifications,
  onMarkRead,
  onMarkAllRead,
  onClearAll,
  onNavigate,
  userRole,
}: NotificationsViewProps) {
  const [filterType, setFilterType] = useState<'all' | 'info' | 'success' | 'warning' | 'error'>('all');
  const [filterRead, setFilterRead] = useState<'all' | 'read' | 'unread'>('all');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

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

  const getIcon = (type: Notification['type']) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-emerald-500" />;
      case 'warning':
        return <AlertCircle className="w-5 h-5 text-amber-500" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Info className="w-5 h-5 text-blue-500" />;
    }
  };

  const formatTime = (ts: number) => {
    return new Date(ts).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="flex-1 flex flex-col gap-6 animate-fade-in">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-h1 font-black text-on-surface tracking-tight md:text-display">Notifications</h1>
          <p className="text-body-lg text-on-surface-variant mt-1">
            Stay updated with all your alerts and messages.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={onMarkAllRead}
            className="px-4 py-2 bg-primary/10 text-primary border border-primary/20 rounded-lg font-semibold text-caption hover:bg-primary/20 transition-colors flex items-center gap-2"
          >
            <Check className="w-4 h-4" />
            Mark all read
          </button>
          <button
            onClick={() => {
              if (window.confirm('Delete all notifications?')) {
                onClearAll();
              }
            }}
            className="px-4 py-2 bg-error/10 text-error border border-error/20 rounded-lg font-semibold text-caption hover:bg-error/20 transition-colors flex items-center gap-2"
          >
            <Trash2 className="w-4 h-4" />
            Clear all
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-outline-variant/30 p-4 flex flex-col md:flex-row gap-4 items-start md:items-center">
        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          <Filter className="w-4 h-4 text-outline" />
          <span className="text-caption font-bold text-on-surface-variant">Filter by:</span>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value as any)}
            className="px-3 py-1.5 border border-outline-variant rounded-lg text-caption font-medium bg-surface focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="all">All types</option>
            <option value="info">Info</option>
            <option value="success">Success</option>
            <option value="warning">Warning</option>
            <option value="error">Error</option>
          </select>
          <select
            value={filterRead}
            onChange={(e) => setFilterRead(e.target.value as any)}
            className="px-3 py-1.5 border border-outline-variant rounded-lg text-caption font-medium bg-surface focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="all">All status</option>
            <option value="read">Read</option>
            <option value="unread">Unread</option>
          </select>
        </div>
        {selectedIds.length > 0 && (
          <div className="flex items-center gap-2 ml-auto">
            <span className="text-caption font-medium text-on-surface-variant">
              {selectedIds.length} selected
            </span>
            <button
              onClick={handleMarkSelectedRead}
              className="px-3 py-1.5 bg-primary text-white rounded-lg text-caption font-bold hover:bg-primary/90 transition"
            >
              Mark read
            </button>
          </div>
        )}
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-outline-variant/30 overflow-hidden">
        {filtered.length === 0 ? (
          <div className="py-12 text-center text-on-surface-variant">
            <Bell className="w-12 h-12 mx-auto text-outline/50 mb-3" />
            <p className="text-body-lg font-medium">No notifications</p>
            <p className="text-caption">You're all caught up!</p>
          </div>
        ) : (
          <>
            <div className="px-4 py-2 border-b border-outline-variant/30 bg-surface-container-lowest flex items-center gap-3">
              <input
                type="checkbox"
                checked={selectedIds.length === filtered.length && filtered.length > 0}
                onChange={toggleSelectAll}
                className="rounded border-outline-variant text-primary focus:ring-primary w-4 h-4"
              />
              <span className="text-caption font-medium text-on-surface-variant">Select all</span>
            </div>
            <ul className="divide-y divide-outline-variant/30">
              {filtered.map((notif) => (
                <li
                  key={notif.id}
                  className={`px-4 py-3 hover:bg-surface-container-low transition-colors cursor-pointer flex items-start gap-3 ${
                    !notif.read ? 'bg-primary/5' : ''
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(notif.id)}
                    onChange={() => toggleSelect(notif.id)}
                    className="mt-1 rounded border-outline-variant text-primary focus:ring-primary w-4 h-4 shrink-0"
                    onClick={(e) => e.stopPropagation()}
                  />
                  <div className="shrink-0 mt-0.5">{getIcon(notif.type)}</div>
                  <div
                    className="flex-1 min-w-0"
                    onClick={() => {
                      if (notif.link) {
                        onNavigate(notif.link);
                      }
                    }}
                  >
                    <p className={`text-body-sm ${!notif.read ? 'font-bold' : 'font-medium'} text-on-surface`}>
                      {notif.message}
                    </p>
                    <p className="text-caption text-outline mt-0.5">{formatTime(notif.timestamp)}</p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onMarkRead(notif.id);
                    }}
                    className={`shrink-0 text-caption font-semibold ${
                      notif.read ? 'text-outline' : 'text-primary'
                    } hover:underline transition`}
                  >
                    {notif.read ? 'Read' : 'Mark read'}
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>

      <div className="flex justify-between items-center text-caption text-on-surface-variant">
        <span>Showing {filtered.length} notifications</span>
        <div className="flex gap-2">
          <button className="p-1 rounded border border-outline-variant disabled:opacity-40" disabled>
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button className="p-1 rounded border border-outline-variant disabled:opacity-40" disabled>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}