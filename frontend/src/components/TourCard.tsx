import { Link } from 'react-router';

import type { DifficultyCode, LatLng, TourSummary } from '../api/public';
import { formatDateTime, formatDay, formatMonth, formatNumber, spotsText } from '../lib/format';
import { clearDash } from '../lib/svg';
import { SceneArt } from './SceneArt';
import './tours.css';

const W = 120;
const H = 64;

/** Oblik rute kao mala linija (projekcija lat/lng -> x/y uz očuvanje proporcija). */
export function routeTracePath(trace: LatLng[], w = W, h = H, pad = 6): { d: string; start: [number, number] } | null {
  if (trace.length < 2) return null;
  const k = Math.cos(((trace[0]![0]) * Math.PI) / 180);
  const xs = trace.map(([, lng]) => lng * k);
  const ys = trace.map(([lat]) => -lat);
  const minX = Math.min(...xs); const maxX = Math.max(...xs);
  const minY = Math.min(...ys); const maxY = Math.max(...ys);
  const span = Math.max(maxX - minX, maxY - minY) || 1;
  const s = Math.min((w - pad * 2) / span, (h - pad * 2) / span);
  const ox = (w - (maxX - minX) * s) / 2;
  const oy = (h - (maxY - minY) * s) / 2;
  const pts = xs.map((x, i): [number, number] => [ox + (x - minX) * s, oy + (ys[i]! - minY) * s]);
  return { d: pts.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(''), start: pts[0]! };
}

const PEAKS: Record<DifficultyCode, number> = { LAKA: 1, SREDNJA: 2, TESKA: 3, VRLO_TESKA: 4 };

/** Težina: broj malih vrhova (1-4) u boji težine + naziv. */
export function DifficultyBadge({ code, label }: { code: DifficultyCode; label: string }) {
  const n = PEAKS[code];
  return (
    <span className={`diff diff-${code.toLowerCase()}`}>
      <svg className="diff-peaks" viewBox="0 0 40 10" aria-hidden="true" focusable="false">
        {[0, 1, 2, 3].map((i) => (
          <path key={i} className={i < n ? 'on' : ''} d={`M${i * 10} 10 L${i * 10 + 5} 1.5 L${i * 10 + 10} 10 Z`} />
        ))}
      </svg>
      {label}
    </span>
  );
}

export function RouteTrace({ trace }: { trace: LatLng[] }) {
  const path = routeTracePath(trace);
  return (
    <svg className="trace" viewBox={`0 0 ${W} ${H}`} aria-hidden="true" focusable="false">
      {path ? (
        <>
          <path className="trace-line" d={path.d} pathLength={1} onAnimationEnd={clearDash} />
          <circle className="trace-start" r={2.5} cx={path.start[0]} cy={path.start[1]} />
        </>
      ) : (
        <text className="trace-empty" x={W / 2} y={H / 2} textAnchor="middle" dominantBaseline="middle">RUTA NIJE UCRTANA</text>
      )}
    </svg>
  );
}

export function SpotsBar({ free, max }: { free: number; max: number }) {
  const taken = Math.min(max, Math.max(0, max - free));
  return (
    <div className="spots">
      <div className="spots-bar" aria-hidden="true">
        <span style={{ transform: `scaleX(${max ? taken / max : 0})` }} className={free <= 0 ? 'full' : ''} />
      </div>
      <span className="spots-text">{spotsText(free, max)}</span>
    </div>
  );
}

type Props = { tour: TourSummary; onHover?: (id: number | null) => void; index?: number };

export function TourCard({ tour, onHover, index = 0 }: Props) {
  return (
    <article
      className="tour-card"
      style={{ animationDelay: `${Math.min(index, 8) * 50}ms` }}
      onMouseEnter={() => onHover?.(tour.id)}
      onMouseLeave={() => onHover?.(null)}
      onFocus={() => onHover?.(tour.id)}
      onBlur={() => onHover?.(null)}
    >
      <Link to={`/ture/${tour.id}`} className="tour-card-link has-scene">
        <div className="tour-card-art">
          <SceneArt seed={tour.id} difficulty={tour.difficulty.code} />
          <div className="sticker date-sticker" aria-hidden="true">
            <span className="mono tour-card-day">{formatDay(tour.startAt)}</span>
            <span className="label-mono">{formatMonth(tour.startAt)}</span>
          </div>
        </div>
        <div className="tour-card-body">
          <div className="tour-card-top">
            <DifficultyBadge code={tour.difficulty.code} label={tour.difficulty.label} />
            {tour.membersOnly && <span className="label-mono tag">Samo članovi</span>}
          </div>
          <h3 className="tour-card-title">{tour.name}</h3>
          <p className="tour-card-meta muted">
            {tour.club.name}{tour.region ? ` · ${tour.region}` : ''}
          </p>
          <p className="mono tour-card-stats">
            <span>{formatDateTime(tour.startAt)}</span>
            <span>{formatNumber(tour.lengthKm)} km</span>
            <span>↑ {tour.elevationGainM} m</span>
            <span>{formatNumber(tour.durationH)} h</span>
          </p>
          <SpotsBar free={tour.freeSpots} max={tour.maxParticipants} />
        </div>
        <RouteTrace trace={tour.trace} />
      </Link>
    </article>
  );
}
