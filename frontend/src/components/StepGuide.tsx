// "Kako funkcioniše": interaktivni vodič u koracima za tri uloge (planinar, vodič, društvo).
// Kartice uloga su role="tablist" (strelice, Home, End); koraci se mijenjaju dugmadima "Dalje"/"Nazad",
// klikom na broj koraka, strelicama dok je fokus na koracima i automatski svakih nekoliko sekundi.
// Automatsko prebacivanje se pauzira na hover ili fokus i gasi uz prefers-reduced-motion.
import { useEffect, useId, useRef, useState, useSyncExternalStore, type KeyboardEvent } from 'react';
import { Link } from 'react-router';

import { cycle, keyToIndex } from '../lib/nav';
import { BadgeArt, Glyph } from './BadgeArt';
import { Frosti, type FrostiMood } from './Frosti';
import { SceneArt } from './SceneArt';
import './steps.css';

type Step = { icon: string; title: string; text: string; mood: FrostiMood };
type Flow = { id: string; label: string; icon: 'boot' | 'compass' | 'tent'; steps: Step[]; cta: { to: string; label: string } };

const FLOWS: Flow[] = [
  {
    id: 'planinar', label: 'Planinar', icon: 'boot', cta: { to: '/ture', label: 'Pogledaj ture' },
    steps: [
      { icon: 'compass', mood: 'think', title: 'Pronađi turu na mapi', text: 'Filtriraj po težini, datumu i društvu. Svaka tura ima rutu, uspon i broj slobodnih mjesta.' },
      { icon: 'check', mood: 'wave', title: 'Prijavi se jednim klikom', text: 'Prijavi se na jednu turu ili odaberi više njih odjednom. Kad je tura puna, ideš na listu čekanja.' },
      { icon: 'boot', mood: 'happy', title: 'Idi na turu', text: 'Na dan ture vodič evidentira prisustvo. Do roka se možeš i odjaviti, a mjesto dobija prvi s liste čekanja.' },
      { icon: 'badge', mood: 'happy', title: 'Osvoji bedž', text: 'Za prvu turu, prvih 5.000 m uspona ili sve četiri težine dobijaš bedž koji vidiš samo ti.' },
    ],
  },
  {
    id: 'vodic', label: 'Vodič', icon: 'compass', cta: { to: '/registracija', label: 'Registruj se' },
    steps: [
      { icon: 'flag', mood: 'wave', title: 'Prijavi se za vođenje', text: 'Vidiš ture svog društva koje još nemaju vodiča. Admin društva odobrava prijavu.' },
      { icon: 'people', mood: 'think', title: 'Upoznaj učesnike', text: 'Lične podatke učesnika, poput hitnog kontakta, vidiš samo ti, i to do 7 dana nakon ture. Svaki pristup se bilježi.' },
      { icon: 'check', mood: 'happy', title: 'Evidentiraj prisustvo', text: 'Na dan ture označiš ko je došao. Tako planinari dobijaju zasluženo priznanje.' },
      { icon: 'book', mood: 'happy', title: 'Pošalji izvještaj', text: 'Kratak izvještaj zatvara turu, a ona prelazi u status održane.' },
    ],
  },
  {
    id: 'drustvo', label: 'Društvo', icon: 'tent', cta: { to: '/drustva/novo', label: 'Registruj društvo' },
    steps: [
      { icon: 'house', mood: 'wave', title: 'Registruj društvo', text: 'Pošalji zahtjev. Sistemski admin ga provjerava, a nakon odobrenja društvo postaje vidljivo.' },
      { icon: 'route', mood: 'think', title: 'Kreiraj turu i nacrtaj rutu', text: 'Rutu nacrtaj na mapi ili uvezi GPX datoteku. Tura ostaje nacrt dok je ne objaviš.' },
      { icon: 'megaphone', mood: 'happy', title: 'Objavi i dodijeli vodiča', text: 'Objavljena tura je javna. Vodiča biraš među prijavljenim vodičima društva.' },
      { icon: 'chart', mood: 'happy', title: 'Prati analitiku', text: 'Popunjenost, prijave po mjesecima i procjena prihoda na jednom mjestu.' },
    ],
  },
];

const AUTO_MS = 6000;

