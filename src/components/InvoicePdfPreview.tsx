import React, { useCallback, useEffect, useState } from 'react';
import { ExternalLink, FileWarning, Loader2 } from 'lucide-react';
import * as api from '../api';
import Button from './ui/Button';

interface InvoicePdfPreviewProps {
  invoiceId: string;
  /** For the frame's accessible name, e.g. "FA-2026-0002". */
  label: string;
  /** Bump to fetch again, e.g. after the invoice was edited. */
  version?: number;
}

/**
 * The invoice PDF exactly as the server generates it, embedded (#127).
 *
 * It replaces a preview drawn in HTML, which drifted from the real document:
 * internal id instead of the number, an invented address, a wrong subtotal.
 * Fetched with the session token (an <iframe src> cannot send it) and shown
 * from an object URL. Some browsers, Chrome on Android among them, do not
 * display an embedded PDF, so "Open PDF" is always offered as well.
 */
export default function InvoicePdfPreview({ invoiceId, label, version = 0 }: InvoicePdfPreviewProps) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const retry = useCallback(() => setAttempt((a) => a + 1), []);

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    setUrl(null);
    setError(null);
    api.invoices
      .pdf(invoiceId, true)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Could not load the PDF.');
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [invoiceId, version, attempt]);

  return (
    <div className="flex h-full min-h-[60vh] flex-col overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest">
      <div className="flex items-center justify-between gap-3 border-b border-outline-variant px-4 py-2.5">
        <span className="font-mono text-[11px] font-medium uppercase tracking-[0.08em] text-on-surface-variant">
          Document sent to the client
        </span>
        {url && (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded text-xs font-semibold text-on-surface-variant hover:text-on-surface"
          >
            Open PDF <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
          </a>
        )}
      </div>
      <div className="relative flex-1 bg-surface-container">
        {/* #view=FitH asks the browser's viewer to fit the page to the frame's width. */}
        {url && <iframe src={`${url}#view=FitH`} title={`Invoice ${label} PDF`} className="absolute inset-0 h-full w-full" />}
        {!url && !error && (
          <p role="status" className="flex h-full items-center justify-center gap-2 text-sm text-on-surface-variant">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Loading the PDF…
          </p>
        )}
        {error && (
          <div role="alert" className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
            <FileWarning className="h-6 w-6 text-error" aria-hidden="true" />
            <p className="text-sm font-semibold text-on-surface">The PDF could not be generated.</p>
            <p className="max-w-sm text-sm text-on-surface-variant">{error}</p>
            <Button variant="secondary" size="sm" onClick={retry}>
              Retry
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
