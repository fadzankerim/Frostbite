// Generisana crtana ilustracija planina za kartice tura i društava.
// Ista za isti seed (ID), pa je kartica uvijek prepoznatljiva. Samo pune boje iz paleta
// (tokens.css: .scene-p0 ... .scene-p5), bez gradijenata i bez vanjskih slika. Ukrasna (aria-hidden).
import { memo, useMemo, type CSSProperties } from 'react';

import type { DifficultyCode } from '../api/public';
import { between, rng } from '../lib/rng';
import './scene.css';

const DEFAULT_W = 320;
const H = 160;
const PALETTES = 6;

type Pt = [number, number];
type Variant = 'tour' | 'club';

const HEIGHT: Record<DifficultyCode, number> = { LAKA: 0.5, SREDNJA: 0.65, TESKA: 0.8, VRLO_TESKA: 0.95 };

const f = (n: number) => n.toFixed(1);
const poly = (pts: Pt[]) => pts.map(([x, y]) => `${f(x)},${f(y)}`).join(' ');

/** Greben: naizmjenično vrhovi i doline od lijeve do desne ivice. */
function ridge(r: () => number, W: number, base: number, peaks: number, minH: number, maxH: number, jag: number): { pts: Pt[]; tops: number[] } {
  const pts: Pt[] = [[-10, base]];
  const tops: number[] = [];
  const step = (W + 20) / peaks;
  for (let i = 0; i < peaks; i++) {
    const x0 = -10 + i * step;
    pts.push([x0 + step * between(r, 0.15, 0.3), base - between(r, 0, jag)]);            // dolina
    tops.push(pts.length);
    pts.push([x0 + step * between(r, 0.4, 0.65), base - between(r, minH, maxH)]);        // vrh
  }
  pts.push([W + 10, base - between(r, 0, jag)]);
  return { pts, tops };
}

/** Snježna kapa: od vrha 30% niz obje padine, cik-cak donja ivica. */
function snowCap(peak: Pt, left: Pt, right: Pt, r: () => number): Pt[] {
  const t = between(r, 0.26, 0.36);
  const a: Pt = [peak[0] + (left[0] - peak[0]) * t, peak[1] + (left[1] - peak[1]) * t];
  const b: Pt = [peak[0] + (right[0] - peak[0]) * t, peak[1] + (right[1] - peak[1]) * t];
  const zig: Pt[] = [];
  const n = 3;
  for (let i = n - 1; i >= 1; i--) {
    const x = a[0] + ((b[0] - a[0]) * i) / n;
    const y = a[1] + ((b[1] - a[1]) * i) / n + (i % 2 ? 4 : -1);
    zig.push([x, y]);
  }
  return [peak, b, ...zig, a];
}

function hillsPath(pts: Pt[], W: number): string {
  let d = `M${f(pts[0]![0])},${f(pts[0]![1])}`;
  for (let i = 1; i < pts.length; i++) {
    const [px, py] = pts[i - 1]!;
    const [x, y] = pts[i]!;
    d += ` Q${f(px)},${f(py)} ${f((px + x) / 2)},${f((py + y) / 2)}`;
  }
  const last = pts[pts.length - 1]!;
  return `${d} L${f(last[0])},${f(last[1])} L${W + 10},${H + 10} L-10,${H + 10} Z`;
}

function yAt(pts: Pt[], x: number): number {
  for (let i = 1; i < pts.length; i++) {
    const [x0, y0] = pts[i - 1]!;
    const [x1, y1] = pts[i]!;
    if (x >= x0 && x <= x1) return y0 + ((y1 - y0) * (x - x0)) / (x1 - x0 || 1);
  }
  return pts[pts.length - 1]![1];
}

