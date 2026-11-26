// Sigurno preusmjeravanje nakon prijave (zaštita od open redirect napada).
// Dozvoljene su samo relativne putanje unutar aplikacije: "/profil", "/ture?x=1".
// Odbija se: "//zlo.example", "/\\zlo.example", "https://...", "javascript:...", kontrolni znakovi.

const PROBE_ORIGIN = 'https://frostbite.invalid';

export function safeNext(raw: string | null | undefined, fallback = '/'): string {
  if (!raw || raw.length > 2000) return fallback;
  if (!raw.startsWith('/') || raw.startsWith('//') || raw.includes('\\')) return fallback;
  // eslint-disable-next-line no-control-regex
  if (/[\u0000-\u001f\u007f]/.test(raw)) return fallback;
  try {
    const url = new URL(raw, PROBE_ORIGIN);
    if (url.origin !== PROBE_ORIGIN) return fallback;
    return url.pathname + url.search + url.hash;
  } catch {
    return fallback;
  }
}
