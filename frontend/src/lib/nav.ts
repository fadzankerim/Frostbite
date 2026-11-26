/** Kružno pomjeranje indeksa (strelice, "Dalje"/"Nazad", automatsko prebacivanje). */
export function cycle(i: number, delta: number, n: number): number {
  if (n <= 0) return 0;
  return (((i + delta) % n) + n) % n;
}

/** Indeks za tipku u listi kartica (role="tablist"); null = tipka se ne obrađuje. */
export function keyToIndex(key: string, i: number, n: number): number | null {
  switch (key) {
    case 'ArrowRight': case 'ArrowDown': return cycle(i, 1, n);
    case 'ArrowLeft': case 'ArrowUp': return cycle(i, -1, n);
    case 'Home': return 0;
    case 'End': return Math.max(0, n - 1);
    default: return null;
  }
}