function build(seed: number, variant: Variant, difficulty: DifficultyCode | undefined, W: number) {
  const scale = W / DEFAULT_W;
  const r = rng(seed * 7 + (variant === 'club' ? 3 : 0));
  const palette = Math.abs(seed) % PALETTES;
  const k = difficulty ? HEIGHT[difficulty] : 0.62;

  const sun = { x: between(r, 36, W - 36), y: between(r, 26, 42), r: between(r, 11, 15) };
  const stars = Array.from({ length: Math.round(14 * scale) }, () => [between(r, 6, W - 6), between(r, 6, 70), between(r, 0.6, 1.4)] as const);
  const clouds = Array.from({ length: Math.max(2, Math.round(2 * scale)) }, (_, i) => ({ x: between(r, 20, W - 90), y: between(r, 18, 54), s: between(r, 0.7, 1.1), d: 26 + i * 9 }));
  const birds = Array.from({ length: 2 }, () => ({ x: between(r, 40, W - 40), y: between(r, 30, 60) }));

  const far = ridge(r, W, 112, Math.round(4 * scale), 26, 46, 10);
  const mid = ridge(r, W, 132, Math.round((difficulty === 'VRLO_TESKA' ? 4 : 3) * scale), 40 * k + 12, 78 * k + 14, 8);
  const caps = mid.tops.map((ti) => snowCap(mid.pts[ti]!, mid.pts[ti - 1]!, mid.pts[ti + 1]!, r));
  const highest = mid.tops.reduce((best, ti) => (mid.pts[ti]![1] < mid.pts[best]![1] ? ti : best), mid.tops[0]!);
  const summit = mid.pts[highest]!;

  const segs = Math.max(5, Math.round(5 * scale));
  const nearPts: Pt[] = Array.from({ length: segs + 1 }, (_, i) => [-10 + (i * (W + 20)) / segs, between(r, 136, 150)] as Pt);
  const trees = Array.from({ length: Math.round((5 + Math.floor(r() * 4)) * scale) }, () => {
    const x = between(r, 8, W - 8);
    return { x, y: yAt(nearPts, x) + 2, s: between(r, 0.7, 1.15) };
  }).sort((a, b) => a.y - b.y);

  // staza od podnožja do vrha (ture)
  const sx = Math.min(W - 20, Math.max(20, summit[0] + between(r, -60, -30)));
  const trail: Pt[] = [
    [sx, H + 2],
    [sx + 18, yAt(nearPts, sx + 18) - 2],
    [summit[0] - 26, summit[1] + (132 - summit[1]) * 0.7],
    [summit[0] + 10, summit[1] + (132 - summit[1]) * 0.42],
    [summit[0] - 4, summit[1] + 10],
    [summit[0], summit[1]],
  ];

  // planinarski dom (društva)
  const cabinX = between(r, 0.58, 0.8) * W;
  const cabin = { x: cabinX, y: yAt(nearPts, cabinX) - 2 };

  return { palette, sun, stars, clouds, birds, far, mid, caps, summit, nearPts, trees, trail, cabin };
}

type Props = {
  seed: number;
  variant?: Variant;
  difficulty?: DifficultyCode | undefined;
  className?: string;
  /** širina scene u jedinicama (visina je 160); šira scena = više vrhova, ne uvećanje */
  width?: number;
};

