// Profil (F07) i promjena lozinke (F08).
import { useState, type FormEvent } from 'react';

import { displayName, useMe } from '../api/auth';
import { ApiError } from '../api/client';
import { useChangePassword, useProfile, useUpdateProfile, type Profile } from '../api/hiker';
import { Field, Notice, PasswordInput, SubmitButton } from '../components/forms';
import { Frosti } from '../components/Frosti';
import { Loading } from '../components/guards';
import './pages.css';

const ROLE_LABELS = { systemAdmin: 'Sistemski admin', clubAdmin: 'Admin društva', guide: 'Vodič' } as const;
type EditableProfile = Omit<Profile, 'email'>;

function ProfileForm({ initial }: { initial: Profile }) {
  const update = useUpdateProfile();
  const { email, ...rest } = initial;
  const [form, setForm] = useState<EditableProfile>(rest);
  const set = (k: keyof EditableProfile) => (v: string) => setForm((f) => ({ ...f, [k]: v }));
  const errors = update.error instanceof ApiError ? update.error.fieldErrors : {};

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!update.isPending) update.mutate(form);
  }

  return (
    <form className="form card-form" onSubmit={onSubmit} noValidate>
      <h2>Lični podaci</h2>
      {update.isSuccess && <Notice kind="ok">{update.data.detail}</Notice>}
      {update.error instanceof ApiError && !Object.keys(errors).length && <Notice kind="error">{update.error.detail}</Notice>}
      <div className="form-row">
        <Field label="Ime" errors={errors.firstName}>
          {(p) => <input {...p} className="input" value={form.firstName} onChange={(e) => set('firstName')(e.target.value)} autoComplete="given-name" maxLength={60} required />}
        </Field>
        <Field label="Prezime" errors={errors.lastName}>
          {(p) => <input {...p} className="input" value={form.lastName} onChange={(e) => set('lastName')(e.target.value)} autoComplete="family-name" maxLength={60} required />}
        </Field>
      </div>
      <Field label="Email" hint="Email se ne može mijenjati.">
        {(p) => <input {...p} className="input" value={email} readOnly disabled />}
      </Field>
      <Field label="Telefon" errors={errors.phone}>
        {(p) => <input {...p} className="input" type="tel" value={form.phone} onChange={(e) => set('phone')(e.target.value)} autoComplete="tel" maxLength={30} />}
      </Field>
      <div className="form-row">
        <Field label="Hitni kontakt (ime)" errors={errors.emergencyContactName} hint="Osoba koju vodič kontaktira u slučaju nezgode.">
          {(p) => <input {...p} className="input" value={form.emergencyContactName} onChange={(e) => set('emergencyContactName')(e.target.value)} maxLength={120} />}
        </Field>
        <Field label="Hitni kontakt (telefon)" errors={errors.emergencyContactPhone}>
          {(p) => <input {...p} className="input" type="tel" value={form.emergencyContactPhone} onChange={(e) => set('emergencyContactPhone')(e.target.value)} maxLength={30} />}
        </Field>
      </div>
      <Field label="Zdravstvene napomene" errors={errors.healthNotes}
        hint="Vidljivo samo vama i vodiču ture na koju ste prijavljeni (npr. alergije, dijabetes).">
        {(p) => <textarea {...p} className="input textarea" rows={4} value={form.healthNotes} onChange={(e) => set('healthNotes')(e.target.value)} maxLength={1000} />}
      </Field>
      <SubmitButton pending={update.isPending}>Sačuvaj profil</SubmitButton>
    </form>
  );
}

const EMPTY_PW = { oldPassword: '', newPassword: '', newPasswordConfirm: '' };

function PasswordForm({ email }: { email: string }) {
  const change = useChangePassword();
  const [pw, setPw] = useState(EMPTY_PW);
  const errors = change.error instanceof ApiError ? change.error.fieldErrors : {};
  const set = (k: keyof typeof EMPTY_PW) => (v: string) => setPw((p) => ({ ...p, [k]: v }));

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (change.isPending) return;
    // lozinke se brišu iz polja nakon svakog pokušaja (uspjeh ili greška)
    change.mutate(pw, { onSettled: () => setPw(EMPTY_PW) });
  }

  return (
    <form className="form card-form" onSubmit={onSubmit} noValidate>
      <h2>Promjena lozinke</h2>
      <p className="muted field-hint">Nakon promjene, sve ostale sesije (drugi uređaji) se odjavljuju.</p>
      {change.isSuccess && <Notice kind="ok">{change.data.detail}</Notice>}
      {/* skriveno korisničko ime pomaže upravljačima lozinki da sačuvaju novu lozinku uz pravi nalog */}
      <input type="text" name="username" autoComplete="username" value={email} readOnly hidden />
      <Field label="Trenutna lozinka" errors={errors.oldPassword}>
        {(p) => <PasswordInput {...p} value={pw.oldPassword} onChange={set('oldPassword')} autoComplete="current-password" />}
      </Field>
      <Field label="Nova lozinka" errors={errors.newPassword} hint="Najmanje 10 znakova; ne smije biti česta niti slična imenu ili emailu.">
        {(p) => <PasswordInput {...p} value={pw.newPassword} onChange={set('newPassword')} autoComplete="new-password" showStrength />}
      </Field>
      <Field label="Ponovite novu lozinku" errors={errors.newPasswordConfirm}>
        {(p) => <PasswordInput {...p} value={pw.newPasswordConfirm} onChange={set('newPasswordConfirm')} autoComplete="new-password" />}
      </Field>
      <SubmitButton pending={change.isPending}>Promijeni lozinku</SubmitButton>
    </form>
  );
}

export function ProfilePage() {
  const { data } = useMe();
  const profile = useProfile();
  if (!data?.authenticated) return null;     // RequireAuth je već preusmjerio
  const { user } = data;
  const roles = (Object.keys(ROLE_LABELS) as (keyof typeof ROLE_LABELS)[]).filter((r) => user.roles[r]);

  return (
    <section className="container page">
      <div className="profile-head">
        <Frosti mood="wave" size={88} />
        <div>
          <span className="label-mono">Profil · ID {String(user.id).padStart(5, '0')}</span>
          <h1 className="page-title">{displayName(user)}</h1>
          <div className="chips">
            {!user.roles.systemAdmin && <span className="chip chip-fun">Planinar</span>}
            {roles.map((r) => <span key={r} className="chip chip-accent">{ROLE_LABELS[r]}</span>)}
          </div>
        </div>
      </div>

      {profile.isPending && <Loading label="Učitavanje profila" />}
      {profile.isError && <Notice kind="error">Profil nije moguće učitati.</Notice>}
      {profile.data && (
        <div className="profile-grid">
          <ProfileForm initial={profile.data} />
          <PasswordForm email={profile.data.email} />
        </div>
      )}
    </section>
  );
}
