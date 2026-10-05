import React, { useEffect, useSyncExternalStore } from 'react';

/**
 * Light / dark theme for the app (#80).
 *
 * The preference is per browser: 'system' (default) follows the OS setting
 * and keeps following it when it changes; 'light' and 'dark' pin it. It is
 * read synchronously on first render, so the first paint already has the
 * right theme.
 *
 * The public site (homepage, contact) keeps its fixed ink/paper composition
 * and is not wrapped in <ThemeScope>.
 */
export type ThemePreference = 'system' | 'light' | 'dark';

const STORAGE_KEY = 'dixpertia_theme';
// The old toggle stored a boolean under this key but never had any effect.
const LEGACY_KEY = 'dixpertia_darkmode';
const MEDIA = '(prefers-color-scheme: dark)';

const listeners = new Set<() => void>();

function readPreference(): ThemePreference {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'light' || saved === 'dark' || saved === 'system') return saved;
  } catch {
    // Storage unavailable (private mode, blocked site data): use the default.
  }
  return 'system';
}

let preference = readPreference();

try {
  localStorage.removeItem(LEGACY_KEY);
} catch {
  // Nothing to clean up if storage is unavailable.
}

function notify() {
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  const media = window.matchMedia(MEDIA);
  media.addEventListener('change', listener);
  return () => {
    listeners.delete(listener);
    media.removeEventListener('change', listener);
  };
}

export function setThemePreference(next: ThemePreference) {
  preference = next;
  try {
    localStorage.setItem(STORAGE_KEY, next);
  } catch {
    // The choice still applies for this session.
  }
  notify();
}

export function useThemePreference(): ThemePreference {
  return useSyncExternalStore(subscribe, () => preference);
}

export function useIsDark(): boolean {
  return useSyncExternalStore(subscribe, () =>
    preference === 'dark' || (preference === 'system' && window.matchMedia(MEDIA).matches)
  );
}

/**
 * Applies the theme to its children. `display: contents` keeps it out of the
 * layout; custom properties still inherit through it. Also paints the page
 * background behind the app, so overscroll does not flash the light ground.
 */
export function ThemeScope({ children }: { children: React.ReactNode }) {
  const dark = useIsDark();

  useEffect(() => {
    document.body.style.backgroundColor = dark ? 'var(--color-ink)' : '';
    return () => {
      document.body.style.backgroundColor = '';
    };
  }, [dark]);

  return (
    <div className={dark ? 'dark' : undefined} style={{ display: 'contents' }}>
      {children}
    </div>
  );
}
