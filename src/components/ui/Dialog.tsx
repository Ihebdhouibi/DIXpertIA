import React, { useEffect, useId, useRef } from 'react';
import { X } from 'lucide-react';
import Button from './Button';

/**
 * Modal dialog (#106), built on the native <dialog> element.
 *
 * showModal() gives most of the behaviour a modal needs: focus moves into the
 * dialog, the page behind becomes inert, Escape closes it, and focus returns
 * to the element that opened it. This component adds the theme, a title wired
 * to aria-labelledby, scrim click to close, a scroll lock on the page, and Tab
 * wrapping - natively, Tab past the last control leaves for the browser UI.
 */

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), ' +
  'textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
export type DialogSize = 'sm' | 'md' | 'lg' | 'xl' | 'full';

const SIZES: Record<DialogSize, string> = {
  sm: 'max-w-sm',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
  full: 'max-w-6xl',
};

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  size?: DialogSize;
  /** Extra controls in the header, before the close button (e.g. a status, a download). */
  headerActions?: React.ReactNode;
  /** Actions row under a hairline, usually Buttons aligned right. */
  footer?: React.ReactNode;
  /** Set when the body manages its own scrolling or padding (e.g. a calendar). */
  bodyClassName?: string;
  children?: React.ReactNode;
}

export default function Dialog({
  open,
  onClose,
  title,
  description,
  size = 'md',
  headerActions,
  footer,
  bodyClassName = 'px-6 py-5 overflow-y-auto',
  children,
}: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  // A confirmation has only a title, a message and buttons: no body, and then
  // no rule under the header, or it would sit right on the footer's rule.
  const hasBody = children !== undefined && children !== null && children !== false;
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  // Keep the page from scrolling behind an open dialog.
  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      aria-describedby={description ? descriptionId : undefined}
      // Escape: let the parent decide, so its `open` state stays the source of truth.
      // React propagates `cancel` up the component tree, so a nested dialog's
      // Escape would also close its parent: only act on this dialog's own event.
      onCancel={(e) => {
        if (e.target !== e.currentTarget) return;
        e.preventDefault();
        onClose();
      }}
      onKeyDown={(e) => {
        if (e.key !== 'Tab') return;
        const dialog = e.currentTarget;
        // Only the innermost open dialog handles Tab.
        if ((e.target as HTMLElement).closest('dialog') !== dialog) return;
        const items = Array.from(dialog.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
          (el) => el.closest('dialog') === dialog && el.offsetParent !== null
        );
        if (items.length === 0) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }}
      // A click on the dialog element itself is a click on the scrim around the panel.
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      className={`m-auto w-[calc(100%-2rem)] ${SIZES[size]} max-h-[90vh] p-0 bg-transparent text-on-surface backdrop:bg-ink/60 backdrop:backdrop-blur-sm`}
    >
      {open && (
        <div className="flex max-h-[90vh] flex-col overflow-hidden rounded-2xl border border-outline-variant bg-surface-container-lowest shadow-xl animate-scale-up">
          <header className={`flex items-start justify-between gap-4 px-6 py-4 ${hasBody ? 'border-b border-outline-variant' : ''}`}>
            <div>
              <h2 id={titleId} className="text-lg font-bold tracking-[-0.02em]">
                {title}
              </h2>
              {description && (
                <p id={descriptionId} className="mt-1 text-sm text-on-surface-variant">
                  {description}
                </p>
              )}
            </div>
            <div className="-mr-2 flex shrink-0 items-center gap-2">
              {headerActions}
              <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close" className="px-2">
                <X className="w-5 h-5" aria-hidden="true" />
              </Button>
            </div>
          </header>
          {hasBody && <div className={`flex-1 min-h-0 ${bodyClassName}`}>{children}</div>}
          {footer && (
            <footer className="flex flex-wrap justify-end gap-3 border-t border-outline-variant px-6 py-4">{footer}</footer>
          )}
        </div>
      )}
    </dialog>
  );
}
