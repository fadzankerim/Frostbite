import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router';

import { useMe } from '../api/auth';
import { useBadgeCatalog } from '../api/badges';
import { useStats, useTours, type DifficultyCode, type TourSummary } from '../api/public';
import { AltitudeTicker } from '../components/AltitudeTicker';
import { BadgeArt } from '../components/BadgeArt';
import { BadgeGallery } from '../components/Badges';
import { BJELASNICA, ContourField } from '../components/ContourField';
import { Faq, type FaqItem } from '../components/Faq';
import { Frosti } from '../components/Frosti';
import { MapView, tourPins } from '../components/MapView';
import { StepGuide } from '../components/StepGuide';
import { TourCard } from '../components/TourCard';
import { formatNumber } from '../lib/format';
import './pages.css';

const NO_FILTERS = {};
const DIFF_ORDER: DifficultyCode[] = ['LAKA', 'SREDNJA', 'TESKA', 'VRLO_TESKA'];
const CHALLENGE_M = 2000;

const MONTHS = ['januar', 'februar', 'mart', 'april', 'maj', 'juni', 'juli', 'avgust', 'septembar', 'oktobar', 'novembar', 'decembar'];

const FAQ: FaqItem[] = [
  { q: 'Šta je lista čekanja?', a: 'Kad je tura popunjena, prijava ide na listu čekanja. Ako se neko odjavi do roka, mjesto automatski dobija prvi s liste. Status prijave vidiš u „Moje prijave“.' },
  { q: 'Ko vidi moje zdravstvene napomene i hitni kontakt?', a: 'Samo ti i vodič ture na koju si prijavljen, i to do 7 dana nakon ture. Svaki vodičev pristup tim podacima se bilježi. Sistemski admin ih ne vidi.' },
  { q: 'Kako se odjavljujem s ture?', a: 'U „Moje prijave“ odaberi „Odjavi se“. Odjava je moguća do roka za prijavu, koji je naveden na stranici ture.' },
  { q: 'Mogu li se prijaviti na turu „samo za članove“?', a: 'Da, ako imaš važeće članstvo u društvu koje organizuje turu. Zahtjev za članstvo šalješ sa stranice društva, a odobrava ga admin društva.' },
  { q: 'Kako društvo postaje vidljivo?', a: 'Nakon registracije društvo čeka odobrenje sistemskog admina. Tek odobreno društvo i njegove objavljene ture vide svi posjetioci.' },
  { q: 'Ko vidi moje bedževe?', a: 'Samo ti, na svom profilu. Bedževe dodjeljuje server na osnovu stvarnih događaja, npr. prisustva koje je potvrdio vodič. Ne mogu se kupiti ni „nabiti“ prijavama.' },
];

/** Mala mapa narednih tura s brzim filterom težine (filtrira se u pregledaču, bez novih zahtjeva). */
function MiniMap({ tours, loading }: { tours: TourSummary[]; loading: boolean }) {
  const navigate = useNavigate();
  const [diff, setDiff] = useState<DifficultyCode | null>(null);
  const diffs = useMemo(() => {
    const seen = new Map<DifficultyCode, string>();
    for (const t of tours) seen.set(t.difficulty.code, t.difficulty.label);
    return DIFF_ORDER.filter((c) => seen.has(c)).map((c) => ({ code: c, label: seen.get(c)! }));
  }, [tours]);
  const pins = useMemo(() => tourPins(diff ? tours.filter((t) => t.difficulty.code === diff) : tours), [tours, diff]);

  return (
    <div className="mini-map">
      <div className="mini-map-side">
        <span className="label-mono"><span className="live-dot" />{loading ? 'Učitavanje' : `${pins.length} na mapi`}</span>
        <h2 id="map-title">Gdje idemo?</h2>
        <p className="muted">Pinovi su početne tačke narednih tura. Klik na pin otvara detalje.</p>
        <div className="chips-row" role="group" aria-label="Težina">
          <button type="button" className={`chip-btn${!diff ? ' is-on' : ''}`} aria-pressed={!diff} onClick={() => setDiff(null)}>Sve</button>
          {diffs.map((d) => (
            <button key={d.code} type="button" aria-pressed={diff === d.code}
              className={`chip-btn chip-${d.code.toLowerCase()}${diff === d.code ? ' is-on' : ''}`}
              onClick={() => setDiff(diff === d.code ? null : d.code)}>
              <span className="diff-dot" aria-hidden="true" />{d.label}
            </button>
          ))}
        </div>
        <Link className="link" to={diff ? `/ture?difficulty=${diff}` : '/ture'}>Otvori pretragu tura →</Link>
      </div>
      <div className="frame mini-map-frame">
        <div className="frame-map">
          <MapView label="Mapa narednih tura" pins={pins} onOpen={(id) => navigate(`/ture/${id}`)} />
        </div>
      </div>
    </div>
  );
}

