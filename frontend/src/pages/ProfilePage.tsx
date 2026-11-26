import { displayName, useMe } from '../api/auth';
import './pages.css';

const ROLE_LABELS = { systemAdmin: 'Sistemski admin', clubAdmin: 'Admin društva', guide: 'Vodič' } as const;

export function ProfilePage() {
  const { data } = useMe();
  if (!data?.authenticated) return null;     // RequireAuth je već preusmjerio
  const { user } = data;
  const roles = (Object.keys(ROLE_LABELS) as (keyof typeof ROLE_LABELS)[]).filter((r) => user.roles[r]);

  return (
    <section className="container page">
      <span className="label-mono">Profil · ID {String(user.id).padStart(5, '0')}</span>
      <h1 className="page-title">{displayName(user)}</h1>

      <dl className="spec">
        <div><dt className="label-mono">Email</dt><dd>{user.email}</dd></div>
        <div>
          <dt className="label-mono">Uloge</dt>
          <dd className="chips">
            <span className="chip">Planinar</span>
            {roles.map((r) => <span key={r} className="chip chip-accent">{ROLE_LABELS[r]}</span>)}
          </dd>
        </div>
      </dl>

      <div className="page-actions">
        <a className="btn btn-ghost" href="/nalog/profil/">Uredi profil</a>
        <a className="btn btn-ghost" href="/nalog/lozinka/">Promijeni lozinku</a>
      </div>
      <p className="muted page-note">Uređivanje profila se još radi u klasičnom prikazu.</p>
    </section>
  );
}
