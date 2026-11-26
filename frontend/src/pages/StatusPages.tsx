import { Link, isRouteErrorResponse, useRouteError } from 'react-router';

import { ContourField } from '../components/ContourField';
import { Frosti, type FrostiMood } from '../components/Frosti';
import './pages.css';

function StatusPage({ code, title, text, mood = 'sad' }: { code: string; title: string; text: string; mood?: FrostiMood }) {
  return (
    <section className="status">
      <div className="status-map" aria-hidden="true"><ContourField interactive={false} seed={3} /></div>
      <div className="status-copy">
        <Frosti mood={mood} size={110} className="status-frosti" />
        <span className="label-mono">Greška · {code}</span>
        <h1>{title}</h1>
        <p className="muted">{text}</p>
        <Link className="btn" to="/">Nazad na početnu</Link>
      </div>
    </section>
  );
}

export function NotFoundPage() {
  return <StatusPage code="404" title="Ova staza ne postoji." text="Frosti je tražio svuda, ali ova stranica nije pronađena ili je premještena." />;
}

export function ForbiddenPage() {
  return <StatusPage code="403" mood="think" title="Pristup nije dozvoljen." text="Nemate prava za ovu stranicu." />;
}

/** Greška pri renderovanju: korisniku bez tehničkih detalja (ne otkrivamo internu strukturu). */
export function ErrorPage() {
  const err = useRouteError();
  if (isRouteErrorResponse(err) && err.status === 404) return <NotFoundPage />;
  return (
    <div className="error-root">
      <StatusPage code="500" title="Nešto je pošlo po zlu." text="Osvježite stranicu ili pokušajte kasnije." />
    </div>
  );
}
