// Prikaz bedževa: mreža s napretkom (profil) i modal "novi bedž" s konfetama i Frostijem.
import { useEffect, useRef, useState } from 'react';

import { useMarkBadgesSeen, useMyBadges, type MyBadge } from '../api/badges';
import { formatDate, formatNumber, plural } from '../lib/format';
import { groupByRole, progressRatio, ROLE_TITLES, TIER_LABELS, unseen } from '../lib/badges';
import { BadgeArt } from './BadgeArt';
import { Confetti } from './Confetti';
import { Notice } from './forms';
import { Frosti } from './Frosti';
import './badges.css';

function BadgeCard({ b }: { b: MyBadge }) {
  const ratio = progressRatio(b.progress, b.goal);
  return (
    <li className={`badge-card ${b.earned ? 'is-earned' : 'is-locked'}`}>
      <BadgeArt icon={b.icon} tier={b.tier} role={b.role} locked={!b.earned} />
      <strong>{b.name}</strong>
      <span className="muted">{b.description}</span>
      {b.earned ? (
        <span className="label-mono badge-meta">
          {TIER_LABELS[b.tier] ?? ''}{b.awardedAt ? ` · ${formatDate(b.awardedAt)}` : ''}
        </span>
      ) : (
        <div className="badge-progress">
          <div className="badge-track" role="progressbar" aria-label={`Napredak: ${b.name}`}
            aria-valuemin={0} aria-valuemax={b.goal} aria-valuenow={b.progress}>
            <span className="badge-fill" style={{ transform: `scaleX(${ratio})` }} />
          </div>
          <span className="label-mono badge-meta">{formatNumber(b.progress)} / {formatNumber(b.goal)}</span>
        </div>
      )}
    </li>
  );
}

/** Sekcija "Bedževi" na profilu: osvojeni u boji, neosvojeni sivi s trakom napretka. */
export function MyBadgesSection() {
  const badges = useMyBadges();
  const earned = badges.data?.filter((b) => b.earned).length ?? 0;
  return (
    <section className="badges-section" aria-labelledby="badges-title">
      <div className="badges-head">
        <h2 id="badges-title">Bedževi</h2>
        {badges.data && <span className="label-mono">Osvojeno {earned} / {badges.data.length}</span>}
      </div>
      <p className="muted">Bedževe vidiš samo ti. Dobijaš ih za završene korake: prisustvo na turi potvrđuje vodič.</p>
      {badges.isPending && <p className="muted" role="status">Učitavanje bedževa…</p>}
      {badges.isError && <Notice kind="error">Bedževe nije moguće učitati.</Notice>}
      {badges.data && groupByRole(badges.data).map((g) => (
        <div key={g.role} className="badges-group">
          <h3>{ROLE_TITLES[g.role]}</h3>
          <ul className="badge-grid">{g.badges.map((b) => <BadgeCard key={b.code} b={b} />)}</ul>
        </div>
      ))}
    </section>
  );
}

/** Modal za nove bedževe (seen=false). Prikazuje se nakon prijave i nakon radnji koje mogu
 *  dati bedž; zatvaranje (dugme ili Escape) ih označava kao viđene na serveru. */
export function BadgeNotifier() {
  const badges = useMyBadges();
  const markSeen = useMarkBadgesSeen();
  const ref = useRef<HTMLDialogElement>(null);
  const [shown, setShown] = useState<MyBadge[]>([]);
  const fresh = unseen(badges.data);
  const freshKey = fresh.map((b) => b.code).join(',');

  if (!shown.length && fresh.length && !markSeen.isPending) setShown(fresh);

  useEffect(() => {
    const d = ref.current;
    if (d && shown.length && !d.open) d.showModal();
  }, [shown]);

  function close() {
    ref.current?.close();
  }

  function onClose() {
    setShown([]);
    if (freshKey) markSeen.mutate();
  }

  if (!shown.length) return null;
  const one = shown.length === 1;
  return (
    <dialog ref={ref} className="badge-dialog" aria-labelledby="badge-dialog-title" onClose={onClose}>
      <Confetti seed={shown.length + shown[0]!.code.length} />
      <div className="badge-dialog-body">
        <Frosti mood="happy" size={84} />
        <span className="label-mono">{one ? 'Novi bedž' : `${shown.length} ${plural(shown.length, ['novi bedž', 'nova bedža', 'novih bedževa'])}`}</span>
        <h2 id="badge-dialog-title">{one ? `Bedž „${shown[0]!.name}“ je tvoj!` : 'Novi bedževi su tvoji!'}</h2>
        <ul className="badge-new-list">
          {shown.map((b) => (
            <li key={b.code}>
              <BadgeArt icon={b.icon} tier={b.tier} role={b.role} size={one ? 96 : 72} />
              {!one && <strong>{b.name}</strong>}
              <span className="muted">{b.description}</span>
            </li>
          ))}
        </ul>
        <button type="button" className="btn" onClick={close} autoFocus>Super!</button>
      </div>
    </dialog>
  );
}
