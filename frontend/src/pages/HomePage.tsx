import { Link } from 'react-router';

import { useMe } from '../api/auth';
import { useStats, useTours } from '../api/public';
import { AltitudeTicker } from '../components/AltitudeTicker';
import { BJELASNICA, ContourField } from '../components/ContourField';
import { Frosti } from '../components/Frosti';
import { TourCard } from '../components/TourCard';
import './pages.css';

const NO_FILTERS = {};

const FEATURES = [
  { n: '01', icon: 'boot', title: 'Za planinare', text: 'Pronađite ture na mapi, prijavite se na jednu ili više njih i pratite svoje prijave.' },
  { n: '02', icon: 'compass', title: 'Za vodiče', text: 'Prijavite se za vođenje, imajte uvid u učesnike i evidentirajte prisustvo.' },
  { n: '03', icon: 'tent', title: 'Za društva', text: 'Objavljujte ture, crtajte rute i upravljajte vodičima i članstvima.' },
] as const;

/** Male crtane ikonice za uloge (pune boje, obris). */
function FunIcon({ name }: { name: 'boot' | 'compass' | 'tent' }) {
  return (
    <svg className={`fun-icon fun-icon-${name}`} viewBox="0 0 48 48" aria-hidden="true" focusable="false">
      {name === 'boot' && (<>
        <path className="fi-a" d="M14 8 L28 8 L28 26 L40 30 Q44 32 44 37 L44 40 L8 40 L8 34 L12 32 Z" />
        <path className="fi-b" d="M8 40 L44 40 L44 44 L8 44 Z" />
        <path className="fi-line" d="M16 15 L24 15 M16 21 L24 21" />
      </>)}
      {name === 'compass' && (<>
        <circle className="fi-a" cx="24" cy="24" r="17" />
        <path className="fi-b" d="M24 10 L29 24 L24 38 L19 24 Z" />
        <path className="fi-c" d="M24 10 L29 24 L19 24 Z" />
        <circle className="fi-dot" cx="24" cy="24" r="2.4" />
      </>)}
      {name === 'tent' && (<>
        <path className="fi-a" d="M4 40 L24 8 L44 40 Z" />
        <path className="fi-b" d="M24 8 L32 40 L16 40 Z" />
        <path className="fi-line" d="M4 40 L44 40 M24 8 L24 3" />
        <path className="fi-c" d="M24 3 L31 5 L24 7 Z" />
      </>)}
    </svg>
  );
}

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
            <div className="frame-map hero-map">
              <ContourField />
              <div className="peek-frosti"><Frosti mood="wave" size={104} /></div>
            </div>
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
            <div className="feature-top"><FunIcon name={f.icon} /><span className="label-mono feature-n">{f.n}</span></div>
            <h3>{f.title}</h3>
            <p className="muted">{f.text}</p>
          </article>
        ))}
      </section>
    </>
  );
}
