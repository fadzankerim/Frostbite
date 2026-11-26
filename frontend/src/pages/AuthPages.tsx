import { useState, type FormEvent, type ReactNode } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router';

import { useLogin, useRegister } from '../api/auth';
import { ApiError } from '../api/client';
import { BJELASNICA, ContourField } from '../components/ContourField';
import { Field, Notice, PasswordInput, SubmitButton } from '../components/forms';
import { Frosti } from '../components/Frosti';
import './pages.css';

function stateNotice(state: unknown): string | null {
  const n = (state as { notice?: unknown } | null)?.notice;
  return typeof n === 'string' ? n : null;
}

function AuthShell({ eyebrow, title, lead, children }: { eyebrow: string; title: string; lead: ReactNode; children: ReactNode }) {
  return (
    <div className="auth">
      <section className="auth-form">
        <div className="auth-form-inner">
          <span className="label-mono">{eyebrow}</span>
          <h1 className="auth-title">{title}</h1>
          <p className="muted auth-lead">{lead}</p>
          {children}
        </div>
      </section>
      <aside className="auth-visual" aria-hidden="true">
        <div className="frame">
          <div className="frame-bar">
            <span className="label-mono"><span className="live-dot" /> Topo · 1:25 000</span>
            <span className="label-mono">{BJELASNICA.lat}° N · {BJELASNICA.lon}° E</span>
          </div>
          <div className="frame-map">
            <ContourField className="cf-panel" seed={11} center={[300, 300]} />
            <div className="peek-frosti"><Frosti mood="wave" size={110} /></div>
          </div>
          <div className="frame-bar">
            <span className="label-mono">Veza šifrovana · TLS</span>
            <span className="label-mono">Pomjerite kursor</span>
          </div>
        </div>
      </aside>
    </div>
  );
}

export function LoginPage() {
  const login = useLogin();
  const location = useLocation();
  const [params] = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const notice = stateNotice(location.state);

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (login.isPending) return;
    // Nakon uspjeha GuestOnly preusmjerava na provjereni ?next= (safeNext).
    login.mutate({ email: email.trim(), password }, { onError: () => setPassword('') });
  }

  const error = login.error instanceof ApiError ? login.error.detail : login.error ? 'Prijava nije uspjela.' : null;

  return (
    <AuthShell
      eyebrow="Prijava · 01"
      title="Dobro došli nazad."
      lead={<>Nemate nalog? <Link className="link" to={`/registracija${params.toString() ? `?${params}` : ''}`}>Registrujte se</Link>.</>}
    >
      <form className="form" onSubmit={onSubmit} noValidate>
        {notice && !error && <Notice kind="ok">{notice}</Notice>}
        {error && <Notice kind="error">{error}</Notice>}
        <Field label="Email">
          {(p) => (
            <input {...p} className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              autoComplete="email" inputMode="email" autoCapitalize="off" spellCheck={false}
              maxLength={254} required autoFocus />
          )}
        </Field>
        <Field label="Lozinka">
          {(p) => <PasswordInput {...p} value={password} onChange={setPassword} autoComplete="current-password" />}
        </Field>
        <SubmitButton pending={login.isPending}>Prijavi se</SubmitButton>
      </form>
    </AuthShell>
  );
}

type RegisterForm = { firstName: string; lastName: string; email: string; phone: string; password: string; passwordConfirm: string };
const EMPTY: RegisterForm = { firstName: '', lastName: '', email: '', phone: '', password: '', passwordConfirm: '' };

export function RegisterPage() {
  const register = useRegister();
  const navigate = useNavigate();
  const [form, setForm] = useState<RegisterForm>(EMPTY);
  const [localErrors, setLocalErrors] = useState<Record<string, string[]>>({});

  const set = (k: keyof RegisterForm) => (v: string) => setForm((f) => ({ ...f, [k]: v }));
  const serverErrors = register.error instanceof ApiError ? register.error.fieldErrors : {};
  const errors = { ...serverErrors, ...localErrors };
  const general = register.error instanceof ApiError
    ? (errors.__all__?.[0] ?? (Object.keys(serverErrors).length ? null : register.error.detail))
    : null;

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (register.isPending) return;
    const local: Record<string, string[]> = {};
    if (form.password !== form.passwordConfirm) local.passwordConfirm = ['Lozinke se ne podudaraju.'];
    setLocalErrors(local);
    if (Object.keys(local).length) return;
    register.mutate(
      { ...form, email: form.email.trim(), firstName: form.firstName.trim(), lastName: form.lastName.trim() },
      {
        onSuccess: (res) => navigate('/prijava', { state: { notice: res.detail } }),
        onError: () => setForm((f) => ({ ...f, password: '', passwordConfirm: '' })),
      },
    );
  }

  return (
    <AuthShell
      eyebrow="Registracija · 02"
      title="Krenite na prvu turu."
      lead={<>Već imate nalog? <Link className="link" to="/prijava">Prijavite se</Link>.</>}
    >
      <form className="form" onSubmit={onSubmit} noValidate>
        {general && <Notice kind="error">{general}</Notice>}
        <div className="form-row">
          <Field label="Ime" errors={errors.firstName}>
            {(p) => <input {...p} className="input" value={form.firstName} onChange={(e) => set('firstName')(e.target.value)}
              autoComplete="given-name" maxLength={60} required />}
          </Field>
          <Field label="Prezime" errors={errors.lastName}>
            {(p) => <input {...p} className="input" value={form.lastName} onChange={(e) => set('lastName')(e.target.value)}
              autoComplete="family-name" maxLength={60} required />}
          </Field>
        </div>
        <Field label="Email" errors={errors.email}>
          {(p) => <input {...p} className="input" type="email" value={form.email} onChange={(e) => set('email')(e.target.value)}
            autoComplete="email" inputMode="email" autoCapitalize="off" spellCheck={false} maxLength={254} required />}
        </Field>
        <Field label="Telefon (opciono)" errors={errors.phone}>
          {(p) => <input {...p} className="input" type="tel" value={form.phone} onChange={(e) => set('phone')(e.target.value)}
            autoComplete="tel" inputMode="tel" maxLength={30} />}
        </Field>
        <Field label="Lozinka" errors={errors.password}
          hint="Najmanje 10 znakova; ne smije biti česta lozinka niti slična imenu ili emailu.">
          {(p) => <PasswordInput {...p} value={form.password} onChange={set('password')} autoComplete="new-password" showStrength />}
        </Field>
        <Field label="Ponovite lozinku" errors={errors.passwordConfirm}>
          {(p) => <PasswordInput {...p} value={form.passwordConfirm} onChange={set('passwordConfirm')} autoComplete="new-password" />}
        </Field>
        <SubmitButton pending={register.isPending}>Kreiraj nalog</SubmitButton>
      </form>
    </AuthShell>
  );
}
