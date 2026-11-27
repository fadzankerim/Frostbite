// Javni podaci: ture i društva (samo čitanje).
import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { api } from './client';

export type LatLng = [number, number];
export type DifficultyCode = 'LAKA' | 'SREDNJA' | 'TESKA' | 'VRLO_TESKA';

export type TourSummary = {
  id: number;
  name: string;
  club: { id: number; name: string };
  region: string;
  startAt: string;
  difficulty: { code: DifficultyCode; label: string };
  lengthKm: number;
  elevationGainM: number;
  durationH: number;
  price: number;
  membersOnly: boolean;
  maxParticipants: number;
  freeSpots: number;
  start: LatLng | null;
  trace: LatLng[];
};

export type TourDetail = TourSummary & {
  description: string;
  meetingPoint: string;
  registrationDeadline: string;
  deadlinePassed: boolean;
  requiredEquipment: string;
  route: LatLng[];
  guides: string[];
  myRegistration: { id: number; status: 'PRIJAVLJEN' | 'NA_LISTI_CEKANJA'; label: string } | null;
  inSelection: boolean;
  canRegister: boolean;
  /** tura samo za članove, a prijavljeni korisnik nema važeće članstvo */
  membersOnlyBlocked: boolean;
};

export type TourFilters = { q?: string; difficulty?: string; club?: string; date_from?: string; date_to?: string };
export type FilterOptions = { difficulties: { code: DifficultyCode; label: string }[]; clubs: { id: number; name: string }[] };
export type Stats = { tours: number; clubs: number; km: number; elevation: number };

export type ClubSummary = { id: number; name: string; city: string; description: string; toursCount: number };
export type ClubDetail = ClubSummary & {
  email: string;
  phone: string;
  tours: TourSummary[];
  membership: { status: string; label: string; validUntil: string | null; expired: boolean } | null;
  canRequest: boolean;
};

const FILTER_KEYS = ['q', 'difficulty', 'club', 'date_from', 'date_to'] as const;
const DIFFICULTIES: readonly string[] = ['LAKA', 'SREDNJA', 'TESKA', 'VRLO_TESKA'];
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

/** Filteri iz URL-a: propušta se samo ono što ima ispravan oblik (server ionako provjerava sve). */
export function cleanFilters(params: URLSearchParams): TourFilters {
  const out: TourFilters = {};
  const q = params.get('q')?.trim().slice(0, 80);
  if (q) out.q = q;
  const d = params.get('difficulty');
  if (d && DIFFICULTIES.includes(d)) out.difficulty = d;
  const club = params.get('club');
  if (club && /^\d{1,9}$/.test(club)) out.club = club;
  for (const k of ['date_from', 'date_to'] as const) {
    const v = params.get(k);
    if (v && DATE_RE.test(v)) out[k] = v;
  }
  return out;
}

function toQuery(filters: TourFilters): string {
  const p = new URLSearchParams();
  for (const k of FILTER_KEYS) {
    const v = filters[k];
    if (v) p.set(k, v);
  }
  const s = p.toString();
  return s ? `?${s}` : '';
}

/** ID iz URL-a: samo pozitivan cijeli broj (inače null -> stranica 404 bez zahtjeva prema serveru). */
export function parseId(raw: string | undefined): number | null {
  if (!raw || !/^\d{1,9}$/.test(raw)) return null;
  const v = Number(raw);
  return v > 0 ? v : null;
}

export function useTours(filters: TourFilters) {
  return useQuery({
    queryKey: ['tours', 'list', filters],
    queryFn: () => api.get<{ results: TourSummary[] }>(`/api/tours/${toQuery(filters)}`).then((r) => r.results),
    placeholderData: keepPreviousData,
    staleTime: 30_000,
  });
}

export function useTour(tourId: number | null) {
  return useQuery({
    queryKey: ['tours', 'detail', tourId],
    queryFn: () => api.get<TourDetail>(`/api/tours/${tourId}/`),
    enabled: tourId !== null,
    staleTime: 30_000,
  });
}

export function useFilterOptions() {
  return useQuery({
    queryKey: ['tours', 'filters'],
    queryFn: () => api.get<FilterOptions>('/api/tours/filters/'),
    staleTime: 5 * 60_000,
  });
}

export function useStats() {
  return useQuery({ queryKey: ['tours', 'stats'], queryFn: () => api.get<Stats>('/api/tours/stats/'), staleTime: 60_000 });
}

export function useClubs() {
  return useQuery({
    queryKey: ['clubs', 'list'],
    queryFn: () => api.get<{ results: ClubSummary[] }>('/api/clubs/').then((r) => r.results),
    staleTime: 60_000,
  });
}

export function useClub(clubId: number | null) {
  return useQuery({
    queryKey: ['clubs', 'detail', clubId],
    queryFn: () => api.get<ClubDetail>(`/api/clubs/${clubId}/`),
    enabled: clubId !== null,
    staleTime: 30_000,
  });
}
