import { describe, expect, it } from 'vitest';

import { passwordStrength } from './passwordStrength';
import { safeNext } from './safeNext';
import { formatClock, secondsLeft } from './session';

describe('safeNext (open redirect)', () => {
  it.each(['/profil', '/ture?x=1', '/a/b#c'])('dozvoljava %s', (p) => {
    expect(safeNext(p)).toBe(p);
  });

  it.each([
    // eslint-disable-next-line no-script-url, no-restricted-syntax -- test namjerno provjerava odbijanje
    'https://zlo.example/', '//zlo.example', '/\\zlo.example', '\\\\zlo.example', 'javascript:alert(1)',
    'zlo.example', '/\nzlo', '/\tx', '', null, undefined, ' /profil', 'http:/zlo.example', '/'.padEnd(3000, 'a'),
  ])('odbija %s', (p) => {
    expect(safeNext(p as string, '/fallback')).toBe('/fallback');
  });

  it('normalizuje putanju', () => {
    expect(safeNext('/a/../profil')).toBe('/profil');
  });
});

describe('passwordStrength', () => {
  it('kratka lozinka je 0', () => expect(passwordStrength('Kratka1!')).toBe(0));
  it('duga ali jednolična je slaba', () => expect(passwordStrength('aaaaaaaaaaaa')).toBe(1));
  it('raznolika i duga je odlična', () => expect(passwordStrength('Snijeg-Na-Bjelasnici-42')).toBe(4));
});

describe('session', () => {
  it('broji unazad od 30 minuta', () => {
    expect(secondsLeft(1_000, 1_000)).toBe(1800);
    expect(secondsLeft(61_000, 1_000)).toBe(1740);
    expect(secondsLeft(10_000_000, 0)).toBe(0);
  });
  it('formatira sat', () => {
    expect(formatClock(1800)).toBe('30:00');
    expect(formatClock(65)).toBe('01:05');
  });
});

describe('format', async () => {
  const { plural, toDms, countdown, mailtoHref, telHref, formatPrice } = await import('./format');
  it('množina', () => {
    expect([1, 2, 5, 11, 12, 21, 22, 25, 111].map((n) => plural(n, ['tura', 'ture', 'tura!']))).toEqual(
      ['tura', 'ture', 'tura!', 'tura!', 'tura!', 'tura', 'ture', 'tura!', 'tura!']);
  });
  it('DMS', () => expect(toDms(43.7155, 'N', 'S')).toBe('43°42\'55.8"N'));
  it('odbrojavanje', () => {
    expect(countdown(new Date(1_000 + 90 * 60_000).toISOString(), 1_000)).toBe('1h 30min');
    expect(countdown(new Date(0).toISOString(), 1_000)).toBeNull();
  });
  it('mailto/tel samo za ispravne vrijednosti', () => {
    expect(mailtoHref('info@pd.ba')).toBe('mailto:info@pd.ba');
    expect(mailtoHref('x@y.ba?bcc=svi@zlo.example')).toBeNull();   // ubacivanje dodatnih primalaca
    // eslint-disable-next-line no-script-url, no-restricted-syntax -- test namjerno provjerava odbijanje
    expect(mailtoHref('javascript:alert(1)//@x.y')).toBeNull();
    expect(telHref('+387 61 123-456')).toBe('tel:+38761123456');
    expect(telHref('061; DROP')).toBeNull();
  });
  it('cijena', () => {
    expect(formatPrice(0)).toBe('Besplatno');
    expect(formatPrice(10)).toBe('10,00 KM');
  });
  it('datumi na bosanskom, u zoni Europe/Sarajevo', async () => {
    const { formatDateTime, formatLong, formatMonth, formatDay, formatNumber } = await import('./format');
    const iso = '2026-12-02T07:00:00Z';                       // 08:00 u Sarajevu (zimsko vrijeme)
    expect(formatDateTime(iso)).toBe('sri, 02.12. · 08:00');
    expect(formatLong(iso)).toBe('srijeda, 02.12.2026. u 08:00');
    expect(formatMonth(iso)).toBe('dec');
    expect(formatDay('2026-12-31T23:30:00Z')).toBe('01');      // već je 1. januar u Sarajevu
    expect(formatNumber(12.5)).toBe('12,5');
    expect(formatNumber(5600)).toBe('5\u00a0600');
  });
});

describe('filteri iz URL-a', async () => {
  const { cleanFilters } = await import('../api/public');
  it('propušta samo ispravne vrijednosti', () => {
    const p = new URLSearchParams({ q: '  Bjelašnica ', difficulty: 'LAKA', club: '3', date_from: '2026-12-01', status: 'NACRT' });
    expect(cleanFilters(p)).toEqual({ q: 'Bjelašnica', difficulty: 'LAKA', club: '3', date_from: '2026-12-01' });
    const bad = new URLSearchParams({ difficulty: '<script>', club: '1 OR 1=1', date_to: '01.12.2026' });
    expect(cleanFilters(bad)).toEqual({});
  });
});

describe('sličica rute', async () => {
  const { routeTracePath } = await import('../components/TourCard');
  it('ostaje unutar okvira', () => {
    const r = routeTracePath([[43.7, 18.2], [43.75, 18.3], [43.72, 18.25]]);
    expect(r).not.toBeNull();
    const nums = r!.d.match(/-?\d+(\.\d+)?/g)!.map(Number);
    expect(Math.min(...nums)).toBeGreaterThanOrEqual(0);
    expect(Math.max(...nums)).toBeLessThanOrEqual(120);
  });
  it('bez rute', () => expect(routeTracePath([])).toBeNull());
});

describe('ID iz URL-a', async () => {
  const { parseId } = await import('../api/public');
  it.each([['1', 1], ['42', 42], ['abc', null], ['0', null], ['-1', null], ['1.5', null], ['1e3', null], ['', null], [undefined, null], ['9999999999', null]])(
    '%s -> %s', (raw, out) => expect(parseId(raw as string | undefined)).toBe(out));
});

describe('panel admina: ruta i grafikon', async () => {
  const { reducePoints, MAX_POINTS } = await import('./route');
  const { niceScale } = await import('../components/ColumnChart');
  it('ruta se svodi na najviše 500 tačaka i zadržava krajeve', () => {
    const pts = Array.from({ length: 5000 }, (_, i) => [43 + i * 0.0001, 18 + Math.sin(i / 50) * 0.01] as [number, number]);
    const out = reducePoints(pts);
    expect(out.length).toBeLessThanOrEqual(MAX_POINTS);
    expect(out[0]).toEqual(pts[0]);
  });
  it('kratka ruta ostaje ista', () => {
    const pts: [number, number][] = [[43, 18], [43.1, 18.1], [43.2, 18]];
    expect(reducePoints(pts)).toEqual(pts);
  });
  it.each([[0, 4, 1], [7, 8, 2], [23, 30, 10], [180, 200, 50], [1234, 1500, 500]])('skala za %i -> max %i, korak %i', (v, max, step) => {
    expect(niceScale(v)).toEqual({ max, step });
  });
});

describe('početna stranica po ulozi', async () => {
  const { landingFor } = await import('../components/guards');
  it.each([
    [{ systemAdmin: true, clubAdmin: false, guide: false }, '/sistem'],
    [{ systemAdmin: false, clubAdmin: true, guide: true }, '/upravljanje'],
    [{ systemAdmin: false, clubAdmin: false, guide: true }, '/vodic'],
    [{ systemAdmin: false, clubAdmin: false, guide: false }, '/'],
  ])('%o -> %s', (roles, path) => expect(landingFor(roles)).toBe(path));
});
