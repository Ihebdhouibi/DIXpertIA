import React, { useState } from 'react';
import { Plus, Search, Edit, Trash2, X, Check, AlertCircle, Calendar, Users } from 'lucide-react';
import { Project } from '../types';

interface ProjectsViewProps {
  projects: Project[];
  onAddProject: (project: Partial<Project>) => void;
  onEditProject: (id: string, updates: Partial<Project>) => void;
  onDeleteProject: (id: string) => void;
  userRole: 'admin' | 'employee';
  teamMembers: { id: string; firstName: string; lastName: string }[];
}

export default function ProjectsView({
  projects,
  onAddProject,
  onEditProject,
  onDeleteProject,
  userRole,
  teamMembers,
}: ProjectsViewProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<Project['status'] | 'All'>('All');
  const [showModal, setShowModal] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const [name, setName] = useState('');
  const [client, setClient] = useState('');
  const [description, setDescription] = useState('');
  const [status, setStatus] = useState<Project['status']>('Active');
  const [deadline, setDeadline] = useState('');
  const [selectedTeam, setSelectedTeam] = useState<string[]>([]);

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const resetForm = () => {
    setName('');
    setClient('');
    setDescription('');
    setStatus('Active');
    setDeadline('');
    setSelectedTeam([]);
    setEditingProject(null);
  };

  const handleOpenCreate = () => {
    resetForm();
    setShowModal(true);
  };

  const handleOpenEdit = (project: Project) => {
    setEditingProject(project);
    setName(project.name);
    setClient(project.client);
    setDescription(project.description || '');
    setStatus(project.status);
    setDeadline(project.deadline);
    setSelectedTeam(project.teamMembers || []);
    setShowModal(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !client.trim() || !deadline) {
      showToast('Please fill in all required fields.', 'error');
      return;
    }

    const projectData: Partial<Project> = {
      name: name.trim(),
      client: client.trim(),
      description: description.trim(),
      status,
      deadline,
      teamMembers: selectedTeam,
    };

    if (editingProject) {
      onEditProject(editingProject.id, projectData);
      showToast(`Project "${name}" updated successfully.`, 'success');
    } else {
      onAddProject(projectData);
      showToast(`Project "${name}" created successfully.`, 'success');
    }

    setShowModal(false);
    resetForm();
  };

  const handleDelete = (id: string, name: string) => {
    if (window.confirm(`Are you sure you want to delete the project "${name}"?`)) {
      onDeleteProject(id);
      showToast(`Project "${name}" deleted.`, 'success');
    }
  };

  const filteredProjects = projects.filter((p) => {
    const query = searchQuery.toLowerCase();
    const matchesSearch =
      p.name.toLowerCase().includes(query) ||
      p.client.toLowerCase().includes(query) ||
      (p.description && p.description.toLowerCase().includes(query));
    const matchesStatus = statusFilter === 'All' || p.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getStatusColor = (status: Project['status']) => {
    switch (status) {
      case 'Active':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'In Progress':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'Completed':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'On Hold':
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getTeamNames = (ids: string[]) => {
    return ids
      .map((id) => {
        const member = teamMembers.find((m) => m.id === id);
        return member ? `${member.firstName} ${member.lastName}` : id;
      })
      .join(', ');
  };

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
          {toast.type === 'success' ? (
            <Check className="w-5 h-5 shrink-0" />
          ) : (
            <AlertCircle className="w-5 h-5 shrink-0" />
          )}
          <span>{toast.message}</span>
        </div>
      )}

      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-h1 font-black text-on-surface tracking-tight md:text-display">Projects</h1>
          <p className="text-body-lg text-on-surface-variant mt-1">
            Manage all active and past projects.
          </p>
        </div>
        {userRole === 'admin' && (
          <button
            onClick={handleOpenCreate}
            className="bg-primary hover:bg-primary/95 text-white font-semibold text-body-sm px-6 py-2.5 rounded-lg shadow-sm transition-all flex items-center gap-2 cursor-pointer shrink-0"
          >
            <Plus className="w-5 h-5" />
            <span>New Project</span>
          </button>
        )}
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-outline-variant/30 p-5 flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="relative w-full md:max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-outline w-5 h-5" />
          <input
            type="text"
            placeholder="Search projects..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-surface border border-outline-variant rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all text-body-sm text-on-surface placeholder:text-outline"
          />
        </div>
        <div className="flex flex-wrap gap-2 w-full md:w-auto">
          <span className="text-caption font-bold text-on-surface-variant mr-2 self-center">Status:</span>
          {(['All', 'Active', 'In Progress', 'Completed', 'On Hold'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 rounded-full text-caption font-bold border transition-all cursor-pointer ${
                statusFilter === s
                  ? 'bg-primary border-primary text-white shadow-sm'
                  : 'bg-surface-container-lowest text-on-surface border-outline-variant hover:bg-surface-container-low'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-outline-variant/30 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[700px]">
            <thead>
              <tr className="border-b border-outline-variant bg-surface-container-lowest">
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Project</th>
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Client</th>
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Status</th>
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Deadline</th>
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Team</th>
                {userRole === 'admin' && (
                  <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider text-right">Actions</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/40">
              {filteredProjects.length > 0 ? (
                filteredProjects.map((p) => (
                  <tr key={p.id} className="hover:bg-surface-container-low transition-colors group">
                    <td className="py-4 px-6">
                      <div>
                        <div className="font-bold text-body-sm text-on-surface">{p.name}</div>
                        {p.description && (
                          <div className="text-caption text-on-surface-variant truncate max-w-xs">{p.description}</div>
                        )}
                      </div>
                    </td>
                    <td className="py-4 px-6 text-body-sm font-semibold text-on-surface-variant">{p.client}</td>
                    <td className="py-4 px-6">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getStatusColor(
                          p.status
                        )}`}
                      >
                        {p.status}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-body-sm font-semibold text-on-surface-variant">
                      <div className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-outline" />
                        {new Date(p.deadline).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                      </div>
                    </td>
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-1.5 text-caption text-on-surface-variant">
                        <Users className="w-3.5 h-3.5 text-outline" />
                        <span className="truncate max-w-[120px]" title={getTeamNames(p.teamMembers)}>
                          {getTeamNames(p.teamMembers) || '—'}
                        </span>
                      </div>
                    </td>
                    {userRole === 'admin' && (
                      <td className="py-4 px-6 text-right">
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => handleOpenEdit(p)}
                            className="p-1.5 text-on-surface-variant hover:text-primary hover:bg-primary/10 rounded transition-colors cursor-pointer"
                            title="Edit"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(p.id, p.name)}
                            className="p-1.5 text-on-surface-variant hover:text-error hover:bg-error-container/50 rounded transition-colors cursor-pointer"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    colSpan={userRole === 'admin' ? 6 : 5}
                    className="py-12 px-6 text-center text-on-surface-variant font-medium"
                  >
                    No projects found. {userRole === 'admin' ? 'Create one now!' : ''}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-on-background/40 backdrop-blur-sm" onClick={() => setShowModal(false)}></div>
          <div className="relative bg-white rounded-xl shadow-[0_8px_32px_rgba(3,34,77,0.15)] w-full max-w-lg max-h-[90%] overflow-y-auto border border-outline-variant animate-scale-up">
            <div className="flex items-center justify-between px-6 py-4 border-b border-outline-variant/50 bg-surface sticky top-0 z-10">
              <h2 className="text-h2 font-black text-on-surface m-0">
                {editingProject ? 'Edit Project' : 'Create New Project'}
              </h2>
              <button
                className="text-on-surface-variant hover:text-on-surface p-1 rounded-full hover:bg-surface-container transition-colors cursor-pointer"
                onClick={() => {
                  setShowModal(false);
                  resetForm();
                }}
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-5">
              <div className="grid grid-cols-1 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-on-surface-variant mb-1">
                    Project Name <span className="text-error">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Cloud Migration"
                    className="w-full px-3 py-2 bg-surface border border-outline-variant rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-body-sm text-on-surface"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-on-surface-variant mb-1">
                    Client <span className="text-error">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={client}
                    onChange={(e) => setClient(e.target.value)}
                    placeholder="e.g. Acme Corp"
                    className="w-full px-3 py-2 bg-surface border border-outline-variant rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-body-sm text-on-surface"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-on-surface-variant mb-1">Description</label>
                  <textarea
                    rows={3}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Brief project scope..."
                    className="w-full px-3 py-2 bg-surface border border-outline-variant rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-body-sm text-on-surface resize-none"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-on-surface-variant mb-1">
                      Status <span className="text-error">*</span>
                    </label>
                    <select
                      value={status}
                      onChange={(e) => setStatus(e.target.value as Project['status'])}
                      className="w-full px-3 py-2 bg-surface border border-outline-variant rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-body-sm text-on-surface cursor-pointer"
                    >
                      <option value="Active">Active</option>
                      <option value="In Progress">In Progress</option>
                      <option value="Completed">Completed</option>
                      <option value="On Hold">On Hold</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-on-surface-variant mb-1">
                      Deadline <span className="text-error">*</span>
                    </label>
                    <input
                      type="date"
                      required
                      value={deadline}
                      onChange={(e) => setDeadline(e.target.value)}
                      className="w-full px-3 py-2 bg-surface border border-outline-variant rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-body-sm text-on-surface"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-on-surface-variant mb-1">Team Members</label>
                  <div className="flex flex-wrap gap-2 p-2 border border-outline-variant rounded-md bg-surface">
                    {teamMembers.map((member) => (
                      <label key={member.id} className="flex items-center gap-1.5 text-caption cursor-pointer">
                        <input
                          type="checkbox"
                          checked={selectedTeam.includes(member.id)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedTeam([...selectedTeam, member.id]);
                            } else {
                              setSelectedTeam(selectedTeam.filter((id) => id !== member.id));
                            }
                          }}
                          className="rounded border-outline-variant text-primary focus:ring-primary w-3.5 h-3.5"
                        />
                        <span>{member.firstName} {member.lastName}</span>
                      </label>
                    ))}
                    {teamMembers.length === 0 && (
                      <span className="text-xs text-outline">No team members available</span>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-outline-variant/30">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false);
                    resetForm();
                  }}
                  className="px-4 py-2 border border-primary text-primary rounded-lg font-bold text-body-sm hover:bg-primary/5 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary text-white rounded-lg font-bold text-body-sm hover:bg-primary/95 transition-colors shadow-sm cursor-pointer"
                >
                  {editingProject ? 'Update Project' : 'Create Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}