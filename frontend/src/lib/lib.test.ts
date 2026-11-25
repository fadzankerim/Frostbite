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
