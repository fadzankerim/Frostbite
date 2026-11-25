import { Link } from 'react-router';

import { useMe } from '../api/auth';
import { AltitudeTicker } from '../components/AltitudeTicker';
import { BJELASNICA, ContourField } from '../components/ContourField';
import './pages.css';

const PEAKS = [
  { name: 'Maglić', value: 2386, note: 'Najviši vrh BiH' },
  { name: 'Čvrsnica', value: 2228, note: 'Pločno' },
  { name: 'Bjelašnica', value: 2067, note: 'Olimpijska planina' },
];

const FEATURES = [
  { n: '01', title: 'Za planinare', text: 'Pronađite ture na mapi, prijavite se na jednu ili više njih i pratite svoje prijave.' },
  { n: '02', title: 'Za vodiče', text: 'Prijavite se za vođenje, imajte uvid u učesnike i evidentirajte prisustvo.' },
  { n: '03', title: 'Za društva', text: 'Objavljujte ture, crtajte rute i upravljajte vodičima i članstvima.' },
];

export function HomePage() {
  const { data: me } = useMe();
  const user = me?.authenticated ? me.user : null;

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
              <a className="btn btn-accent" href="/ture/">Pogledaj ture <span className="arrow" aria-hidden="true">→</span></a>
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

      <section className="container peaks" aria-labelledby="peaks-title">
        <h2 id="peaks-title" className="label-mono">Najviši vrhovi</h2>
        <ul className="peaks-list">
          {PEAKS.map((p) => (
            <li key={p.name} className="peak">
              <AltitudeTicker value={p.value} />
              <div>
                <div className="peak-name">{p.name}</div>
                <div className="label-mono">{p.note}</div>
              </div>
            </li>
          ))}
        </ul>
      </section>

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
