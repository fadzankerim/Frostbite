import { Link, useParams } from 'react-router';

import { ApiError } from '../api/client';
import { parseId, useClub, useClubs } from '../api/public';
import { Notice } from '../components/forms';
import { Loading } from '../components/guards';
import { TourCard } from '../components/TourCard';
import { mailtoHref, plural, telHref } from '../lib/format';
import { NotFoundPage } from './StatusPages';
import './pages.css';

export function ClubsPage() {
  const clubs = useClubs();
  return (
    <section className="container page">
      <span className="label-mono">Planinarska društva</span>
      <h1 className="page-title">Društva</h1>
      <p className="muted page-lead">Odobrena planinarska društva i njihove ture u narednih 30 dana.</p>

      {clubs.isPending && <div className="club-grid">{Array.from({ length: 3 }, (_, i) => <div key={i} className="skeleton" />)}</div>}
      {clubs.isError && <Notice kind="error">Društva nije moguće učitati.</Notice>}
      {clubs.data && clubs.data.length === 0 && <p className="muted">Još nema odobrenih društava.</p>}
      {clubs.data && (
        <ul className="club-grid">
          {clubs.data.map((c, i) => (
            <li key={c.id} className="club-card" style={{ animationDelay: `${Math.min(i, 8) * 50}ms` }}>
              <Link to={`/drustva/${c.id}`} className="club-card-link">
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
      <span className="label-mono">Društvo · {c.city}</span>
      <h1 className="page-title">{c.name}</h1>
      {c.description && <p className="prose page-lead">{c.description}</p>}

      <dl className="spec">
        {c.email && <div><dt className="label-mono">Email</dt><dd>{mail ? <a className="link" href={mail}>{c.email}</a> : c.email}</dd></div>}
        {c.phone && <div><dt className="label-mono">Telefon</dt><dd>{tel ? <a className="link" href={tel}>{c.phone}</a> : c.phone}</dd></div>}
        <div>
          <dt className="label-mono">Članstvo</dt>
          <dd className="chips">
            {c.membership
              ? <span className="chip chip-accent">{c.membership.label}</span>
              : <a className="btn btn-ghost btn-sm" href={`/drustva/${c.id}/`}>Zatraži članstvo</a>}
          </dd>
        </div>
      </dl>

      <h2 className="section-title">Ture <span className="mono muted">({c.tours.length})</span></h2>
      {c.tours.length === 0
        ? <p className="muted">Društvo trenutno nema objavljenih tura u narednih 30 dana.</p>
        : <div className="tour-list">{c.tours.map((t, i) => <TourCard key={t.id} tour={t} index={i} />)}</div>}
    </section>
  );
}
