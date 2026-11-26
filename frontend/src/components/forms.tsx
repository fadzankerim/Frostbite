import { useId, useState, type ChangeEvent, type ReactNode } from 'react';

import { MIN_PASSWORD_LENGTH, passwordStrength, STRENGTH_LABELS } from '../lib/passwordStrength';

type FieldProps = {
  label: string;
  hint?: string;
  errors?: string[] | undefined;
  children: (props: { id: string; 'aria-invalid': boolean; 'aria-describedby': string | undefined }) => ReactNode;
};

/** Polje forme: labela, pomoćni tekst i greške povezani sa inputom (pristupačnost). */
export function Field({ label, hint, errors, children }: FieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errId = errors?.length ? `${id}-err` : undefined;
  const describedBy = [hintId, errId].filter(Boolean).join(' ') || undefined;
  return (
    <div className="field">
      <label className="field-label" htmlFor={id}>{label}</label>
      {children({ id, 'aria-invalid': Boolean(errors?.length), 'aria-describedby': describedBy })}
      {hint && <span className="field-hint" id={hintId}>{hint}</span>}
      {errors?.length ? (
        <ul className="field-error" id={errId}>
          {errors.map((e) => <li key={e}>{e}</li>)}
        </ul>
      ) : null}
    </div>
  );
}

type PasswordProps = {
  id: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete: 'current-password' | 'new-password';
  showStrength?: boolean;
  'aria-invalid': boolean;
  'aria-describedby': string | undefined;
};

/** Lozinka sa prikazom/skrivanjem i (opciono) indikatorom jačine. */
export function PasswordInput({ id, value, onChange, autoComplete, showStrength, ...aria }: PasswordProps) {
  const [visible, setVisible] = useState(false);
  const score = passwordStrength(value);
  return (
    <>
      <div className="pw-wrap">
        <input
          id={id}
          className="input"
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={(e: ChangeEvent<HTMLInputElement>) => onChange(e.target.value)}
          autoComplete={autoComplete}
          autoCapitalize="off"
          autoCorrect="off"
          spellCheck={false}
          maxLength={128}
          required
          {...aria}
        />
        <button
          type="button"
          className="pw-toggle label-mono"
          onClick={() => setVisible((v) => !v)}
          aria-pressed={visible}
          aria-controls={id}
          aria-label={visible ? 'Sakrij lozinku' : 'Prikaži lozinku'}
        >
          {visible ? 'Sakrij' : 'Prikaži'}
        </button>
      </div>
      {showStrength && (
        <div className="strength" data-score={score} aria-live="polite">
          <div className="strength-bars" aria-hidden="true">
            {[1, 2, 3, 4].map((n) => <span key={n} className={n <= score ? 'on' : ''} />)}
          </div>
          <span className="label-mono">
            {value.length > 0 && value.length < MIN_PASSWORD_LENGTH
              ? `${value.length}/${MIN_PASSWORD_LENGTH}`
              : STRENGTH_LABELS[score]}
          </span>
        </div>
      )}
    </>
  );
}

export function Notice({ kind = 'info', children }: { kind?: 'info' | 'error' | 'ok'; children: ReactNode }) {
  return (
    <div className={`notice notice-${kind}`} role={kind === 'error' ? 'alert' : 'status'}>
      <div>{children}</div>
    </div>
  );
}

export function SubmitButton({ pending, children }: { pending: boolean; children: ReactNode }) {
  return (
    <button type="submit" className="btn btn-accent btn-block" disabled={pending} aria-busy={pending}>
      {pending ? <span className="spinner" aria-hidden="true" /> : null}
      <span>{children}</span>
      {!pending && <span className="arrow" aria-hidden="true">→</span>}
    </button>
  );
}
