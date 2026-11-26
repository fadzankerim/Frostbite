// Čiste funkcije za rute (bez mape): pojednostavljenje i čitanje GPX-a.
// GPX se parsira kao XML (DOMParser) - ništa iz datoteke se ne izvršava; uzimaju se samo
// numeričke lat/lon vrijednosti u ispravnom opsegu.
import type { LatLng } from '../api/public';

export const MAX_POINTS = 500;
export const MAX_GPX_BYTES = 5 * 1024 * 1024;
export const valid = (lat: number, lng: number) =>
  Number.isFinite(lat) && Number.isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180;
export const round6 = (n: number) => Math.round(n * 1e6) / 1e6;

/** Douglas-Peucker pojednostavljenje (tolerancija u stepenima). */
function simplify(pts: LatLng[], tol: number): LatLng[] {
  if (pts.length < 3) return pts;
  const [a, b] = [pts[0]!, pts[pts.length - 1]!];
  let maxD = 0;
  let idx = 0;
  for (let i = 1; i < pts.length - 1; i++) {
    const p = pts[i]!;
    const dx = b[1] - a[1];
    const dy = b[0] - a[0];
    const len = Math.hypot(dx, dy) || 1e-12;
    const d = Math.abs(dy * (p[1] - a[1]) - dx * (p[0] - a[0])) / len;
    if (d > maxD) { maxD = d; idx = i; }
  }
  if (maxD <= tol) return [a, b];
  return [...simplify(pts.slice(0, idx + 1), tol).slice(0, -1), ...simplify(pts.slice(idx), tol)];
}

/** Svodi rutu na najviše MAX_POINTS tačaka uz rastuću toleranciju. */
export function reducePoints(pts: LatLng[]): LatLng[] {
  let out = pts;
  let tol = 0.00001;
  while (out.length > MAX_POINTS && tol < 1) { out = simplify(pts, tol); tol *= 2; }
  return out.slice(0, MAX_POINTS);
}

/** GPX tekst -> tačke (trkpt, pa rtept). Baca grešku sa porukom za korisnika. */
export function parseGpx(text: string): LatLng[] {
  const doc = new DOMParser().parseFromString(text, 'application/xml');
  if (doc.getElementsByTagName('parsererror').length) throw new Error('Datoteka nije ispravan GPX.');
  let nodes = Array.from(doc.getElementsByTagName('trkpt'));
  if (nodes.length < 2) nodes = Array.from(doc.getElementsByTagName('rtept'));
  const pts: LatLng[] = [];
  for (const n of nodes) {
    const lat = Number(n.getAttribute('lat'));
    const lng = Number(n.getAttribute('lon'));
    if (valid(lat, lng)) pts.push([round6(lat), round6(lng)]);
  }
  if (pts.length < 2) throw new Error('GPX ne sadrži trasu (trkpt ili rtept tačke).');
  return reducePoints(pts);
}

