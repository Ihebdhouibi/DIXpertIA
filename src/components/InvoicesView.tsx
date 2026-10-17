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
import { Plus, Download, ArrowRight, X, Pencil, Send, CheckCircle2, XCircle, SearchCheck, Banknote, Ban } from 'lucide-react';
import { Invoice, UserRole, Client } from '../types';
import StatusBadge, { ProcessingBadge, ReviewBadge } from './StatusBadge';
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
  REVIEW_LABEL,
  REVIEW_STATUSES,
  REVIEW_TO_API,
  CommercialStatus,
  ProcessingStatus,
  ReviewStatus,
  bookable,
  nextProcessingStatus,
} from '../invoiceStatus';
import Dialog from './ui/Dialog';
import InvoiceCreateDialog from './InvoiceCreateDialog';
import InvoiceEditDialog from './InvoiceEditDialog';
import InvoicePdfPreview from './InvoicePdfPreview';
import { InvoiceReviewPanel, RejectInvoiceDialog } from './InvoiceReview';
import { CancelInvoiceDialog, PayInvoiceDialog } from './InvoiceStatusDialogs';
import InvoiceHistory from './InvoiceHistory';
import Button from './ui/Button';
import { Field, Input, Select } from './ui/Field';
import { useConfirm, useToast, ToastTone } from './ui/feedback';
import { formatTND } from '../format';
import { labelOf, useLocale, useT, type MessageKey } from '../i18n';

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
  const t = useT();
  const locale = useLocale();
  const isAdmin = userRole === 'admin';
  // Who may move an invoice through the books (the API allows admin and
  // accountant, #96); everyone else sees the list read-only.
  const canProcess = userRole === 'admin' || userRole === 'accountant';
  // Verification before sending (#118): the accountant approves or rejects.
  const isAccountant = userRole === 'accountant';
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [isNewInvoiceOpen, setIsNewInvoiceOpen] = useState(false);
  // The draft being corrected (#125), opened from the invoice detail.
  const [editing, setEditing] = useState<Invoice | null>(null);
  // Bumped after an edit so the embedded PDF is generated again (#127).
  const [pdfVersion, setPdfVersion] = useState(0);

  const toast = useToast();
  const confirm = useConfirm();
  const [rejecting, setRejecting] = useState<Invoice | null>(null);
  const [paying, setPaying] = useState<Invoice | null>(null);
  const [cancelling, setCancelling] = useState<Invoice | null>(null);
  const [reviewing, setReviewing] = useState(false);
  const showToast = (message: string, tone: ToastTone = 'success') => toast(message, tone);

  // By internal id: the route takes the id, which exists before an invoice has
  // a legal number (#86, #118). The number only names the file.
  const handleDownload = async (invoice: Invoice) => {
    try {
      const url = URL.createObjectURL(await api.invoices.pdf(invoice.id));
      const a = document.createElement('a');
      a.href = url;
      a.download = t('invoices.fileName', { ref: invoice.reference });
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast(t('invoices.downloaded', { ref: invoice.reference }));
    } catch (error) {
      showToast(
        t('invoices.downloadFailed', { error: error instanceof Error ? error.message : t('invoices.networkError') }),
        'error',
      );
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
  const [review, setReview] = useState<'All' | ReviewStatus>('All');
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

  const filtersActive = !!(
    month || clientFilter || direction || commercial !== 'All' || processing !== 'All' || review !== 'All'
  );

  // A new filter starts from page one with nothing selected.
  useEffect(() => {
    setPagination((p) => ({ ...p, pageIndex: 0 }));
    setRowSelection({});
  }, [month, clientFilter, direction, commercial, processing, review, sorting]);

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
        review_status: review === 'All' ? undefined : REVIEW_TO_API[review],
      })
      .then(({ rows: page, total: count }) => {
        if (cancelled) return;
        setRows(page);
        setTotal(count);
        setLoadError(null);
      })
      .catch((e: unknown) => {
        if (!cancelled) setLoadError(e instanceof Error ? e.message : t('invoices.couldNotLoad'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // The language too: the API writes the dates in it (#135).
  }, [month, clientFilter, direction, commercial, processing, review, sorting, pagination, reloadKey, locale]);

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
    if (done) showToast(t(target === 'Completed' ? 'invoices.moved.Completed' : 'invoices.moved.Processed', { count: done }));
    if (refused) {
      const failed = results.length - done;
      showToast(
        t('invoices.notMoved', { count: failed, reason: refused.reason?.message ?? t('invoices.refused') }),
        'error',
      );
    }
    setRowSelection({});
    reload();
  };

  const formatDirection = (inv: Invoice) =>
    t(inv.direction === 'incoming' ? 'invoices.direction.incoming' : 'invoices.direction.outgoing');

  // TND, not USD: DI Xpertia is a Tunisian company and invoices in dinars,
  // with the dinar's three decimal places, in the language showing.
  const formatCurrency = formatTND;

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
            aria-label={t('invoices.selectAll')}
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
            aria-label={t('invoices.selectOne', { ref: row.original.reference })}
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
        header: t('invoices.col.invoice'),
        enableSorting: false,
        meta: { mono: true },
        cell: ({ row }) => (
          <button
            type="button"
            onClick={() => setSelectedInvoice(row.original)}
            className="rounded font-semibold hover:underline cursor-pointer"
          >
            {row.original.reference}
          </button>
        ),
      },
      {
        id: 'counterparty',
        header: t('invoices.col.counterparty'),
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
        header: t('invoices.col.amount'),
        meta: { numeric: true },
        cell: ({ row }) => <span className="font-semibold">{formatCurrency(row.original.amountTTC)}</span>,
      },
      {
        id: 'date',
        accessorFn: (inv) => inv.dateIssued,
        // Issue and due dates share one column, stacked like the counterparty,
        // so the row action still fits at desktop widths.
        header: t('invoices.col.dates'),
        meta: { numeric: true },
        cell: ({ row }) => (
          <div>
            <div className="text-on-surface-variant">{row.original.dateIssued}</div>
            <div
              className={`text-[11px] ${row.original.status === 'Overdue' ? 'font-semibold text-error' : 'text-on-surface-variant'}`}
            >
              {t('invoices.due', { date: row.original.dueDate })}
            </div>
          </div>
        ),
      },
      {
        id: 'status',
        header: t('invoices.col.status'),
        enableSorting: false,
        // A draft is shown by where it stands in verification (#118).
        cell: ({ row }) =>
          row.original.status === 'Draft' && row.original.direction === 'outgoing' ? (
            <ReviewBadge status={row.original.reviewStatus} />
          ) : (
            <StatusBadge status={row.original.status} />
          ),
      },
      {
        id: 'processing',
        header: t('invoices.books'),
        enableSorting: false,
        cell: ({ row }) => <ProcessingBadge status={row.original.processingStatus} />,
      },
      {
        id: 'actions',
        header: () => <span className="sr-only">{t('invoices.col.actions')}</span>,
        enableSorting: false,
        meta: { numeric: true },
        cell: ({ row }) => {
          // The books start when the invoice is sent (#118): no step on a draft.
          const next = bookable(row.original) ? nextProcessingStatus(row.original.processingStatus) : null;
          return (
            <div className="flex items-center justify-end gap-1 whitespace-nowrap">
              {isAccountant && row.original.reviewStatus === 'Submitted' && (
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => setSelectedInvoice(row.original)}
                  aria-label={t('invoices.verifyOne', { ref: row.original.reference })}
                >
                  <SearchCheck className="w-3.5 h-3.5" aria-hidden="true" />
                  {t('invoices.verify')}
                </Button>
              )}
              {canProcess && next && (
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={moving}
                  onClick={() => moveTo([row.original], next)}
                  aria-label={t('invoices.stepOne', { action: t(PROCESSING_ACTION[next]!), ref: row.original.reference })}
                  title={t(PROCESSING_ACTION[next]!)}
                >
                  <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
                  {t(PROCESSING_ACTION_SHORT[next]!)}
                </Button>
              )}
              <button
                type="button"
                onClick={() => handleDownload(row.original)}
                aria-label={t('invoices.downloadOne', { ref: row.original.reference })}
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
  }, [canProcess, isAccountant, moving, locale]);

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
    enableRowSelection: (row) =>
      canProcess && bookable(row.original) && nextProcessingStatus(row.original.processingStatus) !== null,
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
    setReview('All');
  };

  /** Run a verification step (#118), then show the invoice as the server returned it. */
  const runReview = async (done: MessageKey, step: () => Promise<Invoice>) => {
    setReviewing(true);
    try {
      const updated = await step();
      setSelectedInvoice(updated);
      setPdfVersion((v) => v + 1);
      showToast(t(done, { ref: updated.reference }));
      reload();
      onInvoiceCreated();
    } catch (err) {
      showToast(err instanceof Error ? err.message : t('invoices.refused'), 'error');
    } finally {
      setReviewing(false);
    }
  };

  const approve = async (invoice: Invoice) => {
    const ok = await confirm({
      title: t('invoices.approve.title', { ref: invoice.reference }),
      message: t('invoices.approve.message'),
      confirmLabel: t('invoices.approve'),
    });
    if (ok) await runReview('invoices.done.approved', () => api.invoices.approve(invoice.id));
  };

  const markSent = async (invoice: Invoice) => {
    const ok = await confirm({
      title: t('invoices.send.title', { ref: invoice.reference }),
      message: t('invoices.send.message'),
      confirmLabel: t('invoices.markSent'),
    });
    if (ok) await runReview('invoices.done.sent', () => api.invoices.send(invoice.id));
  };

  return (
    <div className="flex-grow flex flex-col gap-6 animate-fade-in">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-h1 font-black text-on-surface tracking-tight md:text-display">{t('invoices.title')}</h1>
          <p className="text-body-lg text-on-surface-variant mt-1">{t('invoices.intro')}</p>
        </div>
        {isAdmin && (
          <Button onClick={() => setIsNewInvoiceOpen(true)} className="shrink-0">
            <Plus className="w-4 h-4" aria-hidden="true" />
            {t('invoices.new')}
          </Button>
        )}
      </div>

      {/* Filters - each one is a query parameter of GET /api/invoices */}
      <div className="flex flex-col gap-4 rounded-xl border border-outline-variant bg-surface-container-lowest p-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Field label={t('invoices.filter.month')}>
            {({ id }) => <Input id={id} type="month" value={month} onChange={(e) => setMonth(e.target.value)} />}
          </Field>
          <Field label={t('invoices.filter.client')}>
            {({ id }) => (
              <Select id={id} value={clientFilter} onChange={(e) => setClientFilter(e.target.value)}>
                <option value="">{t('invoices.filter.allClients')}</option>
                {clients.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nom}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <Field label={t('invoices.direction')}>
            {({ id }) => (
              <Select id={id} value={direction} onChange={(e) => setDirection(e.target.value as typeof direction)}>
                <option value="">{t('invoices.direction.both')}</option>
                <option value="outgoing">{t('invoices.direction.outgoingLong')}</option>
                <option value="incoming">{t('invoices.direction.incomingLong')}</option>
              </Select>
            )}
          </Field>
          <Field label={t('invoices.filter.status')}>
            {({ id }) => (
              <Select id={id} value={commercial} onChange={(e) => setCommercial(e.target.value as typeof commercial)}>
                <option value="All">{t('invoices.filter.allStatuses')}</option>
                {COMMERCIAL_STATUSES.map((st) => (
                  <option key={st} value={st}>
                    {labelOf(t, 'common.status', st)}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <Field label={t('invoices.filter.verification')}>
            {({ id }) => (
              <Select id={id} value={review} onChange={(e) => setReview(e.target.value as typeof review)}>
                <option value="All">{t('invoices.filter.anyStage')}</option>
                {REVIEW_STATUSES.map((st) => (
                  <option key={st} value={st}>
                    {t(REVIEW_LABEL[st])}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <FilterPills
            label={t('invoices.books')}
            showLabel
            options={['All', ...PROCESSING_STATUSES] as const}
            value={processing}
            onChange={setProcessing}
            renderOption={(option) => (option === 'All' ? t('invoices.filter.all') : labelOf(t, 'common.status', option))}
          />
          {filtersActive && (
            <Button variant="ghost" size="sm" onClick={clearFilters}>
              <X className="w-4 h-4" aria-hidden="true" />
              {t('invoices.filter.clear')}
            </Button>
          )}
        </div>
      </div>

      {/* Bulk actions on the selection */}
      {selected.length > 0 && (
        <div
          role="region"
          aria-label={t('invoices.selection')}
          className="flex flex-wrap items-center gap-3 rounded-xl border border-outline-variant bg-surface-container px-4 py-3"
        >
          <span className="text-sm text-on-surface">
            {t('invoices.selectedCount', { count: selected.length })}
          </span>
          {(['Processed', 'Completed'] as const).map((target) => {
            const eligible = selectedByTarget(target);
            return (
              eligible.length > 0 && (
                <Button key={target} size="sm" loading={moving} onClick={() => moveTo(eligible, target)}>
                  <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
                  {t(PROCESSING_ACTION[target]!)} ({eligible.length})
                </Button>
              )
            );
          })}
          <Button variant="ghost" size="sm" onClick={() => setRowSelection({})}>
            {t('invoices.clearSelection')}
          </Button>
        </div>
      )}

      <Table
        caption={t('invoices.title')}
        footer={
          total > 0 && (
            <Pagination
              page={pagination.pageIndex + 1}
              pageSize={pagination.pageSize}
              total={total}
              onPageChange={(p) => table.setPageIndex(p - 1)}
              noun={t('invoices.noun')}
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
            <TableState kind="loading" colSpan={columns.length} title={t('invoices.loading')} />
          ) : loadError ? (
            <TableState
              kind="error"
              colSpan={columns.length}
              message={loadError}
              action={
                <Button variant="secondary" size="sm" onClick={reload}>
                  {t('invoices.retry')}
                </Button>
              }
            />
          ) : rows.length === 0 ? (
            <TableState
              kind="empty"
              colSpan={columns.length}
              title={filtersActive ? t('invoices.noneMatch') : t('invoices.noneYet')}
              message={filtersActive ? t('invoices.noneMatchHint') : undefined}
              action={
                filtersActive && (
                  <Button variant="secondary" size="sm" onClick={clearFilters}>
                    {t('invoices.filter.clear')}
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
        title={t('invoices.detail.title', { ref: selectedInvoice?.reference ?? '' })}
        size="xl"
        bodyClassName="overflow-auto p-6 bg-surface-container-low"
        headerActions={
          <>
            {selectedInvoice && selectedInvoice.status === 'Draft' && selectedInvoice.direction === 'outgoing' ? (
              <ReviewBadge status={selectedInvoice.reviewStatus} />
            ) : (
              <StatusBadge status={selectedInvoice?.status || 'Draft'} />
            )}
            {selectedInvoice && selectedInvoice.direction === 'outgoing' && selectedInvoice.status === 'Draft'
              && selectedInvoice.processingStatus !== 'Archived' && (
              <>
                {/* The admin corrects and submits a draft that is not under review (#125, #118). */}
                {isAdmin && (selectedInvoice.reviewStatus === 'Not submitted' || selectedInvoice.reviewStatus === 'Rejected') && (
                  <>
                    <Button variant="secondary" size="sm" onClick={() => setEditing(selectedInvoice)} disabled={reviewing}>
                      <Pencil className="w-4 h-4" aria-hidden="true" /> {t('invoices.edit')}
                    </Button>
                    <Button
                      size="sm"
                      loading={reviewing}
                      onClick={() => runReview('invoices.done.submitted', () => api.invoices.submit(selectedInvoice.id))}
                    >
                      <Send className="w-4 h-4" aria-hidden="true" /> {t('invoices.submit')}
                    </Button>
                  </>
                )}
                {/* The accountant decides on a submitted invoice. */}
                {isAccountant && selectedInvoice.reviewStatus === 'Submitted' && (
                  <>
                    <Button variant="secondary" size="sm" onClick={() => setRejecting(selectedInvoice)} disabled={reviewing}>
                      <XCircle className="w-4 h-4" aria-hidden="true" /> {t('invoices.reject')}
                    </Button>
                    <Button size="sm" loading={reviewing} onClick={() => approve(selectedInvoice)}>
                      <CheckCircle2 className="w-4 h-4" aria-hidden="true" /> {t('invoices.approve')}
                    </Button>
                  </>
                )}
                {/* Once approved, the admin marks it sent. */}
                {isAdmin && selectedInvoice.reviewStatus === 'Approved' && (
                  <Button size="sm" loading={reviewing} onClick={() => markSent(selectedInvoice)}>
                    <Send className="w-4 h-4" aria-hidden="true" /> {t('invoices.markSent')}
                  </Button>
                )}
              </>
            )}
            {/* Paid and cancelled (#126). The server holds the same rules; these
                only hide what it would refuse. */}
            {selectedInvoice && (isAdmin || isAccountant)
              && (selectedInvoice.status === 'Sent' || selectedInvoice.status === 'Overdue') && (
              <Button size="sm" onClick={() => setPaying(selectedInvoice)} disabled={reviewing}>
                <Banknote className="w-4 h-4" aria-hidden="true" /> {t('invoices.markPaid')}
              </Button>
            )}
            {selectedInvoice && isAdmin && selectedInvoice.processingStatus !== 'Archived' && (
              (selectedInvoice.status === 'Draft' && selectedInvoice.reviewStatus !== 'Submitted')
              || selectedInvoice.status === 'Sent' || selectedInvoice.status === 'Overdue'
            ) && (
              <Button variant="secondary" size="sm" onClick={() => setCancelling(selectedInvoice)} disabled={reviewing}>
                <Ban className="w-4 h-4" aria-hidden="true" /> {t('invoices.cancelInvoice')}
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={() => selectedInvoice && handleDownload(selectedInvoice)}>
              <Download className="w-4 h-4" aria-hidden="true" /> {t('invoices.download')}
            </Button>
          </>
        }
      >
        {selectedInvoice && (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div className="flex flex-col gap-6">
              <section className="rounded-xl border border-outline-variant bg-surface-container-lowest p-5">
                <h3 className="mb-4 text-sm font-semibold text-on-surface">{t('invoices.summary')}</h3>
                <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-3 text-sm">
                  <dt className={DETAIL_LABEL}>{t('invoices.exclVat')}</dt>
                  <dd className="text-right font-mono tabular-nums text-on-surface">{formatCurrency(selectedInvoice.amountHT)}</dd>
                  <dt className={DETAIL_LABEL}>{t('invoices.vat')}</dt>
                  <dd className="text-right font-mono tabular-nums text-on-surface">
                    {formatCurrency(selectedInvoice.amountTTC - selectedInvoice.amountHT)}
                  </dd>
                  <dt className={`${DETAIL_LABEL} border-t border-outline-variant pt-3`}>{t('invoices.inclVat')}</dt>
                  <dd className="border-t border-outline-variant pt-3 text-right font-mono text-base font-semibold tabular-nums text-on-surface">
                    {formatCurrency(selectedInvoice.amountTTC)}
                  </dd>
                  <dt className={DETAIL_LABEL}>{t('invoices.issued')}</dt>
                  <dd className="whitespace-nowrap text-right font-mono tabular-nums text-on-surface">{selectedInvoice.dateIssued}</dd>
                  <dt className={DETAIL_LABEL}>{t('invoices.dueLabel')}</dt>
                  <dd className={`whitespace-nowrap text-right font-mono tabular-nums ${selectedInvoice.status === 'Overdue' ? 'font-semibold text-error' : 'text-on-surface'}`}>
                    {selectedInvoice.dueDate}
                  </dd>
                  <dt className={DETAIL_LABEL}>{t('invoices.books')}</dt>
                  <dd className="text-right"><ProcessingBadge status={selectedInvoice.processingStatus} /></dd>
                  {selectedInvoice.paidOn && (
                    <>
                      <dt className={DETAIL_LABEL}>{t('invoices.paid')}</dt>
                      <dd className="whitespace-nowrap text-right font-mono tabular-nums text-on-surface">{selectedInvoice.paidOn}</dd>
                    </>
                  )}
                </dl>
                {selectedInvoice.status === 'Cancelled' && selectedInvoice.cancellationReason && (
                  <p className="mt-4 rounded-lg bg-surface-container px-3 py-2 text-sm text-on-surface-variant">
                    <span className="font-semibold text-on-surface">{t('invoices.cancelledPrefix')}</span> {selectedInvoice.cancellationReason}
                  </p>
                )}
              </section>

              <section className="rounded-xl border border-outline-variant bg-surface-container-lowest p-5">
                <h3 className="mb-4 text-sm font-semibold text-on-surface">
                  {t(selectedInvoice.direction === 'incoming' ? 'invoices.supplier' : 'invoices.client')}
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
                  {selectedInvoice.counterpartyAddress || t('invoices.noAddress')}
                </p>
                {selectedInvoice.supplierReference && (
                  <p className="mt-3 text-xs text-on-surface-variant">
                    {t('invoices.supplierReference')} <span className="font-mono text-on-surface">{selectedInvoice.supplierReference}</span>
                  </p>
                )}
              </section>

              {selectedInvoice.direction === 'outgoing' && <InvoiceReviewPanel invoice={selectedInvoice} />}
              <InvoiceHistory invoice={selectedInvoice} />
            </div>

            <div className="lg:col-span-2">
              <InvoicePdfPreview invoiceId={selectedInvoice.id} label={selectedInvoice.reference} version={pdfVersion} />
            </div>
          </div>
        )}
      </Dialog>

      {isAccountant && (
        <RejectInvoiceDialog
          invoice={rejecting}
          onClose={() => setRejecting(null)}
          onReject={async (invoice, comment) => {
            const updated = await api.invoices.reject(invoice.id, comment);
            setRejecting(null);
            setSelectedInvoice(updated);
            showToast(t('invoices.done.rejected', { ref: updated.reference }));
            reload();
          }}
        />
      )}

      {(isAdmin || isAccountant) && (
        <PayInvoiceDialog
          invoice={paying}
          onClose={() => setPaying(null)}
          onPay={async (invoice, paidOn) => {
            const updated = await api.invoices.pay(invoice.id, paidOn);
            setPaying(null);
            setSelectedInvoice(updated);
            showToast(t('invoices.done.paid', { ref: updated.reference }));
            reload();
            onInvoiceCreated();
          }}
        />
      )}

      {isAdmin && (
        <CancelInvoiceDialog
          invoice={cancelling}
          onClose={() => setCancelling(null)}
          onCancelInvoice={async (invoice, reason) => {
            const updated = await api.invoices.cancel(invoice.id, reason);
            setCancelling(null);
            setSelectedInvoice(updated);
            setPdfVersion((v) => v + 1);
            showToast(t('invoices.done.cancelled', { ref: updated.reference }));
            reload();
            onInvoiceCreated();
          }}
        />
      )}

      {isAdmin && (
        <InvoiceEditDialog
          invoice={editing}
          onClose={() => setEditing(null)}
          onSaved={(updated) => {
            setEditing(null);
            setSelectedInvoice(updated);
            setPdfVersion((v) => v + 1);
            showToast(t('invoices.done.updated', { ref: updated.reference }));
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
            showToast(t('invoices.done.created', { ref: created.reference }));
            reload();
            onInvoiceCreated();
          }}
        />
      )}
    </div>
  );
}
