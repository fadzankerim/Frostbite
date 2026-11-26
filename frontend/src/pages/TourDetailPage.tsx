import { useState } from 'react';
import { Link, useParams } from 'react-router';

import { useMe } from '../api/auth';
import { ApiError } from '../api/client';
import { parseId, useTour } from '../api/public';
import { AltitudeTicker } from '../components/AltitudeTicker';
import { Notice } from '../components/forms';
import { Loading } from '../components/guards';
import { MapView } from '../components/MapView';
import { DifficultyBadge, SpotsBar } from '../components/TourCard';
import { countdown, formatLong, formatNumber, formatPrice, toDms } from '../lib/format';
import { NotFoundPage } from './StatusPages';
import './pages.css';

function CopyButton({ text }: { text: string }) {
  const [state, setState] = useState<'idle' | 'ok' | 'err'>('idle');
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setState('ok');
    } catch {
      setState('err');
    }
    window.setTimeout(() => setState('idle'), 1600);
  }
  return (
    <button type="button" className="btn btn-ghost btn-sm" onClick={copy} aria-live="polite">
      {state === 'ok' ? 'Kopirano ✓' : state === 'err' ? 'Nije uspjelo' : 'Kopiraj'}
    </button>
  );
}

export function TourDetailPage() {
  const { id } = useParams();
  const tourId = parseId(id);
  const tour = useTour(tourId);
  const { data: me } = useMe();

  if (tourId === null) return <NotFoundPage />;
  if (tour.isPending) return <Loading label="Učitavanje ture" />;
  if (tour.isError) {
    if (tour.error instanceof ApiError && tour.error.status === 404) return <NotFoundPage />;
    return <div className="container page"><Notice kind="error">Turu nije moguće učitati. Pokušajte ponovo.</Notice></div>;
  }
  const t = tour.data;
  const start = t.route[0] ?? null;
  const coords = start ? `${start[0].toFixed(6)}, ${start[1].toFixed(6)}` : null;
  const gmaps = start ? `https://www.google.com/maps/search/?api=1&query=${start[0].toFixed(6)},${start[1].toFixed(6)}` : null;
  const directions = start ? `https://www.google.com/maps/dir/?api=1&destination=${start[0].toFixed(6)},${start[1].toFixed(6)}` : null;
  const left = countdown(t.startAt);
  const legacyUrl = `/ture/${t.id}/`;

  return (
    <div className="container detail-page">
      <Link to="/ture" className="back label-mono">← Sve ture</Link>

      <header className="detail-head">
        <div className="detail-badges">
          <DifficultyBadge code={t.difficulty.code} label={t.difficulty.label} />
          {t.membersOnly && <span className="label-mono tag">Samo za članove</span>}
          {left && <span className="label-mono tag tag-accent">Polazak za {left}</span>}
        </div>
        <h1 className="detail-title">{t.name}</h1>
        <p className="muted">
          <Link className="link" to={`/drustva/${t.club.id}`}>{t.club.name}</Link>
          {t.region ? ` · ${t.region}` : ''}
        </p>
      </header>

      <div className="detail-grid">
        <div className="detail-main">
          <div className="frame detail-map">
            <div className="frame-bar">
              <span className="label-mono">Ruta · {t.route.length ? `${t.route.length} tačaka` : 'nije ucrtana'}</span>
              {start && <span className="label-mono hide-sm">{toDms(start[0], 'N', 'S')} {toDms(start[1], 'E', 'W')}</span>}
            </div>
            <div className="frame-map">
              {t.route.length >= 2
                ? <MapView label={`Mapa rute ture ${t.name}`} route={t.route} />
                : <div className="map-empty"><span className="label-mono">Ruta za ovu turu još nije ucrtana</span></div>}
            </div>
          </div>

          {coords && (
            <section className="gps">
              <div>
                <span className="label-mono">GPS koordinate polaska</span>
                <p className="mono gps-coords">{coords}</p>
                <p className="muted gps-meta">{t.meetingPoint}</p>
              </div>
              <div className="gps-actions">
                <CopyButton text={coords} />
                {directions && <a className="btn btn-ghost btn-sm" href={directions} target="_blank" rel="noopener noreferrer">Navigacija ↗</a>}
                {gmaps && <a className="btn btn-ghost btn-sm" href={gmaps} target="_blank" rel="noopener noreferrer">Google mape ↗</a>}
                <a className="btn btn-ghost btn-sm" href={`/ture/${t.id}/ruta.gpx`} download>GPX</a>
              </div>
            </section>
          )}

          <ul className="stat-grid">
            <li><AltitudeTicker value={t.lengthKm} unit="km" duration={900} decimals={t.lengthKm % 1 ? 1 : 0} /><span className="label-mono">Dužina</span></li>
            <li><AltitudeTicker value={t.elevationGainM} unit="m" duration={1100} /><span className="label-mono">Uspon</span></li>
            <li><span className="mono altitude">{formatNumber(t.durationH)}<span className="altitude-unit"> h</span></span><span className="label-mono">Trajanje</span></li>
            <li><span className="mono altitude price">{formatPrice(t.price)}</span><span className="label-mono">Cijena</span></li>
          </ul>

          {t.description && (
            <section className="prose-block"><h2>O turi</h2><p className="prose">{t.description}</p></section>
          )}
          {t.requiredEquipment && (
            <section className="prose-block"><h2>Potrebna oprema</h2><p className="prose">{t.requiredEquipment}</p></section>
          )}
        </div>

        <aside className="detail-side">
          <div className="side-card">
            <dl className="facts">
              <div><dt className="label-mono">Polazak</dt><dd>{formatLong(t.startAt)}</dd></div>
              <div><dt className="label-mono">Okupljanje</dt><dd>{t.meetingPoint}</dd></div>
              <div><dt className="label-mono">Rok prijave</dt><dd>{formatLong(t.registrationDeadline)}</dd></div>
              <div><dt className="label-mono">Vodič</dt><dd>{t.guides.length ? t.guides.join(', ') : 'Još nije određen'}</dd></div>
            </dl>
            <SpotsBar free={t.freeSpots} max={t.maxParticipants} />

            {t.myRegistration ? (
              <Notice kind="ok">
                {t.myRegistration.status === 'PRIJAVLJEN' ? 'Prijavljeni ste na ovu turu.' : 'Na listi ste čekanja.'}
              </Notice>
            ) : t.deadlinePassed ? (
              <Notice>Rok za prijavu je istekao.</Notice>
            ) : t.canRegister ? (
              <>
                <a className="btn btn-accent btn-block" href={legacyUrl}>
                  {t.freeSpots > 0 ? 'Prijavi se' : 'Upiši me na listu čekanja'} <span className="arrow" aria-hidden="true">→</span>
                </a>
                {!me?.authenticated && <p className="field-hint">Za prijavu je potreban nalog.</p>}
              </>
            ) : null}
          </div>
        </aside>
      </div>
    </div>
  );
}
