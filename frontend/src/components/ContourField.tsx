// Topografska karta (izohipse) oko vrha. Linije se iscrtavaju pri učitavanju, a kursor
// radi kao "altimetar": prikazuje visinu i koordinate ispod sebe i ističe najbližu izohipsu.
// Čisto ukrasno (aria-hidden); poštuje prefers-reduced-motion kroz CSS.
import { useMemo, useRef, useState, type CSSProperties, type PointerEvent } from 'react';

import { clearDash } from '../lib/svg';
import './contour.css';

export type Summit = { name: string; elevation: number; lat: number; lon: number };

export const BJELASNICA: Summit = { name: 'Bjelašnica', elevation: 2067, lat: 43.7155, lon: 18.2565 };

const SIZE = 600;
const RINGS = 12;
const R0 = 30;          // poluprečnik najviše izohipse
const STEP = 24;        // razmak između izohipsi (100 m)
const POINTS = 120;
const TAU = Math.PI * 2;

type Shape = { k: number[]; a: number[]; p: number[] };

function rng(seed: number) {
  let s = seed >>> 0 || 1;
  return () => {
    s ^= s << 13; s >>>= 0;
    s ^= s >>> 17;
    s ^= s << 5; s >>>= 0;
    return s / 4294967296;
  };
}

function makeShape(seed: number): Shape {
  const r = rng(seed);
  return { k: [2, 3, 5], a: [0.1, 0.06, 0.03], p: [r() * TAU, r() * TAU, r() * TAU] };
}

/** Koliko je izohipsa "izdužena" u pravcu theta; blago se mijenja sa visinom. */
function factor(shape: Shape, theta: number, ring: number): number {
  let f = 1;
  shape.k.forEach((k, j) => {
    f += shape.a[j]! * Math.sin(k * theta + shape.p[j]! + ring * 0.08 * (j + 1));
  });
  return f;
}

function ringPath(cx: number, cy: number, ring: number, shape: Shape): string {
  const radius = R0 + ring * STEP;
  const pts: [number, number][] = [];
  for (let i = 0; i < POINTS; i++) {
    const t = (i / POINTS) * TAU;
    const r = radius * factor(shape, t, ring);
    pts.push([cx + r * Math.cos(t), cy + r * Math.sin(t)]);
  }
  const at = (i: number) => pts[(i + POINTS) % POINTS]!;
  const f = (n: number) => n.toFixed(1);
  let d = `M${f(at(0)[0])},${f(at(0)[1])}`;
  // zatvorena Catmull-Rom kriva -> kubni Bezier
  for (let i = 0; i < POINTS; i++) {
    const [p0, p1, p2, p3] = [at(i - 1), at(i), at(i + 1), at(i + 2)];
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += `C${f(c1[0]!)},${f(c1[1]!)} ${f(c2[0]!)},${f(c2[1]!)} ${f(p2[0])},${f(p2[1])}`;
  }
  return `${d}Z`;
}

type Probe = { x: number; y: number; elevation: number; ring: number; lat: number; lon: number };

type Props = {
  summit?: Summit;
  seed?: number;
  /** centar vrha u koordinatama 0-600 */
  center?: [number, number];
  interactive?: boolean;
  className?: string;
};

