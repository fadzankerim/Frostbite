// Radnje planinara: prijave na ture, odabir, članstva, profil i lozinka.
// Prava provjerava server (IsHiker / prijava); ovdje su samo pozivi i osvježavanje keša.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from './client';
import type { DifficultyCode, TourSummary } from './public';

export type RegStatus = 'PRIJAVLJEN' | 'NA_LISTI_CEKANJA' | 'ODJAVLJEN';
export type Registration = {
  id: number;
  status: RegStatus;
  label: string;
  attendance: string | null;
  canCancel?: boolean;
  tour: {
    id: number; name: string; startAt: string; club: { id: number; name: string };
    difficulty: { code: DifficultyCode; label: string }; cancelled: boolean; public: boolean;
  };
};
export type Selection = { max: number; ids: number[]; tours: TourSummary[] };
export type ConfirmResult = { tourId: number; name: string; ok: boolean; status?: RegStatus; label?: string; detail?: string };
export type Membership = {
  id: number; status: string; label: string; validUntil: string | null; expired: boolean; createdAt: string;
  club: { id: number; name: string; city: string; public: boolean };
};
export type Profile = {
  email: string; firstName: string; lastName: string; phone: string;
  emergencyContactName: string; emergencyContactPhone: string; healthNotes: string;
};
export type PasswordInput = { oldPassword: string; newPassword: string; newPasswordConfirm: string };

const KEYS = {
  registrations: ['me', 'registrations'] as const,
  memberships: ['me', 'memberships'] as const,
  profile: ['me', 'profile'] as const,
  selection: ['selection'] as const,
};

// --- prijave na ture ------------------------------------------------------------
export function useRegisterTour(tourId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<{ id: number; status: RegStatus; label: string }>(`/api/tours/${tourId}/register/`),
    onSettled: () => Promise.all([
      qc.invalidateQueries({ queryKey: ['tours'] }),
      qc.invalidateQueries({ queryKey: KEYS.registrations }),
    ]),
  });
}

export function useMyRegistrations() {
  return useQuery({
    queryKey: KEYS.registrations,
    queryFn: () => api.get<{ upcoming: Registration[]; history: Registration[] }>('/api/me/registrations/'),
  });
}

export function useCancelRegistration() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (registrationId: number) => api.post<{ detail: string }>(`/api/me/registrations/${registrationId}/cancel/`),
    onSettled: () => Promise.all([
      qc.invalidateQueries({ queryKey: KEYS.registrations }),
      qc.invalidateQueries({ queryKey: ['tours'] }),
    ]),
  });
}

// --- odabir više tura ------------------------------------------------------------
export function useSelection() {
  return useQuery({ queryKey: KEYS.selection, queryFn: () => api.get<Selection>('/api/selection/') });
}

function useSelectionMutation<V>(fn: (v: V) => Promise<Selection>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (sel) => {
      qc.setQueryData(KEYS.selection, sel);
      return qc.invalidateQueries({ queryKey: ['tours', 'detail'] });
    },
  });
}

export const useSelectionAdd = () => useSelectionMutation((tourId: number) => api.post<Selection>('/api/selection/', { tourId }));
export const useSelectionRemove = () => useSelectionMutation((tourId: number) => api.delete<Selection>(`/api/selection/${tourId}/`));

export function useSelectionConfirm() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<{ results: ConfirmResult[] }>('/api/selection/confirm/').then((r) => r.results),
    onSettled: () => Promise.all([
      qc.invalidateQueries({ queryKey: KEYS.selection }),
      qc.invalidateQueries({ queryKey: KEYS.registrations }),
      qc.invalidateQueries({ queryKey: ['tours'] }),
    ]),
  });
}

// --- članstva ------------------------------------------------------------------------
export function useMyMemberships() {
  return useQuery({
    queryKey: KEYS.memberships,
    queryFn: () => api.get<{ results: Membership[] }>('/api/me/memberships/').then((r) => r.results),
  });
}

export function useRequestMembership(clubId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<{ detail: string }>(`/api/clubs/${clubId}/membership/`),
    onSettled: () => Promise.all([
      qc.invalidateQueries({ queryKey: ['clubs', 'detail', clubId] }),
      qc.invalidateQueries({ queryKey: KEYS.memberships }),
    ]),
  });
}

// --- profil i lozinka -------------------------------------------------------------
export function useProfile() {
  return useQuery({ queryKey: KEYS.profile, queryFn: () => api.get<Profile>('/api/me/profile/') });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: Omit<Profile, 'email'>) => api.put<Profile & { detail: string }>('/api/me/profile/', p),
    onSuccess: (p) => Promise.all([
      qc.setQueryData(KEYS.profile, p),
      qc.invalidateQueries({ queryKey: ['auth', 'me'] }),    // ime u zaglavlju
    ]),
  });
}

export function useChangePassword() {
  return useMutation({ mutationFn: (p: PasswordInput) => api.post<{ detail: string }>('/api/me/password/', p) });
}
