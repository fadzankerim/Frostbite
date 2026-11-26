// Praćenje aktivnosti sesije na klijentu. Server produžava sesiju pri svakom zahtjevu
// (SESSION_SAVE_EVERY_REQUEST) i briše je nakon 30 min neaktivnosti (SESSION_COOKIE_AGE).
// Klijent mjeri od trenutka kad je STIGAO odgovor, pa je njegov rok uvijek malo kasniji od
// serverskog: kad brojač dođe do nule, sesija na serveru je već istekla i provjera je ne produžava.

export const SESSION_SECONDS = 30 * 60;

let lastActivity = Date.now();
const listeners = new Set<() => void>();

export function markActivity(now = Date.now()): void {
  lastActivity = now;
  listeners.forEach((l) => l());
}

export function getLastActivity(): number {
  return lastActivity;
}

export function subscribeActivity(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Preostale sekunde sesije (nikad negativno). */
export function secondsLeft(now: number, last: number, total = SESSION_SECONDS): number {
  return Math.max(0, Math.ceil(total - (now - last) / 1000));
}

export function formatClock(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}
