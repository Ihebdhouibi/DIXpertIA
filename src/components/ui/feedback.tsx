import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { AlertCircle, CheckCircle, Info, X } from 'lucide-react';
import { ThemeClass } from '../../theme';
import Button from './Button';
import Dialog from './Dialog';
import { useT } from '../../i18n';

/**
 * App-wide feedback (#106): one toast stack and one confirmation dialog,
 * replacing the per-view toast blocks and the browser's confirm().
 *
 *   const toast = useToast();      toast('Invoice downloaded.');
 *                                  toast('Network error.', 'error');
 *   const confirm = useConfirm();  if (await confirm({ title: 'Delete user?' })) ...
 */

// ---------------------------------------------------------------- Toasts ---

export type ToastTone = 'success' | 'error' | 'info';

interface ToastItem {
  id: number;
  message: string;
  tone: ToastTone;
}

const TOAST_STYLE: Record<ToastTone, { box: string; icon: React.ComponentType<{ className?: string }> }> = {
  success: { box: 'bg-success-container text-success border-success/25', icon: CheckCircle },
  error: { box: 'bg-error-container text-on-error-container border-error/25', icon: AlertCircle },
  info: { box: 'bg-info-container text-info border-info/25', icon: Info },
};

const TOAST_MS = 4000;

type ToastFn = (message: string, tone?: ToastTone) => void;
const ToastContext = createContext<ToastFn | null>(null);

export function useToast(): ToastFn {
  const toast = useContext(ToastContext);
  if (!toast) throw new Error('useToast must be used inside <FeedbackProvider>');
  return toast;
}

// ---------------------------------------------------------- Confirmation ---

export interface ConfirmOptions {
  title: string;
  message?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  /** 'danger' for destructive actions (red confirm button). */
  tone?: 'danger' | 'default';
}

type ConfirmFn = (options: ConfirmOptions) => Promise<boolean>;
const ConfirmContext = createContext<ConfirmFn | null>(null);

export function useConfirm(): ConfirmFn {
  const confirm = useContext(ConfirmContext);
  if (!confirm) throw new Error('useConfirm must be used inside <FeedbackProvider>');
  return confirm;
}

// -------------------------------------------------------------- Provider ---

export function FeedbackProvider({ children }: { children: React.ReactNode }) {
  const t = useT();
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(1);
  const toastRegionRef = useRef<HTMLDivElement>(null);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback<ToastFn>(
    (message, tone = 'success') => {
      const id = nextId.current++;
      setToasts((current) => [...current, { id, message, tone }]);
      window.setTimeout(() => dismiss(id), TOAST_MS);
    },
    [dismiss]
  );

  const [pending, setPending] = useState<(ConfirmOptions & { resolve: (ok: boolean) => void }) | null>(null);

  const confirm = useCallback<ConfirmFn>(
    (options) => new Promise<boolean>((resolve) => setPending({ ...options, resolve })),
    []
  );

  const settle = (ok: boolean) => {
    pending?.resolve(ok);
    setPending(null);
  };
  // Keep the toast region in the browser's top layer, above any <dialog>
  // opened with showModal() (#251). showModal() pushes the dialog onto the
  // top layer; we re-show the popover on every dialog open so the toasts
  // render above the dialog and its backdrop.
  useEffect(() => {
    const el = toastRegionRef.current;
    if (!el) return;

    const show = () => {
      try {
        if (!el.matches(':popover-open')) el.showPopover();
      } catch {
        /* popover unsupported: fall back to the z-[200] stacking */
      }
    };

    const restack = () => {
      try {
        if (el.matches(':popover-open')) el.hidePopover();
        el.showPopover();
      } catch {
        /* no-op on browsers without the Popover API */
      }
    };

    show();

    const observer = new MutationObserver((records) => {
      for (const record of records) {
        if (
          record.type === 'attributes' &&
          record.attributeName === 'open' &&
          record.target instanceof HTMLDialogElement &&
          record.target.open
        ) {
          restack();
        }
      }
    });

    observer.observe(document.body, {
      subtree: true,
      attributes: true,
      attributeFilter: ['open'],
    });

    return () => observer.disconnect();
  }, []);


  return (
    <ToastContext.Provider value={toast}>
      <ConfirmContext.Provider value={confirm}>
        {children}
        <ThemeClass>
          <Dialog
            open={pending !== null}
            onClose={() => settle(false)}
            title={pending?.title ?? ''}
            description={pending?.message}
            size="sm"
            footer={
              <>
                <Button variant="secondary" onClick={() => settle(false)}>
                  {pending?.cancelLabel ?? t('common.cancel')}
                </Button>
                <Button variant={pending?.tone === 'danger' ? 'danger' : 'primary'} onClick={() => settle(true)}>
                  {pending?.confirmLabel ?? t('common.confirm')}
                </Button>
              </>
            }
          />
          <div
            ref={toastRegionRef}
            popover="manual"
            className="
              pointer-events-none fixed bottom-4 right-4 top-auto left-auto
              z-[200] m-0 border-0 p-0 bg-transparent overflow-visible
              flex w-[min(24rem,calc(100%-2rem))] flex-col gap-2
            "
            aria-live="polite"
          >
            {toasts.map(({ id, message, tone }) => {
              const { box, icon: Icon } = TOAST_STYLE[tone];
              return (
                <div
                  key={id}
                  role={tone === 'error' ? 'alert' : 'status'}
                  className={`pointer-events-auto flex items-start gap-3 rounded-xl border px-4 py-3 text-sm font-semibold shadow-lg animate-fade-in ${box}`}
                >
                  <Icon className="w-5 h-5 shrink-0" aria-hidden="true" />
                  <span className="flex-1">{message}</span>
                  <button
                    type="button"
                    onClick={() => dismiss(id)}
                    aria-label={t('common.dismissNotification')}
                    className="-m-1 rounded p-1 opacity-70 hover:opacity-100 cursor-pointer"
                  >
                    <X className="w-4 h-4" aria-hidden="true" />
                  </button>
                </div>
              );
            })}
          </div>
        </ThemeClass>
      </ConfirmContext.Provider>
    </ToastContext.Provider>
  );
}
