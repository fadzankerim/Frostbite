// Panel admina društva: pregled (analitika), ture (kreiranje, izmjena, status, vodiči), vodiči društva,
// članstva i profil društva (F18, F21-F28). Prava provjerava server; ovdje je samo prikaz.
import { useState, type FormEvent } from 'react';
import { Link, NavLink, Navigate, Outlet, useLocation, useNavigate, useOutletContext, useParams } from 'react-router';

import { ApiError } from '../api/client';
import {
  useAddGuide, useAssignGuide, useClubGuides, useClubProfile, useCreateTour, useDashboard, useDecideGuide,
  useDecideMember, useManagedClubs, useManageTour, useManageTours, useMembers, useRemoveGuide, useSaveClubProfile,
  useTransition, useUpdateTour, type ClubProfile, type ManagedClub, type TourFormData, type TourRow,
} from '../api/manage';
import { parseId, type DifficultyCode } from '../api/public';
import { ColumnChart } from '../components/ColumnChart';
import { Field, Notice, SubmitButton } from '../components/forms';
import { Frosti } from '../components/Frosti';
import { Loading } from '../components/guards';
import { RouteEditor } from '../components/RouteEditor';
import { SceneArt } from '../components/SceneArt';
import { DifficultyBadge } from '../components/TourCard';
import { formatDateTime, formatLong, formatNumber, formatPrice } from '../lib/format';
import { NotFoundPage } from './StatusPages';
import './pages.css';

type Ctx = { club: ManagedClub };
const useClub = () => useOutletContext<Ctx>().club;

function ErrorNotice({ error }: { error: unknown }) {
  return error instanceof ApiError ? <Notice kind="error">{error.detail}</Notice> : null;
}

