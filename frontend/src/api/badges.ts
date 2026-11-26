// Bedževi: javni katalog i vlastiti bedževi. Dodjeljuje ih isključivo server; frontend samo prikazuje.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useMe } from './auth';
import { api } from './client';

export type BadgeRole = 'PLANINAR' | 'VODIC' | 'ADMIN_DRUSTVA' | 'SISTEM';
export type Badge = { code: string; name: string; description: string; role: BadgeRole; tier: number; icon: string };
export type MyBadge = Badge & { earned: boolean; awardedAt: string | null; seen: boolean; progress: number; goal: number };

export const MY_BADGES_KEY = ['me', 'badges'] as const;

export function useBadgeCatalog() {
  return useQuery({
    queryKey: ['badges', 'catalog'],
    queryFn: () => api.get<{ results: Badge[]; awardedTotal: number }>('/api/badges/'),
    staleTime: 5 * 60_000,
  });
}

/** Vlastiti bedževi; samo za prijavljenog korisnika. Osvježava se nakon svake uspješne radnje
 *  (MutationCache u main.tsx), jer radnja može donijeti novi bedž. */
export function useMyBadges() {
  const { data: me } = useMe();
  return useQuery({
    queryKey: MY_BADGES_KEY,
    queryFn: () => api.get<{ results: MyBadge[] }>('/api/me/badges/').then((d) => d.results),
    enabled: !!me?.authenticated,
  });
}

export function useMarkBadgesSeen() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<{ updated: number }>('/api/me/badges/seen/'),
    meta: { skipBadgeRefresh: true },
    onSuccess: () => qc.setQueryData<MyBadge[]>(MY_BADGES_KEY, (old) => old?.map((b) => ({ ...b, seen: true }))),
  });
}
