import type { AnimationEvent } from 'react';

/** Nakon animacije iscrtavanja (stroke-dashoffset) uklanja crtkanje. Chromium zna izgubiti
 *  iscrtavanje putanje sa pathLength + dasharray pri promjeni veličine prozora; puna linija ne. */
export function clearDash(e: AnimationEvent<SVGElement> | Event): void {
  const el = (e as Event).currentTarget ?? (e as AnimationEvent<SVGElement>).currentTarget;
  if (el instanceof SVGElement) el.style.strokeDasharray = 'none';
}