// --- izbor društva i raspored -------------------------------------------------------
export function ManageIndexPage() {
  const clubs = useManagedClubs();
  if (clubs.isPending) return <Loading label="Učitavanje društava" />;
  if (clubs.isError) return <div className="container page"><Notice kind="error">Društva nije moguće učitati.</Notice></div>;
  if (clubs.data.length === 1) return <Navigate to={`/upravljanje/${clubs.data[0]!.id}`} replace />;
  return (
    <section className="container page">
      <span className="label-mono">Admin društva</span>
      <h1 className="page-title">Izaberite društvo</h1>
      {clubs.data.length === 0 ? (
        <div className="empty"><Frosti mood="think" size={96} /><p className="muted">Ne upravljate nijednim odobrenim društvom.</p></div>
      ) : (
        <ul className="club-grid">
          {clubs.data.map((c) => (
            <li key={c.id} className="club-card">
              <Link to={`/upravljanje/${c.id}`} className="club-card-link has-scene">
                <div className="club-card-art"><SceneArt seed={c.id} variant="club" /></div>
                <span className="label-mono">{c.city}</span>
                <h3>{c.name}</h3>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

const TABS = [
  { to: '', label: 'Pregled', end: true },
  { to: 'ture', label: 'Ture' },
  { to: 'vodici', label: 'Vodiči' },
  { to: 'clanovi', label: 'Članovi' },
  { to: 'profil', label: 'Profil' },
];

export function ManageLayout() {
  const { clubId } = useParams();
  const id = parseId(clubId);
  const clubs = useManagedClubs();
  if (id === null) return <NotFoundPage />;
  if (clubs.isPending) return <Loading label="Učitavanje panela" />;
  const club = clubs.data?.find((c) => c.id === id);
  if (!club) return <NotFoundPage />;
  return (
    <section className="container page manage">
      <div className="manage-head">
        <div className="manage-badge has-scene"><SceneArt seed={club.id} variant="club" /></div>
        <div>
          <span className="label-mono">Admin društva · {club.city}</span>
          <h1 className="page-title">{club.name}</h1>
        </div>
      </div>
      <nav className="tabs" aria-label="Panel društva">
        {TABS.map((t) => (
          <NavLink key={t.label} to={`/upravljanje/${club.id}${t.to ? `/${t.to}` : ''}`} end={t.end ?? false} className="tab">{t.label}</NavLink>
        ))}
      </nav>
      <Outlet context={{ club } satisfies Ctx} />
    </section>
  );
}

// --- pregled --------------------------------------------------------------------------
function StatTile({ value, label, unit, accent }: { value: string | number; label: string; unit?: string; accent: string }) {
  return (
    <div className={`stat-tile stat-${accent}`}>
      <span className="mono altitude">{value}{unit && <span className="altitude-unit"> {unit}</span>}</span>
      <span className="label-mono">{label}</span>
    </div>
  );
}

function TourMiniRow({ t, clubId }: { t: TourRow; clubId: number }) {
  return (
    <li>
      <Link className="mini-row" to={`/upravljanje/${clubId}/ture/${t.id}`}>
        <span className="mini-art"><SceneArt seed={t.id} difficulty={t.difficulty.code} /></span>
        <span className="mini-main"><strong>{t.name}</strong><span className="muted">{formatDateTime(t.startAt)}</span></span>
        {t.taken !== null && <span className="mono muted">{t.taken}/{t.maxParticipants}</span>}
      </Link>
    </li>
  );
}

export function ManageDashboardTab() {
  const club = useClub();
  const d = useDashboard(club.id);
  if (d.isPending) return <Loading label="Učitavanje analitike" />;
  if (d.isError) return <Notice kind="error">Analitiku nije moguće učitati.</Notice>;
  const x = d.data;
  return (
    <div className="manage-body">
      {(x.pendingMembers > 0 || x.pendingGuides > 0 || x.unguided.length > 0) && (
        <div className="todo sticker">
          <Frosti mood="think" size={56} />
          <ul>
            {x.pendingMembers > 0 && <li><Link className="link" to={`/upravljanje/${club.id}/clanovi`}>{x.pendingMembers} zahtjeva za članstvo čeka odluku</Link></li>}
            {x.pendingGuides > 0 && <li><Link className="link" to={`/upravljanje/${club.id}/ture`}>{x.pendingGuides} prijava vodiča čeka odluku</Link></li>}
            {x.unguided.length > 0 && <li>{x.unguided.length} aktivnih tura nema vodiča</li>}
          </ul>
        </div>
      )}
      <div className="stat-tiles">
        <StatTile value={x.phases.active} label="Aktivne ture" accent="coral" />
        <StatTile value={x.phases.draft} label="Nacrti" accent="sun" />
        <StatTile value={x.phases.done} label="Održane" accent="mint" />
        <StatTile value={`${x.fill.pct}%`} label={`Popunjenost (${x.fill.taken}/${x.fill.capacity})`} accent="lilac" />
        <StatTile value={x.membersCount} label="Aktivni članovi" accent="sky" />
        <StatTile value={formatNumber(Math.round(x.money.earned))} unit="KM" label="Prihod (održane)" accent="peach" />
        <StatTile value={formatNumber(Math.round(x.money.expected))} unit="KM" label="Očekivano (aktivne)" accent="coral" />
        <StatTile value={x.guides.length} label="Vodiči" accent="mint" />
      </div>
      <p className="field-hint">Prihod je procjena (cijena × prisutni ili prijavljeni); plaćanje se ne odvija kroz aplikaciju.</p>
      <div className="chart-grid2">
        <ColumnChart title="Učesnici na održanim turama" items={x.months.map((m) => ({ label: m.label, value: m.people }))} color="chart-1" />
        <ColumnChart title="Prihod po mjesecu" unit=" KM" items={x.months.map((m) => ({ label: m.label, value: m.money }))} color="chart-2" />
      </div>
      <div className="two-col">
        <section>
          <h2 className="section-title">Predstojeće ture</h2>
          {x.upcoming.length ? <ul className="mini-list">{x.upcoming.map((t) => <TourMiniRow key={t.id} t={t} clubId={club.id} />)}</ul>
            : <p className="muted">Nema aktivnih tura.</p>}
        </section>
        <section>
          <h2 className="section-title">Vodiči · održane ture</h2>
          {x.guides.length ? (
            <ul className="guide-bars">
              {x.guides.map((g) => {
                const max = Math.max(1, ...x.guides.map((y) => y.led));
                return (
                  <li key={g.name}>
                    <span>{g.name}</span>
                    <span className="guide-bar" aria-hidden="true"><span style={{ transform: `scaleX(${g.led / max})` }} /></span>
                    <span className="mono">{g.led}</span>
                  </li>
                );
              })}
            </ul>
          ) : <p className="muted">Društvo još nema vodiča.</p>}
        </section>
      </div>
    </div>
  );
}

// --- ture -----------------------------------------------------------------------------
function TourTable({ rows, clubId }: { rows: TourRow[]; clubId: number }) {
  return (
    <ul className="reg-list">
      {rows.map((t) => (
        <li key={t.id} className="reg-row">
          <div className="reg-art"><SceneArt seed={t.id} difficulty={t.difficulty.code} /></div>
          <div className="reg-main">
            <DifficultyBadge code={t.difficulty.code} label={t.difficulty.label} />
            <Link className="row-title" to={`/upravljanje/${clubId}/ture/${t.id}`}>{t.name}</Link>
            <span className="muted reg-meta">{formatDateTime(t.startAt)} · {t.taken}/{t.maxParticipants} prijavljenih{t.waiting ? ` · ${t.waiting} čeka` : ''}</span>
          </div>
          <div className="reg-side">
            {!!t.guideApps && <span className="status-chip status-wait">{t.guideApps} prijava vodiča</span>}
            <span className={`status-chip tour-status-${t.status.code.toLowerCase()}`}>{t.status.label}</span>
          </div>
        </li>
      ))}
    </ul>
  );
}

export function ManageToursTab() {
  const club = useClub();
  const tours = useManageTours(club.id);
  if (tours.isPending) return <Loading label="Učitavanje tura" />;
  if (tours.isError) return <Notice kind="error">Ture nije moguće učitati.</Notice>;
  return (
    <div className="manage-body">
      <div className="section-head">
        <h2 className="section-title">Predstojeće</h2>
        <Link className="btn btn-accent btn-sm" to={`/upravljanje/${club.id}/ture/nova`}>+ Nova tura</Link>
      </div>
      {tours.data.upcoming.length ? <TourTable rows={tours.data.upcoming} clubId={club.id} />
        : <div className="empty"><Frosti mood="think" size={88} /><p className="muted">Nema predstojećih tura. Kreirajte prvu!</p></div>}
      {tours.data.past.length > 0 && (<><h2 className="section-title">Prošle</h2><TourTable rows={tours.data.past} clubId={club.id} /></>)}
    </div>
  );
}

const DIFFICULTIES: { code: DifficultyCode; label: string }[] = [
  { code: 'LAKA', label: 'Laka' }, { code: 'SREDNJA', label: 'Srednja' }, { code: 'TESKA', label: 'Teška' }, { code: 'VRLO_TESKA', label: 'Vrlo teška' },
];

const EMPTY_TOUR: TourFormData = {
  name: '', region: '', description: '', startAt: '', registrationDeadline: '', meetingPoint: '', difficulty: 'SREDNJA',
  lengthKm: '', elevationGainM: '', durationH: '', maxParticipants: 15, price: 0, membersOnly: false, requiredEquipment: '', route: [],
};

function TourForm({ initial, onSubmit, pending, error, submitLabel }: {
  initial: TourFormData; onSubmit: (d: TourFormData) => void; pending: boolean; error: unknown; submitLabel: string;
}) {
  const [f, setF] = useState<TourFormData>(initial);
  const errors = error instanceof ApiError ? error.fieldErrors : {};
  const set = <K extends keyof TourFormData>(key: K) => (v: TourFormData[K]) => setF((s) => ({ ...s, [key]: v }));
  const text = (key: keyof TourFormData, label: string, opts: { type?: string; max?: number; hint?: string; step?: string; min?: number } = {}) => (
    <Field label={label} errors={errors[key]} {...(opts.hint ? { hint: opts.hint } : {})}>
      {(p) => <input {...p} className="input" type={opts.type ?? 'text'} value={String(f[key])} maxLength={opts.max}
        step={opts.step} min={opts.min} onChange={(e) => set(key)(e.target.value as never)} />}
    </Field>
  );

  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!pending) onSubmit(f);
  }

  return (
    <form className="form tour-form" onSubmit={submit} noValidate>
      {error instanceof ApiError && !Object.keys(errors).length && <Notice kind="error">{error.detail}</Notice>}
      {Object.keys(errors).length > 0 && <Notice kind="error">Provjerite označena polja.</Notice>}
      <div className="card-form form">
        <h2>Osnovno</h2>
        {text('name', 'Naziv ture', { max: 150 })}
        <div className="form-row">
          {text('region', 'Regija', { max: 80 })}
          <Field label="Težina" errors={errors.difficulty}>
            {(p) => (
              <select {...p} className="input" value={f.difficulty} onChange={(e) => set('difficulty')(e.target.value as DifficultyCode)}>
                {DIFFICULTIES.map((d) => <option key={d.code} value={d.code}>{d.label}</option>)}
              </select>
            )}
          </Field>
        </div>
        <Field label="Opis" errors={errors.description}>
          {(p) => <textarea {...p} className="input textarea" rows={4} maxLength={4000} value={f.description} onChange={(e) => set('description')(e.target.value)} />}
        </Field>
      </div>

      <div className="card-form form">
        <h2>Termin i okupljanje</h2>
        <div className="form-row">
          {text('startAt', 'Polazak', { type: 'datetime-local' })}
          {text('registrationDeadline', 'Rok prijave', { type: 'datetime-local', hint: 'Mora biti prije polaska.' })}
        </div>
        {text('meetingPoint', 'Mjesto okupljanja', { max: 200 })}
      </div>

      <div className="card-form form">
        <h2>Parametri</h2>
        <div className="form-row form-row-3">
          {text('lengthKm', 'Dužina (km)', { type: 'number', step: '0.1', min: 0 })}
          {text('elevationGainM', 'Uspon (m)', { type: 'number', step: '1', min: 0 })}
          {text('durationH', 'Trajanje (h)', { type: 'number', step: '0.5', min: 0 })}
        </div>
        <div className="form-row form-row-3">
          {text('maxParticipants', 'Maks. učesnika', { type: 'number', step: '1', min: 1 })}
          {text('price', 'Cijena (KM)', { type: 'number', step: '0.5', min: 0 })}
          <label className="check-field">
            <input type="checkbox" checked={f.membersOnly} onChange={(e) => set('membersOnly')(e.target.checked)} />
            <span>Samo za članove</span>
          </label>
        </div>
        <Field label="Potrebna oprema" errors={errors.requiredEquipment}>
          {(p) => <textarea {...p} className="input textarea" rows={2} maxLength={1000} value={f.requiredEquipment} onChange={(e) => set('requiredEquipment')(e.target.value)} />}
        </Field>
      </div>

      <div className="card-form form">
        <h2>Ruta</h2>
        <RouteEditor value={f.route} onChange={set('route')} error={errors.route} />
      </div>
      <SubmitButton pending={pending}>{submitLabel}</SubmitButton>
    </form>
  );
}

export function ManageTourCreate() {
  const club = useClub();
  const create = useCreateTour(club.id);
  const navigate = useNavigate();
  return (
    <div className="manage-body">
      <Link to={`/upravljanje/${club.id}/ture`} className="back label-mono">← Ture</Link>
      <h2 className="section-title">Nova tura</h2>
      <p className="muted field-hint">Tura se čuva kao nacrt; objavljujete je kada bude spremna.</p>
      <TourForm initial={EMPTY_TOUR} pending={create.isPending} error={create.error} submitLabel="Sačuvaj nacrt"
        onSubmit={(d) => create.mutate(d, { onSuccess: (r) => navigate(`/upravljanje/${club.id}/ture/${r.id}`, { state: { notice: r.detail } }) })} />
    </div>
  );
}

export function ManageTourEdit() {
  const club = useClub();
  const { tourId } = useParams();
  const id = parseId(tourId);
  const tour = useManageTour(club.id, id);
  const update = useUpdateTour(club.id, id ?? 0);
  const navigate = useNavigate();
  if (id === null) return <NotFoundPage />;
  if (tour.isPending) return <Loading label="Učitavanje ture" />;
  if (tour.isError) return tour.error instanceof ApiError && tour.error.status === 404 ? <NotFoundPage /> : <Notice kind="error">Turu nije moguće učitati.</Notice>;
  if (!tour.data.editable) return <Notice>Održane i otkazane ture se ne mogu mijenjati.</Notice>;
  return (
    <div className="manage-body">
      <Link to={`/upravljanje/${club.id}/ture/${id}`} className="back label-mono">← {tour.data.name}</Link>
      <h2 className="section-title">Uredi turu</h2>
      <TourForm initial={tour.data.form} pending={update.isPending} error={update.error} submitLabel="Sačuvaj izmjene"
        onSubmit={(d) => update.mutate(d, { onSuccess: (r) => navigate(`/upravljanje/${club.id}/ture/${id}`, { state: { notice: r.detail } }) })} />
    </div>
  );
}

const TRANSITION_UI = {
  publish: { label: 'Objavi turu', cls: 'btn-accent', confirm: 'Objaviti turu? Postaće vidljiva svima.' },
  close: { label: 'Zatvori prijave', cls: 'btn-ghost', confirm: 'Zatvoriti prijave?' },
  cancel: { label: 'Otkaži turu', cls: 'btn-danger', confirm: 'Otkazati turu? Ovo se ne može poništiti.' },
} as const;

export function ManageTourDetail() {
  const club = useClub();
  const { tourId } = useParams();
  const id = parseId(tourId);
  const tour = useManageTour(club.id, id);
  const transition = useTransition(club.id, id ?? 0);
  const assign = useAssignGuide(club.id, id ?? 0);
  const decide = useDecideGuide(club.id, id ?? 0);
  const [confirm, setConfirm] = useState<keyof typeof TRANSITION_UI | null>(null);
  const [guide, setGuide] = useState('');
  const location = useLocation();
  const savedNotice = (location.state as { notice?: unknown } | null)?.notice;
  if (id === null) return <NotFoundPage />;
  if (tour.isPending) return <Loading label="Učitavanje ture" />;
  if (tour.isError) return tour.error instanceof ApiError && tour.error.status === 404 ? <NotFoundPage /> : <Notice kind="error">Turu nije moguće učitati.</Notice>;
  const t = tour.data;
  // poruka posljednje radnje (objava, dodjela vodiča, odluka o prijavi vodiča)
  const last = [transition, assign, decide].filter((m) => m.submittedAt).sort((a, b) => b.submittedAt - a.submittedAt)[0];
  const done = last?.isSuccess ? last.data?.detail : undefined;
  const err = last?.error;

  return (
    <div className="manage-body">
      <Link to={`/upravljanje/${club.id}/ture`} className="back label-mono">← Ture</Link>
      <div className="banner banner-sm has-scene"><SceneArt seed={t.id} difficulty={t.difficulty.code} width={800} /></div>
      <div className="detail-badges">
        <DifficultyBadge code={t.difficulty.code} label={t.difficulty.label} />
        <span className={`status-chip tour-status-${t.status.code.toLowerCase()}`}>{t.status.label}</span>
      </div>
      <h2 className="detail-title">{t.name}</h2>
      <p className="muted">{formatLong(t.startAt)} · {t.form.meetingPoint} · {formatPrice(Number(t.form.price))}</p>
      {done ? <Notice kind="ok">{done}</Notice> : typeof savedNotice === 'string' && <Notice kind="ok">{savedNotice}</Notice>}
      <ErrorNotice error={err} />

      <div className="action-bar">
        {t.editable && <Link className="btn btn-ghost btn-sm" to={`/upravljanje/${club.id}/ture/${t.id}/uredi`}>Uredi</Link>}
        {t.transitions.map((a) => (
          confirm === a ? (
            <span key={a} className="confirm-inline">
              <span className="label-mono">{TRANSITION_UI[a].confirm}</span>
              <button type="button" className={`btn btn-sm ${TRANSITION_UI[a].cls}`} disabled={transition.isPending}
                onClick={() => transition.mutate(a, { onSettled: () => setConfirm(null) })}>Da</button>
              <button type="button" className="btn btn-sm btn-ghost" onClick={() => setConfirm(null)}>Ne</button>
            </span>
          ) : (
            <button key={a} type="button" className={`btn btn-sm ${TRANSITION_UI[a].cls}`} onClick={() => setConfirm(a)}>{TRANSITION_UI[a].label}</button>
          )
        ))}
        {t.status.code === 'OBJAVLJENA' && <Link className="btn btn-ghost btn-sm" to={`/ture/${t.id}`}>Javni prikaz ↗</Link>}
      </div>

      <div className="two-col">
        <section>
          <h2 className="section-title">Vodiči</h2>
          {t.guideApplications.length ? (
            <ul className="mini-list">
              {t.guideApplications.map((a) => (
                <li key={a.id} className="mini-row">
                  <span className="mini-main"><strong>{a.name}</strong></span>
                  {a.status.code === 'PRIJAVIO_SE' ? (
                    <span className="row-actions">
                      <button type="button" className="btn btn-sm btn-accent" disabled={decide.isPending} onClick={() => decide.mutate({ appId: a.id, decision: 'approve' })}>Odobri</button>
                      <button type="button" className="btn btn-sm btn-ghost" disabled={decide.isPending} onClick={() => decide.mutate({ appId: a.id, decision: 'reject' })}>Odbij</button>
                    </span>
                  ) : <span className={`status-chip ${a.status.code === 'ODOBREN' ? 'status-ok' : 'status-off'}`}>{a.status.label}</span>}
                </li>
              ))}
            </ul>
          ) : <p className="muted">Nema prijava vodiča.</p>}
          {t.assignable.length > 0 && (
            <form className="assign-form" onSubmit={(e) => { e.preventDefault(); if (guide) assign.mutate(Number(guide)); }}>
              <label className="sr-only" htmlFor="assign">Dodijeli vodiča</label>
              <select id="assign" className="input" value={guide} onChange={(e) => setGuide(e.target.value)}>
                <option value="">Dodijeli vodiča društva…</option>
                {t.assignable.map((g) => <option key={g.id} value={String(g.id)}>{g.name}</option>)}
              </select>
              <button type="submit" className="btn btn-sm" disabled={!guide || assign.isPending}>Dodijeli</button>
            </form>
          )}
        </section>
        <section>
          <h2 className="section-title">Prijave <span className="mono muted">({t.taken ?? 0}/{t.maxParticipants})</span></h2>
          <p className="field-hint">Admin vidi samo ime i status; kontakt i zdravstvene podatke vidi samo vodič ture.</p>
          {t.registrations.length ? (
            <ul className="mini-list">
              {t.registrations.map((r) => (
                <li key={r.id} className="mini-row">
                  <span className="mini-main"><strong>{r.name}</strong>{r.attendance && <span className="muted">{r.attendance}</span>}</span>
                  <span className={`status-chip ${r.status.code === 'PRIJAVLJEN' ? 'status-ok' : r.status.code === 'NA_LISTI_CEKANJA' ? 'status-wait' : 'status-off'}`}>{r.status.label}</span>
                </li>
              ))}
            </ul>
          ) : <p className="muted">Još nema prijava.</p>}
        </section>
      </div>
    </div>
  );
}

// --- vodiči društva -------------------------------------------------------------------
export function ManageGuidesTab() {
  const club = useClub();
  const guides = useClubGuides(club.id);
  const add = useAddGuide(club.id);
  const remove = useRemoveGuide(club.id);
  const [email, setEmail] = useState('');
  const [license, setLicense] = useState('');
  const [confirm, setConfirm] = useState<number | null>(null);
  const errors = add.error instanceof ApiError ? add.error.fieldErrors : {};

  return (
    <div className="manage-body two-col">
      <section>
        <h2 className="section-title">Vodiči društva</h2>
        {remove.isSuccess && <Notice kind="ok">{remove.data.detail}</Notice>}
        {guides.isPending ? <Loading /> : guides.data?.length ? (
          <ul className="mini-list">
            {guides.data.map((g) => (
              <li key={g.id} className="mini-row">
                <span className="avatar sticker mono" aria-hidden="true">{g.name.split(' ').map((w) => w[0]).join('').slice(0, 2)}</span>
                <span className="mini-main"><strong>{g.name}</strong><span className="muted">{g.licenseNumber ? `Licenca ${g.licenseNumber}` : 'Bez broja licence'}</span></span>
                {confirm === g.id ? (
                  <span className="confirm-inline">
                    <button type="button" className="btn btn-sm btn-danger" disabled={remove.isPending} onClick={() => remove.mutate(g.id, { onSettled: () => setConfirm(null) })}>Ukloni</button>
                    <button type="button" className="btn btn-sm btn-ghost" onClick={() => setConfirm(null)}>Ne</button>
                  </span>
                ) : <button type="button" className="btn btn-sm btn-ghost" onClick={() => setConfirm(g.id)}>Ukloni</button>}
              </li>
            ))}
          </ul>
        ) : <div className="empty"><Frosti mood="think" size={80} /><p className="muted">Društvo još nema vodiča.</p></div>}
      </section>
      <form className="card-form form" onSubmit={(e) => { e.preventDefault(); add.mutate({ email: email.trim(), licenseNumber: license.trim() }, { onSuccess: () => { setEmail(''); setLicense(''); } }); }} noValidate>
        <h2>Dodaj vodiča</h2>
        <p className="field-hint">Vodič mora imati nalog planinara. Iz sigurnosnih razloga poruka je ista bez obzira da li nalog postoji.</p>
        {add.isSuccess && <Notice>{add.data.detail}</Notice>}
        <Field label="Email planinara" errors={errors.email}>
          {(p) => <input {...p} className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} maxLength={254} autoComplete="off" required />}
        </Field>
        <Field label="Broj licence (opciono)" errors={errors.licenseNumber}>
          {(p) => <input {...p} className="input" value={license} onChange={(e) => setLicense(e.target.value)} maxLength={40} />}
        </Field>
        <SubmitButton pending={add.isPending}>Dodaj vodiča</SubmitButton>
      </form>
    </div>
  );
}

// --- članovi --------------------------------------------------------------------------
export function ManageMembersTab() {
  const club = useClub();
  const members = useMembers(club.id);
  const decide = useDecideMember(club.id);
  if (members.isPending) return <Loading label="Učitavanje članova" />;
  if (members.isError) return <Notice kind="error">Članove nije moguće učitati.</Notice>;
  const { pending, active } = members.data;
  return (
    <div className="manage-body two-col">
      <section>
        <h2 className="section-title">Zahtjevi <span className="mono muted">({pending.length})</span></h2>
        {decide.isSuccess && <Notice kind="ok">{decide.data.detail}</Notice>}
        <ErrorNotice error={decide.error} />
        {pending.length ? (
          <ul className="mini-list">
            {pending.map((m) => (
              <li key={m.id} className="mini-row">
                <span className="mini-main"><strong>{m.name}</strong><span className="muted">Zahtjev od {formatDateTime(m.createdAt)}</span></span>
                <span className="row-actions">
                  <button type="button" className="btn btn-sm btn-accent" disabled={decide.isPending} onClick={() => decide.mutate({ id: m.id, decision: 'approve' })}>Odobri</button>
                  <button type="button" className="btn btn-sm btn-ghost" disabled={decide.isPending} onClick={() => decide.mutate({ id: m.id, decision: 'reject' })}>Odbij</button>
                </span>
              </li>
            ))}
          </ul>
        ) : <div className="empty"><Frosti mood="happy" size={80} /><p className="muted">Nema zahtjeva na čekanju.</p></div>}
        <p className="field-hint">Odobreno članstvo važi do kraja tekuće godine.</p>
      </section>
      <section>
        <h2 className="section-title">Aktivni članovi <span className="mono muted">({active.length})</span></h2>
        {active.length ? (
          <ul className="mini-list">
            {active.map((m) => (
              <li key={m.id} className="mini-row">
                <span className="mini-main"><strong>{m.name}</strong></span>
                {m.validUntil && <span className="mono muted">do {m.validUntil.split('-').reverse().join('.')}.</span>}
              </li>
            ))}
          </ul>
        ) : <p className="muted">Društvo još nema aktivnih članova.</p>}
      </section>
    </div>
  );
}

// --- profil društva -------------------------------------------------------------------
function ProfileForm({ initial }: { initial: ClubProfile }) {
  const club = useClub();
  const save = useSaveClubProfile(club.id);
  const { name, ...rest } = initial;
  const [f, setF] = useState(rest);
  const errors = save.error instanceof ApiError ? save.error.fieldErrors : {};
  const set = (k: keyof typeof rest) => (v: string) => setF((s) => ({ ...s, [k]: v }));
  return (
    <form className="card-form form profile-club-form" onSubmit={(e) => { e.preventDefault(); save.mutate(f); }} noValidate>
      {save.isSuccess && <Notice kind="ok">{save.data.detail}</Notice>}
      <Field label="Naziv" hint="Naziv mijenja samo sistemski admin.">{(p) => <input {...p} className="input" value={name} disabled readOnly />}</Field>
      <Field label="Grad" errors={errors.city}>{(p) => <input {...p} className="input" value={f.city} onChange={(e) => set('city')(e.target.value)} maxLength={80} />}</Field>
      <Field label="Opis" errors={errors.description}>{(p) => <textarea {...p} className="input textarea" rows={5} value={f.description} onChange={(e) => set('description')(e.target.value)} maxLength={2000} />}</Field>
      <div className="form-row">
        <Field label="Kontakt email" errors={errors.email}>{(p) => <input {...p} className="input" type="email" value={f.email} onChange={(e) => set('email')(e.target.value)} maxLength={254} />}</Field>
        <Field label="Kontakt telefon" errors={errors.phone}>{(p) => <input {...p} className="input" type="tel" value={f.phone} onChange={(e) => set('phone')(e.target.value)} maxLength={30} />}</Field>
      </div>
      <SubmitButton pending={save.isPending}>Sačuvaj profil društva</SubmitButton>
    </form>
  );
}

export function ManageProfileTab() {
  const club = useClub();
  const profile = useClubProfile(club.id);
  if (profile.isPending) return <Loading />;
  if (profile.isError) return <Notice kind="error">Profil nije moguće učitati.</Notice>;
  return <div className="manage-body"><ProfileForm initial={profile.data} /></div>;
}
