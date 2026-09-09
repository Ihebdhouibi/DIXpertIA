import React, { useState } from 'react';
import { Plus, Search, Filter, MoreVertical, X, Download, ZoomIn, ZoomOut, Check, ChevronLeft, ChevronRight } from 'lucide-react';
import { Invoice, UserRole } from '../types';

interface InvoicesViewProps {
  invoices: Invoice[];
  onAddInvoice: (invoice: Partial<Invoice>) => void;
  userRole: UserRole;
}

export default function InvoicesView({ invoices, onAddInvoice, userRole }: InvoicesViewProps) {
  const isAdmin = userRole === 'admin';
  const [selectedFilter, setSelectedFilter] = useState<'All' | 'Draft' | 'Sent' | 'Paid' | 'Overdue'>('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [isNewInvoiceOpen, setIsNewInvoiceOpen] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(100);

  // Form states for new invoice creation
  const [clientName, setClientName] = useState('');
  const [amount, setAmount] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [invoiceStatus, setInvoiceStatus] = useState<'Draft' | 'Sent' | 'Paid' | 'Overdue'>('Sent');

  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (message: string) => {
    setToastMessage(message);
    setTimeout(() => setToastMessage(null), 3000);
  };

  // ✅ Updated download handler
  const handleDownload = async (id: string) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        showToast('Please log in again.');
        return;
      }

      const response = await fetch(`/api/invoices/${id}/download`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        const errorText = await response.text();
        showToast(`Download failed: ${errorText || response.statusText}`);
        return;
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Invoice_${id}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      showToast(`Invoice ${id} downloaded.`);
    } catch (error) {
      console.error('Download error:', error);
      showToast('Network error. Please try again.');
    }
  };

  const handleNewInvoiceSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!clientName || !amount) {
      showToast('Please specify client and amount.');
      return;
    }

    const nextId = `INV-2024-00${invoices.length + 1}`;
    const initials = clientName.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();

    onAddInvoice({
      id: nextId,
      client: clientName,
      clientInitials: initials,
      amount: parseFloat(amount),
      dateIssued: new Date().toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }),
      dueDate: dueDate ? new Date(dueDate).toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }) : '-',
      status: invoiceStatus,
      items: [
        { description: 'Consultation & Cloud Integration Services', qty: 1, price: parseFloat(amount), total: parseFloat(amount) }
      ]
    });

    setIsNewInvoiceOpen(false);
    setClientName('');
    setAmount('');
    setDueDate('');
    showToast(`Invoice ${nextId} created.`);
  };

  const filteredInvoices = invoices.filter(inv => {
    const query = searchQuery.toLowerCase();
    const matchesSearch = inv.client.toLowerCase().includes(query) || inv.id.toLowerCase().includes(query);
    const matchesStatus = selectedFilter === 'All' || inv.status === selectedFilter;
    return matchesSearch && matchesStatus;
  });

  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'Paid':
        return 'bg-[#e6f4ea] text-[#137333] border border-[#ceead6]';
      case 'Sent':
        return 'bg-tertiary-fixed text-on-tertiary-fixed-variant border border-outline-variant/30';
      case 'Overdue':
        return 'bg-error-container text-on-error-container border border-error/10';
      case 'Draft':
      default:
        return 'bg-surface-container-highest text-on-surface-variant border border-outline-variant';
    }
  };

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
  };

  return (
    <div className="flex-grow flex flex-col gap-6 animate-fade-in">
      {toastMessage && (
        <div className="fixed bottom-4 right-4 z-50 bg-[#137333] text-white py-3 px-5 rounded-lg shadow-lg flex items-center gap-2 animate-fade-in text-body-sm font-semibold border border-white/10">
          <Check className="w-5 h-5 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-h1 font-black text-on-surface tracking-tight md:text-display">Invoices</h1>
          <p className="text-body-lg text-on-surface-variant mt-1">Manage and track billing across all projects.</p>
        </div>
        {isAdmin && (
          <button
            onClick={() => setIsNewInvoiceOpen(true)}
            className="bg-primary hover:bg-primary/95 text-white font-semibold text-body-sm px-6 py-2.5 rounded-lg shadow-sm transition-all flex items-center gap-2 cursor-pointer shrink-0"
          >
            <Plus className="w-5 h-5" />
            <span>New Invoice</span>
          </button>
        )}
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-outline-variant/30 p-5 flex flex-col gap-4">
        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-caption font-bold text-on-surface-variant mr-2">Filter by Status:</span>
          {(['All', 'Draft', 'Sent', 'Paid', 'Overdue'] as const).map(f => (
            <button
              key={f}
              onClick={() => setSelectedFilter(f)}
              className={`px-4 py-1.5 rounded-full text-caption font-bold border transition-all cursor-pointer ${
                selectedFilter === f
                  ? 'bg-primary border-primary text-white shadow-sm'
                  : 'bg-surface-container-lowest text-on-surface border-outline-variant hover:bg-surface-container-low'
              }`}
            >
              {f}
            </button>
          ))}
          <div className="ml-auto relative w-full md:w-64 mt-2 md:mt-0">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant w-5 h-5" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-surface-container-lowest border border-outline-variant rounded-lg font-medium text-body-sm text-on-surface focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
              placeholder="Search invoices..."
              type="text"
            />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-outline-variant overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[700px]">
            <thead>
              <tr className="border-b border-outline-variant bg-surface-container-lowest">
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Invoice #</th>
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Client</th>
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Amount</th>
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Date Issued</th>
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Due Date</th>
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider">Status</th>
                <th className="py-4 px-6 font-bold text-caption text-on-surface-variant uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant">
              {filteredInvoices.length > 0 ? (
                filteredInvoices.map((inv) => (
                  <tr
                    key={inv.id}
                    onClick={() => setSelectedInvoice(inv)}
                    className="hover:bg-surface-container-low transition-colors cursor-pointer group"
                  >
                    <td className="py-4 px-6 font-mono text-body-sm font-semibold text-primary">{inv.id}</td>
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded bg-secondary-fixed text-on-secondary-fixed flex items-center justify-center font-bold text-caption shadow-sm">
                          {inv.clientInitials}
                        </div>
                        <span className="font-semibold text-body-sm text-on-surface">{inv.client}</span>
                      </div>
                    </td>
                    <td className="py-4 px-6 font-semibold text-body-sm text-on-surface">
                      {formatCurrency(inv.amount)}
                    </td>
                    <td className="py-4 px-6 text-body-sm text-on-surface-variant font-medium">
                      {inv.dateIssued}
                    </td>
                    <td className={`py-4 px-6 text-body-sm font-semibold ${inv.status === 'Overdue' ? 'text-error' : 'text-on-surface-variant'}`}>
                      {inv.dueDate}
                    </td>
                    <td className="py-4 px-6">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${getStatusStyle(inv.status)}`}>
                        {inv.status}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-right" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => handleDownload(inv.id)}
                        className="text-on-surface-variant hover:text-primary transition-colors p-1 cursor-pointer"
                      >
                        <MoreVertical className="w-5 h-5" />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="py-12 px-6 text-center text-on-surface-variant font-medium">
                    No invoices found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="border-t border-outline-variant px-6 py-4 flex items-center justify-between bg-surface-container-lowest">
          <span className="text-caption text-on-surface-variant font-medium">
            Showing 1-{filteredInvoices.length} of {filteredInvoices.length} results
          </span>
          <div className="flex items-center gap-2">
            <button className="p-1 rounded text-on-surface-variant hover:bg-surface-container-high disabled:opacity-40" disabled>
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button className="w-8 h-8 rounded bg-primary-container text-on-primary-container font-bold text-xs flex items-center justify-center">1</button>
            <button className="p-1 rounded text-on-surface-variant hover:bg-surface-container-high disabled:opacity-40" disabled>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Invoice Detail Modal */}
      {selectedInvoice && (
        <div className="fixed inset-0 z-50 bg-on-background/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-4xl max-h-[92%] rounded-xl shadow-[0_8px_32px_rgba(31,56,100,0.2)] border border-outline-variant flex flex-col overflow-hidden animate-scale-up">
            <div className="px-6 py-4 border-b border-outline-variant flex items-center justify-between bg-surface shrink-0">
              <div className="flex items-center gap-4">
                <h3 className="text-h2 font-black text-on-surface">
                  Invoice <span className="font-mono text-body-sm font-normal text-on-surface-variant ml-1">{selectedInvoice?.id}</span>
                </h3>
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${getStatusStyle(selectedInvoice?.status || 'Draft')}`}>
                  {selectedInvoice?.status}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleDownload(selectedInvoice?.id || '')}
                  className="px-4 py-2 text-primary font-bold text-body-sm hover:bg-primary/10 rounded-lg transition-colors flex items-center gap-2 cursor-pointer"
                >
                  <Download className="w-4 h-4" /> Download
                </button>
                <button
                  className="p-2 text-on-surface-variant hover:bg-surface-container-high rounded-full transition-colors cursor-pointer"
                  onClick={() => setSelectedInvoice(null)}
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-auto p-6 bg-surface-container-low">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-1 flex flex-col gap-6">
                  <div className="bg-white p-5 rounded-xl border border-outline-variant shadow-sm">
                    <h4 className="font-bold text-body-sm text-on-surface mb-4">Summary</h4>
                    <div className="space-y-4">
                      <div>
                        <span className="block text-caption text-on-surface-variant mb-1 font-semibold">Total Amount</span>
                        <span className="text-h1 font-black text-primary tracking-tight">{formatCurrency(selectedInvoice?.amount || 0)}</span>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <span className="block text-caption text-on-surface-variant mb-1 font-semibold">Issued Date</span>
                          <span className="text-body-sm text-on-surface font-semibold">{selectedInvoice?.dateIssued}</span>
                        </div>
                        <div>
                          <span className="block text-caption text-on-surface-variant mb-1 font-semibold">Due Date</span>
                          <span className={`text-body-sm font-bold ${selectedInvoice?.status === 'Overdue' ? 'text-error' : 'text-on-surface'}`}>
                            {selectedInvoice?.dueDate}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="bg-white p-5 rounded-xl border border-outline-variant shadow-sm">
                    <h4 className="font-bold text-body-sm text-on-surface mb-4">Client Information</h4>
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-10 h-10 rounded-md bg-secondary-fixed text-on-secondary-fixed flex items-center justify-center font-bold text-body-sm shadow-sm">
                        {selectedInvoice?.clientInitials}
                      </div>
                      <div>
                        <div className="text-body-sm font-bold text-on-surface">{selectedInvoice?.client}</div>
                        <div className="text-caption text-on-surface-variant font-medium">{selectedInvoice?.client?.toLowerCase().replace(/\s+/g, '')}.example.com</div>
                      </div>
                    </div>
                    <div className="space-y-1 text-caption text-on-surface-variant font-medium border-t border-outline-variant/30 pt-3">
                      <p>123 Business Road, Suite 400</p>
                      <p>San Francisco, CA 94107</p>
                      <p>United States</p>
                    </div>
                  </div>
                </div>
                <div className="lg:col-span-2 bg-white rounded-xl border border-outline-variant shadow-sm flex flex-col overflow-hidden">
                  <div className="h-12 bg-surface border-b border-outline-variant flex items-center justify-between px-4 select-none">
                    <div className="flex items-center gap-2 text-on-surface-variant font-medium">
                      <button onClick={() => setZoomLevel(prev => Math.max(prev - 10, 50))} className="p-1 hover:bg-surface-container-high rounded cursor-pointer">
                        <ZoomOut className="w-4 h-4" />
                      </button>
                      <span className="font-mono text-caption">{zoomLevel}%</span>
                      <button onClick={() => setZoomLevel(prev => Math.min(prev + 10, 150))} className="p-1 hover:bg-surface-container-high rounded cursor-pointer">
                        <ZoomIn className="w-4 h-4" />
                      </button>
                    </div>
                    <span className="text-caption text-on-surface-variant font-semibold">Page 1 of 1</span>
                  </div>
                  <div className="flex-1 bg-surface-variant overflow-auto p-4 md:p-8 flex items-start justify-center">
                    <div
                      style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: 'top center' }}
                      className="bg-white w-full max-w-[580px] shadow-lg aspect-[1/1.4] p-8 border border-outline-variant relative transition-transform"
                    >
                      <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-[0.03] select-none">
                        <span className="font-sans text-[90px] font-black rotate-45 text-on-surface">PREVIEW</span>
                      </div>
                      <div className="flex justify-between items-start mb-8 select-none">
                        <div>
                          <div className="font-sans text-h2 font-black text-primary mb-1">DIXpertIA</div>
                          <div className="text-[10px] text-on-surface-variant w-44 font-medium leading-relaxed">
                            Enterprise IT Solutions & Infrastructure Services
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-sans text-h3 font-black text-on-surface mb-2 tracking-wide uppercase">INVOICE</div>
                          <div className="font-mono text-caption text-primary font-bold mb-1">{selectedInvoice?.id}</div>
                          <div className="text-caption text-on-surface-variant font-semibold">Date: {selectedInvoice?.dateIssued}</div>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-4 border-t border-outline-variant/50 pt-4 mb-8 text-caption select-none">
                        <div>
                          <span className="block text-outline font-bold uppercase tracking-wider mb-1">Billed To:</span>
                          <span className="block font-bold text-on-surface">{selectedInvoice?.client}</span>
                          <span className="block text-on-surface-variant">123 Business Road, Suite 400</span>
                          <span className="block text-on-surface-variant">San Francisco, CA 94107</span>
                        </div>
                        <div className="text-right">
                          <span className="block text-outline font-bold uppercase tracking-wider mb-1">Due Date:</span>
                          <span className="block font-bold text-on-surface">{selectedInvoice?.dueDate}</span>
                          <span className="block text-on-surface-variant">Status: {selectedInvoice?.status}</span>
                        </div>
                      </div>
                      <div className="border-t border-b border-outline-variant py-2">
                        <div className="flex font-semibold text-caption text-on-surface-variant mb-2 select-none">
                          <div className="flex-grow">Description</div>
                          <div className="w-12 text-right">Qty</div>
                          <div className="w-24 text-right">Price</div>
                          <div className="w-24 text-right">Total</div>
                        </div>
                        {selectedInvoice?.items?.map((item, index) => (
                          <div key={index} className="flex text-caption text-on-surface py-2.5 border-t border-outline-variant/20">
                            <div className="flex-grow font-semibold text-on-surface">{item.description}</div>
                            <div className="w-12 text-right font-mono text-on-surface-variant">{item.qty}</div>
                            <div className="w-24 text-right font-mono text-on-surface-variant">{formatCurrency(item.price)}</div>
                            <div className="w-24 text-right font-mono font-bold text-primary">{formatCurrency(item.total)}</div>
                          </div>
                        ))}
                      </div>
                      <div className="mt-6 flex justify-end">
                        <div className="w-48 border-t border-outline-variant pt-3">
                          <div className="flex justify-between text-caption text-on-surface-variant font-medium py-1">
                            <span>Subtotal:</span>
                            <span className="font-mono">{formatCurrency(selectedInvoice?.amount || 0)}</span>
                          </div>
                          <div className="flex justify-between text-caption font-bold text-on-surface py-1.5 border-t border-outline-variant/30 mt-2">
                            <span>Total Due:</span>
                            <span className="font-mono text-primary">{formatCurrency(selectedInvoice?.amount || 0)}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* New Invoice Modal */}
      {isAdmin && isNewInvoiceOpen && (
        <div className="fixed inset-0 z-50 bg-on-background/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-[0_8px_32px_rgba(3,34,77,0.15)] w-full max-w-md border border-outline-variant overflow-hidden animate-scale-up">
            <div className="flex items-center justify-between px-6 py-4 border-b border-outline-variant/50 bg-surface shrink-0">
              <h3 className="text-h2 font-black text-on-surface m-0">Create New Invoice</h3>
              <button className="text-on-surface-variant hover:text-on-surface hover:bg-surface-container rounded-full p-1 transition-colors cursor-pointer" onClick={() => setIsNewInvoiceOpen(false)}>
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6">
              <form onSubmit={handleNewInvoiceSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-on-surface-variant mb-1">Client Name</label>
                  <input
                    required
                    value={clientName}
                    onChange={(e) => setClientName(e.target.value)}
                    placeholder="e.g. Acme Corp"
                    className="w-full px-3 py-2 bg-surface border border-outline-variant rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-body-sm text-on-surface"
                    type="text"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-on-surface-variant mb-1">Amount ($)</label>
                    <input
                      required
                      value={amount}
                      onChange={(e) => setAmount(e.target.value)}
                      placeholder="e.g. 12450.00"
                      className="w-full px-3 py-2 bg-surface border border-outline-variant rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-body-sm text-on-surface font-semibold"
                      type="number"
                      step="0.01"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-on-surface-variant mb-1">Status</label>
                    <select
                      value={invoiceStatus}
                      onChange={(e) => setInvoiceStatus(e.target.value as any)}
                      className="w-full px-3 py-2 bg-surface border border-outline-variant rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-body-sm text-on-surface cursor-pointer font-semibold"
                    >
                      <option value="Draft">Draft</option>
                      <option value="Sent">Sent</option>
                      <option value="Paid">Paid</option>
                      <option value="Overdue">Overdue</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-on-surface-variant mb-1">Due Date</label>
                  <input
                    value={dueDate}
                    onChange={(e) => setDueDate(e.target.value)}
                    className="w-full px-3 py-2 bg-surface border border-outline-variant rounded-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-body-sm text-on-surface"
                    type="date"
                  />
                </div>
                <div className="pt-4 border-t border-outline-variant/30 flex justify-end gap-3 shrink-0 mt-4">
                  <button
                    type="button"
                    onClick={() => setIsNewInvoiceOpen(false)}
                    className="px-4 py-2 border border-primary text-primary rounded-lg font-bold text-body-sm hover:bg-primary/5 transition-colors cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-primary text-white rounded-lg font-bold text-body-sm hover:bg-primary/95 transition-colors shadow-sm cursor-pointer"
                  >
                    Create Invoice
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}