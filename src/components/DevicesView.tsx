import React, { useState, useEffect } from 'react';
import { Plus, Search, Edit, Trash2, X, Check, AlertCircle } from 'lucide-react';
import { UserRole } from '../types';

interface Device {
  id: string;
  name: string;
  model: string;
  serialNumber: string;
  price: number;
  status: 'Available' | 'Sold' | 'In Repair';
  createdAt: string;
}

interface DevicesViewProps {
  userRole: UserRole;
}

export default function DevicesView({ userRole }: DevicesViewProps) {
  const isAdmin = userRole === 'admin';
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingDevice, setEditingDevice] = useState<Device | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'All' | 'Available' | 'Sold' | 'In Repair'>('All');

  const [name, setName] = useState('');
  const [model, setModel] = useState('');
  const [serialNumber, setSerialNumber] = useState('');
  const [price, setPrice] = useState('');
  const [status, setStatus] = useState<'Available' | 'Sold' | 'In Repair'>('Available');

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const fetchDevices = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/devices', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setDevices(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDevices();
  }, []);

  const resetForm = () => {
    setName('');
    setModel('');
    setSerialNumber('');
    setPrice('');
    setStatus('Available');
    setEditingDevice(null);
  };

  const handleOpenCreate = () => {
    if (!isAdmin) return;
    resetForm();
    setShowModal(true);
  };

  const handleOpenEdit = (device: Device) => {
    if (!isAdmin) return;
    setEditingDevice(device);
    setName(device.name);
    setModel(device.model);
    setSerialNumber(device.serialNumber);
    setPrice(device.price.toString());
    setStatus(device.status);
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAdmin) return;
    if (!name || !model || !serialNumber || !price) {
      showToast('Please fill in all fields.', 'error');
      return;
    }
    try {
      const token = localStorage.getItem('token');
      const method = editingDevice ? 'PUT' : 'POST';
      const url = editingDevice ? `/api/devices/${editingDevice.id}` : '/api/devices';
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ name, model, serialNumber, price: parseFloat(price), status })
      });
      if (response.ok) {
        fetchDevices();
        showToast(editingDevice ? 'Device updated.' : 'Device created.', 'success');
        setShowModal(false);
        resetForm();
      } else {
        const error = await response.json();
        showToast(error.detail || 'Something went wrong.', 'error');
      }
    } catch (err) {
      showToast('Network error.', 'error');
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!isAdmin) return;
    if (!window.confirm(`Delete device "${name}"?`)) return;
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/devices/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        fetchDevices();
        showToast(`Device "${name}" deleted.`, 'success');
      }
    } catch (err) {
      showToast('Network error.', 'error');
    }
  };

  const filteredDevices = devices.filter(d => {
    const matchesSearch = d.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         d.model.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         d.serialNumber.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'All' || d.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  if (userRole !== 'admin' && userRole !== 'accountant' && userRole !== 'employee') {
    return <div className="p-8 text-center">Access Denied</div>;
  }

  return (
    <div className="flex-1 flex flex-col gap-6 animate-fade-in">
      {toast && (
        <div className={`fixed bottom-4 right-4 z-50 py-3 px-5 rounded-lg shadow-lg flex items-center gap-2 animate-fade-in text-body-sm font-semibold border ${toast.type === 'success' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' : 'bg-red-50 text-red-800 border-red-200'}`}>
          {toast.type === 'success' ? <Check className="w-5 h-5 shrink-0" /> : <AlertCircle className="w-5 h-5 shrink-0" />}
          <span>{toast.message}</span>
        </div>
      )}

      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-h1 font-black text-on-surface tracking-tight md:text-display">Devices</h1>
          <p className="text-body-lg text-on-surface-variant mt-1">{isAdmin ? 'Manage device inventory.' : 'View device inventory.'}</p>
        </div>
        {isAdmin && (
          <button onClick={handleOpenCreate} className="bg-primary hover:bg-primary/95 text-white font-semibold text-body-sm px-6 py-2.5 rounded-lg shadow-sm transition-all flex items-center gap-2 cursor-pointer shrink-0">
            <Plus className="w-5 h-5" /> <span>Add Device</span>
          </button>
        )}
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-outline-variant/30 p-4 flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="relative w-full md:max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-outline w-5 h-5" />
          <input type="text" placeholder="Search devices..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="w-full pl-10 pr-4 py-2 bg-surface border border-outline-variant rounded-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all text-body-sm text-on-surface placeholder:text-outline" />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-caption font-bold text-on-surface-variant">Status:</span>
          {(['All', 'Available', 'Sold', 'In Repair'] as const).map(s => (
            <button key={s} onClick={() => setStatusFilter(s)} className={`px-3 py-1.5 rounded-full text-caption font-bold border transition-all cursor-pointer ${statusFilter === s ? 'bg-primary border-primary text-white shadow-sm' : 'bg-surface-container-lowest text-on-surface border-outline-variant hover:bg-surface-container-low'}`}>{s}</button>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-outline-variant/30 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[700px]">
            <thead>
              <tr className="border-b border-outline-variant bg-surface-container-lowest">
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Name</th>
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Model</th>
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Serial #</th>
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Price</th>
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Status</th>
                {isAdmin && <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/40">
              {filteredDevices.length === 0 ? (
                <tr><td colSpan={isAdmin ? 6 : 5} className="py-12 px-6 text-center text-on-surface-variant font-medium">No devices found.</td></tr>
              ) : (
                filteredDevices.map(d => (
                  <tr key={d.id} className="hover:bg-surface-container-low transition-colors group">
                    <td className="py-4 px-6 font-semibold text-body-sm text-on-surface">{d.name}</td>
                    <td className="py-4 px-6 text-body-sm text-on-surface-variant">{d.model}</td>
                    <td className="py-4 px-6 font-mono text-caption text-on-surface-variant">{d.serialNumber}</td>
                    <td className="py-4 px-6 font-semibold text-body-sm text-on-surface">${d.price.toFixed(2)}</td>
                    <td className="py-4 px-6">
                      <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${d.status === 'Available' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : d.status === 'Sold' ? 'bg-gray-100 text-gray-700 border-gray-200' : 'bg-amber-50 text-amber-700 border-amber-200'}`}>{d.status}</span>
                    </td>
                    {isAdmin && (
                      <td className="py-4 px-6 text-right">
                        <div className="flex justify-end gap-2">
                          <button onClick={() => handleOpenEdit(d)} className="p-1.5 text-on-surface-variant hover:text-primary rounded transition-colors cursor-pointer"><Edit className="w-4 h-4" /></button>
                          <button onClick={() => handleDelete(d.id, d.name)} className="p-1.5 text-on-surface-variant hover:text-error rounded transition-colors cursor-pointer"><Trash2 className="w-4 h-4" /></button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))
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
              <h2 className="text-h2 font-black text-on-surface">{editingDevice ? 'Edit Device' : 'Add New Device'}</h2>
              <button onClick={() => { setShowModal(false); resetForm(); }} className="text-on-surface-variant hover:text-on-surface p-1 rounded-full hover:bg-surface-container transition-colors cursor-pointer"><X className="w-5 h-5" /></button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-5">
              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1">Device Name *</label>
                <input type="text" required value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Laptop Dell XPS" className="w-full px-3 py-2 bg-surface border border-outline-variant rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-body-sm text-on-surface" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1">Model *</label>
                <input type="text" required value={model} onChange={(e) => setModel(e.target.value)} placeholder="e.g. XPS 13" className="w-full px-3 py-2 bg-surface border border-outline-variant rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-body-sm text-on-surface" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1">Serial Number *</label>
                <input type="text" required value={serialNumber} onChange={(e) => setSerialNumber(e.target.value)} placeholder="e.g. SN123456" className="w-full px-3 py-2 bg-surface border border-outline-variant rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-body-sm text-on-surface" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1">Price *</label>
                <input type="number" step="0.01" required value={price} onChange={(e) => setPrice(e.target.value)} placeholder="0.00" className="w-full px-3 py-2 bg-surface border border-outline-variant rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-body-sm text-on-surface" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1">Status</label>
                <select value={status} onChange={(e) => setStatus(e.target.value as any)} className="w-full px-3 py-2 bg-surface border border-outline-variant rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-body-sm text-on-surface cursor-pointer">
                  <option value="Available">Available</option>
                  <option value="Sold">Sold</option>
                  <option value="In Repair">In Repair</option>
                </select>
              </div>
              <div className="flex justify-end gap-3 pt-4 border-t border-outline-variant/30">
                <button type="button" onClick={() => { setShowModal(false); resetForm(); }} className="px-4 py-2 border border-primary text-primary rounded-lg font-bold text-body-sm hover:bg-primary/5 transition-colors cursor-pointer">Cancel</button>
                <button type="submit" className="px-4 py-2 bg-primary text-white rounded-lg font-bold text-body-sm hover:bg-primary/95 transition-colors shadow-sm cursor-pointer">{editingDevice ? 'Update Device' : 'Create Device'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}