function subscribeMotion(cb: () => void) {
  const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
  mq.addEventListener('change', cb);
  return () => mq.removeEventListener('change', cb);
}
const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/** Male crtane ikonice za uloge (pune boje, obris). */
function FunIcon({ name }: { name: Flow['icon'] }) {
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

export function StepGuide({ loggedIn = false }: { loggedIn?: boolean }) {
  const uid = useId();
  const [role, setRole] = useState(0);
  const [step, setStep] = useState(0);
  const [hover, setHover] = useState(false);
  const [focused, setFocused] = useState(false);
  const reduced = useSyncExternalStore(subscribeMotion, reducedMotion, () => true);
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  const flow = FLOWS[role]!;
  const s = flow.steps[step]!;
  const n = flow.steps.length;
  const last = step === n - 1;
  const paused = hover || focused || reduced;

  // automatsko prebacivanje koraka (ponovo se pokreće pri svakoj promjeni koraka)
  useEffect(() => {
    if (paused) return;
    const t = window.setTimeout(() => setStep((i) => cycle(i, 1, n)), AUTO_MS);
    return () => window.clearTimeout(t);
  }, [paused, step, role, n]);

  function selectRole(i: number) {
    setRole(i);
    setStep(0);
  }

  function onTabKey(e: KeyboardEvent<HTMLButtonElement>) {
    const next = keyToIndex(e.key, role, FLOWS.length);
    if (next === null) return;
    e.preventDefault();
    selectRole(next);
    tabs.current[next]?.focus();
  }

  function onStepsKey(e: KeyboardEvent<HTMLElement>) {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    e.preventDefault();
    setStep((i) => Math.min(n - 1, Math.max(0, i + (e.key === 'ArrowRight' ? 1 : -1))));
  }

  const cta = loggedIn && flow.cta.to === '/registracija' ? { to: '/profil', label: 'Moj profil' } : flow.cta;

  return (
    <div
      className="step-guide"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onFocus={() => setFocused(true)}
      onBlur={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setFocused(false); }}
    >
      <div className="step-tabs" role="tablist" aria-label="Uloga">
        {FLOWS.map((f, i) => (
          <button
            key={f.id}
            ref={(el) => { tabs.current[i] = el; }}
            type="button"
            role="tab"
            id={`${uid}-tab-${f.id}`}
            aria-selected={i === role}
            aria-controls={`${uid}-panel`}
            tabIndex={i === role ? 0 : -1}
            className={`step-tab${i === role ? ' is-on' : ''}`}
            onClick={() => selectRole(i)}
            onKeyDown={onTabKey}
          >
            <FunIcon name={f.icon} />
            <span>{f.label}</span>
          </button>
        ))}
      </div>

      <div className="step-panel" role="tabpanel" id={`${uid}-panel`} aria-labelledby={`${uid}-tab-${flow.id}`}>
        <div className="step-art" aria-hidden="true">
          <SceneArt seed={role * 10 + step + 3} variant="tour" width={320} className="step-scene" />
          <div key={`${role}-${step}`} className="step-sticker sticker">
            {s.icon === 'badge'
              ? <BadgeArt icon="peak" tier={1} role="PLANINAR" size={64} />
              : <Glyph icon={s.icon} size={52} />}
          </div>
          <Frosti mood={s.mood} size={78} className="step-frosti" />
        </div>

        <div className="step-copy">
          <ol className="step-dots" aria-label="Koraci" onKeyDown={onStepsKey}>
            {flow.steps.map((st, i) => (
              <li key={st.title}>
                <button type="button" className={`step-dot mono${i === step ? ' is-on' : ''}${i < step ? ' is-done' : ''}`}
                  aria-current={i === step ? 'step' : undefined} aria-label={`Korak ${i + 1}: ${st.title}`}
                  onClick={() => setStep(i)}>
                  {i + 1}
                </button>
              </li>
            ))}
          </ol>
          <div key={`${role}-${step}`} className="step-text" aria-live={paused ? 'polite' : 'off'}>
            <span className="label-mono">{flow.label} · korak {step + 1} od {n}</span>
            <h3>{s.title}</h3>
            <p className="muted">{s.text}</p>
          </div>
          <div className="step-actions">
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setStep((i) => Math.max(0, i - 1))}
              disabled={step === 0}>
              <span aria-hidden="true">←</span> Nazad
            </button>
            {last
              ? <Link className="btn btn-accent btn-sm" to={cta.to}>{cta.label} <span aria-hidden="true">→</span></Link>
              : <button type="button" className="btn btn-sm" onClick={() => setStep((i) => Math.min(n - 1, i + 1))}>
                Dalje <span aria-hidden="true">→</span>
              </button>}
          </div>
          {!reduced && (
            <div className={`step-timer${paused ? ' is-paused' : ''}`} aria-hidden="true">
              <span key={`${role}-${step}`} style={{ animationDuration: `${AUTO_MS}ms` }} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
