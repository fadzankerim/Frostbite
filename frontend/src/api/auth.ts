import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';

import { api, setCsrfToken } from './client';

export type Roles = { systemAdmin: boolean; clubAdmin: boolean; guide: boolean };
export type User = { id: number; email: string; firstName: string; lastName: string; roles: Roles };
export type Me = { authenticated: true; user: User } | { authenticated: false; user: null };

export type LoginInput = { email: string; password: string };
export type RegisterInput = {
  email: string; firstName: string; lastName: string; phone: string; password: string; passwordConfirm: string;
};

export const ME_KEY = ['auth', 'me'] as const;
export const ANONYMOUS: Me = { authenticated: false, user: null };

/** Promjena sesije (prijava, odjava, istek): brišu se SVI podaci prethodne sesije, a "me" se
 *  postavlja na novo stanje. "me" se ne briše nego zamjenjuje, da komponente koje ga prate
 *  odmah vide promjenu. */
export function resetSession(qc: QueryClient, me: Me): void {
  qc.cancelQueries();
  qc.removeQueries({ predicate: (q) => q.queryKey[0] !== ME_KEY[0] });
  qc.setQueryData(ME_KEY, me);
}

/** Ko je prijavljen. Uloge služe samo za prikaz - server provjerava prava za svaki zahtjev. */
export function useMe() {
  return useQuery({
    queryKey: ME_KEY,
    queryFn: () => api.get<Me>('/api/auth/me/'),
    staleTime: Infinity,          // osvježava se eksplicitno (prijava, odjava, istek sesije)
    refetchOnWindowFocus: false,  // provjera ne smije sama produžavati sesiju
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: LoginInput) => api.post<Me & { csrfToken: string }>('/api/auth/login/', input),
    onSuccess: ({ csrfToken, ...me }) => {
      setCsrfToken(csrfToken);    // server je promijenio token pri prijavi
      resetSession(qc, me);       // ništa iz prethodne (anonimne ili tuđe) sesije
    },
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<null>('/api/auth/logout/'),
    onSettled: () => {
      setCsrfToken(null);
      resetSession(qc, ANONYMOUS);
    },
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: (input: RegisterInput) => api.post<{ detail: string }>('/api/auth/register/', input),
  });
}

export function displayName(user: User): string {
  return `${user.firstName} ${user.lastName}`.trim() || user.email;
}
