// Panel admina društva (F18, F21-F28). Društvo iz URL-a server traži samo među društvima
// kojima korisnik upravlja; ovdje se samo pozivaju endpointi i osvježava keš.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from './client';
import type { DifficultyCode, LatLng } from './public';

type Coded<T extends string = string> = { code: T; label: string };

export type ManagedClub = { id: number; name: string; city: string };
export type TourRow = {
  id: number; name: string; startAt: string; status: Coded; difficulty: Coded<DifficultyCode>;
  maxParticipants: number; taken: number | null; waiting: number | null; guideApps: number | null;
};
export type Dashboard = {
  club: ManagedClub;
  phases: { draft: number; active: number; done: number; cancelled: number };
  money: { earned: number; expected: number };
  fill: { taken: number; capacity: number; pct: number };
  guides: { name: string; led: number }[];
  membersCount: number; pendingMembers: number; pendingGuides: number;
  unguided: TourRow[]; upcoming: TourRow[];
  months: { label: string; people: number; money: number }[];
};
export type TourFormData = {
  name: string; region: string; description: string; startAt: string; registrationDeadline: string;
  meetingPoint: string; difficulty: DifficultyCode; lengthKm: number | string; elevationGainM: number | string;
  durationH: number | string; maxParticipants: number | string; price: number | string; membersOnly: boolean;
  requiredEquipment: string; route: LatLng[];
};
export type ManageTour = TourRow & {
  editable: boolean;
  transitions: ('publish' | 'close' | 'cancel')[];
  form: TourFormData;
  registrations: { id: number; name: string; status: Coded; attendance: string | null }[];
  guideApplications: { id: number; name: string; status: Coded }[];
  assignable: { id: number; name: string }[];
};
export type ClubGuideRow = { id: number; name: string; licenseNumber: string; since: string };
export type MemberRow = { id: number; name: string; createdAt: string; validUntil: string | null };
export type ClubProfile = { name: string; city: string; description: string; email: string; phone: string };

const base = (clubId: number) => `/api/manage/${clubId}`;
const k = (clubId: number, ...rest: (string | number)[]) => ['manage', clubId, ...rest] as const;

export function useManagedClubs() {
  return useQuery({
    queryKey: ['manage', 'clubs'],
    queryFn: () => api.get<{ results: ManagedClub[] }>('/api/manage/').then((r) => r.results),
  });
}

export const useDashboard = (clubId: number) =>
  useQuery({ queryKey: k(clubId, 'dashboard'), queryFn: () => api.get<Dashboard>(`${base(clubId)}/`) });

export const useManageTours = (clubId: number) =>
  useQuery({ queryKey: k(clubId, 'tours'), queryFn: () => api.get<{ upcoming: TourRow[]; past: TourRow[] }>(`${base(clubId)}/tours/`) });

export const useManageTour = (clubId: number, tourId: number | null) =>
  useQuery({
    queryKey: k(clubId, 'tour', tourId ?? 0),
    queryFn: () => api.get<ManageTour>(`${base(clubId)}/tours/${tourId}/`),
    enabled: tourId !== null,
  });

export const useClubGuides = (clubId: number) =>
  useQuery({ queryKey: k(clubId, 'guides'), queryFn: () => api.get<{ results: ClubGuideRow[] }>(`${base(clubId)}/guides/`).then((r) => r.results) });

export const useMembers = (clubId: number) =>
  useQuery({ queryKey: k(clubId, 'members'), queryFn: () => api.get<{ pending: MemberRow[]; active: MemberRow[] }>(`${base(clubId)}/members/`) });

export const useClubProfile = (clubId: number) =>
  useQuery({ queryKey: k(clubId, 'profile'), queryFn: () => api.get<ClubProfile>(`${base(clubId)}/profile/`) });

/** Sve izmjene osvježavaju cijeli keš ovog društva (pregled, ture, vodiči, članovi). */
function useManageMutation<V, R = { detail: string }>(clubId: number, fn: (v: V) => Promise<R>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSettled: () => Promise.all([
      qc.invalidateQueries({ queryKey: ['manage', clubId] }),
      qc.invalidateQueries({ queryKey: ['tours'] }),
    ]),
  });
}

export const useCreateTour = (clubId: number) =>
  useManageMutation(clubId, (d: TourFormData) => api.post<{ id: number; detail: string }>(`${base(clubId)}/tours/`, d));
export const useUpdateTour = (clubId: number, tourId: number) =>
  useManageMutation(clubId, (d: TourFormData) => api.put<{ id: number; detail: string }>(`${base(clubId)}/tours/${tourId}/`, d));
export const useTransition = (clubId: number, tourId: number) =>
  useManageMutation(clubId, (action: string) => api.post<{ detail: string }>(`${base(clubId)}/tours/${tourId}/transition/`, { action }));
export const useAssignGuide = (clubId: number, tourId: number) =>
  useManageMutation(clubId, (guideId: number) => api.post<{ detail: string }>(`${base(clubId)}/tours/${tourId}/guides/assign/`, { guideId }));
export const useDecideGuide = (clubId: number, tourId: number) =>
  useManageMutation(clubId, ({ appId, decision }: { appId: number; decision: 'approve' | 'reject' }) =>
    api.post<{ detail: string }>(`${base(clubId)}/tours/${tourId}/guides/${appId}/decide/`, { decision }));
export const useAddGuide = (clubId: number) =>
  useManageMutation(clubId, (d: { email: string; licenseNumber: string }) => api.post<{ detail: string }>(`${base(clubId)}/guides/`, d));
export const useRemoveGuide = (clubId: number) =>
  useManageMutation(clubId, (id: number) => api.post<{ detail: string }>(`${base(clubId)}/guides/${id}/remove/`));
export const useDecideMember = (clubId: number) =>
  useManageMutation(clubId, ({ id, decision }: { id: number; decision: 'approve' | 'reject' }) =>
    api.post<{ detail: string }>(`${base(clubId)}/members/${id}/decide/`, { decision }));
export const useSaveClubProfile = (clubId: number) =>
  useManageMutation(clubId, (d: Omit<ClubProfile, 'name'>) => api.put<ClubProfile & { detail: string }>(`${base(clubId)}/profile/`, d));