export function ContourField({ summit = BJELASNICA, seed = 7, center = [320, 290], interactive = true, className }: Props) {
  const [cx, cy] = center;
  const shape = useMemo(() => makeShape(seed), [seed]);
  const topRing = Math.floor((summit.elevation - 1) / 100) * 100;   // npr. 2000 m
  const rings = useMemo(
    () => Array.from({ length: RINGS }, (_, i) => ({ i, d: ringPath(cx, cy, i, shape), elevation: topRing - i * 100 })),
    [cx, cy, shape, topRing],
  );

  const svgRef = useRef<SVGSVGElement>(null);
  const frame = useRef(0);
  const [probe, setProbe] = useState<Probe | null>(null);

  function measure(clientX: number, clientY: number) {
    const svg = svgRef.current;
    const ctm = svg?.getScreenCTM();
    if (!svg || !ctm) return;
    const pt = new DOMPoint(clientX, clientY).matrixTransform(ctm.inverse());
    const dx = pt.x - cx;
    const dy = pt.y - cy;
    const theta = Math.atan2(dy, dx);
    const dist = Math.hypot(dx, dy);
    let ringF = (dist / factor(shape, theta, 0) - R0) / STEP;
    const norm = dist / factor(shape, theta, Math.max(0, ringF));
    ringF = (norm - R0) / STEP;
    const elevation = norm <= R0
      ? topRing + (summit.elevation - topRing) * (1 - norm / R0)
      : Math.max(400, topRing - ringF * 100);
    setProbe({
      x: pt.x, y: pt.y, elevation: Math.round(elevation), ring: Math.round(ringF),
      lat: summit.lat - dy * 0.00013, lon: summit.lon + dx * 0.00018,
    });
  }

  function onPointerMove(e: PointerEvent<SVGSVGElement>) {
    const { clientX, clientY } = e;
    cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(() => measure(clientX, clientY));
  }

  function onPointerLeave() {
    cancelAnimationFrame(frame.current);
    setProbe(null);
  }

  const readoutW = 132;
  const readoutH = 46;
  const rx = probe ? (probe.x + 16 + readoutW > SIZE ? probe.x - 16 - readoutW : probe.x + 16) : 0;
  const ry = probe ? (probe.y + 16 + readoutH > SIZE ? probe.y - 16 - readoutH : probe.y + 16) : 0;

  return (
    <svg
      ref={svgRef}
      className={`contour-field${interactive ? ' is-interactive' : ''}${className ? ` ${className}` : ''}`}
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
      focusable="false"
      onPointerMove={interactive ? onPointerMove : undefined}
      onPointerLeave={interactive ? onPointerLeave : undefined}
    >
      <g className="cf-grid">
        {Array.from({ length: 11 }, (_, i) => (i + 1) * 50).map((v) => (
          <g key={v}>
            <line x1={v} y1={0} x2={v} y2={SIZE} />
            <line x1={0} y1={v} x2={SIZE} y2={v} />
          </g>
        ))}
      </g>

      <g className="cf-drift">
        {rings.map(({ i, d }) => (
          <path
            key={i}
            d={d}
            pathLength={1}
            className={`cf-ring${i % 5 === 0 ? ' is-index' : ''}${probe?.ring === i ? ' is-active' : ''}`}
            style={{ '--i': i } as CSSProperties}
            onAnimationEnd={clearDash}
          />
        ))}
        {rings.filter(({ i }) => i % 2 === 0 && i > 0).map(({ i, elevation }) => {
          const t = -0.75;
          const r = (R0 + i * STEP) * factor(shape, t, i);
          return (
            <text key={i} className="cf-label" x={cx + r * Math.cos(t)} y={cy + r * Math.sin(t)}
              textAnchor="middle" dominantBaseline="middle" style={{ '--i': i } as CSSProperties}>
              {elevation}
            </text>
          );
        })}
        <g className="cf-summit" transform={`translate(${cx} ${cy})`}>
          <circle className="cf-pulse" r={10} />
          <path d="M0,-6 L6,5 L-6,5 Z" />
          <text className="cf-summit-label" x={12} y={-10}>{summit.name.toUpperCase()} · {summit.elevation} m</text>
        </g>
      </g>

      {probe && (
        <g className="cf-probe">
          <line className="cf-cross" x1={probe.x} y1={0} x2={probe.x} y2={SIZE} />
          <line className="cf-cross" x1={0} y1={probe.y} x2={SIZE} y2={probe.y} />
          <rect className="cf-reticle" x={probe.x - 6} y={probe.y - 6} width={12} height={12} />
          <g transform={`translate(${rx} ${ry})`}>
            <rect className="cf-readout" width={readoutW} height={readoutH} rx={4} />
            <text className="cf-readout-alt" x={10} y={19}>ALT {probe.elevation} m</text>
            <text className="cf-readout-pos" x={10} y={35}>
              {probe.lat.toFixed(4)}°N {probe.lon.toFixed(4)}°E
            </text>
          </g>
        </g>
      )}
    </svg>
  );
}
