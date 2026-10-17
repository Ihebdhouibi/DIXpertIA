import React, { useEffect, useRef, useState, useSyncExternalStore } from 'react';

/**
 * Motion helpers for the public homepage (#165). Small and in-house on
 * purpose: the page animates transform and opacity only, and needs no
 * animation library (design/homepage-v2/README.md, "Performance").
 */

const REDUCE = '(prefers-reduced-motion: reduce)';

function subscribeToReduce(onChange: () => void) {
  const media = window.matchMedia(REDUCE);
  media.addEventListener('change', onChange);
  return () => media.removeEventListener('change', onChange);
}

/** True when the visitor asked their system for less motion. Follows changes live. */
export function useReducedMotion(): boolean {
  return useSyncExternalStore(subscribeToReduce, () => window.matchMedia(REDUCE).matches, () => false);
}

/**
 * True once the element has been at least `threshold` visible, then stays
 * true: a reveal plays once. Without IntersectionObserver it is true at once,
 * so nothing stays hidden.
 */
export function useInView<T extends Element>(threshold = 0.12) {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el || inView) return;
    if (typeof IntersectionObserver === 'undefined') {
      setInView(true);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setInView(true);
          observer.disconnect();
        }
      },
      { threshold },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [threshold, inView]);

  return [ref, inView] as const;
}

type RevealProps<E extends React.ElementType> = {
  /** Position in its group: each step delays the entrance by 90ms. */
  index?: number;
  as?: E;
} & Omit<React.ComponentPropsWithoutRef<E>, 'as'>;

/**
 * Fades its content in and up 22px when it scrolls into view (.home-reveal in
 * src/index.css). Under reduced motion the CSS shows it at once.
 */
export function Reveal<E extends React.ElementType = 'div'>({ index = 0, as, className, style, ...rest }: RevealProps<E>) {
  const [ref, inView] = useInView<HTMLElement>();
  const Component = (as ?? 'div') as React.ElementType;
  return (
    <Component
      ref={ref}
      data-shown={inView ? '' : undefined}
      className={`home-reveal${className ? ` ${className}` : ''}`}
      style={{ ...style, '--reveal-index': index } as React.CSSProperties}
      {...rest}
    />
  );
}
