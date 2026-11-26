import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router';

import { displayName, useLogout, useMe } from '../api/auth';
import { SessionIndicator } from './SessionIndicator';
import './layout.css';

export function Logo() {
  return (
    <svg className="logo" viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <path d="M3 25 L12 10 L17 18 L21 13 L29 25 Z" />
      <path className="logo-snow" d="M10.2 13 L12 10 L13.8 13" />
    </svg>
  );
}

/** Stare Django stranice (još nisu prebačene u React) - običan link, puno učitavanje stranice. */
function Legacy({ href, children }: { href: string; children: string }) {
  return <a className="nav-link" href={href}>{children}</a>;
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
            {user?.roles.guide && <Legacy href="/vodic/">Vođenje</Legacy>}
            {user?.roles.clubAdmin && <Legacy href="/upravljanje/">Upravljanje</Legacy>}
            {user?.roles.systemAdmin && <Legacy href="/sistem/">Sistem</Legacy>}
          </div>
          <div className="nav-group">
            {user ? (
              <>
                <SessionIndicator />
                <NavLink to="/profil" className="nav-link nav-user">{displayName(user)}</NavLink>
                <button type="button" className="btn btn-ghost btn-sm" onClick={onLogout} disabled={logout.isPending}>
                  Odjava
                </button>
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
          <a className="label-mono footer-link" href="/">Klasični prikaz</a>
        </div>
      </footer>
    </>
  );
}
