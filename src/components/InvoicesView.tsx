import React, { useEffect, useState } from 'react';
import { Plus, Download, ZoomIn, ZoomOut } from 'lucide-react';
import { Invoice, UserRole, Client } from '../types';
import StatusBadge from './StatusBadge';
import Avatar from './ui/Avatar';
import { Table, THead, Th, TBody, Tr, Td, TableState } from './ui/Table';
import { FilterPills, SearchField, Pagination, TableToolbar } from './ui/TableControls';
import { useDataStatus } from '../dataStatus';
import Dialog from './ui/Dialog';
import Button from './ui/Button';
import { Field, Input, Select } from './ui/Field';
import { useToast, ToastTone } from './ui/feedback';

interface InvoicesViewProps {
  invoices: Invoice[];
  /** Clients the invoice may be issued to. The API requires a real one. */
  clients: Client[];
  onAddInvoice: (invoice: {
    client_id: number;
    date_echeance: string;
    items: { designation: string; quantite: number; prix_unitaire: number; taux_tva: number }[];
  }) => void;
  userRole: UserRole;
}

export default function InvoicesView({ invoices, clients, onAddInvoice, userRole }: InvoicesViewProps) {
  const isAdmin = userRole === 'admin';
  const [selectedFilter, setSelectedFilter] = useState<'All' | 'Draft' | 'Sent' | 'Paid' | 'Overdue'>('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const status = useDataStatus();
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [isNewInvoiceOpen, setIsNewInvoiceOpen] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(100);

  // Form states for new invoice creation
  const [clientId, setClientId] = useState('');
  const [amount, setAmount] = useState('');
  const [dueDate, setDueDate] = useState('');
  // The status is not chosen here any more: a new invoice is always a draft
  // and the server sets it (#87). Letting the form pick meant an invoice
  // could be created already marked Paid.

  const toast = useToast();
  const showToast = (message: string, tone: ToastTone = 'success') => toast(message, tone);

  // ✅ Updated download handler
  const handleDownload = async (id: string) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        showToast('Please log in again.', 'error');
        return;
      }

      const response = await fetch(`/api/invoices/${id}/download`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        const errorText = await response.text();
        showToast(`Download failed: ${errorText || response.statusText}`, 'error');
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
      showToast('Network error. Please try again.', 'error');
    }
  };

  const handleNewInvoiceSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!clientId || !amount || !dueDate) {
      showToast('Choose a client, an amount and a due date.', 'error');
      return;
    }

    // The number, the issue date and the status all come from the server: the
    // number belongs to a gapless series (#38), and letting the client pick any
    // of them is how duplicates and out-of-order invoices happen.
    onAddInvoice({
      client_id: Number(clientId),
      date_echeance: dueDate,
      items: [{
        designation: 'Consultation & Cloud Integration Services',
        quantite: 1,
        prix_unitaire: parseFloat(amount),
        taux_tva: 19,
      }],
    });

    setIsNewInvoiceOpen(false);
    setClientId('');
    setAmount('');
    setDueDate('');
  };

  const filteredInvoices = invoices.filter(inv => {
    const query = searchQuery.toLowerCase();
    const matchesSearch = inv.counterparty.toLowerCase().includes(query) || inv.id.toLowerCase().includes(query);
    const matchesStatus = selectedFilter === 'All' || inv.status === selectedFilter;
    return matchesSearch && matchesStatus;
  });

  // Client-side pages over the loaded list. The old footer always said
  // "Showing 1-N of N" and its page buttons were disabled.
  const PAGE_SIZE = 10;
  const pageCount = Math.max(1, Math.ceil(filteredInvoices.length / PAGE_SIZE));
  const pageRows = filteredInvoices.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  useEffect(() => setPage(1), [selectedFilter, searchQuery]);
  useEffect(() => {
    if (page > pageCount) setPage(pageCount);
  }, [page, pageCount]);

  const formatCurrency = (val: number) => {
    // TND, not USD: DI Xpertia is a Tunisian company and invoices in dinars.
    // The dinar has three decimal places, which is why minimumFractionDigits is
    // set rather than left to the default two.
    return new Intl.NumberFormat('fr-TN', {
      style: 'currency', currency: 'TND', minimumFractionDigits: 3,
    }).format(val);
  };

  return (
    <div className="flex-grow flex flex-col gap-6 animate-fade-in">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-h1 font-black text-on-surface tracking-tight md:text-display">Invoices</h1>
          <p className="text-body-lg text-on-surface-variant mt-1">Manage and track billing across all projects.</p>
        </div>
        {isAdmin && (
          <Button onClick={() => setIsNewInvoiceOpen(true)} className="shrink-0">
            <Plus className="w-4 h-4" aria-hidden="true" />
            New invoice
          </Button>
        )}
      </div>

      <TableToolbar>
        <FilterPills
          label="Filter by status"
          showLabel
          options={['All', 'Draft', 'Sent', 'Paid', 'Overdue'] as const}
          value={selectedFilter}
          onChange={setSelectedFilter}
        />
        <SearchField label="Search invoices" value={searchQuery} onChange={setSearchQuery} />
      </TableToolbar>

      <Table
        caption="Invoices"
        footer={
          filteredInvoices.length > 0 && (
            <Pagination page={page} pageSize={PAGE_SIZE} total={filteredInvoices.length} onPageChange={setPage} noun="invoices" />
          )
        }
      >
        <THead>
          <Th>Invoice</Th>
          <Th>Client</Th>
          <Th numeric>Amount</Th>
          <Th numeric>Issued</Th>
          <Th numeric>Due</Th>
          <Th>Status</Th>
          <Th numeric>
            <span className="sr-only">Actions</span>
          </Th>
        </THead>
        <TBody>
          {pageRows.length > 0 ? (
            pageRows.map((inv) => (
              <Tr key={inv.id} interactive onClick={() => setSelectedInvoice(inv)}>
                <Td mono>
                  {/* The row opens the details; this button is the keyboard path to it. */}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedInvoice(inv);
                    }}
                    className="rounded font-semibold hover:underline cursor-pointer"
                  >
                    {inv.id}
                  </button>
                </Td>
                <Td>
                  <div className="flex items-center gap-3">
                    <Avatar name={inv.counterparty} size="sm" shape="square" />
                    <span className="font-semibold">{inv.counterparty}</span>
                  </div>
                </Td>
                <Td numeric className="font-semibold">{formatCurrency(inv.amountTTC)}</Td>
                <Td numeric muted>{inv.dateIssued}</Td>
                <Td numeric className={inv.status === 'Overdue' ? 'text-error font-semibold' : 'text-on-surface-variant'}>
                  {inv.dueDate}
                </Td>
                <Td>
                  <StatusBadge status={inv.status} />
                </Td>
                <Td numeric onClick={(e) => e.stopPropagation()}>
                  <button
                    type="button"
                    onClick={() => handleDownload(inv.id)}
                    aria-label={`Download invoice ${inv.id}`}
                    className="rounded-lg p-1.5 text-on-surface-variant transition-colors hover:bg-surface-container hover:text-on-surface cursor-pointer"
                  >
                    <Download className="w-4 h-4" aria-hidden="true" />
                  </button>
                </Td>
              </Tr>
            ))
          ) : status.loading ? (
            <TableState kind="loading" colSpan={7} title="Loading invoices..." />
          ) : status.error && invoices.length === 0 ? (
            <TableState kind="error" colSpan={7} message={status.error} />
          ) : (
            <TableState
              kind="empty"
              colSpan={7}
              title={invoices.length === 0 ? 'No invoices yet' : 'No invoices match'}
              message={invoices.length === 0 ? undefined : 'Try another status or search term.'}
            />
          )}
        </TBody>
      </Table>

      {/* Invoice detail */}
      <Dialog
        open={selectedInvoice !== null}
        onClose={() => setSelectedInvoice(null)}
        title={`Invoice ${selectedInvoice?.id ?? ''}`}
        size="xl"
        bodyClassName="overflow-auto p-6 bg-surface-container-low"
        headerActions={
          <>
            <StatusBadge status={selectedInvoice?.status || 'Draft'} />
            <Button variant="ghost" size="sm" onClick={() => handleDownload(selectedInvoice?.id || '')}>
              <Download className="w-4 h-4" aria-hidden="true" /> Download
            </Button>
          </>
        }
      >
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1 flex flex-col gap-6">
              <div className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant shadow-sm">
                <h4 className="font-bold text-body-sm text-on-surface mb-4">Summary</h4>
                <div className="space-y-4">
                  <div>
                    <span className="block text-caption text-on-surface-variant mb-1 font-semibold">Total Amount</span>
                    <span className="text-h1 font-black text-primary tracking-tight">{formatCurrency(selectedInvoice?.amountTTC || 0)}</span>
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
              <div className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant shadow-sm">
                <h4 className="font-bold text-body-sm text-on-surface mb-4">Client Information</h4>
                <div className="flex items-center gap-3 mb-4">
                  <Avatar name={selectedInvoice?.counterparty ?? ''} shape="square" />
                  <div>
                    <div className="text-body-sm font-bold text-on-surface">{selectedInvoice?.counterparty}</div>
                    <div className="text-caption text-on-surface-variant font-medium">{selectedInvoice?.counterparty?.toLowerCase().replace(/\s+/g, '')}.example.com</div>
                  </div>
                </div>
                <div className="space-y-1 text-caption text-on-surface-variant font-medium border-t border-outline-variant/30 pt-3">
                  <p>123 Business Road, Suite 400</p>
                  <p>San Francisco, CA 94107</p>
                  <p>United States</p>
                </div>
              </div>
            </div>
            <div className="lg:col-span-2 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm flex flex-col overflow-hidden">
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
                  className="bg-surface-container-lowest w-full max-w-[580px] shadow-lg aspect-[1/1.4] p-8 border border-outline-variant relative transition-transform"
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
                      <span className="block font-bold text-on-surface">{selectedInvoice?.counterparty}</span>
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
                        <span className="font-mono">{formatCurrency(selectedInvoice?.amountTTC || 0)}</span>
                      </div>
                      <div className="flex justify-between text-caption font-bold text-on-surface py-1.5 border-t border-outline-variant/30 mt-2">
                        <span>Total Due:</span>
                        <span className="font-mono text-primary">{formatCurrency(selectedInvoice?.amountTTC || 0)}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
      </Dialog>

      {/* New invoice */}
      {isAdmin && (
        <Dialog
          open={isNewInvoiceOpen}
          onClose={() => setIsNewInvoiceOpen(false)}
          title="Create new invoice"
          footer={
            <>
              <Button variant="secondary" onClick={() => setIsNewInvoiceOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" form="new-invoice-form">
                Create invoice
              </Button>
            </>
          }
        >
          <form id="new-invoice-form" onSubmit={handleNewInvoiceSubmit} className="flex flex-col gap-4">
            {/*
              A chosen client, not a typed name. An invoice references a
              real client row, so a free-text field could only ever
              produce an invoice that does not belong to anybody.
            */}
            <Field
              label="Client"
              hint={clients.length === 0 ? 'No clients yet. Add one before issuing an invoice.' : undefined}
            >
              {({ id, describedBy }) => (
                <Select id={id} aria-describedby={describedBy} required value={clientId} onChange={(e) => setClientId(e.target.value)}>
                  <option value="">Choose a client</option>
                  {clients.map(c => (
                    <option key={c.id} value={c.id}>{c.nom}</option>
                  ))}
                </Select>
              )}
            </Field>
            {/*
              No status field. A new invoice is always a draft and the
              server sets it (#87); offering the choice here meant an
              invoice could be created already marked Paid.
            */}
            <Field label="Amount (TND, excl. VAT)">
              {({ id }) => (
                <Input
                  id={id}
                  required
                  type="number"
                  step="0.001"
                  min="0"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="e.g. 12450.000"
                  className="font-mono"
                />
              )}
            </Field>
            <Field label="Due date">
              {({ id }) => <Input id={id} type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />}
            </Field>
          </form>
        </Dialog>
      )}
    </div>
  );
}
