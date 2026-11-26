// Konfete za uspjeh (npr. prijava na turu). Komadići u bojama zabavne palete padaju ~2 s.
// Ne prikazuju se uz prefers-reduced-motion. Ukrasne (aria-hidden), ne hvataju klikove.
import { useMemo, type CSSProperties } from 'react';

import { rng } from '../lib/rng';
import './confetti.css';

const COLORS = ['--fun-coral', '--fun-sun', '--fun-mint', '--fun-lilac', '--fun-sky', '--fun-peach'];

export function Confetti({ seed = 1, pieces = 42 }: { seed?: number; pieces?: number }) {
  const items = useMemo(() => {
    const r = rng(seed);
    return Array.from({ length: pieces }, (_, i) => ({
      x: r() * 100,
      dx: (r() - 0.5) * 30,
      rot: Math.round(r() * 720 - 360),
      delay: r() * 0.35,
      dur: 1.4 + r() * 0.9,
      color: COLORS[i % COLORS.length]!,
      shape: i % 3,
    }));
  }, [seed, pieces]);

  if (typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return null;

  return (
    <div className="confetti" aria-hidden="true">
      {items.map((p, i) => (
        <span
          key={i}
          className={`confetti-piece shape-${p.shape}`}
          style={{
            left: `${p.x}%`,
            background: `var(${p.color})`,
            '--dx': `${p.dx}vw`,
            '--rot': `${p.rot}deg`,
            animationDelay: `${p.delay}s`,
            animationDuration: `${p.dur}s`,
          } as CSSProperties}
        />
      ))}
    </div>
  );
}
