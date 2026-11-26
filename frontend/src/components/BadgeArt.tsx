// Crtani bedž iz koda (SVG, pune boje, obris --fun-ink, bez gradijenata).
// Oblik po nivou: bronza krug, srebro šestougao, zlato rozeta. Boja unutrašnjeg kruga po ulozi.
// Neosvojen bedž je siv. Ukrasna slika (aria-hidden): naziv i opis nosi tekst pored.
import type { BadgeRole } from '../api/badges';
import { tierPoints } from '../lib/badges';
import './badges.css';

const ICONS: Record<string, string[]> = {
  peak: ['M20 40 L29 26 L33 32 L37 27 L44 40 Z', 'M26.6 29.7 L29 26 L31.4 29.7'],
  boot: ['M25 22 H32 V32 L40 35 Q43 36 43 39 V41 H25 Z', 'M28 26 H32 M28 29 H32'],
  backpack: ['M23 28 Q23 21 32 21 Q41 21 41 28 V41 H23 Z', 'M27 33 H37 V38 H27 Z', 'M29 21 V19 H35 V21'],
  altitude: ['M21 41 L29 31 L34 35 L42 24', 'M37 24 H42 V29'],
  compass: ['M32 22 A10 10 0 1 1 31.99 22', 'M32 25 L35 32 L32 39 L29 32 Z'],
  people: ['M27 23.5 A3.5 3.5 0 1 1 26.99 23.5', 'M37 23.5 A3.5 3.5 0 1 1 36.99 23.5',
    'M21 41 Q21 33 27 33 Q33 33 33 41', 'M31 41 Q31 33 37 33 Q43 33 43 41'],
  flag: ['M25 20 V43', 'M25 21 H40 L36 26 L40 31 H25'],
  book: ['M21 24 Q26 22 32 25 Q38 22 43 24 V40 Q38 38 32 41 Q26 38 21 40 Z', 'M32 25 V41'],
  house: ['M21 31 L32 22 L43 31', 'M24 29 V41 H40 V29', 'M30 41 V35 H34 V41'],
  megaphone: ['M21 29 V35 H25 L37 41 V23 L25 29 Z', 'M40 28 Q43 32 40 36'],
  tent: ['M20 41 L32 22 L44 41 Z', 'M28 41 L32 33 L36 41'],
  shield: ['M32 21 L42 25 V32 Q42 39 32 43 Q22 39 22 32 V25 Z', 'M27 32 L31 36 L37 29'],
  eye: ['M20 32 Q32 20 44 32 Q32 44 20 32 Z', 'M32 28 A4 4 0 1 1 31.99 28'],
};

const ROLE_CLASS: Record<BadgeRole, string> = {
  PLANINAR: 'ba-hiker', VODIC: 'ba-guide', ADMIN_DRUSTVA: 'ba-club', SISTEM: 'ba-system',
};

type Props = { icon: string; tier: number; role: BadgeRole; locked?: boolean; size?: number; className?: string };

export function BadgeArt({ icon, tier, role, locked = false, size = 72, className }: Props) {
  const outline = tierPoints(tier, 32, 29, 24);
  const paths = ICONS[icon] ?? ICONS.peak!;
  const cls = ['badge-art', `ba-tier-${Math.min(3, Math.max(1, tier))}`, ROLE_CLASS[role], locked ? 'is-locked' : '', className ?? '']
    .filter(Boolean).join(' ');
  return (
    <svg className={cls} width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" focusable="false">
      <path className="ba-ribbon ba-stroke" d="M23 44 L18 60 L24 57 L27 62 L31 48 Z" />
      <path className="ba-ribbon ba-stroke" d="M41 44 L46 60 L40 57 L37 62 L33 48 Z" />
      {outline
        ? <polygon className="ba-rim ba-stroke" points={outline} strokeLinejoin="round" />
        : <circle className="ba-rim ba-stroke" cx="32" cy="29" r="24" />}
      <circle className="ba-disc ba-stroke" cx="32" cy="29" r="16" />
      <g className="ba-icon" transform="translate(0 -3)">
        {paths.map((d) => <path key={d} d={d} />)}
      </g>
      {!locked && <path className="ba-shine" d="M20 20 Q24 14 31 13" />}
    </svg>
  );
}
