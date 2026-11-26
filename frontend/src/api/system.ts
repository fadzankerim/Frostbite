// Panel sistemskog admina (F29-F31). Server dozvoljava samo sistemskom adminu.
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from './client';

type Coded = { code: string; label: string };
type Page<T> = { page: number; pages: number; total: number; results: T[] };

export type SystemDashboard = {
  kpi: { users: number; newUsers: number; clubs: number; pendingClubs: number; toursActive: number; registrations: number };
  security: { failed: number; lockouts: number; lockedNow: number; blocked: number; personalDataAccess: number };
  logins: { label: string; value: number }[];
  fails: { label: string; value: number }[];
  tourStatus: { label: string; count: number }[];
  pendingClubs: { id: number; name: string; city: string; createdAt: string }[];
  events: AuditEntry[];
};
export type SysClub = {
  id: number; name: string; city: string; createdAt: string; status: Coded;
  createdBy: { name: string; email: string }; actions: ('approve' | 'reject' | 'suspend')[];
};
export type SysUser = {
  id: number; email: string; firstName: string; lastName: string; isActive: boolean; isSystemAdmin: boolean;
  dateJoined: string; locked: boolean; isSelf: boolean;
};
export type AuditEntry = {
  id: number; action: string; entity?: string; entityId?: string; details: string; ip: string | null;
  createdAt: string; user: string | null;
};

const qs = (params: Record<string, string | number | undefined>) => {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== '') p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : '';
};

export const useSystemDashboard = () =>
  useQuery({ queryKey: ['system', 'dashboard'], queryFn: () => api.get<SystemDashboard>('/api/system/') });

export const useSystemClubs = () =>
  useQuery({ queryKey: ['system', 'clubs'], queryFn: () => api.get<{ pending: SysClub[]; others: SysClub[] }>('/api/system/clubs/') });

export const useSystemUsers = (q: string, page: number) =>
  useQuery({
    queryKey: ['system', 'users', q, page],
    queryFn: () => api.get<Page<SysUser>>(`/api/system/users/${qs({ q, page })}`),
    placeholderData: keepPreviousData,
  });

export const useAudit = (action: string, page: number) =>
  useQuery({
    queryKey: ['system', 'audit', action, page],
    queryFn: () => api.get<Page<AuditEntry>>(`/api/system/audit/${qs({ action, page })}`),
    placeholderData: keepPreviousData,
  });

function useSystemMutation<V>(fn: (v: V) => Promise<{ detail: string }>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSettled: () => Promise.all([qc.invalidateQueries({ queryKey: ['system'] }), qc.invalidateQueries({ queryKey: ['clubs'] }), qc.invalidateQueries({ queryKey: ['tours'] })]),
  });
}

export const useDecideClub = () =>
  useSystemMutation(({ id, action }: { id: number; action: string }) => api.post(`/api/system/clubs/${id}/decide/`, { action }));
export const useToggleUser = () =>
  useSystemMutation((id: number) => api.post(`/api/system/users/${id}/toggle/`));
