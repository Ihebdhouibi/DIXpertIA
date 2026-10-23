import React, { useState } from 'react';
import { Plus, Edit, UserX, ShieldOff, UserCheck, Mail } from 'lucide-react';
import { User, UserRole } from '../types';
import * as api from '../api';
import StatusBadge from './StatusBadge';
import Dialog from './ui/Dialog';
import Button from './ui/Button';
import { Field, Input, Select } from './ui/Field';
import { useConfirm, useToast } from './ui/feedback';
import Avatar from './ui/Avatar';
import { Table, THead, Th, TBody, Tr, Td, TableState } from './ui/Table';
import { SearchField, TableToolbar } from './ui/TableControls';
import { useDataStatus } from '../dataStatus';
import { useT, type MessageKey } from '../i18n';

const ROLE_LABEL: Record<UserRole, MessageKey> = {
  admin: 'common.role.admin',
  accountant: 'common.role.accountant',
  employee: 'common.role.employee',
};

interface UsersViewProps {
  users: User[];
  userRole: UserRole;
  /** The signed-in account: an admin cannot demote or deactivate themselves. */
  currentUserId?: string;
  /**
   * Called after the server accepted a change, so the app reloads the list.
   * The view talks to the API itself (#62), like the invoice view (#128): it
   * can then report what actually happened instead of announcing success
   * before the server has answered.
   */
  onChanged?: () => void;
}

function failure(error: unknown, fallback: string): string {
  return error instanceof api.ApiError ? error.message : fallback;
}

