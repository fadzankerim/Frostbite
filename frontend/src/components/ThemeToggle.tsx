// Prekidač svijetle/tamne teme: crtano sunce koje se pretvara u mjesec.
import { useTheme } from '../lib/theme';

export function ThemeToggle() {
  const [theme, setTheme] = useTheme();
  const dark = theme === 'dark';
  return (
    <button
      type="button"
      className={`theme-toggle${dark ? ' is-dark' : ''}`}
      role="switch"
      aria-checked={dark}
      aria-label="Tamni način"
      title={dark ? 'Prebaci na svijetli način' : 'Prebaci na tamni način'}
      onClick={() => setTheme(dark ? 'light' : 'dark')}
    >
      <svg viewBox="0 0 32 32" aria-hidden="true" focusable="false">
        <g className="tt-rays">
          {Array.from({ length: 8 }, (_, i) => (
            <line key={i} x1="16" y1="3" x2="16" y2="6.5" transform={`rotate(${i * 45} 16 16)`} />
          ))}
        </g>
        <circle className="tt-body" cx="16" cy="16" r="7" />
        <circle className="tt-bite" cx="21.5" cy="11.5" r="6" />
        <g className="tt-stars">
          <circle cx="7" cy="9" r="1" />
          <circle cx="25" cy="24" r="0.9" />
        </g>
      </svg>
    </button>
  );
}
