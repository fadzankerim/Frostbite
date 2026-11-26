// Tema: 'light' | 'dark' izabrana prekidačem, inače prati sistem.
// Jedini podatak koji frontend čuva u pregledaču (vidi SKILL.md, sigurnost 1) - nije lični podatak.
import { useSyncExternalStore } from 'react';

export type Theme = 'light' | 'dark';
const KEY = 'fb-theme';
const media = () => window.matchMedia('(prefers-color-scheme: dark)');
const listeners = new Set<() => void>();

function stored(): Theme | null {
  try {
    const v = localStorage.getItem(KEY);
    return v === 'light' || v === 'dark' ? v : null;
  } catch {
    return null;
  }
}

export function currentTheme(): Theme {
  const attr = document.documentElement.getAttribute('data-theme');
  if (attr === 'light' || attr === 'dark') return attr;
  return stored() ?? (media().matches ? 'dark' : 'light');
}

export function setTheme(theme: Theme): void {
  document.documentElement.setAttribute('data-theme', theme);
  try {
    localStorage.setItem(KEY, theme);
  } catch {
    /* pohrana nije dostupna: tema važi do zatvaranja stranice */
  }
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  const m = media();
  m.addEventListener('change', listener);
  return () => {
    listeners.delete(listener);
    m.removeEventListener('change', listener);
  };
}

export function useTheme(): [Theme, (t: Theme) => void] {
  return [useSyncExternalStore(subscribe, currentTheme), setTheme];
}
