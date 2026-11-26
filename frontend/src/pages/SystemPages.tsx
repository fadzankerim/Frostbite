// Panel sistemskog admina: pregled platforme i sigurnosti, društva, korisnici, evidencija (F29-F31).
// Sistemski admin ne vidi telefon, hitni kontakt ni zdravstvene napomene (server ih ne šalje).
import { useState, type FormEvent } from 'react';
import { Link, NavLink, Outlet, useSearchParams } from 'react-router';

import { ApiError } from '../api/client';
import {
  useAudit, useDecideClub, useSystemClubs, useSystemDashboard, useSystemUsers, useToggleUser, type AuditEntry, type SysClub,
} from '../api/system';
import { ColumnChart } from '../components/ColumnChart';
import { Notice } from '../components/forms';
import { Frosti } from '../components/Frosti';
import { Loading } from '../components/guards';
import { SceneArt } from '../components/SceneArt';
import { formatDateTime, formatLong } from '../lib/format';
import './pages.css';

const TABS = [
  { to: '/sistem', label: 'Pregled', end: true },
  { to: '/sistem/drustva', label: 'Društva' },
  { to: '/sistem/korisnici', label: 'Korisnici' },
  { to: '/sistem/evidencija', label: 'Evidencija' },
];

export function SystemLayout() {
  return (
    <section className="container page manage">
      <div className="manage-head">
        <Frosti mood="think" size={72} />
        <div>
          <span className="label-mono">Sistemski admin</span>
          <h1 className="page-title">Kontrolna tabla</h1>
        </div>
      </div>
      <nav className="tabs" aria-label="Sistemski panel">
        {TABS.map((t) => <NavLink key={t.to} to={t.to} end={t.end ?? false} className="tab">{t.label}</NavLink>)}
      </nav>
      <Outlet />
    </section>
  );
}

/** Akcije iz evidencije u čitljivom obliku: LOGIN_NEUSPJEH -> "login neuspjeh". */
const prettyAction = (a: string) => a.toLowerCase().replace(/_/g, ' ');
const SECURITY = new Set(['LOGIN_NEUSPJEH', 'NALOG_ZAKLJUCAN', 'LOGIN_ZAKLJUCAN', 'LOGIN_BLOKIRAN', 'NALOG_BLOKIRAN', 'REGISTRACIJA_DUPLIKAT']);

function ActionChip({ action }: { action: string }) {
  const kind = SECURITY.has(action) ? 'status-err' : action === 'PRISTUP_LICNIM_PODACIMA' ? 'status-wait' : 'status-off';
  return <span className={`status-chip mono audit-chip ${kind}`}>{prettyAction(action)}</span>;
}

function Tile({ value, label, accent, alert }: { value: number; label: string; accent: string; alert?: boolean }) {
  return (
    <div className={`stat-tile stat-${accent}${alert && value > 0 ? ' is-alert' : ''}`}>
      <span className="mono altitude">{value}</span>
      <span className="label-mono">{label}</span>
    </div>
  );
}