export const SceneArt = memo(function SceneArt({ seed, variant = 'tour', difficulty, className, width = DEFAULT_W }: Props) {
  const W = width;
  const s = useMemo(() => build(seed, variant, difficulty, width), [seed, variant, difficulty, width]);
  return (
    <svg
      className={`scene scene-p${s.palette} scene-${variant}${className ? ` ${className}` : ''}`}
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
      focusable="false"
    >
      <rect className="sc-sky" width={W} height={H} />
      <g className="sc-stars">
        {s.stars.map(([x, y, rad], i) => <circle key={i} cx={f(x)} cy={f(y)} r={f(rad)} style={{ animationDelay: `${(i % 5) * 0.6}s` }} />)}
      </g>

      <g className="sc-sun" transform={`translate(${f(s.sun.x)} ${f(s.sun.y)})`}>
        <g className="sc-rays">
          {Array.from({ length: 10 }, (_, i) => (
            <line key={i} x1="0" y1={f(-s.sun.r - 4)} x2="0" y2={f(-s.sun.r - 9)} transform={`rotate(${i * 36})`} />
          ))}
        </g>
        <circle className="sc-sun-body sc-stroke" r={f(s.sun.r)} />
        <circle className="sc-crater" cx={f(s.sun.r * 0.3)} cy={f(-s.sun.r * 0.2)} r={f(s.sun.r * 0.22)} />
        <circle className="sc-crater" cx={f(-s.sun.r * 0.35)} cy={f(s.sun.r * 0.3)} r={f(s.sun.r * 0.15)} />
      </g>

      {s.clouds.map((c, i) => (
        <g key={i} className="sc-cloud-move" style={{ animationDuration: `${c.d}s` } as CSSProperties}>
          <g transform={`translate(${f(c.x)} ${f(c.y)}) scale(${f(c.s)})`}>
            <path className="sc-cloud sc-stroke" d="M8 20 Q0 20 2 13 Q4 7 11 9 Q14 1 23 3 Q31 0 34 8 Q42 7 43 14 Q45 20 37 20 Z" />
          </g>
        </g>
      ))}

      {s.birds.map((b, i) => (
        <g key={i} transform={`translate(${f(b.x)} ${f(b.y)})`}>
          <path className="sc-bird" d="M-5 0 Q-2.5 -3 0 0 Q2.5 -3 5 0" style={{ animationDelay: `${i * 0.3}s` }} />
        </g>
      ))}

      <polygon className="sc-far" points={`${poly(s.far.pts)} ${W + 10},${H + 10} -10,${H + 10}`} />
      <g className="sc-mid-layer">
        <polygon className="sc-mid sc-stroke" points={`${poly(s.mid.pts)} ${W + 10},${H + 10} -10,${H + 10}`} />
        {s.caps.map((c, i) => <polygon key={i} className="sc-snow sc-stroke" points={poly(c)} />)}
      </g>

      {variant === 'tour' && (
        <>
          <path className="sc-trail" d={`M${s.trail.map(([x, y]) => `${f(x)},${f(y)}`).join(' L')}`} />
          <g className="sc-flag" transform={`translate(${f(s.summit[0])} ${f(s.summit[1])})`}>
            <line className="sc-pole" x1="0" y1="0" x2="0" y2="-17" />
            <path className="sc-flag-cloth sc-stroke" d="M0.5 -17 L12 -13.5 L0.5 -10 Z" />
          </g>
        </>
      )}

      <path className="sc-near sc-stroke" d={hillsPath(s.nearPts, W)} />

      {variant === 'club' && (
        <g className="sc-cabin" transform={`translate(${f(s.cabin.x)} ${f(s.cabin.y)})`}>
          <g className="sc-smoke">
            <circle cx="7" cy="-26" r="2.4" />
            <circle cx="9" cy="-31" r="3" />
            <circle cx="6" cy="-37" r="3.4" />
          </g>
          <rect className="sc-chimney sc-stroke" x="4" y="-25" width="4" height="8" />
          <rect className="sc-wall sc-stroke" x="-11" y="-14" width="22" height="14" />
          <path className="sc-roof sc-stroke" d="M-14 -13 L0 -25 L14 -13 Z" />
          <rect className="sc-window sc-stroke" x="-7" y="-10" width="5" height="5" />
          <rect className="sc-door sc-stroke" x="3" y="-9" width="5" height="9" />
        </g>
      )}

      {s.trees.map((t, i) => (
        <g key={i} transform={`translate(${f(t.x)} ${f(t.y)}) scale(${f(t.s)})`} className="sc-tree-wrap">
          <rect className="sc-trunk" x="-1.2" y="-3" width="2.4" height="4" />
          <path className="sc-tree sc-stroke" d="M0 -22 L7 -11 L4 -11 L9 -3 L-9 -3 L-4 -11 L-7 -11 Z" />
        </g>
      ))}

      <rect className="sc-night" width={W} height={H} />
    </svg>
  );
});
