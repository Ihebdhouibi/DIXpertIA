import { useEffect, useState } from 'react';
import { invoices as invoicesApi, type InvoiceHistoryEvent } from '../api';
import type { Invoice } from '../types';

/**
 * Everything that happened to an invoice, newest first (#115): created,
 * corrected, verified, sent, and each move through the books, with who did it
 * and when. Read from the audit trail (#63), the one record of what happened.
 */

const when = (iso: string) =>
  new Date(iso).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });

export default function InvoiceHistory({ invoice }: { invoice: Invoice }) {
  const [events, setEvents] = useState<InvoiceHistoryEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Reloaded when the invoice moves, so a decision taken in the dialog shows at once.
  useEffect(() => {
    let current = true;
    setError(null);
    invoicesApi
      .history(invoice.id)
      .then((rows) => current && setEvents(rows))
      .catch((err) => current && setError(err instanceof Error ? err.message : 'Could not load the history.'));
    return () => {
      current = false;
    };
  }, [invoice.id, invoice.status, invoice.reviewStatus, invoice.processingStatus]);

  return (
    <section className="rounded-xl border border-outline-variant bg-surface-container-lowest p-5" aria-busy={events === null && !error}>
      <h3 className="mb-4 text-sm font-semibold text-on-surface">History</h3>
      {error ? (
        <p role="alert" className="text-sm text-danger">{error}</p>
      ) : events === null ? (
        <p className="text-sm text-on-surface-variant">Loading the history...</p>
      ) : events.length === 0 ? (
        <p className="text-sm text-on-surface-variant">Nothing recorded yet. Steps are recorded since the audit trail was introduced.</p>
      ) : (
        <ol className="flex flex-col gap-3 border-l border-outline-variant pl-4">
          {events.map((e) => (
            <li key={e.id} className="text-sm">
              <p className="font-semibold text-on-surface">{e.label}</p>
              <p className="font-mono text-[11px] text-on-surface-variant">
                {when(e.occurredAt)} · {e.actorName}
                {e.actorRole ? ` (${e.actorRole})` : ''}
              </p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
