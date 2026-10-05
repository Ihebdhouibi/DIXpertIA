import React, { useState } from 'react';
import { Plus, Search, Edit, Trash2, X, Check, AlertCircle } from 'lucide-react';
import { User, UserRole } from '../types';
import StatusBadge from './StatusBadge';
import Dialog from './ui/Dialog';
import Button from './ui/Button';
import { Field, Input, Select } from './ui/Field';
import { useConfirm, useToast } from './ui/feedback';

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
          <button
            onClick={handleOpenCreate}
            className="bg-primary hover:bg-primary/95 text-on-primary font-semibold text-body-sm px-6 py-2.5 rounded-lg shadow-sm transition-all flex items-center gap-2 cursor-pointer shrink-0"
          >
            <Plus className="w-5 h-5" />
            <span>Add User</span>
          </button>
        )}
      </div>

      <div className="bg-surface-container-lowest rounded-xl shadow-sm border border-outline-variant/30 p-4 flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="relative w-full md:max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-outline w-5 h-5" />
          <input
            type="text"
            placeholder="Search users..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-surface border border-outline-variant rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all text-body-sm text-on-surface placeholder:text-outline"
          />
        </div>
      </div>

      <div className="bg-surface-container-lowest rounded-xl shadow-sm border border-outline-variant/30 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[700px]">
            <thead>
              <tr className="border-b border-outline-variant bg-surface-container-lowest">
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">User</th>
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Email</th>
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Role</th>
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Status</th>
                {isAdmin && (
                  <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider text-right">Actions</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/40">
              {filteredUsers.map((u) => (
                <tr key={u.id} className="hover:bg-surface-container-low transition-colors group">
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-xs">
                        {u.firstName[0]}{u.lastName[0]}
                      </div>
                      <span className="font-bold text-body-sm text-on-surface">{u.firstName} {u.lastName}</span>
                    </div>
                  </td>
                  <td className="py-4 px-6 text-body-sm text-on-surface-variant">{u.email}</td>
                  <td className="py-4 px-6">
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                      u.role === 'admin'
                        ? 'bg-primary/10 text-primary border-primary/20'
                        : u.role === 'accountant'
                        ? 'bg-info-container text-info border-info/20'
                        : 'bg-surface-variant text-on-surface-variant border-outline-variant'
                    }`}>
                      {u.role}
                    </span>
                  </td>
                  <td className="py-4 px-6">
                    <StatusBadge status={u.isActive ? 'Active' : 'Inactive'} />
                  </td>
                  {/*
                    Each button appears only if its handler was supplied. The
                    API has no endpoint for editing or deleting an account yet
                    (#62), so they are currently hidden rather than shown doing
                    nothing - a button that silently fails is worse than no
                    button.
                  */}
                  {isAdmin && (
                    <td className="py-4 px-6 text-right">
                      <div className="flex justify-end gap-2">
                        {onEditUser && (
                          <button
                            onClick={() => handleOpenEdit(u)}
                            className="p-1.5 text-on-surface-variant hover:text-primary rounded transition-colors cursor-pointer"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                        )}
                        {onDeleteUser && (
                          <button
                            onClick={() => handleDelete(u.id, `${u.firstName} ${u.lastName}`)}
                            className="p-1.5 text-on-surface-variant hover:text-error rounded transition-colors cursor-pointer"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  )}
                  {!isAdmin && (
                    <td className="py-4 px-6 text-right text-caption text-on-surface-variant">—</td>
                  )}
                </tr>
              ))}
              {filteredUsers.length === 0 && (
                <tr>
                  <td colSpan={isAdmin ? 5 : 4} className="py-12 px-6 text-center text-on-surface-variant font-medium">
                    No users found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

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
