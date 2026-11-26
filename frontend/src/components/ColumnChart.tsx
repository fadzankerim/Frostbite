// Stubičasti grafikon jedne serije (dataviz specifikacija): stub najviše 24px, 4px zaobljen vrh,
// ravna osnovica, okrugli koraci ose, recesivna mreža, tooltip na hover/fokus i tabelarni prikaz.
// Jedna serija -> bez legende (naslov je imenuje). Boja dolazi iz tokena (--chart-1 / --chart-2).
import { useId, useState } from 'react';

import { formatNumber } from '../lib/format';
import './chart.css';

type Item = { label: string; value: number };
type Props = { title: string; items: Item[]; unit?: string; color?: 'chart-1' | 'chart-2' };

const W = 640;
const H = 220;
const PAD = { left: 48, right: 8, top: 14, bottom: 28 };
const BAR_MAX = 24;
const RADIUS = 4;

/** Okrugli koraci ose (1, 2, 5 x 10^k), ~4 podioka. */
export function niceScale(v: number): { max: number; step: number } {
  if (v <= 0) return { max: 4, step: 1 };
  const raw = v / 4;
  const exp = raw >= 1 ? 10 ** Math.floor(Math.log10(raw)) : 1;
  const step = [1, 2, 5, 10].map((m) => m * exp).find((s) => s >= raw) ?? raw;
  return { max: step * Math.ceil(v / step), step };
}

function barPath(x: number, y: number, w: number, h: number): string {
  if (h <= 0) return '';
  const r = Math.min(RADIUS, w / 2, h);
  const f = (n: number) => n.toFixed(1);
  return `M${f(x)},${f(y + h)} L${f(x)},${f(y + r)} Q${f(x)},${f(y)} ${f(x + r)},${f(y)} `
    + `L${f(x + w - r)},${f(y)} Q${f(x + w)},${f(y)} ${f(x + w)},${f(y + r)} L${f(x + w)},${f(y + h)} Z`;
}

const fmt = (v: number, unit: string) => `${formatNumber(Math.round(v))}${unit}`;

export function ColumnChart({ title, items, unit = '', color = 'chart-1' }: Props) {
  const id = useId();
  const [hover, setHover] = useState<number | null>(null);
  const [table, setTable] = useState(false);
  const pw = W - PAD.left - PAD.right;
  const ph = H - PAD.top - PAD.bottom;
  const { max, step } = niceScale(Math.max(0, ...items.map((i) => i.value)));
  const slot = pw / Math.max(items.length, 1);
  const bw = Math.min(BAR_MAX, slot * 0.62);
  const ticks = Array.from({ length: Math.round(max / step) + 1 }, (_, i) => i * step);
  const total = items.reduce((s, i) => s + i.value, 0);
  const hovered = hover !== null ? items[hover] : undefined;

  return (
    <figure className="chart" aria-labelledby={`${id}-t`}>
      <figcaption className="chart-head">
        <div>
          <span id={`${id}-t`} className="chart-title">{title}</span>
          <span className="mono chart-total">{fmt(total, unit)}</span>
        </div>
        <button type="button" className="btn btn-ghost btn-sm" aria-pressed={table} onClick={() => setTable((t) => !t)}>
          {table ? 'Grafikon' : 'Tabela'}
        </button>
      </figcaption>

      {table ? (
        <table className="chart-table">
          <thead><tr><th scope="col">Mjesec</th><th scope="col">{title}</th></tr></thead>
          <tbody>{items.map((i) => <tr key={i.label}><td>{i.label}</td><td className="mono">{fmt(i.value, unit)}</td></tr>)}</tbody>
        </table>
      ) : (
        <div className="chart-plot">
          <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${title}: ${items.map((i) => `${i.label} ${fmt(i.value, unit)}`).join(', ')}`}>
            {ticks.map((t) => {
              const y = PAD.top + ph - (ph * t) / max;
              return (
                <g key={t} className="chart-grid">
                  <line x1={PAD.left} x2={W - PAD.right} y1={y} y2={y} />
                  <text x={PAD.left - 8} y={y} dominantBaseline="middle" textAnchor="end">{formatNumber(t)}</text>
                </g>
              );
            })}
            {items.map((it, i) => {
              const h = max ? (ph * it.value) / max : 0;
              const x = PAD.left + i * slot + (slot - bw) / 2;
              const y = PAD.top + ph - h;
              return (
                <g key={it.label}>
                  <path className={`chart-bar ${color}${hover === i ? ' is-hover' : ''}`} d={barPath(x, y, bw, h)} />
                  <text className="chart-x" x={x + bw / 2} y={H - 8} textAnchor="middle">{it.label}</text>
                  {/* zona za hover/fokus šira od stuba */}
                  <rect className="chart-hit" x={PAD.left + i * slot} y={PAD.top} width={slot} height={ph}
                    tabIndex={0} aria-label={`${it.label}: ${fmt(it.value, unit)}`}
                    onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}
                    onFocus={() => setHover(i)} onBlur={() => setHover(null)} />
                </g>
              );
            })}
            <line className="chart-base" x1={PAD.left} x2={W - PAD.right} y1={PAD.top + ph} y2={PAD.top + ph} />
          </svg>
          {hovered && hover !== null && (
            <div className="chart-tip" style={{ left: `${((PAD.left + (hover + 0.5) * slot) / W) * 100}%` }} role="status">
              <span className="label-mono">{hovered.label}</span>
              <strong className="mono">{fmt(hovered.value, unit)}</strong>
            </div>
          )}
        </div>
      )}
    </figure>
  );
}
