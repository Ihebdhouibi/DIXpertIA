import { RefObject, useEffect } from 'react';

/**
 * Closes a popover (menu, dropdown) on Escape or on a pointer press outside
 * `ref` (#27). On Escape, focus goes back to `returnFocusTo`, usually the
 * button that opened it, so keyboard users are not stranded.
 */
export function useDismiss(
  ref: RefObject<HTMLElement | null>,
  open: boolean,
  onClose: () => void,
  returnFocusTo?: RefObject<HTMLElement | null>
) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return;
      onClose();
      returnFocusTo?.current?.focus();
    };
    const onPointer = (e: PointerEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('pointerdown', onPointer);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onPointer);
    };
  }, [open, onClose, ref, returnFocusTo]);
}
