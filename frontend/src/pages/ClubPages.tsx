import { Link, useParams } from 'react-router';

import { useMe } from '../api/auth';
import { ApiError } from '../api/client';
import { useRequestMembership } from '../api/hiker';
import { parseId, useClub, useClubs } from '../api/public';
import { Notice } from '../components/forms';
import { Frosti } from '../components/Frosti';
import { Loading } from '../components/guards';
import { SceneArt } from '../components/SceneArt';
import { TourCard } from '../components/TourCard';
import { mailtoHref, plural, telHref } from '../lib/format';
import { NotFoundPage } from './StatusPages';
import './pages.css';

/** "PD Bjelašnica" -> "BJ" (bez skraćenica PD/PK/PSD na početku). */
function initials(name: string): string {
  const words = name.split(/\s+/).filter((w) => w && !/^(P[DKS]?D?|HPD|PSD)$/i.test(w));
  const w = words.length ? words : name.split(/\s+/);
  return (w.length > 1 ? (w[0]![0] ?? '') + (w[1]![0] ?? '') : (w[0] ?? '').slice(0, 2)).toUpperCase();
}

export function ClubsPage() {
  const clubs = useClubs();
  const { data: me } = useMe();
  const canRequest = me?.authenticated && !me.user.roles.systemAdmin;
  return (
    <section className="container page">
      <span className="label-mono">Planinarska društva</span>
      <div className="section-head">
        <h1 className="page-title">Društva</h1>
        {canRequest && <Link className="btn btn-ghost btn-sm" to="/drustva/novo">+ Registruj društvo</Link>}
      </div>
      <p className="muted page-lead">Odobrena planinarska društva i njihove ture u narednih 30 dana.</p>

      {clubs.isPending && <div className="club-grid">{Array.from({ length: 3 }, (_, i) => <div key={i} className="skeleton" />)}</div>}
      {clubs.isError && <Notice kind="error">Društva nije moguće učitati.</Notice>}
      {clubs.data && clubs.data.length === 0 && (
        <div className="empty"><Frosti mood="think" size={96} /><p className="muted">Još nema odobrenih društava.</p></div>
      )}
      {clubs.data && (
        <ul className="club-grid">
          {clubs.data.map((c, i) => (
            <li key={c.id} className="club-card" style={{ animationDelay: `${Math.min(i, 8) * 50}ms` }}>
              <Link to={`/drustva/${c.id}`} className="club-card-link has-scene">
                <div className="club-card-art">
                  <SceneArt seed={c.id} variant="club" />
                  <span className="sticker club-initials mono" aria-hidden="true">{initials(c.name)}</span>
                </div>
                <span className="label-mono">{c.city}</span>
                <h3>{c.name}</h3>
                {c.description && <p className="muted club-desc">{c.description}</p>}
                <span className="mono club-count">
                  <span className="club-count-n">{c.toursCount}</span> {plural(c.toursCount, ['tura', 'ture', 'tura'])}
                  <span className="arrow" aria-hidden="true">→</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function MembershipAction({ clubId, canRequest, current }: { clubId: number; canRequest: boolean; current: { label: string; expired: boolean } | null }) {
  const { data: me } = useMe();
  const req = useRequestMembership(clubId);
  if (req.isSuccess) {
    return <span className="membership-done"><Frosti mood="happy" size={44} /><span>{req.data.detail}</span></span>;
  }
  return (
    <span className="chips">
      {current && <span className="chip chip-accent">{current.expired ? 'Članstvo isteklo' : current.label}</span>}
      {canRequest && (me?.authenticated ? (
        <button type="button" className="btn btn-ghost btn-sm" disabled={req.isPending} onClick={() => req.mutate()}>
          {req.isPending && <span className="spinner" aria-hidden="true" />}Zatraži članstvo
        </button>
      ) : (
        <Link className="btn btn-ghost btn-sm" to={`/prijava?next=${encodeURIComponent(`/drustva/${clubId}`)}`}>Prijavite se za članstvo</Link>
      ))}
      {req.error instanceof ApiError && <span className="field-error">{req.error.detail}</span>}
    </span>
  );
}

export function ClubDetailPage() {
  const { id } = useParams();
  const clubId = parseId(id);
  const club = useClub(clubId);

  if (clubId === null) return <NotFoundPage />;
  if (club.isPending) return <Loading label="Učitavanje društva" />;
  if (club.isError) {
    if (club.error instanceof ApiError && club.error.status === 404) return <NotFoundPage />;
    return <div className="container page"><Notice kind="error">Društvo nije moguće učitati.</Notice></div>;
  }
  const c = club.data;
  const mail = c.email ? mailtoHref(c.email) : null;
  const tel = c.phone ? telHref(c.phone) : null;

  return (
    <section className="container page">
      <Link to="/drustva" className="back label-mono">← Sva društva</Link>
      <div className="banner has-scene"><SceneArt seed={c.id} variant="club" width={800} /></div>
      <span className="label-mono">Društvo · {c.city}</span>
      <h1 className="page-title">{c.name}</h1>
      {c.description && <p className="prose page-lead">{c.description}</p>}

      <dl className="spec">
        {c.email && <div><dt className="label-mono">Email</dt><dd>{mail ? <a className="link" href={mail}>{c.email}</a> : c.email}</dd></div>}
        {c.phone && <div><dt className="label-mono">Telefon</dt><dd>{tel ? <a className="link" href={tel}>{c.phone}</a> : c.phone}</dd></div>}
        <div>
          <dt className="label-mono">Članstvo</dt>
          <dd><MembershipAction clubId={c.id} canRequest={c.canRequest} current={c.membership} /></dd>
        </div>
      </dl>

      <h2 className="section-title">Ture <span className="mono muted">({c.tours.length})</span></h2>
      {c.tours.length === 0
        ? <div className="empty"><Frosti mood="think" size={96} /><p className="muted">Društvo trenutno nema objavljenih tura u narednih 30 dana.</p></div>
        : <div className="tour-list">{c.tours.map((t, i) => <TourCard key={t.id} tour={t} index={i} />)}</div>}
    </section>
  );
}