export function SystemDashboardTab() {
  const d = useSystemDashboard();
  if (d.isPending) return <Loading label="Učitavanje pregleda" />;
  if (d.isError) return <Notice kind="error">Pregled nije moguće učitati.</Notice>;
  const x = d.data;
  const tmax = Math.max(1, ...x.tourStatus.map((t) => t.count));
  return (
    <div className="manage-body">
      <h2 className="section-title">Platforma</h2>
      <div className="stat-tiles stat-tiles-3">
        <Tile value={x.kpi.users} label={`Korisnika (+${x.kpi.newUsers} u 30 dana)`} accent="sky" />
        <Tile value={x.kpi.clubs} label="Odobrenih društava" accent="mint" />
        <Tile value={x.kpi.pendingClubs} label="Društava na čekanju" accent="sun" alert />
        <Tile value={x.kpi.toursActive} label="Aktivnih tura" accent="coral" />
        <Tile value={x.kpi.registrations} label="Prijava na predstojeće ture" accent="lilac" />
      </div>

      <h2 className="section-title">Sigurnost · posljednjih 7 dana</h2>
      <div className="stat-tiles stat-tiles-3">
        <Tile value={x.security.failed} label="Neuspjelih prijava" accent="coral" alert />
        <Tile value={x.security.lockouts} label="Zaključavanja naloga" accent="peach" alert />
        <Tile value={x.security.lockedNow} label="Trenutno zaključano" accent="sun" alert />
        <Tile value={x.security.blocked} label="Blokiranih naloga" accent="lilac" />
        <Tile value={x.security.personalDataAccess} label="Pristupa ličnim podacima" accent="sky" />
      </div>

      <div className="chart-grid2">
        <ColumnChart title="Uspješne prijave · 14 dana" items={x.logins} xLabel="Dan" color="chart-1" />
        <ColumnChart title="Neuspjele i odbijene prijave · 14 dana" items={x.fails} xLabel="Dan" color="chart-1" />
      </div>

      <div className="two-col">
        <section>
          <h2 className="section-title">Ture po statusu</h2>
          <ul className="guide-bars">
            {x.tourStatus.map((t) => (
              <li key={t.label}>
                <span>{t.label}</span>
                <span className="guide-bar" aria-hidden="true"><span style={{ transform: `scaleX(${t.count / tmax})` }} /></span>
                <span className="mono">{t.count}</span>
              </li>
            ))}
          </ul>
          {x.pendingClubs.length > 0 && (
            <>
              <h2 className="section-title">Društva na čekanju</h2>
              <ul className="mini-list">
                {x.pendingClubs.map((c) => (
                  <li key={c.id}><Link className="mini-row" to="/sistem/drustva">
                    <span className="mini-art"><SceneArt seed={c.id} variant="club" /></span>
                    <span className="mini-main"><strong>{c.name}</strong><span className="muted">{c.city} · {formatDateTime(c.createdAt)}</span></span>
                  </Link></li>
                ))}
              </ul>
            </>
          )}
        </section>
        <section>
          <h2 className="section-title">Sigurnosni događaji</h2>
          {x.events.length ? (
            <ul className="mini-list">
              {x.events.map((e) => (
                <li key={e.id} className="mini-row event-row">
                  <span className="mini-main">
                    <ActionChip action={e.action} />
                    <span className="muted">{formatDateTime(e.createdAt)} · {e.user ?? 'nepoznat nalog'}{e.ip ? ` · ${e.ip}` : ''}</span>
                  </span>
                </li>
              ))}
            </ul>
          ) : <div className="empty"><Frosti mood="happy" size={72} /><p className="muted">Mirno je. Nema sigurnosnih događaja.</p></div>}
        </section>
      </div>
    </div>
  );
}

// --- društva ---------------------------------------------------------------------------
const CLUB_ACTIONS = {
  approve: { label: 'Odobri', cls: 'btn-accent' },
  reject: { label: 'Odbij', cls: 'btn-ghost' },
  suspend: { label: 'Suspenduj', cls: 'btn-danger' },
} as const;

function ClubRow({ c, onAction, pending }: { c: SysClub; onAction: (a: string) => void; pending: boolean }) {
  const [confirm, setConfirm] = useState<string | null>(null);
  return (
    <li className="reg-row">
      <div className="reg-art"><SceneArt seed={c.id} variant="club" /></div>
      <div className="reg-main">
        <span className="label-mono">{c.city}</span>
        <span className="row-title">{c.name}</span>
        <span className="muted reg-meta">Podnio {c.createdBy.name} ({c.createdBy.email}) · {formatLong(c.createdAt)}</span>
      </div>
      <div className="reg-side">
        <span className={`status-chip club-status-${c.status.code.toLowerCase()}`}>{c.status.label}</span>
        {c.actions.map((a) => confirm === a ? (
          <span key={a} className="confirm-inline">
            <span className="label-mono">Sigurno?</span>
            <button type="button" className={`btn btn-sm ${CLUB_ACTIONS[a].cls}`} disabled={pending} onClick={() => { onAction(a); setConfirm(null); }}>Da</button>
            <button type="button" className="btn btn-sm btn-ghost" onClick={() => setConfirm(null)}>Ne</button>
          </span>
        ) : (
          <button key={a} type="button" className={`btn btn-sm ${CLUB_ACTIONS[a].cls}`} onClick={() => setConfirm(a)}>{CLUB_ACTIONS[a].label}</button>
        ))}
      </div>
    </li>
  );
}

