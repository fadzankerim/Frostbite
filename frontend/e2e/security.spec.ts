// Sigurnost na nivou HTTP-a i API-ja: HTTPS, zaglavlja, kolačići, CSRF, kontrola pristupa po ulozi,
// IDOR (tuđi objekti daju 404), lični podaci i statičke datoteke.
import { expect, request, test } from '@playwright/test';

import { apiAs, BASE, clubId, loginApi, tourId, USERS, type Json } from './helpers';

test('HTTP se preusmjerava na HTTPS', async () => {
  const ctx = await request.newContext({ ignoreHTTPSErrors: true });
  const r = await ctx.get(BASE.replace('https://', 'http://').replace(':8443', ':8080') + '/ture', { maxRedirects: 0 });
  expect(r.status()).toBe(301);
  expect(r.headers().location).toMatch(/^https:\/\//);
  await ctx.dispose();
});

test('sigurnosna zaglavlja na stranici i API-ju', async () => {
  const api = await apiAs(null);
  for (const path of ['/', '/ture/1', '/api/tours/']) {
    const h = (await api.get(path)).headers();
    expect(h['strict-transport-security'], path).toContain('max-age=');
    expect(h['content-security-policy'], path).toContain("default-src 'self'");
    expect(h['content-security-policy'], path).toContain("frame-ancestors 'none'");
    expect(h['x-frame-options'], path).toBe('DENY');
    expect(h['x-content-type-options'], path).toBe('nosniff');
    expect(h['referrer-policy'], path).toBe('same-origin');
    expect(h.server ?? '', path).not.toMatch(/\d/);         // bez verzije servera
  }
  const apiHeaders = (await api.get('/api/tours/')).headers();
  expect(apiHeaders['cache-control']).toMatch(/no-cache|no-store|max-age=0/);
});

test('kolačići sesije: __Host-, HttpOnly, Secure, SameSite=Lax', async () => {
  const api = await loginApi(USERS.hiker2);
  const cookies = (await api.ctx.storageState()).cookies;
  for (const name of ['__Host-sessionid', '__Host-csrftoken']) {
    const c = cookies.find((x) => x.name === name);
    expect(c, name).toBeDefined();
    expect(c!.httpOnly, name).toBe(true);
    expect(c!.secure, name).toBe(true);
    expect(c!.sameSite, name).toBe('Lax');
    expect(c!.path, name).toBe('/');
  }
  await api.post('/api/auth/logout/');
});

test('CSRF: zahtjev bez tokena ili s tuđeg origina se odbija', async () => {
  const api = await apiAs('hiker');
  expect((await api.post('/api/me/badges/seen/', {}, { csrf: false })).status()).toBe(403);
  expect((await api.post('/api/me/badges/seen/', {}, { headers: { Origin: 'https://zlo.example', Referer: 'https://zlo.example/' } })).status()).toBe(403);
  expect((await api.post('/api/me/badges/seen/')).status()).toBe(200);
  // CSRF važi i za anonimne POST zahtjeve (prijava)
  const anon = await apiAs(null);
  expect((await anon.post('/api/auth/login/', { email: USERS.hiker, password: 'x' }, { csrf: false })).status()).toBe(403);
});

test('API prima samo JSON', async () => {
  const anon = await apiAs(null);
  const r = await anon.ctx.post('/api/auth/login/', {
    form: { email: USERS.hiker, password: 'x' },
    headers: { 'X-CSRFToken': anon.csrf, Origin: BASE, Referer: `${BASE}/` },
  });
  expect(r.status()).toBe(415);
});

test('anonimni korisnik ne dobija ništa iza prijave', async () => {
  const anon = await apiAs(null);
  for (const path of ['/api/me/profile/', '/api/me/registrations/', '/api/me/badges/', '/api/guide/', '/api/manage/', '/api/system/',
    '/api/system/users/', '/api/system/audit/']) {
    expect((await anon.get(path)).status(), path).toBe(403);
  }
  const t = await tourId(anon, 'Igman zimska šetnja');
  expect((await anon.post(`/api/tours/${t}/register/`)).status()).toBe(403);
});

test('prava po ulogama: planinar, vodič i admin ne ulaze u tuđe panele', async () => {
  const hiker = await apiAs('hiker');
  for (const path of ['/api/guide/', '/api/system/', '/api/system/users/']) {
    expect((await hiker.get(path)).status(), `planinar ${path}`).toBe(403);
  }
  expect((await (await hiker.get('/api/manage/')).json() as Json).results ?? []).toEqual([]);

  const guide = await apiAs('guide');
  expect((await guide.get('/api/system/')).status()).toBe(403);

  const admin = await apiAs('admin');
  expect((await admin.get('/api/system/')).status()).toBe(403);
  expect((await admin.get('/api/system/clubs/')).status()).toBe(403);

  const sys = await apiAs('sys');
  const t = await tourId(sys, 'Igman zimska šetnja');
  expect((await sys.post(`/api/tours/${t}/register/`)).status()).toBe(403);   // sistemski admin nije planinar
});

test('IDOR: admin i vodič drugog društva dobijaju 404', async () => {
  const anon = await apiAs(null);
  const bjelasnica = await clubId(anon, 'PD Bjelašnica');
  const opservatorija = await tourId(anon, 'Bjelašnica: Opservatorija');

  const adminB = await apiAs('adminB');
  expect((await adminB.get(`/api/manage/${bjelasnica}/`)).status()).toBe(404);
  expect((await adminB.get(`/api/manage/${bjelasnica}/tours/${opservatorija}/`)).status()).toBe(404);
  expect((await adminB.get(`/api/manage/${bjelasnica}/members/`)).status()).toBe(404);
  expect((await adminB.post(`/api/manage/${bjelasnica}/tours/${opservatorija}/transition/`, { action: 'cancel' })).status()).toBe(404);

  const guideB = await apiAs('guideB');
  expect((await guideB.get(`/api/guide/tours/${opservatorija}/`)).status()).toBe(404);

  const hiker2 = await apiAs('hiker2');
  const regs = (await (await apiAs('hiker')).get('/api/me/registrations/').then((r) => r.json() as Json)) as { upcoming: { id: number }[] };
  const foreign = regs.upcoming[0]!.id;
  expect((await hiker2.post(`/api/me/registrations/${foreign}/cancel/`)).status()).toBe(404);
});

test('nacrt ture nije javan ni preko API-ja', async () => {
  const admin = await apiAs('admin');
  const bjelasnica = await clubId(admin, 'PD Bjelašnica');
  const tours = (await (await admin.get(`/api/manage/${bjelasnica}/tours/`)).json()) as Json;
  const all = [...(tours.upcoming ?? []), ...(tours.past ?? []), ...(tours.results ?? [])] as { id: number; name: string }[];
  const draft = all.find((t) => t.name === 'Nacrt: Visočica');
  expect(draft, 'nacrt u panelu admina').toBeDefined();
  const anon = await apiAs(null);
  expect((await anon.get(`/api/tours/${draft!.id}/`)).status()).toBe(404);
  expect((await anon.get(`/api/tours/${draft!.id}/gpx/`)).status()).toBe(404);
});

test('sistemski admin ne vidi zdravstvene podatke ni telefone planinara', async () => {
  const sys = await apiAs('sys');
  const body = await (await sys.get('/api/system/users/?q=planinar1')).text();
  expect(body).toContain(USERS.hiker);
  expect(body).not.toContain('Alergija');
  expect(body).not.toContain('063 333 333');
  expect(body).not.toContain('Mika Planinar');
});

test('bedževi: samo vlastiti; katalog se ne može mijenjati', async () => {
  // planinar vidi samo bedževe svojih uloga; tuđi bedževi (npr. vodiča) se ne mogu ni zatražiti
  const hiker = await apiAs('hiker');
  const mine = (await (await hiker.get('/api/me/badges/')).json() as Json).results as { role: string }[];
  expect(new Set(mine.map((b) => b.role))).toEqual(new Set(['PLANINAR']));
  expect((await hiker.get('/api/me/badges/?user=vodic1@pd-bjelasnica.ba')).status()).toBe(200);
  const again = (await (await hiker.get('/api/me/badges/?user=vodic1@pd-bjelasnica.ba')).json() as Json).results as { role: string }[];
  expect(again).toHaveLength(mine.length);                                     // parametar se ignoriše
  const hiker2 = await apiAs('hiker2');
  for (const method of ['post', 'put', 'delete'] as const) {
    const r = await hiker2.ctx[method]('/api/badges/', { headers: { 'X-CSRFToken': hiker2.csrf, Origin: BASE, Referer: `${BASE}/` } });
    expect(r.status(), method).toBe(405);
  }
});

test('nema skrivenih datoteka, source mapa ni Django admina', async () => {
  const anon = await apiAs(null);
  for (const path of ['/.env', '/.git/config', '/api/admin/', '/api/nepostojece/']) {
    expect((await anon.get(path)).status(), path).toBe(404);
  }
  const html = await (await anon.get('/')).text();
  const js = html.match(/\/assets\/[^"]+\.js/)?.[0];
  expect(js).toBeTruthy();
  expect((await anon.get(`${js}.map`)).status()).toBe(404);
  expect(await (await anon.get(js!)).text()).not.toContain('sourceMappingURL');
});
