// Panel vodiča: ture koje vodi, ture bez vodiča, učesnici, prisustvo i izvještaj (F15-F20).
import { useState, type FormEvent, type ReactNode } from 'react';
import { Link, useParams } from 'react-router';

import { ApiError } from '../api/client';
import {
  useGuideApply, useGuideAttendance, useGuideClose, useGuideDashboard, useGuideReport, useGuideTour,
  type GuideTour, type GuideTourBrief, type Participant,
} from '../api/guide';
import { parseId } from '../api/public';
import { Confetti } from '../components/Confetti';
import { Field, Notice, SubmitButton } from '../components/forms';
import { Frosti } from '../components/Frosti';
import { Loading } from '../components/guards';
import { SceneArt } from '../components/SceneArt';
import { DifficultyBadge } from '../components/TourCard';
import { countdown, formatDateTime, formatLong, telHref } from '../lib/format';
import { NotFoundPage } from './StatusPages';
import './pages.css';

function Phone({ value }: { value: string }) {
  if (!value) return <span className="muted">—</span>;
  const href = telHref(value);
  return href ? <a className="link mono" href={href}>{value}</a> : <span className="mono">{value}</span>;
}

function TourRow({ t, children }: { t: GuideTourBrief; children?: ReactNode }) {
  return (
    <li className="reg-row">
      <div className="reg-art"><SceneArt seed={t.id} difficulty={t.difficulty.code} /></div>
      <div className="reg-main">
        <DifficultyBadge code={t.difficulty.code} label={t.difficulty.label} />
        <span className="row-title">{t.name}</span>
        <span className="muted reg-meta">{formatDateTime(t.startAt)} · {t.club.name} · {t.status.label}</span>
      </div>
      <div className="reg-side">{children}</div>
    </li>
  );
}

function ApplyButton({ t }: { t: GuideTourBrief & { applied: boolean } }) {
  const apply = useGuideApply(t.id);
  if (t.applied || apply.isSuccess) return <span className="status-chip status-wait">Prijava poslana</span>;
  return (
    <>
      {apply.error instanceof ApiError && <span className="field-error">{apply.error.detail}</span>}
      <button type="button" className="btn btn-sm btn-ghost" disabled={apply.isPending} onClick={() => apply.mutate(undefined)}>
        Prijavi se za vođenje
      </button>
    </>
  );
}

export function GuideDashboardPage() {
  const dash = useGuideDashboard();
  if (dash.isPending) return <Loading label="Učitavanje panela" />;
  if (dash.isError) return <div className="container page"><Notice kind="error">Panel nije moguće učitati.</Notice></div>;
  const { myTours, openTours } = dash.data;
  return (
    <section className="container page">
      <span className="label-mono">Vodič · Panel</span>
      <h1 className="page-title">Vođenje tura</h1>

      <h2 className="section-title">Ture koje vodim</h2>
      {myTours.length ? (
        <ul className="reg-list">
          {myTours.map((t) => (
            <TourRow key={t.id} t={t}>
              {countdown(t.startAt) && <span className="label-mono tag">za {countdown(t.startAt)}</span>}
              <Link className="btn btn-sm btn-accent" to={`/vodic/ture/${t.id}`}>Učesnici <span className="arrow" aria-hidden="true">→</span></Link>
            </TourRow>
          ))}
        </ul>
      ) : (
        <div className="empty"><Frosti mood="think" size={88} /><p className="muted">Trenutno ne vodite nijednu turu.</p></div>
      )}

      <h2 className="section-title">Ture bez vodiča</h2>
      <p className="muted page-lead">Ture vaših društava kojima još nije određen vodič. Prijavu odobrava admin društva.</p>
      {openTours.length ? (
        <ul className="reg-list">{openTours.map((t) => <TourRow key={t.id} t={t}><ApplyButton t={t} /></TourRow>)}</ul>
      ) : (
        <div className="empty"><Frosti mood="happy" size={88} /><p className="muted">Sve ture vaših društava imaju vodiča.</p></div>
      )}
    </section>
  );
}

