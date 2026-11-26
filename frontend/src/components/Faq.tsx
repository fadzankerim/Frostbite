// Često postavljana pitanja: harmonika iz <details>/<summary> (radi bez JavaScripta i s tastaturom).
import type { ReactNode } from 'react';

import './steps.css';

export type FaqItem = { q: string; a: ReactNode };

export function Faq({ items }: { items: FaqItem[] }) {
  return (
    <div className="faq">
      {items.map((it) => (
        <details key={it.q} className="faq-item">
          <summary>
            <span>{it.q}</span>
            <span className="faq-plus" aria-hidden="true" />
          </summary>
          <div className="faq-body muted">{it.a}</div>
        </details>
      ))}
    </div>
  );
}
