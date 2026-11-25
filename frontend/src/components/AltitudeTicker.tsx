// Brojač visine: broji od 0 do vrijednosti kad uđe u vidno polje (kao altimetar pri usponu).
import { useEffect, useRef, useState } from 'react';

function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

type Props = { value: number; unit?: string; duration?: number };

export function AltitudeTicker({ value, unit = 'm', duration = 1400 }: Props) {
  const [shown, setShown] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let raf = 0;
    const run = () => {
      if (prefersReducedMotion()) {
        raf = requestAnimationFrame(() => setShown(value));
        return;
      }
      const start = performance.now();
      const tick = (now: number) => {
        const t = Math.min(1, (now - start) / duration);
        const eased = 1 - (1 - t) ** 3;
        setShown(Math.round(value * eased));
        if (t < 1) raf = requestAnimationFrame(tick);
      };
      raf = requestAnimationFrame(tick);
    };
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) {
        io.disconnect();
        run();
      }
    }, { threshold: 0.4 });
    io.observe(el);
    return () => {
      io.disconnect();
      cancelAnimationFrame(raf);
    };
  }, [value, duration]);

  return (
    <span ref={ref} className="mono altitude" aria-label={`${value} ${unit}`}>
      <span aria-hidden="true">{shown}</span>
      <span className="altitude-unit" aria-hidden="true"> {unit}</span>
    </span>
  );
}
