// Pomoćne funkcije za bedževe (čiste, testirane u lib.test.ts).
import type { BadgeRole, MyBadge } from '../api/badges';

export const ROLE_ORDER: BadgeRole[] = ['PLANINAR', 'VODIC', 'ADMIN_DRUSTVA', 'SISTEM'];
export const ROLE_TITLES: Record<BadgeRole, string> = {
  PLANINAR: 'Planinar', VODIC: 'Vodič', ADMIN_DRUSTVA: 'Admin društva', SISTEM: 'Sistemski admin',
};
export const TIER_LABELS: Record<number, string> = { 1: 'Bronza', 2: 'Srebro', 3: 'Zlato' };

/** Obris bedža po nivou: 1 krug (null), 2 šestougao, 3 rozeta. Tačke kao SVG "points". */
export function tierPoints(tier: number, cx: number, cy: number, r: number): string | null {
  if (tier <= 1) return null;
  const pts: string[] = [];
  const n = tier === 2 ? 6 : 24;
  for (let i = 0; i < n; i++) {
    const a = (Math.PI * 2 * i) / n - Math.PI / 2;
    const rr = tier === 2 ? r : (i % 2 ? r * 0.88 : r);
    pts.push(`${(cx + rr * Math.cos(a)).toFixed(2)},${(cy + rr * Math.sin(a)).toFixed(2)}`);
  }
  return pts.join(' ');
}

/** Bedževi grupisani po ulozi, redoslijedom ROLE_ORDER; prazne grupe se izostavljaju. */
export function groupByRole<T extends { role: BadgeRole }>(badges: T[]): { role: BadgeRole; badges: T[] }[] {
  return ROLE_ORDER.map((role) => ({ role, badges: badges.filter((b) => b.role === role) }))
    .filter((g) => g.badges.length > 0);
}

/** Osvojeni a neviđeni bedževi (za modal "novi bedž"). */
export function unseen(badges: MyBadge[] | undefined): MyBadge[] {
  return (badges ?? []).filter((b) => b.earned && !b.seen);
}

/** Udio napretka 0..1 (zaštićeno od dijeljenja nulom i vrijednosti van opsega). */
export function progressRatio(progress: number, goal: number): number {
  if (!(goal > 0)) return 0;
  return Math.min(1, Math.max(0, progress / goal));
}