export function SystemClubsTab() {
  const clubs = useSystemClubs();
  const decide = useDecideClub();
  if (clubs.isPending) return <Loading label="Učitavanje društava" />;
  if (clubs.isError) return <Notice kind="error">Društva nije moguće učitati.</Notice>;
  const act = (id: number) => (action: string) => decide.mutate({ id, action });
  return (
    <div className="manage-body">
      {decide.isSuccess && <Notice kind="ok">{decide.data.detail}</Notice>}
      {decide.error instanceof ApiError && <Notice kind="error">{decide.error.detail}</Notice>}
      <h2 className="section-title">Na čekanju <span className="mono muted">({clubs.data.pending.length})</span></h2>
      {clubs.data.pending.length ? (
        <ul className="reg-list">{clubs.data.pending.map((c) => <ClubRow key={c.id} c={c} onAction={act(c.id)} pending={decide.isPending} />)}</ul>
      ) : <div className="empty"><Frosti mood="happy" size={72} /><p className="muted">Nema zahtjeva za registraciju društva.</p></div>}
      <p className="field-hint">Odobravanjem društva podnosilac zahtjeva postaje admin društva.</p>
      <h2 className="section-title">Ostala društva</h2>
      <ul className="reg-list">{clubs.data.others.map((c) => <ClubRow key={c.id} c={c} onAction={act(c.id)} pending={decide.isPending} />)}</ul>
    </div>
  );
}

// --- korisnici i evidencija: pretraga + stranice u URL-u ----------------------------------
function usePagedSearch(key: string) {
  const [params, setParams] = useSearchParams();
  const q = (params.get(key) ?? '').slice(0, 100);
  const raw = params.get('page') ?? '1';
  const page = /^\d{1,5}$/.test(raw) && Number(raw) > 0 ? Number(raw) : 1;
  const [draft, setDraft] = useState(q);
  const [lastQ, setLastQ] = useState(q);
  if (lastQ !== q) {          // URL se promijenio (nazad/naprijed): polje prati URL
    setLastQ(q);
    setDraft(q);
  }
  const set = (next: { q?: string; page?: number }) => {
    const p = new URLSearchParams();
    const nq = next.q ?? q;
    if (nq) p.set(key, nq);
    if ((next.page ?? 1) > 1) p.set('page', String(next.page));
    setParams(p, { replace: true });
  };
  return { q, page, draft, setDraft, set };
}

function Pager({ page, pages, onPage }: { page: number; pages: number; onPage: (p: number) => void }) {
  if (pages <= 1) return null;
  return (
    <nav className="pager" aria-label="Stranice">
      <button type="button" className="btn btn-ghost btn-sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>← Prethodna</button>
      <span className="mono muted">{page} / {pages}</span>
      <button type="button" className="btn btn-ghost btn-sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>Sljedeća →</button>
    </nav>
  );
}

