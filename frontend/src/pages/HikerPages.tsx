// Stranice planinara: moje prijave (F11, F12), moja članstva (F14), odabir više tura (F10).
import { useState } from 'react';
import { Link } from 'react-router';

import { useMe } from '../api/auth';
import { ApiError } from '../api/client';
import {
  useCancelRegistration, useMyMemberships, useMyRegistrations, useSelection, useSelectionConfirm,
  useSelectionRemove, type ConfirmResult, type Registration,
} from '../api/hiker';
import { Confetti } from '../components/Confetti';
import { Notice } from '../components/forms';
import { Frosti } from '../components/Frosti';
import { Loading } from '../components/guards';
import { SceneArt } from '../components/SceneArt';
import { DifficultyBadge, TourCard } from '../components/TourCard';
import { formatDateTime, formatLong, formatPrice } from '../lib/format';
import './pages.css';

function Empty({ text, cta }: { text: string; cta?: { to: string; label: string } }) {
  return (
    <div className="empty">
      <Frosti mood="think" size={96} />
      <p className="muted">{text}</p>
      {cta && <Link className="btn btn-ghost btn-sm" to={cta.to}>{cta.label}</Link>}
    </div>
  );
}

function StatusChip({ status, label }: { status: string; label: string }) {
  const kind = status === 'PRIJAVLJEN' || status === 'ODOBRENO' ? 'ok'
    : status === 'NA_LISTI_CEKANJA' || status === 'ZAHTJEV' ? 'wait' : 'off';
  return <span className={`status-chip status-${kind}`}>{label}</span>;
}

// --- Moje prijave -------------------------------------------------------------------
function RegistrationRow({ r, onCancel, pending }: { r: Registration; onCancel?: (id: number) => void; pending?: boolean }) {
  const [confirming, setConfirming] = useState(false);
  const title = r.tour.public ? <Link className="row-title" to={`/ture/${r.tour.id}`}>{r.tour.name}</Link> : <span className="row-title">{r.tour.name}</span>;
  return (
    <li className="reg-row">
      <div className="reg-art"><SceneArt seed={r.tour.id} difficulty={r.tour.difficulty.code} /></div>
      <div className="reg-main">
        <DifficultyBadge code={r.tour.difficulty.code} label={r.tour.difficulty.label} />
        {title}
        <span className="muted reg-meta">{formatDateTime(r.tour.startAt)} · {r.tour.club.name}</span>
      </div>
      <div className="reg-side">
        <StatusChip status={r.status} label={r.attendance ?? r.label} />
        {r.tour.cancelled && <span className="status-chip status-err">Tura otkazana</span>}
        {onCancel && r.canCancel && (confirming ? (
          <span className="confirm-inline">
            <span className="label-mono">Sigurno?</span>
            <button type="button" className="btn btn-sm btn-danger" disabled={pending} onClick={() => onCancel(r.id)}>Da, odjavi</button>
            <button type="button" className="btn btn-sm btn-ghost" onClick={() => setConfirming(false)}>Ne</button>
          </span>
        ) : (
          <button type="button" className="btn btn-sm btn-ghost" onClick={() => setConfirming(true)}>Odjavi se</button>
        ))}
      </div>
    </li>
  );
}

export function MyRegistrationsPage() {
  const regs = useMyRegistrations();
  const cancel = useCancelRegistration();
  if (regs.isPending) return <Loading label="Učitavanje prijava" />;
  if (regs.isError) return <div className="container page"><Notice kind="error">Prijave nije moguće učitati.</Notice></div>;
  const { upcoming, history } = regs.data;
  return (
    <section className="container page">
      <span className="label-mono">Planinar · Prijave</span>
      <h1 className="page-title">Moje prijave</h1>
      {cancel.isSuccess && <Notice kind="ok">{cancel.data.detail}</Notice>}
      {cancel.error instanceof ApiError && <Notice kind="error">{cancel.error.detail}</Notice>}

      <h2 className="section-title">Predstojeće</h2>
      {upcoming.length
        ? <ul className="reg-list">{upcoming.map((r) => <RegistrationRow key={r.id} r={r} onCancel={(id) => cancel.mutate(id)} pending={cancel.isPending} />)}</ul>
        : <Empty text="Nemate predstojećih prijava." cta={{ to: '/ture', label: 'Pregledaj ture' }} />}

      {history.length > 0 && (
        <>
          <h2 className="section-title">Historija</h2>
          <ul className="reg-list reg-list-quiet">{history.map((r) => <RegistrationRow key={r.id} r={r} />)}</ul>
        </>
      )}
    </section>
  );
}

