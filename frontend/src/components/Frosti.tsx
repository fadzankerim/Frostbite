// Frosti - maskota aplikacije: mali jeti sa kapom. Crtani SVG iz punih boja (bez gradijenata).
// Raspoloženja: wave (maše), happy (skače), sad (izgubljen), think (razmišlja).
// Ukrasna slika (aria-hidden); poruku uz nju uvijek nosi tekst pored.
import './scene.css';

export type FrostiMood = 'wave' | 'happy' | 'sad' | 'think';

type Props = { mood?: FrostiMood; size?: number; className?: string };

export function Frosti({ mood = 'wave', size = 120, className }: Props) {
  const mouth = {
    wave: 'M52 78 Q60 85 68 78',
    happy: 'M50 76 Q60 90 70 76 Z',
    sad: 'M52 82 Q60 75 68 82',
    think: 'M54 80 L66 79',
  }[mood];
  return (
    <svg
      className={`frosti frosti-${mood}${className ? ` ${className}` : ''}`}
      width={size}
      height={size}
      viewBox="0 0 120 120"
      aria-hidden="true"
      focusable="false"
    >
      <ellipse className="fr-shadow" cx="60" cy="113" rx="30" ry="4" />
      <g className="fr-body-wrap">
        {/* lijeva ruka (statična) */}
        <path className="fr-fur fr-stroke" d="M30 70 Q16 78 20 92 Q26 96 32 88 Z" />
        {/* desna ruka (maše) */}
        <g className="fr-arm">
          <path className="fr-fur fr-stroke" d="M90 70 Q106 60 104 46 Q98 42 94 50 Q92 60 86 66 Z" />
        </g>
        {/* tijelo: čupavo krzno */}
        <path
          className="fr-fur fr-stroke"
          d="M60 22 C82 22 94 40 94 62 C94 80 92 96 86 104 Q80 108 74 104 Q67 109 60 104 Q53 109 46 104 Q40 108 34 104 C28 96 26 80 26 62 C26 40 38 22 60 22 Z"
        />
        <path className="fr-shade" d="M34 96 Q46 102 60 100 Q74 102 86 96 L86 102 Q74 106 60 104 Q46 106 34 102 Z" />
        {/* lice */}
        <path className="fr-face fr-stroke" d="M60 46 C76 46 82 56 80 70 C78 82 70 88 60 88 C50 88 42 82 40 70 C38 56 44 46 60 46 Z" />
        <g className="fr-eyes">
          <ellipse className="fr-ink" cx="52" cy="63" rx="3.4" ry="4.4" />
          <ellipse className="fr-ink" cx="68" cy="63" rx="3.4" ry="4.4" />
          <circle className="fr-shine" cx="53.2" cy="61.4" r="1.2" />
          <circle className="fr-shine" cx="69.2" cy="61.4" r="1.2" />
        </g>
        {mood === 'sad' && <path className="fr-brow" d="M46 57 L55 54 M74 57 L65 54" />}
        {mood === 'think' && <path className="fr-brow" d="M47 55 L56 54 M65 52 L74 55" />}
        <ellipse className="fr-blush" cx="46" cy="72" rx="4" ry="2.4" />
        <ellipse className="fr-blush" cx="74" cy="72" rx="4" ry="2.4" />
        <path className={`fr-mouth${mood === 'happy' ? ' is-open' : ''}`} d={mouth} />
        {/* kapa sa pomponom */}
        <path className="fr-hat fr-stroke" d="M34 36 Q38 14 60 12 Q82 14 86 36 Q60 28 34 36 Z" />
        <path className="fr-hat-band fr-stroke" d="M32 36 Q60 26 88 36 L88 42 Q60 33 32 42 Z" />
        <circle className="fr-pompom fr-stroke" cx="60" cy="10" r="6" />
      </g>
      {mood === 'think' && (
        <g className="fr-bubbles">
          <circle className="fr-bubble fr-stroke" cx="98" cy="30" r="3" />
          <circle className="fr-bubble fr-stroke" cx="106" cy="20" r="5" />
        </g>
      )}
    </svg>
  );
}
