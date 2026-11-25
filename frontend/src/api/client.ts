// Jedini klijent za JSON API. Svi pozivi prema serveru idu kroz api().
//
// - samo putanje /api/... (isti origin; nikad drugi domen)
// - sesija je HttpOnly kolačić koji šalje pregledač; ovdje se ne vidi i ne čuva
// - CSRF token se drži SAMO u memoriji i šalje u X-CSRFToken za zahtjeve koji mijenjaju stanje
// - nakon prijave server mijenja CSRF token; novi se postavlja preko setCsrfToken()
import { markActivity } from '../lib/session';

type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export class ApiError extends Error {
  readonly status: number;
  readonly data: unknown;

  constructor(status: number, data: unknown, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }

  /** Poruka za korisnika: ono što je server vratio ("detail"), inače generička. */
  get detail(): string {
    const d = this.data as { detail?: unknown } | null;
    return typeof d?.detail === 'string' ? d.detail : this.message;
  }

  /** Greške po poljima forme: {"email": ["..."]}. */
  get fieldErrors(): Record<string, string[]> {
    const d = this.data as { errors?: unknown } | null;
    if (!d || typeof d.errors !== 'object' || d.errors === null) return {};
    const out: Record<string, string[]> = {};
    for (const [k, v] of Object.entries(d.errors as Record<string, unknown>)) {
      if (Array.isArray(v)) out[k] = v.filter((x): x is string => typeof x === 'string');
    }
    return out;
  }
}

const GENERIC_ERROR = 'Došlo je do greške. Pokušajte ponovo.';
const NETWORK_ERROR = 'Server nije dostupan. Provjerite vezu i pokušajte ponovo.';

let csrfToken: string | null = null;

export function setCsrfToken(token: string | null): void {
  csrfToken = token;
}

async function ensureCsrfToken(): Promise<string> {
  if (csrfToken) return csrfToken;
  const data = await request<{ csrfToken: string }>('GET', '/api/auth/csrf/');
  csrfToken = data.csrfToken;
  return csrfToken;
}

async function request<T>(method: Method, path: string, body?: unknown, retried = false): Promise<T> {
  if (!path.startsWith('/api/') || path.includes('..') || path.includes('//')) {
    throw new Error(`Nedozvoljena API putanja: ${path}`);
  }
  const unsafe = method !== 'GET';
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (unsafe) headers['X-CSRFToken'] = await ensureCsrfToken();

  let res: Response;
  try {
    res = await fetch(path, {
      method,
      headers,
      body: body === undefined ? null : JSON.stringify(body),
      credentials: 'same-origin',
      cache: 'no-store',
      redirect: 'error',          // API nikad ne preusmjerava; preusmjerenje = nešto nije u redu
      referrerPolicy: 'same-origin',
    });
  } catch {
    throw new ApiError(0, null, NETWORK_ERROR);
  }
  markActivity();

  const isJson = res.headers.get('Content-Type')?.includes('application/json') ?? false;
  const data: unknown = res.status === 204 || !isJson ? null : await res.json().catch(() => null);

  if (!res.ok) {
    const err = new ApiError(res.status, data, res.status === 429 ? 'Previše pokušaja. Sačekajte malo.' : GENERIC_ERROR);
    // Istekao ili zamijenjen CSRF token: uzmi novi i pokušaj jednom ponovo.
    if (unsafe && res.status === 403 && !retried && err.detail.startsWith('CSRF')) {
      csrfToken = null;
      return request<T>(method, path, body, true);
    }
    throw err;
  }
  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body ?? {}),
  put: <T>(path: string, body: unknown) => request<T>('PUT', path, body),
  patch: <T>(path: string, body: unknown) => request<T>('PATCH', path, body),
  delete: <T>(path: string) => request<T>('DELETE', path),
};
