// Panel vodiča (F15-F20). Lični podaci učesnika se ne zadržavaju u kešu nakon napuštanja
// stranice (gcTime: 0) i uvijek se ponovo dohvataju sa servera (koji bilježi svaki pristup).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from './client';
import type { DifficultyCode, LatLng } from './public';

type Coded<T extends string = string> = { code: T; label: string };

export type GuideTourBrief = {
  id: number; name: string; startAt: string; club: { id: number; name: string };
  status: Coded; difficulty: Coded<DifficultyCode>; meetingPoint: string; start: LatLng | null;
};
export type GuideDashboard = { openTours: (GuideTourBrief & { applied: boolean })[]; myTours: GuideTourBrief[] };
export type Participant = {
  id: number; name: string; phone: string; emergencyContactName: string; emergencyContactPhone: string;
  healthNotes: string; status: Coded<'PRIJAVLJEN' | 'NA_LISTI_CEKANJA'>; attendance: 'PRISUSTVOVAO' | 'NIJE_DOSAO' | null;
};
export type GuideTour = GuideTourBrief & {
  maxParticipants: number; canClose: boolean; attendanceOpen: boolean; canReport: boolean;
  report: { text: string; attendeesCount: number; createdAt: string } | null;
  participants: Participant[];
};

const DASH = ['guide', 'dashboard'] as const;
const tourKey = (id: number) => ['guide', 'tour', id] as const;

export function useGuideDashboard() {
  return useQuery({ queryKey: DASH, queryFn: () => api.get<GuideDashboard>('/api/guide/') });
}

export function useGuideTour(id: number | null) {
  return useQuery({
    queryKey: tourKey(id ?? 0),
    queryFn: () => api.get<GuideTour>(`/api/guide/tours/${id}/`),
    enabled: id !== null,
    gcTime: 0,
    staleTime: 0,
  });
}

function useGuideAction<V>(id: number, path: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: V) => api.post<{ detail: string }>(`/api/guide/tours/${id}/${path}/`, body),
    onSettled: () => Promise.all([
      qc.invalidateQueries({ queryKey: tourKey(id) }),
      qc.invalidateQueries({ queryKey: DASH }),
    ]),
  });
}

export const useGuideApply = (id: number) => useGuideAction<undefined>(id, 'apply');
export const useGuideClose = (id: number) => useGuideAction<undefined>(id, 'close');
export const useGuideAttendance = (id: number) => useGuideAction<{ present: number[] }>(id, 'attendance');
export const useGuideReport = (id: number) => useGuideAction<{ text: string }>(id, 'report');