export function SystemUsersTab() {
  const s = usePagedSearch('q');
  const users = useSystemUsers(s.q, s.page);
  const toggle = useToggleUser();
  const [confirm, setConfirm] = useState<number | null>(null);
  function submit(e: FormEvent<HTMLFormElement>) { e.preventDefault(); s.set({ q: s.draft.trim(), page: 1 }); }
  return (
    <div className="manage-body">
      <form className="search-bar" role="search" onSubmit={submit}>
        <label className="sr-only" htmlFor="user-q">Pretraga korisnika</label>
        <input id="user-q" className="input" type="search" placeholder="Ime, prezime ili email" maxLength={100}
          value={s.draft} onChange={(e) => s.setDraft(e.target.value)} autoComplete="off" />
        <button type="submit" className="btn btn-sm">Traži</button>
      </form>
      {toggle.isSuccess && <Notice kind="ok">{toggle.data.detail}</Notice>}
      {toggle.error instanceof ApiError && <Notice kind="error">{toggle.error.detail}</Notice>}
      <p className="field-hint">Prikazani su samo ime, email i status naloga. Blokiranje odmah prekida sve aktivne sesije korisnika.</p>
      {users.isPending ? <Loading /> : users.isError ? <Notice kind="error">Korisnike nije moguće učitati.</Notice> : (
        <>
          <span className="label-mono">{users.data.total} korisnika</span>
          <ul className={`mini-list${users.isFetching ? ' is-refreshing' : ''}`}>
            {users.data.results.map((u) => (
              <li key={u.id} className="mini-row">
                <span className="avatar sticker mono" aria-hidden="true">{(u.firstName[0] ?? '') + (u.lastName[0] ?? '')}</span>
                <span className="mini-main">
                  <strong>{u.firstName} {u.lastName}{u.isSelf && <span className="muted"> (vi)</span>}</strong>
                  <span className="muted">{u.email} · od {formatDateTime(u.dateJoined)}</span>
                </span>
                {u.isSystemAdmin && <span className="status-chip status-wait">Sistemski admin</span>}
                {u.locked && <span className="status-chip status-err">Zaključan</span>}
                <span className={`status-chip ${u.isActive ? 'status-ok' : 'status-off'}`}>{u.isActive ? 'Aktivan' : 'Blokiran'}</span>
                {!u.isSelf && (confirm === u.id ? (
                  <span className="confirm-inline">
                    <button type="button" className={`btn btn-sm ${u.isActive ? 'btn-danger' : 'btn-accent'}`} disabled={toggle.isPending}
                      onClick={() => toggle.mutate(u.id, { onSettled: () => setConfirm(null) })}>{u.isActive ? 'Da, blokiraj' : 'Da, deblokiraj'}</button>
                    <button type="button" className="btn btn-sm btn-ghost" onClick={() => setConfirm(null)}>Ne</button>
                  </span>
                ) : (
                  <button type="button" className="btn btn-sm btn-ghost" onClick={() => setConfirm(u.id)}>{u.isActive ? 'Blokiraj' : 'Deblokiraj'}</button>
                ))}
              </li>
            ))}
          </ul>
          {users.data.results.length === 0 && <div className="empty"><Frosti mood="think" size={72} /><p className="muted">Nema korisnika za ovu pretragu.</p></div>}
          <Pager page={users.data.page} pages={users.data.pages} onPage={(p) => s.set({ page: p })} />
        </>
      )}
    </div>
  );
}

function AuditRow({ e }: { e: AuditEntry }) {
  return (
    <tr>
      <td className="mono nowrap">{formatDateTime(e.createdAt)}</td>
      <td><ActionChip action={e.action} /></td>
      <td>{e.user ?? '—'}</td>
      <td className="mono">{e.entity ? `${e.entity}${e.entityId ? ` #${e.entityId}` : ''}` : ''}</td>
      <td className="audit-details">{e.details}</td>
      <td className="mono nowrap">{e.ip ?? ''}</td>
    </tr>
  );
}

export function SystemAuditTab() {
  const s = usePagedSearch('action');
  const log = useAudit(s.q, s.page);
  function submit(e: FormEvent<HTMLFormElement>) { e.preventDefault(); s.set({ q: s.draft.trim(), page: 1 }); }
  return (
    <div className="manage-body">
      <form className="search-bar" role="search" onSubmit={submit}>
        <label className="sr-only" htmlFor="audit-q">Filter po akciji</label>
        <input id="audit-q" className="input mono" type="search" placeholder="npr. LOGIN_NEUSPJEH" maxLength={50}
          value={s.draft} onChange={(e) => s.setDraft(e.target.value)} autoComplete="off" />
        <button type="submit" className="btn btn-sm">Filtriraj</button>
      </form>
      <p className="field-hint">Evidencija je samo za čitanje; zapisi se ne mogu mijenjati ni brisati (ni u bazi).</p>
      {log.isPending ? <Loading /> : log.isError ? <Notice kind="error">Evidenciju nije moguće učitati.</Notice> : (
        <>
          <span className="label-mono">{log.data.total} zapisa</span>
          <div className={`table-wrap${log.isFetching ? ' is-refreshing' : ''}`}>
            <table className="audit-table">
              <thead><tr><th scope="col">Vrijeme</th><th scope="col">Akcija</th><th scope="col">Korisnik</th><th scope="col">Objekat</th><th scope="col">Detalji</th><th scope="col">IP</th></tr></thead>
              <tbody>{log.data.results.map((e) => <AuditRow key={e.id} e={e} />)}</tbody>
            </table>
          </div>
          <Pager page={log.data.page} pages={log.data.pages} onPage={(p) => s.set({ page: p })} />
        </>
      )}
    </div>
  );
}
