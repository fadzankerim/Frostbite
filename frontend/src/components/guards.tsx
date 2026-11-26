// Zaštita ruta na klijentu. OVO JE SAMO UX: prava provjerava server za svaki API zahtjev.
import type { ReactNode } from 'react';
import { Navigate, useLocation, useSearchParams } from 'react-router';

import { useMe, type Roles } from '../api/auth';
import { safeNext } from '../lib/safeNext';
import { Notice } from './forms';

export function Loading({ label = 'Učitavanje' }: { label?: string }) {
  return (
    <div className="center-screen" role="status" aria-live="polite">
      <div className="loading">
        <span className="spinner" aria-hidden="true" />
        <span className="label-mono">{label}</span>
      </div>
    </div>
  );
}

function MeError({ retry }: { retry: () => void }) {
  return (
    <div className="center-screen">
      <div className="stack-sm">
        <Notice kind="error">Server nije dostupan. Provjerite vezu i pokušajte ponovo.</Notice>
        <button type="button" className="btn btn-ghost" onClick={retry}>Pokušaj ponovo</button>
      </div>
    </div>
  );
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { data, isPending, isError, refetch } = useMe();
  const location = useLocation();
  if (isPending) return <Loading />;
  if (isError) return <MeError retry={() => void refetch()} />;
  if (!data.authenticated) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/prijava?next=${next}`} replace />;
  }
  return children;
}

export function RequireRole({ role, children }: { role: keyof Roles; children: ReactNode }) {
  const { data } = useMe();
  return (
    <RequireAuth>
      {data?.authenticated && data.user.roles[role] ? children : <Navigate to="/zabranjeno" replace />}
    </RequireAuth>
  );
}

/** Početna stranica prema ulozi (kao na starim stranicama): sistemski admin -> sistem,
 *  admin društva -> upravljanje, vodič -> vođenje, planinar -> početna. */
export function landingFor(roles: Roles): string {
  if (roles.systemAdmin) return '/sistem';
  if (roles.clubAdmin) return '/upravljanje';
  if (roles.guide) return '/vodic';
  return '/';
}

/** Prijava i registracija: prijavljeni korisnik ide dalje (na provjeren ?next= ili početnu svoje uloge). */
export function GuestOnly({ children }: { children: ReactNode }) {
  const { data, isPending } = useMe();
  const [params] = useSearchParams();
  if (isPending) return <Loading />;
  if (data?.authenticated) return <Navigate to={safeNext(params.get('next'), landingFor(data.user.roles))} replace />;
  return children;
}

/** Funkcionalnosti planinara: prijavljen korisnik koji nije sistemski admin (server isto provjerava). */
export function RequireHiker({ children }: { children: ReactNode }) {
  const { data } = useMe();
  return (
    <RequireAuth>
      {data?.authenticated && !data.user.roles.systemAdmin ? children : <Navigate to="/zabranjeno" replace />}
    </RequireAuth>
  );
}
