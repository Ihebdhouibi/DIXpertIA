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
import { Plus, Download, ArrowRight, X, Pencil } from 'lucide-react';
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
import InvoiceCreateDialog from './InvoiceCreateDialog';
import InvoiceEditDialog from './InvoiceEditDialog';
import InvoicePdfPreview from './InvoicePdfPreview';
import Button from './ui/Button';
import { Field, Input, Select } from './ui/Field';
import { useToast, ToastTone } from './ui/feedback';

interface InvoicesViewProps {
  /** Kept for the dashboard's sake; this view loads its own pages from the server (#113). */
  invoices?: Invoice[];
  /** Clients the invoice may be issued to. The API requires a real one. */
  clients: Client[];
  /** Tells the app an invoice was created, so data loaded elsewhere (the dashboard) refreshes. */
  onInvoiceCreated: () => void;
  userRole: UserRole;
}

const DETAIL_LABEL = 'font-mono text-[11px] font-medium uppercase tracking-[0.08em] text-on-surface-variant self-center whitespace-nowrap';

export default function InvoicesView({ clients, onInvoiceCreated, userRole }: InvoicesViewProps) {
  const isAdmin = userRole === 'admin';
  // Who may move an invoice through the books (the API allows admin and
  // accountant, #96); everyone else sees the list read-only.
  const canProcess = userRole === 'admin' || userRole === 'accountant';
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [isNewInvoiceOpen, setIsNewInvoiceOpen] = useState(false);
  // The draft being corrected (#125), opened from the invoice detail.
  const [editing, setEditing] = useState<Invoice | null>(null);
  // Bumped after an edit so the embedded PDF is generated again (#127).
  const [pdfVersion, setPdfVersion] = useState(0);

  const toast = useToast();
  const showToast = (message: string, tone: ToastTone = 'success') => toast(message, tone);

  // By internal id: the route takes the id, which exists before an invoice has
  // a legal number (#86, #118). The number only names the file.
  const handleDownload = async (invoice: Invoice) => {
    try {
      const url = URL.createObjectURL(await api.invoices.pdf(invoice.id));
      const a = document.createElement('a');
      a.href = url;
      a.download = `Invoice_${invoice.numero}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast(`Invoice ${invoice.numero} downloaded.`);
    } catch (error) {
      showToast(`Download failed: ${error instanceof Error ? error.message : 'network error'}`, 'error');
    }
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
                onClick={() => handleDownload(row.original)}
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

      {/* Invoice detail (#127): real figures on the left, the real PDF on the right. */}
      <Dialog
        open={selectedInvoice !== null}
        onClose={() => setSelectedInvoice(null)}
        title={`Invoice ${selectedInvoice?.numero ?? ''}`}
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
            <Button variant="ghost" size="sm" onClick={() => selectedInvoice && handleDownload(selectedInvoice)}>
              <Download className="w-4 h-4" aria-hidden="true" /> Download
            </Button>
          </>
        }
      >
        {selectedInvoice && (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div className="flex flex-col gap-6">
              <section className="rounded-xl border border-outline-variant bg-surface-container-lowest p-5">
                <h3 className="mb-4 text-sm font-semibold text-on-surface">Summary</h3>
                <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-3 text-sm">
                  <dt className={DETAIL_LABEL}>Excl. VAT</dt>
                  <dd className="text-right font-mono tabular-nums text-on-surface">{formatCurrency(selectedInvoice.amountHT)}</dd>
                  <dt className={DETAIL_LABEL}>VAT</dt>
                  <dd className="text-right font-mono tabular-nums text-on-surface">
                    {formatCurrency(selectedInvoice.amountTTC - selectedInvoice.amountHT)}
                  </dd>
                  <dt className={`${DETAIL_LABEL} border-t border-outline-variant pt-3`}>Total incl. VAT</dt>
                  <dd className="border-t border-outline-variant pt-3 text-right font-mono text-base font-semibold tabular-nums text-on-surface">
                    {formatCurrency(selectedInvoice.amountTTC)}
                  </dd>
                  <dt className={DETAIL_LABEL}>Issued</dt>
                  <dd className="text-right font-mono tabular-nums text-on-surface">{selectedInvoice.dateIssued}</dd>
                  <dt className={DETAIL_LABEL}>Due</dt>
                  <dd className={`text-right font-mono tabular-nums ${selectedInvoice.status === 'Overdue' ? 'font-semibold text-error' : 'text-on-surface'}`}>
                    {selectedInvoice.dueDate}
                  </dd>
                  <dt className={DETAIL_LABEL}>Books</dt>
                  <dd className="text-right"><ProcessingBadge status={selectedInvoice.processingStatus} /></dd>
                </dl>
              </section>

              <section className="rounded-xl border border-outline-variant bg-surface-container-lowest p-5">
                <h3 className="mb-4 text-sm font-semibold text-on-surface">
                  {selectedInvoice.direction === 'incoming' ? 'Supplier' : 'Client'}
                </h3>
                <div className="flex items-center gap-3">
                  <Avatar name={selectedInvoice.counterparty} shape="square" />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-on-surface">{selectedInvoice.counterparty}</p>
                    {selectedInvoice.counterpartyEmail && (
                      <p className="truncate text-xs text-on-surface-variant" title={selectedInvoice.counterpartyEmail}>
                        {selectedInvoice.counterpartyEmail}
                      </p>
                    )}
                  </div>
                </div>
                {/* The address as stored, line breaks kept; nothing invented when it is missing. */}
                <p className="mt-4 whitespace-pre-line border-t border-outline-variant pt-3 text-sm text-on-surface-variant">
                  {selectedInvoice.counterpartyAddress || 'No address on file.'}
                </p>
                {selectedInvoice.supplierReference && (
                  <p className="mt-3 text-xs text-on-surface-variant">
                    Supplier reference <span className="font-mono text-on-surface">{selectedInvoice.supplierReference}</span>
                  </p>
                )}
              </section>
            </div>

            <div className="lg:col-span-2">
              <InvoicePdfPreview invoiceId={selectedInvoice.id} label={selectedInvoice.numero} version={pdfVersion} />
            </div>
          </div>
        )}
      </Dialog>

      {isAdmin && (
        <InvoiceEditDialog
          invoice={editing}
          onClose={() => setEditing(null)}
          onSaved={(updated) => {
            setEditing(null);
            setSelectedInvoice(updated);
            setPdfVersion((v) => v + 1);
            showToast(`Invoice ${updated.numero} updated.`);
            reload();
          }}
        />
      )}

      {/* New invoice (#128): real lines, idempotent, errors kept in the form. */}
      {isAdmin && (
        <InvoiceCreateDialog
          open={isNewInvoiceOpen}
          clients={clients}
          onClose={() => setIsNewInvoiceOpen(false)}
          onCreated={(created) => {
            setIsNewInvoiceOpen(false);
            showToast(`Invoice ${created.numero} created as a draft.`);
            reload();
            onInvoiceCreated();
          }}
        />
      )}
    </div>
  );
}
