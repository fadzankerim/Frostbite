// Formatiranje za prikaz. Vrijeme se uvijek prikazuje u vremenskoj zoni aplikacije.
// Nazivi dana i mjeseci i decimalni zarez su ovdje, a ne iz Intl locale podataka: mnogi pregledači
// nemaju podatke za bosanski (bs-BA) i tiho prelaze na engleski. Intl se koristi samo za vremensku zonu.
const TZ = 'Europe/Sarajevo';
const DAYS = ['nedjelja', 'ponedjeljak', 'utorak', 'srijeda', 'četvrtak', 'petak', 'subota'];
const DAYS_SHORT = ['ned', 'pon', 'uto', 'sri', 'čet', 'pet', 'sub'];
const MONTHS_SHORT = ['jan', 'feb', 'mar', 'apr', 'maj', 'jun', 'jul', 'avg', 'sep', 'okt', 'nov', 'dec'];
const WEEKDAY_EN = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

const partsFmt = new Intl.DateTimeFormat('en-US', {
  timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  weekday: 'short', hourCycle: 'h23',
});

type Parts = { y: string; m: number; d: string; hh: string; mm: string; wd: number };

function parts(iso: string): Parts {
  const p = Object.fromEntries(partsFmt.formatToParts(new Date(iso)).map((x) => [x.type, x.value]));
  return {
    y: p.year ?? '', m: Number(p.month), d: p.day ?? '', hh: p.hour ?? '', mm: p.minute ?? '',
    wd: Math.max(0, WEEKDAY_EN.indexOf(p.weekday ?? '')),
  };
}

const pad2 = (n: number) => String(n).padStart(2, '0');

/** "sri, 02.12. · 08:00" */
export function formatDateTime(iso: string): string {
  const p = parts(iso);
  return `${DAYS_SHORT[p.wd]}, ${p.d}.${pad2(p.m)}. · ${p.hh}:${p.mm}`;
}

/** "srijeda, 02.12.2026. u 08:00" */
export function formatLong(iso: string): string {
  const p = parts(iso);
  return `${DAYS[p.wd]}, ${p.d}.${pad2(p.m)}.${p.y}. u ${p.hh}:${p.mm}`;
}

/** "02.12.2026." */
export function formatDate(iso: string): string {
  const p = parts(iso);
  return `${p.d}.${pad2(p.m)}.${p.y}.`;
}

export const formatDay = (iso: string) => parts(iso).d;
export const formatMonth = (iso: string) => MONTHS_SHORT[parts(iso).m - 1] ?? '';

/** Broj sa decimalnim zarezom i razmakom za hiljade: 1234.5 -> "1 234,5". */
export function formatNumber(n: number, decimals?: number): string {
  const fixed = decimals === undefined ? String(Math.round(n * 10) / 10) : n.toFixed(decimals);
  const [int = '', frac] = fixed.replace('-', '').split('.');
  const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, '\u00a0');
  return `${n < 0 ? '−' : ''}${grouped}${frac ? `,${frac}` : ''}`;
}

export const formatPrice = (n: number) => (n > 0 ? `${formatNumber(n, 2)} KM` : 'Besplatno');

/** "4d 12h" / "3h 20min" do polaska; null ako je prošlo. */
export function countdown(iso: string, now = Date.now()): string | null {
  const ms = new Date(iso).getTime() - now;
  if (!(ms > 0)) return null;
  const min = Math.floor(ms / 60_000);
  const d = Math.floor(min / 1440);
  const h = Math.floor((min % 1440) / 60);
  const m = min % 60;
  return d > 0 ? `${d}d ${h}h` : `${h}h ${m}min`;
}

/** 43.715500 -> 43°42'55.8"N */
export function toDms(value: number, pos: string, neg: string): string {
  const hemi = value >= 0 ? pos : neg;
  const v = Math.abs(value);
  const d = Math.floor(v);
  const m = Math.floor((v - d) * 60);
  const s = (v - d - m / 60) * 3600;
  return `${d}°${String(m).padStart(2, '0')}'${s.toFixed(1).padStart(4, '0')}"${hemi}`;
}

export function spotsText(free: number, max: number): string {
  return free > 0 ? `${free} slobodnih od ${max}` : 'Popunjeno · lista čekanja';
}

/** Samo validan email ide u mailto:, inače se prikazuje kao tekst. */
export function mailtoHref(email: string): string | null {
  return /^[^\s@<>"'()\\]+@[^\s@<>"'()\\]+\.[^\s@<>"'()\\]+$/.test(email) ? `mailto:${email}` : null;
}

/** tel: samo od cifara i vodećeg +. */
export function telHref(phone: string): string | null {
  const digits = phone.replace(/[\s\-/().]/g, '');
  return /^\+?\d{6,15}$/.test(digits) ? `tel:${digits}` : null;
}

/** Bosanska množina: 1 tura, 2 ture, 5 tura, 21 tura, 12 tura. */
export function plural(n: number, [one, few, many]: [string, string, string]): string {
  const m10 = n % 10;
  const m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
  return many;
}
