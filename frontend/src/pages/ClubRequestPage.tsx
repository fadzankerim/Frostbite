// F09 - zahtjev za registraciju planinarskog društva. Društvo postaje vidljivo (a podnosilac
// admin društva) tek kad ga odobri sistemski admin.
import { useState, type FormEvent } from 'react';
import { Link } from 'react-router';

import { ApiError } from '../api/client';
import { useClubRequestStatus, useRequestClub, type ClubRequestInput } from '../api/hiker';
import { Field, Notice, SubmitButton } from '../components/forms';
import { Frosti } from '../components/Frosti';
import { Loading } from '../components/guards';
import './pages.css';

const EMPTY: ClubRequestInput = { name: '', city: '', description: '', email: '', phone: '' };

export function ClubRequestPage() {
  const status = useClubRequestStatus();
  const req = useRequestClub();
  const [f, setF] = useState(EMPTY);
  const errors = req.error instanceof ApiError ? req.error.fieldErrors : {};
  const set = (k: keyof ClubRequestInput) => (v: string) => setF((s) => ({ ...s, [k]: v }));

  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!req.isPending) req.mutate({ ...f, name: f.name.trim(), city: f.city.trim(), email: f.email.trim() });
  }

  if (status.isPending) return <Loading />;
  return (
    <section className="container page">
      <Link to="/drustva" className="back label-mono">← Društva</Link>
      <span className="label-mono">Planinar · Novo društvo</span>
      <h1 className="page-title">Registracija društva</h1>
      <p className="muted page-lead">
        Pošaljite zahtjev za registraciju planinarskog društva. Nakon što ga sistemski admin odobri, društvo postaje
        vidljivo i vi postajete njegov admin (ture, vodiči, članstva).
      </p>

      {req.isSuccess ? (
        <div className="register-done">
          <Frosti mood="happy" size={104} />
          <strong>{req.data.detail}</strong>
          <Link className="btn btn-ghost" to="/drustva">Nazad na društva</Link>
        </div>
      ) : status.data && !status.data.canRequest ? (
        <div className="empty">
          <Frosti mood="think" size={96} />
          <p className="muted">Već imate zahtjev za registraciju društva koji čeka odobrenje.</p>
        </div>
      ) : (
        <form className="card-form form profile-club-form" onSubmit={submit} noValidate>
          {req.error instanceof ApiError && !Object.keys(errors).length && <Notice kind="error">{req.error.detail}</Notice>}
          <Field label="Naziv društva" errors={errors.name}>
            {(p) => <input {...p} className="input" value={f.name} onChange={(e) => set('name')(e.target.value)} maxLength={120} required />}
          </Field>
          <Field label="Grad" errors={errors.city}>
            {(p) => <input {...p} className="input" value={f.city} onChange={(e) => set('city')(e.target.value)} maxLength={80} required />}
          </Field>
          <Field label="Opis (opciono)" errors={errors.description}>
            {(p) => <textarea {...p} className="input textarea" rows={4} value={f.description} onChange={(e) => set('description')(e.target.value)} maxLength={2000} />}
          </Field>
          <div className="form-row">
            <Field label="Kontakt email (opciono)" errors={errors.email}>
              {(p) => <input {...p} className="input" type="email" value={f.email} onChange={(e) => set('email')(e.target.value)} maxLength={254} />}
            </Field>
            <Field label="Kontakt telefon (opciono)" errors={errors.phone}>
              {(p) => <input {...p} className="input" type="tel" value={f.phone} onChange={(e) => set('phone')(e.target.value)} maxLength={30} />}
            </Field>
          </div>
          <SubmitButton pending={req.isPending}>Pošalji zahtjev</SubmitButton>
        </form>
      )}
    </section>
  );
}
