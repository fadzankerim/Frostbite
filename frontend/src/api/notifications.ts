// Postavke obavještenja i odjava iz emaila. Server odlučuje koje kategorije korisnik vidi i
// koji načini su dozvoljeni (sigurnosna kategorija se ne može isključiti).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from './client';

export type NotificationMode = 'odmah' | 'pregled' | 'iskljuceno';
export type NotificationCategory = {
  code: string; label: string; description: string; security: boolean;
  mode: NotificationMode; modes: { code: NotificationMode; label: string }[];
};

const KEY = ['me', 'notifications'] as const;

export function useNotificationSettings() {
  return useQuery({
    queryKey: KEY,
    queryFn: () => api.get<{ results: NotificationCategory[] }>('/api/me/notifications/').then((d) => d.results),
  });
}

export function useSaveNotificationSetting() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ code, mode }: { code: string; mode: NotificationMode }) =>
      api.put<{ results: NotificationCategory[]; detail: string }>('/api/me/notifications/', { [code]: mode }),
    onSuccess: (d) => qc.setQueryData(KEY, d.results),
  });
}

/** Odjava jednim klikom sa stranice iz emaila (token je potpisan na serveru). */
export function useUnsubscribe() {
  return useMutation({
    mutationFn: (token: string) => api.post<{ detail: string; category: string }>('/api/notifications/unsubscribe/', { token }),
  });
}