// --- Moja članstva -------------------------------------------------------------------
export function MyMembershipsPage() {
  const items = useMyMemberships();
  if (items.isPending) return <Loading label="Učitavanje članstava" />;
  if (items.isError) return <div className="container page"><Notice kind="error">Članstva nije moguće učitati.</Notice></div>;
  return (
    <section className="container page">
      <span className="label-mono">Planinar · Društva</span>
      <h1 className="page-title">Moja članstva</h1>
      {items.data.length === 0 ? (
        <Empty text="Još niste član nijednog društva." cta={{ to: '/drustva', label: 'Pregledaj društva' }} />
      ) : (
        <ul className="reg-list">
          {items.data.map((m) => (
            <li key={m.id} className="reg-row">
              <div className="reg-art"><SceneArt seed={m.club.id} variant="club" /></div>
              <div className="reg-main">
                <span className="label-mono">{m.club.city}</span>
                {m.club.public ? <Link className="row-title" to={`/drustva/${m.club.id}`}>{m.club.name}</Link> : <span className="row-title">{m.club.name}</span>}
                <span className="muted reg-meta">
                  Zahtjev: {formatLong(m.createdAt)}
                  {m.validUntil && ` · važi do ${m.validUntil.split('-').reverse().join('.')}.`}
                </span>
              </div>
              <div className="reg-side">
                {m.expired ? <span className="status-chip status-off">Isteklo</span> : <StatusChip status={m.status} label={m.label} />}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// --- Odabir više tura -----------------------------------------------------------------
function ConfirmResults({ results }: { results: ConfirmResult[] }) {
  const anyOk = results.some((r) => r.ok);
  return (
    <div className="results">
      {anyOk && <Confetti seed={results.length} />}
      <Frosti mood={anyOk ? 'happy' : 'sad'} size={104} />
      <h2>{anyOk ? 'Gotovo! Evo rezultata prijava.' : 'Nijedna prijava nije uspjela.'}</h2>
      <ul className="result-list">
        {results.map((r) => (
          <li key={r.tourId} className={r.ok ? 'is-ok' : 'is-err'}>
            <span className="result-icon" aria-hidden="true">{r.ok ? '✓' : '×'}</span>
            <strong>{r.name}</strong>
            <span className="muted">{r.ok ? (r.status === 'PRIJAVLJEN' ? 'prijavljeni ste' : 'na listi čekanja') : r.detail}</span>
          </li>
        ))}
      </ul>
      <Link className="btn btn-accent" to="/moje-prijave">Moje prijave <span className="arrow" aria-hidden="true">→</span></Link>
    </div>
  );
}

export function SelectionPage() {
  const sel = useSelection();
  const remove = useSelectionRemove();
  const confirm = useSelectionConfirm();
  const { data: me } = useMe();

  if (confirm.isSuccess) return <section className="container page"><ConfirmResults results={confirm.data} /></section>;
  if (sel.isPending) return <Loading label="Učitavanje odabira" />;
  if (sel.isError) return <div className="container page"><Notice kind="error">Odabir nije moguće učitati.</Notice></div>;
  const tours = sel.data.tours;
  const total = tours.reduce((sum, t) => sum + t.price, 0);
  const canConfirm = me?.authenticated && !me.user.roles.systemAdmin;

  return (
    <section className="container page">
      <span className="label-mono">Odabir · {tours.length}/{sel.data.max}</span>
      <h1 className="page-title">Odabrane ture</h1>
      <p className="muted page-lead">Prijavite se na sve odabrane ture odjednom. Svaka prijava se provjerava zasebno.</p>
      {confirm.error instanceof ApiError && <Notice kind="error">{confirm.error.detail}</Notice>}

      {tours.length === 0 ? (
        <Empty text="Niste odabrali nijednu turu." cta={{ to: '/ture', label: 'Pregledaj ture' }} />
      ) : (
        <>
          <div className="tour-list">
            {tours.map((t, i) => (
              <div key={t.id} className="selection-item">
                <TourCard tour={t} index={i} />
                <button type="button" className="btn btn-ghost btn-sm selection-remove" disabled={remove.isPending}
                  onClick={() => remove.mutate(t.id)} aria-label={`Ukloni turu ${t.name} iz odabira`}>Ukloni</button>
              </div>
            ))}
          </div>
          <div className="selection-bar sticker">
            <span className="mono">{tours.length} {tours.length === 1 ? 'tura' : 'ture'} · ukupno {formatPrice(total)}</span>
            {canConfirm ? (
              <button type="button" className="btn btn-accent" disabled={confirm.isPending} onClick={() => confirm.mutate()}>
                {confirm.isPending && <span className="spinner" aria-hidden="true" />}Prijavi me na sve
              </button>
            ) : me?.authenticated ? null : (
              <Link className="btn btn-accent" to={`/prijava?next=${encodeURIComponent('/odabir')}`}>Prijavite se za nastavak</Link>
            )}
          </div>
        </>
      )}
    </section>
  );
}
