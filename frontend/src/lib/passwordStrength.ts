// Indikator jačine lozinke - samo pomoć korisniku. Pravila lozinke provjerava server
// (Django validatori: min. 10 znakova, nije česta, nije slična imenu ili emailu, nije samo brojevi).

export const MIN_PASSWORD_LENGTH = 10;

export const STRENGTH_LABELS = ['Najmanje 10 znakova', 'Slaba', 'Osrednja', 'Dobra', 'Odlična'] as const;

export type Strength = 0 | 1 | 2 | 3 | 4;

export function passwordStrength(value: string): Strength {
  if (value.length < MIN_PASSWORD_LENGTH) return 0;
  const kinds = [/[a-zšđčćž]/, /[A-ZŠĐČĆŽ]/, /\d/, /[^A-Za-z0-9šđčćžŠĐČĆŽ]/].filter((r) => r.test(value)).length;
  let score: Strength = 1;
  if (kinds >= 2) score = 2;
  if (kinds >= 3 && value.length >= 12) score = 3;
  if (kinds >= 3 && value.length >= 16) score = 4;
  return score;
}
