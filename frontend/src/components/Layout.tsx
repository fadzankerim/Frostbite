import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router';

import { displayName, useLogout, useMe, type User } from '../api/auth';
import { useSelection } from '../api/hiker';
import { SessionIndicator } from './SessionIndicator';
import { ThemeToggle } from './ThemeToggle';
import './layout.css';

export function Logo() {
  return (
    <svg className="logo" viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <path d="M3 25 L12 10 L17 18 L21 13 L29 25 Z" />
      <path className="logo-snow" d="M10.2 13 L12 10 L13.8 13" />
    </svg>
  );
}

function initialsOf(user: User): string {
  return ((user.firstName[0] ?? '') + (user.lastName[0] ?? '')).toUpperCase() || (user.email[0] ?? '?').toUpperCase();
}

/** Meni korisnika: profil, prijave, članstva, odjava. Zatvara se klikom van, Escape-om i promjenom stranice. */
function UserMenu({ user, onLogout, pending }: { user: User; onLogout: () => void; pending: boolean }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const location = useLocation();
  const [lastPath, setLastPath] = useState(location.pathname);
  if (lastPath !== location.pathname) {
    setLastPath(location.pathname);
    setOpen(false);
  }

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const hiker = !user.roles.systemAdmin;
  return (
    <div className="user-menu" ref={ref}>
      <button type="button" className="user-btn" aria-expanded={open} aria-haspopup="true" aria-controls="user-menu-list"
        onClick={() => setOpen((o) => !o)}>
        <span className="avatar sticker mono" aria-hidden="true">{initialsOf(user)}</span>
        <span className="nav-user">{displayName(user)}</span>
        <span className="caret" aria-hidden="true">▾</span>
      </button>
      <div id="user-menu-list" className={`user-dropdown${open ? ' is-open' : ''}`}>
        <NavLink to="/profil" className="menu-item">Profil</NavLink>
        {hiker && <NavLink to="/moje-prijave" className="menu-item">Moje prijave</NavLink>}
        {hiker && <NavLink to="/moja-clanstva" className="menu-item">Moja članstva</NavLink>}
        <button type="button" className="menu-item menu-logout" onClick={onLogout} disabled={pending}>Odjava</button>
      </div>
    </div>
  );
}

function SelectionLink() {
  const { data } = useSelection();
  const n = data?.ids.length ?? 0;
  if (!n) return null;
  return (
    <NavLink to="/odabir" className="nav-link nav-selection">
      Odabir <span className="count-badge mono" aria-label={`${n} odabranih tura`}>{n}</span>
    </NavLink>
  );
}

function Header() {
  const { data: me } = useMe();
  const logout = useLogout();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const user = me?.authenticated ? me.user : null;

  // zatvori mobilni meni pri promjeni stranice
  const [lastPath, setLastPath] = useState(location.pathname);
  if (lastPath !== location.pathname) {
    setLastPath(location.pathname);
    setOpen(false);
  }

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  function onLogout() {
    logout.mutate(undefined, { onSettled: () => navigate('/', { replace: true }) });
  }

  return (
    <header className="site-header">
      <div className="container header-inner">
        <Link to="/" className="brand" aria-label="Frostbite - početna">
          <Logo />
          <span className="brand-name">Frostbite</span>
          <span className="brand-tag label-mono">Beta</span>
        </Link>

        <div className="header-tools"><ThemeToggle /></div>

        <button
          type="button"
          className="menu-toggle"
          aria-expanded={open}
          aria-controls="site-nav"
          onClick={() => setOpen((o) => !o)}
        >
          <span className="sr-only">{open ? 'Zatvori meni' : 'Otvori meni'}</span>
          <span className="menu-bars" aria-hidden="true"><span /><span /></span>
        </button>

        <nav id="site-nav" className={`site-nav${open ? ' is-open' : ''}`} aria-label="Glavni meni">
          <div className="nav-group">
            <NavLink to="/ture" className="nav-link">Ture</NavLink>
            <NavLink to="/drustva" className="nav-link">Društva</NavLink>
            {user?.roles.guide && <NavLink to="/vodic" className="nav-link">Vođenje</NavLink>}
            {user?.roles.clubAdmin && <NavLink to="/upravljanje" className="nav-link">Upravljanje</NavLink>}
            {user?.roles.systemAdmin && <NavLink to="/sistem" className="nav-link">Sistem</NavLink>}
            {!user?.roles.systemAdmin && <SelectionLink />}
          </div>
          <div className="nav-group">
            {user ? (
              <>
                <SessionIndicator />
                <UserMenu user={user} onLogout={onLogout} pending={logout.isPending} />
              </>
            ) : (
              <>
                <NavLink to="/prijava" className="nav-link">Prijava</NavLink>
                <Link to="/registracija" className="btn btn-sm">Registracija</Link>
              </>
            )}
          </div>
        </nav>
      </div>
    </header>
  );
}

export function Layout() {
  const location = useLocation();
  return (
    <>
      <a className="skip-link" href="#main">Preskoči na sadržaj</a>
      <Header />
      <main id="main" key={location.pathname} className="site-main page-enter">
        <Outlet />
      </main>
      <footer className="site-footer">
        <div className="container footer-inner">
          <span className="label-mono">Frostbite · 43.8563° N 18.4131° E · Sarajevo</span>
          <span className="label-mono">Planinarske ture · Bosna i Hercegovina</span>
        </div>
      </footer>
    </>
  );
}
