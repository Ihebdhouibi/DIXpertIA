import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ExternalLink, FileWarning, Loader2 } from 'lucide-react';
import type { PDFDocumentProxy, RenderTask } from 'pdfjs-dist';
import * as api from '../api';
import Button from './ui/Button';
import { useT } from '../i18n';

interface InvoicePdfPreviewProps {
  invoiceId: string;
  /** For the pages' accessible names, e.g. "FA-2026-0002". */
  label: string;
  /** Bump to fetch again, e.g. after the invoice was edited. */
  version?: number;
}

/** pdf.js, loaded the first time an invoice is previewed, not with the app. */
async function loadPdfJs() {
  const [pdfjs, worker] = await Promise.all([
    import('pdfjs-dist'),
    import('pdfjs-dist/build/pdf.worker.min.mjs?url'),
  ]);
  pdfjs.GlobalWorkerOptions.workerSrc = worker.default;
  return pdfjs;
}

/**
 * The invoice PDF exactly as the server generates it (#127), drawn by pdf.js
 * (#139).
 *
 * The browser's own viewer in an <iframe> opened zoomed and cropped in Edge
 * when it sat in a modal <dialog>, intermittently and whatever the delay, and
 * Chrome on Android shows no embedded PDF at all. Drawing each page into a
 * canvas sized to the frame gives the same preview everywhere. "Open PDF"
 * still opens the file itself, for zoom, search, print or copy.
 */
export default function InvoicePdfPreview({ invoiceId, label, version = 0 }: InvoicePdfPreviewProps) {
  const t = useT();
  const [url, setUrl] = useState<string | null>(null);
  const [pageCount, setPageCount] = useState(0);
  const [rendered, setRendered] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const retry = useCallback(() => setAttempt((a) => a + 1), []);

  const frameRef = useRef<HTMLDivElement>(null);
  const canvasRefs = useRef<(HTMLCanvasElement | null)[]>([]);
  const docRef = useRef<PDFDocumentProxy | null>(null);
  const tasksRef = useRef<RenderTask[]>([]);

  // Fetch the file, keep an object URL for "Open PDF", and parse it.
  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    setUrl(null);
    setPageCount(0);
    setRendered(false);
    setError(null);
    (async () => {
      try {
        const blob = await api.invoices.pdf(invoiceId, true);
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
        const pdfjs = await loadPdfJs();
        // Our own server's PDF, but no reason to let a document run code.
        const doc = await pdfjs.getDocument({ data: await blob.arrayBuffer(), isEvalSupported: false }).promise;
        if (cancelled) {
          void doc.destroy();
          return;
        }
        docRef.current = doc;
        setPageCount(doc.numPages);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : t('invoices.pdf.couldNotLoad'));
      }
    })();
    return () => {
      cancelled = true;
      tasksRef.current.forEach((t) => t.cancel());
      tasksRef.current = [];
      void docRef.current?.destroy();
      docRef.current = null;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [invoiceId, version, attempt]);

  // Draw every page at the frame's width, and again when that width changes.
  useEffect(() => {
    const frame = frameRef.current;
    if (!pageCount || !frame) return;
    let generation = 0;

    const draw = async () => {
      const doc = docRef.current;
      if (!doc) return;
      const mine = ++generation;
      tasksRef.current.forEach((t) => t.cancel());
      tasksRef.current = [];
      // The frame's inner width, minus the padding around the pages.
      const width = Math.max(frame.clientWidth - 32, 200);
      const ratio = window.devicePixelRatio || 1;
      try {
        for (let n = 1; n <= doc.numPages; n++) {
          const page = await doc.getPage(n);
          const canvas = canvasRefs.current[n - 1];
          if (mine !== generation || !canvas) return;
          const viewport = page.getViewport({ scale: width / page.getViewport({ scale: 1 }).width });
          canvas.width = Math.floor(viewport.width * ratio);
          canvas.height = Math.floor(viewport.height * ratio);
          canvas.style.width = `${Math.floor(viewport.width)}px`;
          canvas.style.height = `${Math.floor(viewport.height)}px`;
          const task = page.render({
            canvas,
            viewport,
            transform: ratio === 1 ? undefined : [ratio, 0, 0, ratio, 0, 0],
          });
          tasksRef.current.push(task);
          await task.promise;
        }
        if (mine === generation) setRendered(true);
      } catch (err) {
        // A redraw cancels the previous one; only a real failure is shown.
        if ((err as { name?: string })?.name !== 'RenderingCancelledException') {
          setError(err instanceof Error ? err.message : t('invoices.pdf.couldNotDraw'));
        }
      }
    };

    let lastWidth = 0;
    let frameRequest = 0;
    const observer = new ResizeObserver(([entry]) => {
      const width = Math.round(entry.contentRect.width);
      if (width === lastWidth || width === 0) return;
      lastWidth = width;
      cancelAnimationFrame(frameRequest);
      frameRequest = requestAnimationFrame(() => void draw());
    });
    observer.observe(frame);
    return () => {
      observer.disconnect();
      cancelAnimationFrame(frameRequest);
      generation++;
    };
  }, [pageCount]);

  const loading = !error && !rendered;

  return (
    <div className="flex h-full min-h-[60vh] flex-col overflow-hidden rounded-xl border border-outline-variant bg-surface-container-lowest">
      <div className="flex items-center justify-between gap-3 border-b border-outline-variant px-4 py-2.5">
        <span className="font-mono text-[11px] font-medium uppercase tracking-[0.08em] text-on-surface-variant">
          {t('invoices.pdf.heading')}
        </span>
        {url && (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded text-xs font-semibold text-on-surface-variant hover:text-on-surface"
          >
            {t('invoices.pdf.open')} <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
          </a>
        )}
      </div>
      <div ref={frameRef} className="relative flex-1 overflow-auto bg-surface-container">
        {pageCount > 0 && !error && (
          <div className={`flex flex-col items-center gap-4 p-4 ${rendered ? '' : 'invisible'}`} data-pdf-pages={pageCount}>
            {Array.from({ length: pageCount }, (_, i) => (
              <canvas
                key={i}
                ref={(el) => { canvasRefs.current[i] = el; }}
                role="img"
                aria-label={t('invoices.pdf.page', { ref: label, page: i + 1, count: pageCount })}
                className="shadow-md"
              />
            ))}
          </div>
        )}
        {loading && (
          <p role="status" className="absolute inset-0 flex items-center justify-center gap-2 text-sm text-on-surface-variant">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> {t('invoices.pdf.loading')}
          </p>
        )}
        {error && (
          <div role="alert" className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
            <FileWarning className="h-6 w-6 text-error" aria-hidden="true" />
            <p className="text-sm font-semibold text-on-surface">{t('invoices.pdf.failed')}</p>
            <p className="max-w-sm text-sm text-on-surface-variant">{error}</p>
            <Button variant="secondary" size="sm" onClick={retry}>
              {t('invoices.retry')}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
