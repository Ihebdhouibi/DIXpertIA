import React, { useState } from 'react';
import { Plus, Edit, UserX, UserCheck, Mail } from 'lucide-react';
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
import { ROLE_LABEL } from '../navigation';

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
      showToast('Please fill in all fields.', 'error');
      return;
    }
    setSaving(true);
    try {
      if (editingUser) {
        await api.users.update(editingUser.id, { firstName, lastName, role });
        showToast(`User ${firstName} ${lastName} updated.`, 'success');
      } else {
        const created = await api.users.create({ email, firstName, lastName, role });
        showToast(
          created.activationEmailSent
            ? `Account created. An activation link was e-mailed to ${email}.`
            : 'Account created, but the activation e-mail could not be sent. Use "Resend activation link".',
          created.activationEmailSent ? 'success' : 'info',
        );
      }
      setShowModal(false);
      resetForm();
      onChanged?.();
    } catch (error) {
      // The form stays open with what was typed, so it can be corrected.
      showToast(failure(error, editingUser ? 'Could not update the account.' : 'Could not create the account.'), 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDeactivate = async (user: User) => {
    if (!isAdmin) return;
    const name = `${user.firstName} ${user.lastName}`;
    const ok = await confirm({
      title: `Deactivate ${name}?`,
      message: 'They are signed out everywhere at once and can no longer sign in. '
        + 'Their payslips and history are kept, and the account can be reactivated.',
      confirmLabel: 'Deactivate',
      tone: 'danger',
    });
    if (!ok) return;
    try {
      await api.users.deactivate(user.id);
      showToast(`${name} was deactivated.`, 'success');
      onChanged?.();
    } catch (error) {
      showToast(failure(error, 'Could not deactivate the account.'), 'error');
    }
  };

  const handleReactivate = async (user: User) => {
    if (!isAdmin) return;
    try {
      await api.users.update(user.id, { isActive: true });
      showToast(`${user.firstName} ${user.lastName} was reactivated.`, 'success');
      onChanged?.();
    } catch (error) {
      showToast(failure(error, 'Could not reactivate the account.'), 'error');
    }
  };

  const handleResendActivation = async (user: User) => {
    if (!isAdmin) return;
    try {
      const result = await api.users.resendActivation(user.id);
      showToast(
        result.activationEmailSent
          ? `A new activation link was e-mailed to ${user.email}. The previous one no longer works.`
          : 'The activation e-mail could not be sent. Check the e-mail settings and try again.',
        result.activationEmailSent ? 'success' : 'error',
      );
    } catch (error) {
      showToast(failure(error, 'Could not send the activation link.'), 'error');
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
          <h2 className="text-h2 font-black text-on-surface">Access Denied</h2>
          <p className="text-body-sm text-on-surface-variant mt-2">You do not have permission to view this page.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col gap-6 animate-fade-in">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-h1 font-black text-on-surface tracking-tight md:text-display">Users</h1>
          <p className="text-body-lg text-on-surface-variant mt-1">
            {isAdmin ? 'Manage employee accounts.' : 'View employee accounts.'}
          </p>
        </div>
        {isAdmin && (
          <Button onClick={handleOpenCreate} className="shrink-0">
            <Plus className="w-4 h-4" aria-hidden="true" />
            Add user
          </Button>
        )}
      </div>

      <TableToolbar>
        <SearchField label="Search users" value={searchQuery} onChange={setSearchQuery} className="sm:w-96" />
      </TableToolbar>

      <Table caption="User accounts">
        <THead>
          <Th>User</Th>
          <Th>Email</Th>
          <Th>Role</Th>
          <Th>Status</Th>
          {/* Only admins get an actions column; it used to render an extra
              body cell for accountants that had no header. */}
          {isAdmin && (
            <Th numeric>
              <span className="sr-only">Actions</span>
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
                  {ROLE_LABEL[u.role]}
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
                      aria-label={`Edit ${u.firstName} ${u.lastName}`}
                      className="rounded-lg p-1.5 text-on-surface-variant transition-colors hover:bg-surface-container hover:text-on-surface cursor-pointer"
                    >
                      <Edit className="w-4 h-4" aria-hidden="true" />
                    </button>
                    {u.isActive && !u.isVerified && (
                      <button
                        type="button"
                        onClick={() => handleResendActivation(u)}
                        aria-label={`Resend activation link to ${u.firstName} ${u.lastName}`}
                        title="Resend activation link"
                        className="rounded-lg p-1.5 text-on-surface-variant transition-colors hover:bg-surface-container hover:text-on-surface cursor-pointer"
                      >
                        <Mail className="w-4 h-4" aria-hidden="true" />
                      </button>
                    )}
                    {u.isActive && u.id !== currentUserId && (
                      <button
                        type="button"
                        onClick={() => handleDeactivate(u)}
                        aria-label={`Deactivate ${u.firstName} ${u.lastName}`}
                        title="Deactivate"
                        className="rounded-lg p-1.5 text-on-surface-variant transition-colors hover:bg-error-container hover:text-error cursor-pointer"
                      >
                        <UserX className="w-4 h-4" aria-hidden="true" />
                      </button>
                    )}
                    {!u.isActive && (
                      <button
                        type="button"
                        onClick={() => handleReactivate(u)}
                        aria-label={`Reactivate ${u.firstName} ${u.lastName}`}
                        title="Reactivate"
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
              <TableState kind="loading" colSpan={isAdmin ? 5 : 4} title="Loading users..." />
            ) : status.error && users.length === 0 ? (
              <TableState kind="error" colSpan={isAdmin ? 5 : 4} message={status.error} />
            ) : (
              <TableState
                kind="empty"
                colSpan={isAdmin ? 5 : 4}
                title={users.length === 0 ? 'No user accounts' : 'No users match'}
                message={users.length === 0 ? undefined : 'Try another name or e-mail.'}
              />
            ))}
        </TBody>
      </Table>

      {isAdmin && (
        <Dialog
          open={showModal}
          onClose={() => { setShowModal(false); resetForm(); }}
          title={editingUser ? 'Edit user' : 'Add new user'}
          footer={
            <>
              <Button variant="secondary" onClick={() => { setShowModal(false); resetForm(); }}>
                Cancel
              </Button>
              <Button type="submit" form="user-form" loading={saving}>
                {editingUser ? 'Update user' : 'Create user'}
              </Button>
            </>
          }
        >
          <form id="user-form" onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Field label="First name *">
              {({ id }) => (
                <Input id={id} required value={firstName} onChange={(e) => setFirstName(e.target.value)} placeholder="e.g. Jane" />
              )}
            </Field>
            <Field label="Last name *">
              {({ id }) => (
                <Input id={id} required value={lastName} onChange={(e) => setLastName(e.target.value)} placeholder="e.g. Doe" />
              )}
            </Field>
            <Field
              label="Email *"
              hint={editingUser
                ? 'The e-mail is the sign-in identity and cannot be changed here.'
                : 'An activation link is sent here; the person chooses their own password.'}
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
                  placeholder="jane.doe@example.com"
                />
              )}
            </Field>
            <Field
              label="Role"
              hint={editingUser?.id === currentUserId ? 'You cannot change your own role.' : undefined}
            >
              {({ id, describedBy }) => (
                <Select
                  id={id}
                  aria-describedby={describedBy}
                  value={role}
                  disabled={editingUser?.id === currentUserId}
                  onChange={(e) => setRole(e.target.value as UserRole)}
                >
                  <option value="employee">Employee</option>
                  <option value="admin">Admin</option>
                  <option value="accountant">Accountant</option>
                </Select>
              )}
            </Field>
          </form>
        </Dialog>
      )}
    </div>
  );
}
