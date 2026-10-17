import { useCallback, useEffect, useState } from 'react';
import { CheckCircle2 } from 'lucide-react';
import { contactRequests, type ContactRequest } from '../api';
import { Table, THead, Th, TBody, Tr, Td, TableState } from './ui/Table';
import { FilterPills, Pagination } from './ui/TableControls';
import Button from './ui/Button';
import Dialog from './ui/Dialog';
import { useToast } from './ui/feedback';

/**
 * The enquiries sent from the website's contact form (#98), admin only.
 * Every one is kept and notified here, whether or not the e-mail inbox is
 * configured yet. The message is shown as text, never as markup: it comes
 * from an anonymous visitor.
 */

export const TOPIC_LABEL: Record<string, string> = {
  security_audit: 'Security audit / penetration testing',
  cloud_migration: 'Hybrid cloud migration',
  custom_development: 'Custom API / CRM development',
  support_subscription: 'Support subscription',
  other: 'Other request',
};

type Filter = 'Open' | 'Handled' | 'All';
const FILTERS: Filter[] = ['Open', 'Handled', 'All'];
const PAGE_SIZE = 20;

const when = (iso: string) =>
  new Date(iso).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });

export default function EnquiriesView() {
  const toast = useToast();
  const [filter, setFilter] = useState<Filter>('Open');
  const [page, setPage] = useState(1);
  const [rows, setRows] = useState<ContactRequest[] | null>(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<ContactRequest | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    setError(null);
    setRows(null);
    const handled = filter === 'All' ? undefined : filter === 'Handled';
    contactRequests
      .page({ handled, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
      .then((result) => {
        setRows(result.rows);
        setTotal(result.total);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load the enquiries.'));
  }, [filter, page]);

  useEffect(load, [load]);

  const markHandled = async (enquiry: ContactRequest) => {
    setSaving(true);
    try {
      const updated = await contactRequests.handle(enquiry.id);
      setOpen(updated);
      toast(`Enquiry from ${enquiry.name} marked as handled.`);
      load();
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Could not update the enquiry.', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-1 flex-col gap-6">
      <div>
        <h1 className="text-h1 font-black tracking-tight text-on-surface md:text-display">Enquiries</h1>
        <p className="mt-1 text-body-lg text-on-surface-variant">Messages sent from the website's contact form.</p>
      </div>

      <FilterPills
        label="Show"
        options={FILTERS}
        value={filter}
        onChange={(next) => {
          setFilter(next);
          setPage(1);
        }}
      />

      <Table
        caption="Enquiries"
        footer={
          total > PAGE_SIZE && (
            <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} noun="enquiries" />
          )
        }
      >
        <THead>
          <Th>From</Th>
          <Th>Topic</Th>
          <Th>Message</Th>
          <Th numeric>Received</Th>
          <Th>Status</Th>
        </THead>
        <TBody>
          {error ? (
            <TableState kind="error" colSpan={5} message={error} />
          ) : rows === null ? (
            <TableState kind="loading" colSpan={5} title="Loading enquiries..." />
          ) : rows.length === 0 ? (
            <TableState
              kind="empty"
              colSpan={5}
              title={filter === 'Open' ? 'No open enquiries' : 'No enquiries yet'}
              message="Messages sent from the website's contact form appear here."
            />
          ) : (
            rows.map((r) => (
              <Tr key={r.id} interactive onClick={() => setOpen(r)}>
                <Td>
                  <button type="button" onClick={() => setOpen(r)} className="cursor-pointer text-left font-semibold hover:underline">
                    {r.name}
                  </button>
                  <div className="text-body-sm text-on-surface-variant">{r.email}</div>
                </Td>
                <Td muted>{TOPIC_LABEL[r.topic] ?? r.topic}</Td>
                <Td muted className="max-w-[28ch] truncate">{r.message}</Td>
                <Td numeric muted>{when(r.createdAt)}</Td>
                <Td>
                  {r.handledAt ? (
                    <span className="inline-flex items-center gap-1.5 text-body-sm text-success">
                      <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> Handled
                    </span>
                  ) : (
                    <span className="text-body-sm font-semibold text-on-surface">Open</span>
                  )}
                </Td>
              </Tr>
            ))
          )}
        </TBody>
      </Table>

      <Dialog
        open={open !== null}
        onClose={() => setOpen(null)}
        title={open ? `Enquiry from ${open.name}` : ''}
        description={open ? `${TOPIC_LABEL[open.topic] ?? open.topic} · received ${when(open.createdAt)}` : undefined}
        footer={
          open && (
            <>
              <Button variant="secondary" onClick={() => setOpen(null)}>
                Close
              </Button>
              {open.handledAt ? null : (
                <Button onClick={() => markHandled(open)} loading={saving}>
                  Mark as handled
                </Button>
              )}
            </>
          )
        }
      >
        {open && (
          <div className="flex flex-col gap-4 text-sm">
            <p className="m-0">
              Reply to{' '}
              <a className="font-semibold underline" href={`mailto:${open.email}`}>
                {open.email}
              </a>
            </p>
            {/* Shown as text: React escapes it, so markup in a visitor's message is never run. */}
            <p className="m-0 whitespace-pre-line rounded-lg bg-surface-container-low p-4 text-on-surface">{open.message}</p>
            {open.handledAt && (
              <p className="m-0 text-on-surface-variant">
                Handled {when(open.handledAt)}
                {open.handledBy ? ` by ${open.handledBy}` : ''}.
              </p>
            )}
          </div>
        )}
      </Dialog>
    </div>
  );
}
