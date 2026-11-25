// Indikator sesije u zaglavlju: koliko je ostalo do isteka (30 min neaktivnosti na serveru).
// Kad dođe do nule, provjerava sesiju na serveru i, ako je istekla, vodi na prijavu.
// Klik na indikator produžava sesiju (jedan zahtjev prema serveru).
import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { useLocation, useNavigate } from 'react-router';

import { ME_KEY, resetSession, type Me } from '../api/auth';
import { api, setCsrfToken } from '../api/client';
import { formatClock, getLastActivity, secondsLeft, subscribeActivity } from '../lib/session';

const WARN_SECONDS = 120;
const EXPIRED_NOTICE = 'Sesija je istekla zbog neaktivnosti. Prijavite se ponovo.';

export function SessionIndicator() {
  const last = useSyncExternalStore(subscribeActivity, getLastActivity);
  const [now, setNow] = useState(() => Date.now());
  const qc = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const checking = useRef(false);

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const left = secondsLeft(now, last);

  useEffect(() => {
    if (left > 0 || checking.current) return;
    checking.current = true;
    api.get<Me>('/api/auth/me/')
      .then((me) => {
        if (me.authenticated) {
          qc.setQueryData(ME_KEY, me);      // aktivnost u drugom tabu je produžila sesiju
          return;
        }
        setCsrfToken(null);
        resetSession(qc, me);
        const next = location.pathname + location.search;
        navigate(`/prijava?next=${encodeURIComponent(next)}`, { replace: true, state: { notice: EXPIRED_NOTICE } });
      })
      .catch(() => undefined)
      .finally(() => { checking.current = false; });
  }, [left, qc, navigate, location.pathname, location.search]);

  function extend() {
    api.get<Me>('/api/auth/me/').then((me) => qc.setQueryData(ME_KEY, me)).catch(() => undefined);
  }

  const state = left <= WARN_SECONDS ? 'warn' : 'ok';
  return (
    <button
      type="button"
      className={`session session-${state}`}
      onClick={extend}
      title="Sesija ističe nakon 30 minuta neaktivnosti. Kliknite za produženje."
    >
      <span className="session-dot" aria-hidden="true" />
      <span className="label-mono">Sesija</span>
      <span className="mono session-time" aria-live={state === 'warn' ? 'polite' : 'off'}>{formatClock(left)}</span>
    </button>
  );
}