function ParticipantCard({ p, attendanceMode, checked, onToggle }: {
  p: Participant; attendanceMode: boolean; checked: boolean; onToggle: () => void;
}) {
  const canMark = attendanceMode && p.status.code === 'PRIJAVLJEN';
  return (
    <li className={`participant${checked && canMark ? ' is-present' : ''}`}>
      {canMark && (
        <label className="present-box">
          <input type="checkbox" checked={checked} onChange={onToggle} />
          <span className="sr-only">Prisutan: {p.name}</span>
          <span className="present-check" aria-hidden="true">✓</span>
        </label>
      )}
      <div className="participant-main">
        <strong>{p.name}</strong>
        <dl className="participant-facts">
          <div><dt className="label-mono">Telefon</dt><dd><Phone value={p.phone} /></dd></div>
          <div>
            <dt className="label-mono">Hitni kontakt</dt>
            <dd>{p.emergencyContactName || p.emergencyContactPhone
              ? <>{p.emergencyContactName} <Phone value={p.emergencyContactPhone} /></>
              : <span className="muted">—</span>}</dd>
          </div>
        </dl>
        {p.healthNotes && <p className="health-note"><span className="label-mono">Zdravlje</span>{p.healthNotes}</p>}
      </div>
      <div className="participant-side">
        <span className={`status-chip ${p.status.code === 'PRIJAVLJEN' ? 'status-ok' : 'status-wait'}`}>{p.status.label}</span>
        {!attendanceMode && p.attendance && (
          <span className={`status-chip ${p.attendance === 'PRISUSTVOVAO' ? 'status-ok' : 'status-off'}`}>
            {p.attendance === 'PRISUSTVOVAO' ? 'Prisutan' : 'Nije došao'}
          </span>
        )}
      </div>
    </li>
  );
}

