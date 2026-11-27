// Postavke obavještenja na profilu: za svaku kategoriju uloga korisnika bira se način slanja.
// Promjena se odmah čuva na serveru; sigurnosna obavještenja se ne mogu isključiti.
import { useId, useState } from 'react';

import { ApiError } from '../api/client';
import {
  useNotificationSettings, useSaveNotificationSetting, type NotificationCategory, type NotificationMode,
} from '../api/notifications';
import { Notice } from './forms';
import './notifications.css';

function CategoryRow({ c }: { c: NotificationCategory }) {
  const save = useSaveNotificationSetting();
  const name = useId();
  // izbor se prikaže odmah (lokalno stanje), a vraća se na serversko ako čuvanje ne uspije
  const [mode, setMode] = useState(c.mode);
  const [serverMode, setServerMode] = useState(c.mode);
  if (serverMode !== c.mode) {
    setServerMode(c.mode);
    setMode(c.mode);
  }

  function choose(next: NotificationMode) {
    setMode(next);
    save.mutate({ code: c.code, mode: next }, { onError: () => setMode(c.mode) });
  }
  return (
    <li className="notif-row">
      <div className="notif-copy">
        <strong>{c.label}</strong>
        <span className="muted">{c.description}</span>
      </div>
      {c.security ? (
        <span className="notif-locked label-mono">Uvijek uključeno</span>
      ) : (
        <fieldset className="notif-modes">
          <legend className="sr-only">{c.label}</legend>
          {c.modes.map((m) => (
            <label key={m.code} className={`notif-mode${mode === m.code ? ' is-on' : ''}`}>
              <input type="radio" name={name} value={m.code} checked={mode === m.code} onChange={() => choose(m.code)} />
              <span>{m.label}</span>
            </label>
          ))}
        </fieldset>
      )}
      {save.error instanceof ApiError && <span className="field-error">{save.error.detail}</span>}
    </li>
  );
}

export function NotificationSettings() {
  const settings = useNotificationSettings();
  return (
    <section className="notif-section card-form" id="obavjestenja" aria-labelledby="notif-title">
      <h2 id="notif-title">Obavještenja na email</h2>
      <p className="muted field-hint">
        „Pregled“ skuplja obavještenja u jedan email (dnevno ili sedmično). Emailovi nikad ne sadrže lične
        podatke drugih korisnika; za detalje vodi link u aplikaciju.
      </p>
      {settings.isPending && <p className="muted" role="status">Učitavanje postavki…</p>}
      {settings.isError && <Notice kind="error">Postavke obavještenja nije moguće učitati.</Notice>}
      {settings.data && <ul className="notif-list">{settings.data.map((c) => <CategoryRow key={c.code} c={c} />)}</ul>}
    </section>
  );
}
