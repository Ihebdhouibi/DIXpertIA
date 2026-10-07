import React, { useState } from 'react';
import { Plus, Edit, Trash2 } from 'lucide-react';
import { User, UserRole } from '../types';
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
  onAddUser?: (user: Partial<User> & { password?: string }) => void;
  onEditUser?: (id: string, updates: Partial<User>) => void;
  onDeleteUser?: (id: string) => void;
  userRole: UserRole;
}

export default function UsersView({ users, onAddUser, onEditUser, onDeleteUser, userRole }: UsersViewProps) {
  const isAdmin = userRole === 'admin';
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
  const showToast = (message: string, type: 'success' | 'error') => {
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAdmin) return;
    if (!email || !firstName || !lastName) {
      showToast('Please fill in all fields.', 'error');
      return;
    }
    if (editingUser) {
      onEditUser?.(editingUser.id, { email, firstName, lastName, role });
      showToast(`User ${firstName} ${lastName} updated.`, 'success');
    } else {
      onAddUser?.({ email, firstName, lastName, role });
      showToast(`User ${firstName} ${lastName} created.`, 'success');
    }
    setShowModal(false);
    resetForm();
  };

  const handleDelete = async (id: string, name: string) => {
    if (!isAdmin) return;
    const ok = await confirm({
      title: `Delete user ${name}?`,
      message: 'Their account will be removed. This cannot be undone.',
      confirmLabel: 'Delete user',
      tone: 'danger',
    });
    if (ok) {
      onDeleteUser?.(id);
      showToast(`User ${name} deleted.`, 'success');
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
                <StatusBadge status={u.isActive ? 'Active' : 'Inactive'} />
              </Td>
              {/*
                Each button appears only if its handler was supplied. The
                API has no endpoint for editing or deleting an account yet
                (#62), so they are currently hidden rather than shown doing
                nothing - a button that silently fails is worse than no
                button.
              */}
              {isAdmin && (
                <Td numeric>
                  <div className="flex justify-end gap-1">
                    {onEditUser && (
                      <button
                        type="button"
                        onClick={() => handleOpenEdit(u)}
                        aria-label={`Edit ${u.firstName} ${u.lastName}`}
                        className="rounded-lg p-1.5 text-on-surface-variant transition-colors hover:bg-surface-container hover:text-on-surface cursor-pointer"
                      >
                        <Edit className="w-4 h-4" aria-hidden="true" />
                      </button>
                    )}
                    {onDeleteUser && (
                      <button
                        type="button"
                        onClick={() => handleDelete(u.id, `${u.firstName} ${u.lastName}`)}
                        aria-label={`Delete ${u.firstName} ${u.lastName}`}
                        className="rounded-lg p-1.5 text-on-surface-variant transition-colors hover:bg-error-container hover:text-error cursor-pointer"
                      >
                        <Trash2 className="w-4 h-4" aria-hidden="true" />
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
              <Button type="submit" form="user-form">
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
            <Field label="Email *">
              {({ id }) => (
                <Input
                  id={id}
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="jane.doe@example.com"
                />
              )}
            </Field>
            <Field label="Role">
              {({ id }) => (
                <Select id={id} value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
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
