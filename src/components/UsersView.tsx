import React, { useState } from 'react';
import { Plus, Search, Edit, Trash2, X, Check, AlertCircle } from 'lucide-react';
import { User, UserRole } from '../types';

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
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const [email, setEmail] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [role, setRole] = useState<UserRole>('employee');
  const [searchQuery, setSearchQuery] = useState('');

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
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

  const handleDelete = (id: string, name: string) => {
    if (!isAdmin) return;
    if (window.confirm(`Delete user ${name}?`)) {
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
        <div className="bg-white p-8 rounded-xl border border-outline-variant shadow-sm text-center max-w-2xl mx-auto">
          <h2 className="text-h2 font-black text-on-surface">Access Denied</h2>
          <p className="text-body-sm text-on-surface-variant mt-2">You do not have permission to view this page.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col gap-6 animate-fade-in">
      {toast && (
        <div
          className={`fixed bottom-4 right-4 z-50 py-3 px-5 rounded-lg shadow-lg flex items-center gap-2 animate-fade-in text-body-sm font-semibold border ${
            toast.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
              : 'bg-red-50 text-red-800 border-red-200'
          }`}
        >
          {toast.type === 'success' ? <Check className="w-5 h-5 shrink-0" /> : <AlertCircle className="w-5 h-5 shrink-0" />}
          <span>{toast.message}</span>
        </div>
      )}

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
            className="bg-primary hover:bg-primary/95 text-white font-semibold text-body-sm px-6 py-2.5 rounded-lg shadow-sm transition-all flex items-center gap-2 cursor-pointer shrink-0"
          >
            <Plus className="w-5 h-5" />
            <span>Add User</span>
          </button>
        )}
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-outline-variant/30 p-4 flex flex-col md:flex-row gap-4 items-center justify-between">
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

      <div className="bg-white rounded-xl shadow-sm border border-outline-variant/30 overflow-hidden">
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
                        ? 'bg-amber-50 text-amber-700 border-amber-200'
                        : 'bg-surface-variant text-on-surface-variant border-outline-variant'
                    }`}>
                      {u.role}
                    </span>
                  </td>
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${u.isActive ? 'bg-emerald-500' : 'bg-gray-400'}`}></div>
                      <span className="text-body-sm font-semibold text-on-surface">{u.isActive ? 'Active' : 'Inactive'}</span>
                    </div>
                  </td>
                  {isAdmin && (
                    <td className="py-4 px-6 text-right">
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => handleOpenEdit(u)}
                          className="p-1.5 text-on-surface-variant hover:text-primary rounded transition-colors cursor-pointer"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(u.id, `${u.firstName} ${u.lastName}`)}
                          className="p-1.5 text-on-surface-variant hover:text-error rounded transition-colors cursor-pointer"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
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

      {isAdmin && showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-on-background/40 backdrop-blur-sm" onClick={() => setShowModal(false)}></div>
          <div className="relative bg-white rounded-xl shadow-[0_8px_32px_rgba(3,34,77,0.15)] w-full max-w-md max-h-[90%] overflow-y-auto border border-outline-variant animate-scale-up">
            <div className="flex items-center justify-between px-6 py-4 border-b border-outline-variant/50 bg-surface sticky top-0 z-10">
              <h2 className="text-h2 font-black text-on-surface">{editingUser ? 'Edit User' : 'Add New User'}</h2>
              <button
                className="text-on-surface-variant hover:text-on-surface p-1 rounded-full hover:bg-surface-container transition-colors cursor-pointer"
                onClick={() => { setShowModal(false); resetForm(); }}
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-5">
              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1">
                  First Name <span className="text-error">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="e.g. Jane"
                  className="w-full px-3 py-2 bg-surface border border-outline-variant rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-body-sm text-on-surface"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1">
                  Last Name <span className="text-error">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="e.g. Doe"
                  className="w-full px-3 py-2 bg-surface border border-outline-variant rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-body-sm text-on-surface"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1">
                  Email <span className="text-error">*</span>
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="jane.doe@example.com"
                  className="w-full px-3 py-2 bg-surface border border-outline-variant rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-body-sm text-on-surface"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1">Role</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value as UserRole)}
                  className="w-full px-3 py-2 bg-surface border border-outline-variant rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-body-sm text-on-surface cursor-pointer"
                >
                  <option value="employee">Employee</option>
                  <option value="admin">Admin</option>
                  <option value="accountant">Accountant</option>
                </select>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-outline-variant/30">
                <button
                  type="button"
                  onClick={() => { setShowModal(false); resetForm(); }}
                  className="px-4 py-2 border border-primary text-primary rounded-lg font-bold text-body-sm hover:bg-primary/5 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary text-white rounded-lg font-bold text-body-sm hover:bg-primary/95 transition-colors shadow-sm cursor-pointer"
                >
                  {editingUser ? 'Update User' : 'Create User'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}