export function HomePage() {
  const { data: me } = useMe();
  const user = me?.authenticated ? me.user : null;
  const stats = useStats();
  const tours = useTours(NO_FILTERS);
  const catalog = useBadgeCatalog();
  const featured = (tours.data ?? []).slice(0, 3);
  const month = MONTHS[new Date().getMonth()];
  const statItems = stats.data ? [
    { value: stats.data.tours, unit: '', label: 'Tura u ponudi' },
    { value: stats.data.clubs, unit: '', label: 'Društava' },
    { value: stats.data.km, unit: 'km', label: 'Ukupna dužina' },
    { value: stats.data.elevation, unit: 'm', label: 'Ukupni uspon' },
    ...(catalog.data ? [{ value: catalog.data.awardedTotal, unit: '', label: 'Osvojenih bedževa' }] : []),
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

      <section className="container home-section" aria-labelledby="how-title">
        <div className="section-head">
          <div>
            <span className="label-mono">Kako funkcioniše</span>
            <h2 id="how-title">Četiri koraka za svaku ulogu</h2>
          </div>
        </div>
        <StepGuide loggedIn={!!user} />
      </section>

      <section className="container home-section" aria-labelledby="map-title">
        <MiniMap tours={tours.data ?? []} loading={tours.isPending} />
      </section>

      <section className="container home-section challenge-wrap" aria-labelledby="challenge-title">
        <div className="challenge">
          <BadgeArt icon="altitude" tier={3} role="PLANINAR" size={96} className="challenge-badge" />
          <div className="challenge-copy">
            <span className="label-mono">Izazov mjeseca · {month}</span>
            <h2 id="challenge-title">Popni se {formatNumber(CHALLENGE_M)} m ovog mjeseca</h2>
            <p className="muted">
              Skupi uspon na turama s potvrđenim prisustvom. Usput se otključavaju bedževi „Visinac“ za 5.000 i 10.000 m.
            </p>
          </div>
          <div className="challenge-actions">
            <a className="btn btn-sm" href="#bedzevi">Pogledaj bedževe</a>
            {user && <Link className="btn btn-ghost btn-sm" to="/profil">Moj napredak</Link>}
          </div>
        </div>
      </section>

      <section className="container home-section" id="bedzevi" aria-labelledby="badges-gallery-title">
        <div className="section-head">
          <div>
            <span className="label-mono">Nagrade</span>
            <h2 id="badges-gallery-title">Bedževi koje možeš osvojiti</h2>
          </div>
        </div>
        <p className="muted section-lead">Za svaki završen korak, od prve ture do prvog odobrenog društva. Bedževe vidiš samo ti.</p>
        <BadgeGallery />
      </section>

      <section className="container home-section home-faq" aria-labelledby="faq-title">
        <div className="faq-head">
          <Frosti mood="think" size={88} />
          <div>
            <span className="label-mono">Pitanja</span>
            <h2 id="faq-title">Često postavljana pitanja</h2>
          </div>
        </div>
        <Faq items={FAQ} />
      </section>
    </>
  );
}
