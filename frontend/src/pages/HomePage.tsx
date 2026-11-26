import { Link } from 'react-router';

import { useMe } from '../api/auth';
import { useStats, useTours } from '../api/public';
import { AltitudeTicker } from '../components/AltitudeTicker';
import { BJELASNICA, ContourField } from '../components/ContourField';
import { TourCard } from '../components/TourCard';
import './pages.css';

const NO_FILTERS = {};

const FEATURES = [
  { n: '01', title: 'Za planinare', text: 'Pronađite ture na mapi, prijavite se na jednu ili više njih i pratite svoje prijave.' },
  { n: '02', title: 'Za vodiče', text: 'Prijavite se za vođenje, imajte uvid u učesnike i evidentirajte prisustvo.' },
  { n: '03', title: 'Za društva', text: 'Objavljujte ture, crtajte rute i upravljajte vodičima i članstvima.' },
];

export function HomePage() {
  const { data: me } = useMe();
  const user = me?.authenticated ? me.user : null;
  const stats = useStats();
  const tours = useTours(NO_FILTERS);
  const featured = (tours.data ?? []).slice(0, 3);
  const statItems = stats.data ? [
    { value: stats.data.tours, unit: '', label: 'Tura u ponudi' },
    { value: stats.data.clubs, unit: '', label: 'Društava' },
    { value: stats.data.km, unit: 'km', label: 'Ukupna dužina' },
    { value: stats.data.elevation, unit: 'm', label: 'Ukupni uspon' },
  ] : [];

  return (
    <>
      <section className="hero">
        <div className="container hero-inner">
          <div className="hero-copy">
            <span className="label-mono"><span className="live-dot" /> Planinarske ture · Bosna i Hercegovina</span>
            <h1>Ture, vodiči i društva na jednom mjestu.</h1>
            <p className="hero-lead muted">
              Frostbite povezuje planinarska društva, vodiče i planinare. Od prijave na turu do evidencije prisustva na vrhu.
            </p>
            <div className="hero-actions">
              <Link className="btn btn-accent" to="/ture">Pogledaj ture <span className="arrow" aria-hidden="true">→</span></Link>
              {user
                ? <Link className="btn btn-ghost" to="/profil">Moj profil</Link>
                : <Link className="btn btn-ghost" to="/registracija">Registruj se</Link>}
            </div>
          </div>

          <div className="hero-visual frame">
            <div className="frame-bar">
              <span className="label-mono">Topo · {BJELASNICA.name}</span>
              <span className="label-mono">{BJELASNICA.lat}° N · {BJELASNICA.lon}° E</span>
            </div>
            <div className="frame-map hero-map"><ContourField /></div>
            <div className="frame-bar">
              <span className="label-mono">Ekvidistanca 100 m</span>
              <span className="label-mono hide-sm">Pomjerite kursor preko karte</span>
            </div>
          </div>
        </div>
      </section>

      <section className="container peaks" aria-labelledby="stats-title">
        <h2 id="stats-title" className="label-mono"><span className="live-dot" />Narednih 30 dana</h2>
        <ul className="peaks-list stats-list">
          {stats.isPending && Array.from({ length: 4 }, (_, i) => <li key={i} className="peak"><div className="skeleton skeleton-sm" /></li>)}
          {statItems.map((s) => (
            <li key={s.label} className="peak">
              <AltitudeTicker value={s.value} unit={s.unit} />
              <div className="label-mono">{s.label}</div>
            </li>
          ))}
        </ul>
      </section>

      {featured.length > 0 && (
        <section className="container featured" aria-labelledby="featured-title">
          <div className="section-head">
            <h2 id="featured-title">Najbliže ture</h2>
            <Link className="link" to="/ture">Sve ture →</Link>
          </div>
          <div className="tour-list">{featured.map((t, i) => <TourCard key={t.id} tour={t} index={i} />)}</div>
        </section>
      )}

      <section className="container features" aria-label="Uloge">
        {FEATURES.map((f) => (
          <article key={f.n} className="feature">
            <span className="label-mono feature-n">{f.n}</span>
            <h3>{f.title}</h3>
            <p className="muted">{f.text}</p>
          </article>
        ))}
      </section>
    </>
  );
}
