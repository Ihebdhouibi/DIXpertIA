import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ColumnDef,
  PaginationState,
  RowSelectionState,
  SortingState,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table';
import { Plus, Download, ZoomIn, ZoomOut, ArrowRight, X, Pencil } from 'lucide-react';
import { Invoice, UserRole, Client } from '../types';
import StatusBadge, { ProcessingBadge } from './StatusBadge';
import Avatar from './ui/Avatar';
import { Table, Th, TBody, Tr, Td, TableState } from './ui/Table';
import { FilterPills, Pagination } from './ui/TableControls';
import * as api from '../api';
import {
  COMMERCIAL_STATUSES,
  COMMERCIAL_TO_API,
  PROCESSING_ACTION,
  PROCESSING_ACTION_SHORT,
  PROCESSING_STATUSES,
  PROCESSING_TO_API,
  CommercialStatus,
  ProcessingStatus,
  nextProcessingStatus,
} from '../invoiceStatus';
import Dialog from './ui/Dialog';
import InvoiceEditDialog from './InvoiceEditDialog';
import Button from './ui/Button';
import { Field, Input, Select } from './ui/Field';
import { useToast, ToastTone } from './ui/feedback';

interface InvoicesViewProps {
  /** Kept for the dashboard's sake; this view loads its own pages from the server (#113). */
  invoices?: Invoice[];
  /** Clients the invoice may be issued to. The API requires a real one. */
  clients: Client[];
  onAddInvoice: (invoice: {
    client_id: number;
    date_echeance: string;
    items: { designation: string; quantite: number; prix_unitaire: number; taux_tva: number }[];
  }) => unknown;
  userRole: UserRole;
}