export default function UsersView({ users, userRole, currentUserId, onChanged }: UsersViewProps) {
  const isAdmin = userRole === 'admin';
  const [saving, setSaving] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);

  const [email, setEmail] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [role, setRole] = useState<UserRole>('employee');
  const [searchQuery, setSearchQuery] = useState('');
  const status = useDataStatus();
  const t = useT();

  const toast = useToast();
  const confirm = useConfirm();
  const showToast = (message: string, type: 'success' | 'error' | 'info') => {
    toast(message, type);
  };

  const resetForm = () => {
    setEmail('');
    setFirstName('');
    setLastName('');
    setRole('employee');
    setEditingUser(null);
  };

  const handleOpenCreate = () => {
    if (!isAdmin) return;
    resetForm();
    setShowModal(true);
  };

  const handleOpenEdit = (user: User) => {
    if (!isAdmin) return;
    setEditingUser(user);
    setEmail(user.email);
    setFirstName(user.firstName);
    setLastName(user.lastName);
    setRole(user.role);
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAdmin || saving) return;
    if (!email || !firstName || !lastName) {
      showToast(t('people.users.fillAll'), 'error');
      return;
    }
    setSaving(true);
    try {
      if (editingUser) {
        await api.users.update(editingUser.id, { firstName, lastName, role });
        showToast(t('people.users.updated', { name: `${firstName} ${lastName}` }), 'success');
      } else {
        const created = await api.users.create({ email, firstName, lastName, role });
        showToast(
          created.activationEmailSent
            ? t('people.users.createdSent', { email })
            : t('people.users.createdNotSent'),
          created.activationEmailSent ? 'success' : 'info',
        );
      }
      setShowModal(false);
      resetForm();
      onChanged?.();
    } catch (error) {
      // The form stays open with what was typed, so it can be corrected.
      showToast(
        failure(error, editingUser ? t('people.users.couldNotUpdate') : t('people.users.couldNotCreate')),
        'error',
      );
    } finally {
      setSaving(false);
    }
  };

  const handleDeactivate = async (user: User) => {
    if (!isAdmin) return;
    const name = `${user.firstName} ${user.lastName}`;
    const ok = await confirm({
      title: t('people.users.deactivateTitle', { name }),
      message: t('people.users.deactivateMessage'),
      confirmLabel: t('people.users.deactivate'),
      tone: 'danger',
    });
    if (!ok) return;
    try {
      await api.users.deactivate(user.id);
      showToast(t('people.users.deactivated', { name }), 'success');
      onChanged?.();
    } catch (error) {
      showToast(failure(error, t('people.users.couldNotDeactivate')), 'error');
    }
  };

  const handleReactivate = async (user: User) => {
    if (!isAdmin) return;
    try {
      await api.users.update(user.id, { isActive: true });
      showToast(t('people.users.reactivated', { name: `${user.firstName} ${user.lastName}` }), 'success');
      onChanged?.();
    } catch (error) {
      showToast(failure(error, t('people.users.couldNotReactivate')), 'error');
    }
  };

  // A lost phone (#44): the person signs in with the password alone, then sets
  // two-factor up again. Not one's own: that would skip the second factor.
  const handleResetMfa = async (user: User) => {
    if (!isAdmin) return;
    const name = `${user.firstName} ${user.lastName}`;
    const ok = await confirm({
      title: t('people.users.resetMfaTitle', { name }),
      message: t('people.users.resetMfaMessage'),
      confirmLabel: t('people.users.resetMfa'),
      tone: 'danger',
    });
    if (!ok) return;
    try {
      await api.mfa.reset(user.id);
      showToast(t('people.users.mfaReset', { name }), 'success');
    } catch (error) {
      showToast(failure(error, t('people.users.couldNotResetMfa')), 'error');
    }
  };

  const handleResendActivation = async (user: User) => {
    if (!isAdmin) return;
    try {
      const result = await api.users.resendActivation(user.id);
      showToast(
        result.activationEmailSent
          ? t('people.users.resentSent', { email: user.email })
          : t('people.users.resentNotSent'),
        result.activationEmailSent ? 'success' : 'error',
      );
    } catch (error) {
      showToast(failure(error, t('people.users.couldNotResend')), 'error');
    }
  };

  const filteredUsers = users.filter(u =>
    `${u.firstName} ${u.lastName}`.toLowerCase().includes(searchQuery.toLowerCase()) ||
    u.email.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (!isAdmin && userRole !== 'accountant') {
    return (
      <div className="flex-1 flex flex-col gap-6 animate-fade-in">
        <div className="bg-surface-container-lowest p-8 rounded-xl border border-outline-variant shadow-sm text-center max-w-2xl mx-auto">
          <h2 className="text-h2 font-black text-on-surface">{t('common.accessDenied')}</h2>
          <p className="text-body-sm text-on-surface-variant mt-2">{t('common.noPermissionPage')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col gap-6 animate-fade-in">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-h1 font-black text-on-surface tracking-tight md:text-display">{t('people.users.title')}</h1>
          <p className="text-body-lg text-on-surface-variant mt-1">
            {isAdmin ? t('people.users.subtitleAdmin') : t('people.users.subtitleRead')}
          </p>
        </div>
        {isAdmin && (
          <Button onClick={handleOpenCreate} className="shrink-0">
            <Plus className="w-4 h-4" aria-hidden="true" />
            {t('people.users.add')}
          </Button>
        )}
      </div>

      <TableToolbar>
        <SearchField label={t('people.users.search')} value={searchQuery} onChange={setSearchQuery} className="sm:w-96" />
      </TableToolbar>

      <Table caption={t('people.users.caption')}>
        <THead>
          <Th>{t('people.users.colUser')}</Th>
          <Th>{t('people.col.email')}</Th>
          <Th>{t('people.users.colRole')}</Th>
          <Th>{t('people.col.status')}</Th>
          {/* Only admins get an actions column; it used to render an extra
              body cell for accountants that had no header. */}
          {isAdmin && (
            <Th numeric>
              <span className="sr-only">{t('people.col.actions')}</span>
            </Th>
          )}
        </THead>
        <TBody>
          {filteredUsers.map((u) => (
            <Tr key={u.id}>
              <Td>
                <div className="flex items-center gap-3">
                  <Avatar name={`${u.firstName} ${u.lastName}`} size="sm" />
                  <span className="font-semibold">
                    {u.firstName} {u.lastName}
                  </span>
                </div>
              </Td>
              <Td muted>{u.email}</Td>
              <Td>
                <span className="font-mono text-[11px] uppercase tracking-[0.08em] text-on-surface-variant">
                  {ROLE_LABEL[u.role] ? t(ROLE_LABEL[u.role]) : u.role}
                </span>
              </Td>
              <Td>
                {/* Pending: created, but the owner has not set a password yet. */}
                <StatusBadge status={!u.isActive ? 'Inactive' : u.isVerified ? 'Active' : 'Pending'} />
              </Td>
              {/*
                No delete: payslips and leave history must be kept, so a
                departure is a deactivation, which also signs the person out
                everywhere (#62). An admin's own row has no deactivate button;
                the server refuses it as well.
              */}
              {isAdmin && (
                <Td numeric>
                  <div className="flex justify-end gap-1">
                    <button
                      type="button"
                      onClick={() => handleOpenEdit(u)}
                      aria-label={t('people.users.edit', { name: `${u.firstName} ${u.lastName}` })}
                      className="rounded-lg p-1.5 text-on-surface-variant transition-colors hover:bg-surface-container hover:text-on-surface cursor-pointer"
                    >
                      <Edit className="w-4 h-4" aria-hidden="true" />
                    </button>
                    {u.isActive && !u.isVerified && (
                      <button
                        type="button"
                        onClick={() => handleResendActivation(u)}
                        aria-label={t('people.users.resendTo', { name: `${u.firstName} ${u.lastName}` })}
                        title={t('people.users.resend')}
                        className="rounded-lg p-1.5 text-on-surface-variant transition-colors hover:bg-surface-container hover:text-on-surface cursor-pointer"
                      >
                        <Mail className="w-4 h-4" aria-hidden="true" />
                      </button>
                    )}
                    {u.isActive && u.isVerified && u.id !== currentUserId && (
                      <button
                        type="button"
                        onClick={() => handleResetMfa(u)}
                        aria-label={t('people.users.resetMfaName', { name: `${u.firstName} ${u.lastName}` })}
                        title={t('people.users.resetMfa')}
                        className="rounded-lg p-1.5 text-on-surface-variant transition-colors hover:bg-surface-container hover:text-on-surface cursor-pointer"
                      >
                        <ShieldOff className="w-4 h-4" aria-hidden="true" />
                      </button>
                    )}
                    {u.isActive && u.id !== currentUserId && (
                      <button
                        type="button"
                        onClick={() => handleDeactivate(u)}
                        aria-label={t('people.users.deactivateName', { name: `${u.firstName} ${u.lastName}` })}
                        title={t('people.users.deactivate')}
                        className="rounded-lg p-1.5 text-on-surface-variant transition-colors hover:bg-error-container hover:text-error cursor-pointer"
                      >
                        <UserX className="w-4 h-4" aria-hidden="true" />
                      </button>
                    )}
                    {!u.isActive && (
                      <button
                        type="button"
                        onClick={() => handleReactivate(u)}
                        aria-label={t('people.users.reactivateName', { name: `${u.firstName} ${u.lastName}` })}
                        title={t('people.users.reactivate')}
                        className="rounded-lg p-1.5 text-on-surface-variant transition-colors hover:bg-surface-container hover:text-on-surface cursor-pointer"
                      >
                        <UserCheck className="w-4 h-4" aria-hidden="true" />
                      </button>
                    )}
                  </div>
                </Td>
              )}
            </Tr>
          ))}
          {filteredUsers.length === 0 &&
            (status.loading ? (
              <TableState kind="loading" colSpan={isAdmin ? 5 : 4} title={t('people.users.loading')} />
            ) : status.error && users.length === 0 ? (
              <TableState kind="error" colSpan={isAdmin ? 5 : 4} message={status.error} />
            ) : (
              <TableState
                kind="empty"
                colSpan={isAdmin ? 5 : 4}
                title={users.length === 0 ? t('people.users.emptyNone') : t('people.users.emptyNoMatch')}
                message={users.length === 0 ? undefined : t('people.users.emptyHint')}
              />
            ))}
        </TBody>
      </Table>

      {isAdmin && (
        <Dialog
          open={showModal}
          onClose={() => { setShowModal(false); resetForm(); }}
          title={editingUser ? t('people.users.editTitle') : t('people.users.addTitle')}
          footer={
            <>
              <Button variant="secondary" onClick={() => { setShowModal(false); resetForm(); }}>
                {t('people.cancel')}
              </Button>
              <Button type="submit" form="user-form" loading={saving}>
                {editingUser ? t('people.users.save') : t('people.users.create')}
              </Button>
            </>
          }
        >
          <form id="user-form" onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Field label={t('people.users.firstName')}>
              {({ id }) => (
                <Input
                  id={id}
                  required
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder={t('people.users.firstNamePlaceholder')}
                />
              )}
            </Field>
            <Field label={t('people.users.lastName')}>
              {({ id }) => (
                <Input
                  id={id}
                  required
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder={t('people.users.lastNamePlaceholder')}
                />
              )}
            </Field>
            <Field
              label={t('people.users.email')}
              hint={editingUser ? t('people.users.emailHintEdit') : t('people.users.emailHintNew')}
            >
              {({ id, describedBy }) => (
                <Input
                  id={id}
                  aria-describedby={describedBy}
                  type="email"
                  required
                  disabled={!!editingUser}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={t('people.users.emailPlaceholder')}
                />
              )}
            </Field>
            <Field
              label={t('people.users.role')}
              hint={editingUser?.id === currentUserId ? t('people.users.ownRole') : undefined}
            >
              {({ id, describedBy }) => (
                <Select
                  id={id}
                  aria-describedby={describedBy}
                  value={role}
                  disabled={editingUser?.id === currentUserId}
                  onChange={(e) => setRole(e.target.value as UserRole)}
                >
                  <option value="employee">{t('common.role.employee')}</option>
                  <option value="admin">{t('common.role.admin')}</option>
                  <option value="accountant">{t('common.role.accountant')}</option>
                </Select>
              )}
            </Field>
          </form>
        </Dialog>
      )}
    </div>
  );
}