function AttendanceAndReport({ t, report }: { t: GuideTour; report: ReturnType<typeof useGuideReport> }) {
  const registered = t.participants.filter((p) => p.status.code === 'PRIJAVLJEN');
  const [present, setPresent] = useState<Set<number>>(
    () => new Set(registered.filter((p) => p.attendance === 'PRISUSTVOVAO').map((p) => p.id)));
  const attendance = useGuideAttendance(t.id);
  const [text, setText] = useState('');

  function toggle(id: number) {
    setPresent((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  }

  function submitReport(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!report.isPending) report.mutate({ text: text.trim() });
  }

  const reportErrors = report.error instanceof ApiError ? report.error.fieldErrors.text : undefined;

  return (
    <>
      <div className="section-head">
        <h2 className="section-title">Prisustvo <span className="mono muted">{present.size}/{registered.length}</span></h2>
        <button type="button" className="btn btn-accent btn-sm" disabled={attendance.isPending}
          onClick={() => attendance.mutate({ present: [...present] })}>Sačuvaj prisustvo</button>
      </div>
      {attendance.isSuccess && <Notice kind="ok">{attendance.data.detail}</Notice>}
      {attendance.error instanceof ApiError && <Notice kind="error">{attendance.error.detail}</Notice>}
      <ul className="participant-list">
        {t.participants.map((p) => (
          <ParticipantCard key={p.id} p={p} attendanceMode checked={present.has(p.id)} onToggle={() => toggle(p.id)} />
        ))}
      </ul>

      {t.canReport && (
        <form className="form card-form report-form" onSubmit={submitReport} noValidate>
          <h2>Izvještaj sa ture</h2>
          <p className="muted field-hint">Nakon izvještaja tura se označava kao održana i više se ne mijenja. Prvo sačuvajte prisustvo.</p>
          {report.error instanceof ApiError && !reportErrors && <Notice kind="error">{report.error.detail}</Notice>}
          <Field label="Kako je prošlo?" errors={reportErrors}>
            {(p) => <textarea {...p} className="input textarea" rows={5} maxLength={4000} value={text} onChange={(e) => setText(e.target.value)} required />}
          </Field>
          <SubmitButton pending={report.isPending}>Pošalji izvještaj</SubmitButton>
        </form>
      )}
    </>
  );
}

export function GuideTourPage() {
  const { id } = useParams();
  const tourId = parseId(id);
  const tour = useGuideTour(tourId);
  const close = useGuideClose(tourId ?? 0);
  // izvještaj se drži ovdje: nakon slanja tura postaje "održana" i dio za prisustvo nestaje,
  // a poruka o uspjehu treba ostati vidljiva
  const report = useGuideReport(tourId ?? 0);
  const [confirmClose, setConfirmClose] = useState(false);

  if (tourId === null) return <NotFoundPage />;
  if (tour.isPending) return <Loading label="Učitavanje učesnika" />;
  if (tour.isError) {
    if (tour.error instanceof ApiError && tour.error.status === 404) return <NotFoundPage />;
    return <div className="container page"><Notice kind="error">Turu nije moguće učitati.</Notice></div>;
  }
  const t = tour.data;
  const registered = t.participants.filter((p) => p.status.code === 'PRIJAVLJEN').length;

  return (
    <section className="container page">
      <Link to="/vodic" className="back label-mono">← Panel vodiča</Link>
      <div className="banner banner-sm has-scene"><SceneArt seed={t.id} difficulty={t.difficulty.code} width={800} /></div>
      <div className="detail-badges">
        <DifficultyBadge code={t.difficulty.code} label={t.difficulty.label} />
        <span className="label-mono tag">{t.status.label}</span>
      </div>
      <h1 className="page-title">{t.name}</h1>
      <p className="muted">{formatLong(t.startAt)} · {t.meetingPoint} · {t.club.name}</p>

      <div className="privacy-note sticker" role="note">
        <svg className="lock-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <rect x="4.5" y="10.5" width="15" height="10" rx="2.5" />
          <path className="lock-shackle" d="M8 10.5 V8 a4 4 0 0 1 8 0 V10.5" />
          <circle cx="12" cy="15.5" r="1.6" />
        </svg>
        <span>Lični podaci učesnika vidljivi su samo vama, do 7 dana nakon ture. Svaki pristup se bilježi.</span>
      </div>

      <div className="guide-stats">
        <div><span className="mono altitude">{registered}</span><span className="label-mono">Prijavljeno</span></div>
        <div><span className="mono altitude">{t.participants.length - registered}</span><span className="label-mono">Lista čekanja</span></div>
        <div><span className="mono altitude">{t.maxParticipants}</span><span className="label-mono">Kapacitet</span></div>
        <div className="guide-actions">
          {t.canClose && (confirmClose ? (
            <span className="confirm-inline">
              <span className="label-mono">Zatvoriti prijave?</span>
              <button type="button" className="btn btn-sm btn-danger" disabled={close.isPending} onClick={() => close.mutate(undefined)}>Da</button>
              <button type="button" className="btn btn-sm btn-ghost" onClick={() => setConfirmClose(false)}>Ne</button>
            </span>
          ) : (
            <button type="button" className="btn btn-sm btn-ghost" onClick={() => setConfirmClose(true)}>Zatvori prijave</button>
          ))}
        </div>
      </div>
      {close.isSuccess && <Notice kind="ok">{close.data.detail}</Notice>}
      {close.error instanceof ApiError && <Notice kind="error">{close.error.detail}</Notice>}

      {report.isSuccess && (
        <div className="register-done"><Confetti seed={t.id} /><Frosti mood="happy" size={96} /><strong>{report.data.detail}</strong></div>
      )}
      {t.report && (
        <section className="card-form report-done">
          <span className="label-mono">Izvještaj · {formatDateTime(t.report.createdAt)} · prisutno {t.report.attendeesCount}</span>
          <p className="prose">{t.report.text}</p>
        </section>
      )}

      {t.attendanceOpen ? (
        <AttendanceAndReport key={t.id} t={t} report={report} />
      ) : (
        <>
          <h2 className="section-title">Učesnici <span className="mono muted">({t.participants.length})</span></h2>
          {!t.report && <p className="muted field-hint">Prisustvo i izvještaj se unose od 12 sati prije polaska.</p>}
          {t.participants.length ? (
            <ul className="participant-list">
              {t.participants.map((p) => <ParticipantCard key={p.id} p={p} attendanceMode={false} checked={false} onToggle={() => undefined} />)}
            </ul>
          ) : (
            <div className="empty"><Frosti mood="think" size={88} /><p className="muted">Još nema prijavljenih učesnika.</p></div>
          )}
        </>
      )}
    </section>
  );
}