export default function InvoicesView({ clients, onAddInvoice, userRole }: InvoicesViewProps) {
  const isAdmin = userRole === 'admin';
  // Who may move an invoice through the books (the API allows admin and
  // accountant, #96); everyone else sees the list read-only.
  const canProcess = userRole === 'admin' || userRole === 'accountant';
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [isNewInvoiceOpen, setIsNewInvoiceOpen] = useState(false);
  // The draft being corrected (#125), opened from the invoice detail.
  const [editing, setEditing] = useState<Invoice | null>(null);
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
    Promise.resolve(onAddInvoice({
      client_id: Number(clientId),
      date_echeance: dueDate,
      items: [{
        designation: 'Consultation & Cloud Integration Services',
        quantite: 1,
        prix_unitaire: parseFloat(amount),
        taux_tva: 19,
      }],
    })).then(reload);

    setIsNewInvoiceOpen(false);
    setClientId('');
    setAmount('');
    setDueDate('');
  };

  // --- Server-driven list (#113) -------------------------------------------
  // Filters, sorting and pagination are query parameters of GET /api/invoices,
  // so they cover every invoice, not the first 200 the app preloads.
  const [month, setMonth] = useState('');
  const [clientFilter, setClientFilter] = useState('');
  const [direction, setDirection] = useState<'' | 'outgoing' | 'incoming'>('');
  const [commercial, setCommercial] = useState<'All' | CommercialStatus>('All');
  const [processing, setProcessing] = useState<'All' | ProcessingStatus>('All');
  const [sorting, setSorting] = useState<SortingState>([{ id: 'date', desc: true }]);
  const [pagination, setPagination] = useState<PaginationState>({ pageIndex: 0, pageSize: 20 });
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [rows, setRows] = useState<Invoice[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [moving, setMoving] = useState(false);
  const reload = useCallback(() => setReloadKey((k) => k + 1), []);

  const filtersActive = !!(month || clientFilter || direction || commercial !== 'All' || processing !== 'All');

  // A new filter starts from page one with nothing selected.
  useEffect(() => {
    setPagination((p) => ({ ...p, pageIndex: 0 }));
    setRowSelection({});
  }, [month, clientFilter, direction, commercial, processing, sorting]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const sort = sorting[0] ? `${sorting[0].desc ? '-' : ''}${sorting[0].id}` : '-date';
    api.invoices
      .page({
        limit: pagination.pageSize,
        offset: pagination.pageIndex * pagination.pageSize,
        sort,
        month: month || undefined,
        client_id: clientFilter || undefined,
        direction: direction || undefined,
        statut: commercial === 'All' ? undefined : COMMERCIAL_TO_API[commercial],
        processing_status: processing === 'All' ? undefined : PROCESSING_TO_API[processing],
      })
      .then(({ rows: page, total: count }) => {
        if (cancelled) return;
        setRows(page);
        setTotal(count);
        setLoadError(null);
      })
      .catch((e: unknown) => {
        if (!cancelled) setLoadError(e instanceof Error ? e.message : 'Could not load invoices');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [month, clientFilter, direction, commercial, processing, sorting, pagination, reloadKey]);

  /** Move invoices to `target`, one request each (no bulk endpoint yet - #115). */
  const moveTo = async (targets: Invoice[], target: ProcessingStatus) => {
    if (targets.length === 0) return;
    setMoving(true);
    const results = await Promise.allSettled(
      targets.map((inv) => api.invoices.setProcessingStatus(inv.id, PROCESSING_TO_API[target])),
    );
    setMoving(false);
    const done = results.filter((r) => r.status === 'fulfilled').length;
    const refused = results.find((r): r is PromiseRejectedResult => r.status === 'rejected');
    if (done) showToast(`${done} invoice${done === 1 ? '' : 's'} ${target.toLowerCase()}.`);
    if (refused) {
      const failed = results.length - done;
      showToast(
        `${failed} invoice${failed === 1 ? '' : 's'} not moved: ${refused.reason?.message ?? 'refused by the server'}`,
        'error',
      );
    }
    setRowSelection({});
    reload();
  };

  const formatDirection = (inv: Invoice) => (inv.direction === 'incoming' ? 'Incoming' : 'Outgoing');

  const formatCurrency = (val: number) => {
    // TND, not USD: DI Xpertia is a Tunisian company and invoices in dinars.
    // The dinar has three decimal places, which is why minimumFractionDigits is
    // set rather than left to the default two.
    return new Intl.NumberFormat('fr-TN', {
      style: 'currency', currency: 'TND', minimumFractionDigits: 3,
    }).format(val);
  };

  // --- Columns ---------------------------------------------------------------
  // meta.numeric right-aligns a column in mono; ids 'date' and 'amount' are the
  // API's sort keys, so TanStack's sorting state maps straight onto ?sort=.
  const columns = useMemo<ColumnDef<Invoice>[]>(() => {
    const cols: ColumnDef<Invoice>[] = [];
    if (canProcess) {
      cols.push({
        id: 'select',
        enableSorting: false,
        header: ({ table }) => (
          <input
            type="checkbox"
            aria-label="Select every invoice on this page that can move"
            className="h-4 w-4 accent-primary cursor-pointer"
            checked={table.getIsAllPageRowsSelected()}
            ref={(el) => {
              if (el) el.indeterminate = table.getIsSomePageRowsSelected();
            }}
            onChange={table.getToggleAllPageRowsSelectedHandler()}
          />
        ),
        cell: ({ row }) => (
          <input
            type="checkbox"
            aria-label={`Select invoice ${row.original.numero}`}
            className="h-4 w-4 accent-primary cursor-pointer disabled:cursor-not-allowed disabled:opacity-40"
            checked={row.getIsSelected()}
            disabled={!row.getCanSelect()}
            onChange={row.getToggleSelectedHandler()}
          />
        ),
      });
    }
    cols.push(
      {
        id: 'numero',
        header: 'Invoice',
        enableSorting: false,
        meta: { mono: true },
        cell: ({ row }) => (
          <button
            type="button"
            onClick={() => setSelectedInvoice(row.original)}
            className="rounded font-semibold hover:underline cursor-pointer"
          >
            {row.original.numero}
          </button>
        ),
      },
      {
        id: 'counterparty',
        header: 'Client / supplier',
        enableSorting: false,
        cell: ({ row }) => (
          <div className="flex items-center gap-3">
            <Avatar name={row.original.counterparty} size="sm" shape="square" />
            <div className="min-w-0">
              <div className="truncate font-semibold">{row.original.counterparty}</div>
              <div className="font-mono text-[11px] uppercase tracking-[0.08em] text-on-surface-variant">
                {formatDirection(row.original)}
              </div>
            </div>
          </div>
        ),
      },
      {
        // An accessor is what makes a TanStack column sortable; the value itself
        // is never compared here (manualSorting), the server orders by it.
        id: 'amount',
        accessorFn: (inv) => inv.amountTTC,
        header: 'Amount',
        meta: { numeric: true },
        cell: ({ row }) => <span className="font-semibold">{formatCurrency(row.original.amountTTC)}</span>,
      },
      {
        id: 'date',
        accessorFn: (inv) => inv.dateIssued,
        // Issue and due dates share one column, stacked like the counterparty,
        // so the row action still fits at desktop widths.
        header: 'Issued / due',
        meta: { numeric: true },
        cell: ({ row }) => (
          <div>
            <div className="text-on-surface-variant">{row.original.dateIssued}</div>
            <div
              className={`text-[11px] ${row.original.status === 'Overdue' ? 'font-semibold text-error' : 'text-on-surface-variant'}`}
            >
              due {row.original.dueDate}
            </div>
          </div>
        ),
      },
      {
        id: 'status',
        header: 'Status',
        enableSorting: false,
        cell: ({ row }) => <StatusBadge status={row.original.status} />,
      },
      {
        id: 'processing',
        header: 'Books',
        enableSorting: false,
        cell: ({ row }) => <ProcessingBadge status={row.original.processingStatus} />,
      },
      {
        id: 'actions',
        header: () => <span className="sr-only">Actions</span>,
        enableSorting: false,
        meta: { numeric: true },
        cell: ({ row }) => {
          const next = nextProcessingStatus(row.original.processingStatus);
          return (
            <div className="flex items-center justify-end gap-1 whitespace-nowrap">
              {canProcess && next && (
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={moving}
                  onClick={() => moveTo([row.original], next)}
                  aria-label={`${PROCESSING_ACTION[next]}: invoice ${row.original.numero}`}
                  title={PROCESSING_ACTION[next]}
                >
                  <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
                  {PROCESSING_ACTION_SHORT[next]}
                </Button>
              )}
              <button
                type="button"
                onClick={() => handleDownload(row.original.id)}
                aria-label={`Download invoice ${row.original.numero}`}
                className="rounded-lg p-1.5 text-on-surface-variant transition-colors hover:bg-surface-container hover:text-on-surface cursor-pointer"
              >
                <Download className="w-4 h-4" aria-hidden="true" />
              </button>
            </div>
          );
        },
      },
    );
    return cols;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canProcess, moving]);

  const table = useReactTable({
    data: rows,
    columns,
    getRowId: (row) => row.id,
    getCoreRowModel: getCoreRowModel(),
    // Everything happens on the server; TanStack keeps the state and the UI.
    manualPagination: true,
    manualSorting: true,
    manualFiltering: true,
    rowCount: total,
    enableSortingRemoval: false,
    // An invoice can be selected for a bulk move only while it has a next step.
    enableRowSelection: (row) => canProcess && nextProcessingStatus(row.original.processingStatus) !== null,
    state: { sorting, pagination, rowSelection },
    onSortingChange: setSorting,
    onPaginationChange: setPagination,
    onRowSelectionChange: setRowSelection,
  });

  const selected = table.getSelectedRowModel().rows.map((r) => r.original);
  const selectedByTarget = (target: ProcessingStatus) =>
    selected.filter((inv) => nextProcessingStatus(inv.processingStatus) === target);

  const clearFilters = () => {
    setMonth('');
    setClientFilter('');
    setDirection('');
    setCommercial('All');
    setProcessing('All');
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

      {/* Filters - each one is a query parameter of GET /api/invoices */}
      <div className="flex flex-col gap-4 rounded-xl border border-outline-variant bg-surface-container-lowest p-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Month">
            {({ id }) => <Input id={id} type="month" value={month} onChange={(e) => setMonth(e.target.value)} />}
          </Field>
          <Field label="Client">
            {({ id }) => (
              <Select id={id} value={clientFilter} onChange={(e) => setClientFilter(e.target.value)}>
                <option value="">All clients</option>
                {clients.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nom}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <Field label="Direction">
            {({ id }) => (
              <Select id={id} value={direction} onChange={(e) => setDirection(e.target.value as typeof direction)}>
                <option value="">Incoming and outgoing</option>
                <option value="outgoing">Outgoing (we bill)</option>
                <option value="incoming">Incoming (we are billed)</option>
              </Select>
            )}
          </Field>
          <Field label="Status">
            {({ id }) => (
              <Select id={id} value={commercial} onChange={(e) => setCommercial(e.target.value as typeof commercial)}>
                <option value="All">All statuses</option>
                {COMMERCIAL_STATUSES.map((st) => (
                  <option key={st} value={st}>
                    {st}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <FilterPills
            label="Books"
            showLabel
            options={['All', ...PROCESSING_STATUSES] as const}
            value={processing}
            onChange={setProcessing}
          />
          {filtersActive && (
            <Button variant="ghost" size="sm" onClick={clearFilters}>
              <X className="w-4 h-4" aria-hidden="true" />
              Clear filters
            </Button>
          )}
        </div>
      </div>

      {/* Bulk actions on the selection */}
      {selected.length > 0 && (
        <div
          role="region"
          aria-label="Selected invoices"
          className="flex flex-wrap items-center gap-3 rounded-xl border border-outline-variant bg-surface-container px-4 py-3"
        >
          <span className="text-sm text-on-surface">
            <span className="font-mono tabular-nums font-semibold">{selected.length}</span> selected
          </span>
          {(['Processed', 'Completed'] as const).map((target) => {
            const eligible = selectedByTarget(target);
            return (
              eligible.length > 0 && (
                <Button key={target} size="sm" loading={moving} onClick={() => moveTo(eligible, target)}>
                  <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
                  {PROCESSING_ACTION[target]} ({eligible.length})
                </Button>
              )
            );
          })}
          <Button variant="ghost" size="sm" onClick={() => setRowSelection({})}>
            Clear selection
          </Button>
        </div>
      )}

      <Table
        caption="Invoices"
        footer={
          total > 0 && (
            <Pagination
              page={pagination.pageIndex + 1}
              pageSize={pagination.pageSize}
              total={total}
              onPageChange={(p) => table.setPageIndex(p - 1)}
              noun="invoices"
            />
          )
        }
      >
        <thead className="border-b border-outline-variant bg-surface-container-low">
          {table.getHeaderGroups().map((group) => (
            <tr key={group.id}>
              {group.headers.map((header) => {
                const meta = header.column.columnDef.meta as { numeric?: boolean } | undefined;
                const sortable = header.column.getCanSort();
                return (
                  <Th
                    key={header.id}
                    numeric={meta?.numeric}
                    sort={sortable ? header.column.getIsSorted() : undefined}
                    onSort={sortable ? () => header.column.toggleSorting(header.column.getIsSorted() !== 'desc') : undefined}
                  >
                    {flexRender(header.column.columnDef.header, header.getContext())}
                  </Th>
                );
              })}
            </tr>
          ))}
        </thead>
        <TBody>
          {loading && rows.length === 0 ? (
            <TableState kind="loading" colSpan={columns.length} title="Loading invoices..." />
          ) : loadError ? (
            <TableState
              kind="error"
              colSpan={columns.length}
              message={loadError}
              action={
                <Button variant="secondary" size="sm" onClick={reload}>
                  Retry
                </Button>
              }
            />
          ) : rows.length === 0 ? (
            <TableState
              kind="empty"
              colSpan={columns.length}
              title={filtersActive ? 'No invoices match' : 'No invoices yet'}
              message={filtersActive ? 'Try another month, client or status.' : undefined}
              action={
                filtersActive && (
                  <Button variant="secondary" size="sm" onClick={clearFilters}>
                    Clear filters
                  </Button>
                )
              }
            />
          ) : (
            table.getRowModel().rows.map((row) => (
              <Tr key={row.id} selected={row.getIsSelected()} className={loading ? 'opacity-60' : ''}>
                {row.getVisibleCells().map((cell) => {
                  const meta = cell.column.columnDef.meta as { numeric?: boolean; mono?: boolean } | undefined;
                  return (
                    <Td key={cell.id} numeric={meta?.numeric} mono={meta?.mono}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </Td>
                  );
                })}
              </Tr>
            ))
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
            {/* Only a draft we issued can be corrected, by the admin, and not
                once its month is closed; the server refuses anything else. */}
            {isAdmin && selectedInvoice && selectedInvoice.direction === 'outgoing'
              && selectedInvoice.status === 'Draft' && selectedInvoice.processingStatus !== 'Archived' && (
              <Button variant="secondary" size="sm" onClick={() => setEditing(selectedInvoice)}>
                <Pencil className="w-4 h-4" aria-hidden="true" /> Edit
              </Button>
            )}
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

      {isAdmin && (
        <InvoiceEditDialog
          invoice={editing}
          onClose={() => setEditing(null)}
          onSaved={(updated) => {
            setEditing(null);
            setSelectedInvoice(updated);
            showToast(`Invoice ${updated.numero} updated.`);
            reload();
          }}
        />
      )}

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
