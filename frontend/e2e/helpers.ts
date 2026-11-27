// Zajedničko za E2E testove: nalozi, prijava preko API-ja, pozivi API-ja s CSRF tokenom.
import { test as base, expect, request, type APIRequestContext, type Page } from '@playwright/test';

/** Odgovor API-ja u testovima (oblik provjeravaju sami testovi). */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Json = any;

export const BASE = process.env.E2E_BASE_URL ?? 'https://localhost:8443';
export const PASSWORD = 'Demo-Lozinka-2026';
export const GENERIC_LOGIN_ERROR = 'Pogrešan email ili lozinka, ili je nalog privremeno zaključan.';

/** Demo nalozi iz seed_e2e (app/accounts/demo.py). */
export const USERS = {
  hiker: 'planinar1@primjer.ba',        // član PD Bjelašnica, ima zdravstvenu napomenu
  hiker2: 'planinar2@primjer.ba',       // nije član; podnio zahtjev za "PD Na čekanju"
  guide: 'vodic1@pd-bjelasnica.ba',
  guideB: 'vodic@pd-prenj.ba',
  admin: 'admin@pd-bjelasnica.ba',
  adminB: 'admin@pd-prenj.ba',
  sys: 'sysadmin@frostbite.ba',
  // nalozi za testove koji mijenjaju stanje naloga
  lockout: 'e2e-zakljucavanje@primjer.ba',
  session: 'e2e-sesija@primjer.ba',
  password: 'e2e-lozinka@primjer.ba',
  blocked: 'e2e-blokada@primjer.ba',
  badge: 'e2e-bedz@primjer.ba',
} as const;
export type Role = keyof typeof USERS;

export const statePath = (role: Role) => `e2e/.auth/${role}.json`;

/**
 * Test sa zatvaranjem modala "novi bedž". Radnje u testovima (odobrenje članstva, odluka o društvu...)
 * dodjeljuju bedževe, a modal tada prekrije stranicu. To je ispravno ponašanje aplikacije, pa ga
 * testovi samo zatvore. Sam modal provjerava poseban test (hiker.spec.ts) s običnim `test`-om.
 */
export const test = base.extend({
  page: async ({ page }, use) => {
    const dialog = page.getByRole('dialog').filter({ has: page.getByRole('button', { name: 'Super!' }) });
    await page.addLocatorHandler(dialog, async (d) => { await d.getByRole('button', { name: 'Super!' }).click(); });
    await use(page);
  },
});

/** Isti origin kao pregledač: Django provjerava Origin i Referer za HTTPS zahtjeve. */
const ORIGIN_HEADERS = { Origin: BASE, Referer: `${BASE}/` };

export type Api = {
  ctx: APIRequestContext;
  csrf: string;
  get: (path: string) => ReturnType<APIRequestContext['get']>;
  post: (path: string, data?: unknown, opts?: { csrf?: boolean; headers?: Record<string, string> }) => ReturnType<APIRequestContext['post']>;
};

async function wrap(ctx: APIRequestContext): Promise<Api> {
  const r = await ctx.get('/api/auth/csrf/');
  expect(r.ok()).toBeTruthy();
  const api: Api = {
    ctx,
    csrf: (await r.json() as Json).csrfToken as string,
    get: (path) => ctx.get(path),
    post: (path, data = {}, opts = {}) => ctx.post(path, {
      data,
      headers: { ...ORIGIN_HEADERS, ...(opts.csrf === false ? {} : { 'X-CSRFToken': api.csrf }), ...opts.headers },
    }),
  };
  return api;
}

/** API kontekst: anoniman, sa sačuvanom sesijom uloge ili prazan. */
export async function apiAs(role: Role | null): Promise<Api> {
  const ctx = await request.newContext({
    baseURL: BASE, ignoreHTTPSErrors: true, ...(role ? { storageState: statePath(role) } : {}),
  });
  return wrap(ctx);
}

/** Nova prijava preko API-ja (nova sesija). Vraća kontekst s prijavljenim korisnikom. */
export async function loginApi(email: string, password = PASSWORD): Promise<Api> {
  const api = await apiAs(null);
  const r = await api.post('/api/auth/login/', { email, password });
  expect(r.status(), `prijava ${email}`).toBe(200);
  api.csrf = (await r.json() as Json).csrfToken as string;      // Django mijenja token pri prijavi
  return api;
}

/** Prijava kroz formu (kao korisnik). */
export async function loginUi(page: Page, email: string, password = PASSWORD, next?: string) {
  await page.goto(next ? `/prijava?next=${encodeURIComponent(next)}` : '/prijava');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Lozinka', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Prijavi se' }).click();
}

/** Prijava kroz formu koja mora uspjeti: čeka da forma nestane (korisnik je preusmjeren). */
export async function loginOk(page: Page, email: string, password = PASSWORD, next?: string) {
  await loginUi(page, email, password, next);
  await expect(page).not.toHaveURL(/\/prijava/);
}

/** ID-jevi iz javnog API-ja (ture i društva po nazivu), da testovi ne zavise od redoslijeda u bazi. */
export async function tourId(api: Api, name: string): Promise<number> {
  const list = (await (await api.get('/api/tours/')).json() as Json).results as { id: number; name: string }[];
  const t = list.find((x) => x.name === name);
  if (!t) throw new Error(`Tura nije pronađena: ${name}`);
  return t.id;
}

export async function clubId(api: Api, name: string): Promise<number> {
  const list = (await (await api.get('/api/clubs/')).json() as Json).results as { id: number; name: string }[];
  const c = list.find((x) => x.name === name);
  if (!c) throw new Error(`Društvo nije pronađeno: ${name}`);
  return c.id;
}
