// Prijava, registracija, odjava, zaključavanje naloga, promjena lozinke, preusmjeravanje.
import { expect, request } from '@playwright/test';

import { apiAs, BASE, GENERIC_LOGIN_ERROR, loginApi, loginOk, loginUi, PASSWORD, USERS, test } from './helpers';

test('ista poruka za pogrešnu lozinku i nepostojeći nalog', async ({ page }) => {
  await loginUi(page, USERS.hiker2, 'Pogresna-Lozinka-1');
  await expect(page.getByText(GENERIC_LOGIN_ERROR)).toBeVisible();
  await expect(page.getByLabel('Lozinka', { exact: true })).toHaveValue('');   // lozinka se ne vraća u polje
  await loginUi(page, 'ne-postoji@primjer.ba', 'Pogresna-Lozinka-1');
  await expect(page.getByText(GENERIC_LOGIN_ERROR)).toBeVisible();
});

test('nalog se zaključava nakon 5 pogrešnih lozinki (i ispravna lozinka tada ne prolazi)', async ({ page }) => {
  const api = await apiAs(null);
  for (let i = 0; i < 5; i++) {
    const r = await api.post('/api/auth/login/', { email: USERS.lockout, password: 'Pogresna-Lozinka-1' });
    expect(r.status()).toBe(400);
  }
  await loginUi(page, USERS.lockout, PASSWORD);
  await expect(page.getByText(GENERIC_LOGIN_ERROR)).toBeVisible();
  await expect(page).toHaveURL(/\/prijava/);
});

test('registracija: novi nalog, a postojeći email daje isti odgovor', async ({ page }) => {
  const email = `novi-${Date.now()}@primjer.ba`;
  for (const e of [email, USERS.hiker]) {
    await page.goto('/registracija');
    await page.getByLabel('Ime', { exact: true }).fill('Novi');
    await page.getByLabel('Prezime').fill('Planinar');
    await page.getByLabel('Email').fill(e);
    await page.getByLabel('Lozinka', { exact: true }).fill('Snijeg-Na-Vrhu-2026');
    await page.getByLabel('Ponovite lozinku').fill('Snijeg-Na-Vrhu-2026');
    await page.getByRole('button', { name: 'Kreiraj nalog' }).click();
    await expect(page).toHaveURL('/prijava');
    await expect(page.getByText('Registracija je završena.')).toBeVisible();
  }
  await loginOk(page, email, 'Snijeg-Na-Vrhu-2026');
  await expect(page).toHaveURL('/');
  await expect(page.getByRole('button', { name: /Novi Planinar/ })).toBeVisible();
});

test('prijava vodi na ?next=, ali nikad na drugi domen', async ({ browser }) => {
  const a = await browser.newPage();
  await loginOk(a, USERS.session, PASSWORD, '/moje-prijave');
  await expect(a).toHaveURL('/moje-prijave');
  const b = await browser.newPage();
  for (const evil of ['https://zlo.example/krađa', '//zlo.example', '/\\zlo.example']) {
    await b.context().clearCookies();
    await loginOk(b, USERS.session, PASSWORD, evil);
    expect(new URL(b.url()).origin).toBe(BASE);
    await expect(b).toHaveURL('/');
  }
  await a.close();
  await b.close();
});

test('odjava briše sesiju na serveru (stari kolačić više ne vrijedi)', async ({ page }) => {
  await loginOk(page, USERS.session);
  const stolen = await page.context().storageState();
  await page.getByRole('button', { name: /Sesija E2E/ }).click();
  await page.getByRole('button', { name: 'Odjava' }).click();
  await expect(page.getByRole('link', { name: 'Prijava' })).toBeVisible();
  await page.goto('/profil');
  await expect(page).toHaveURL(/\/prijava\?next=/);

  const ctx = await request.newContext({ baseURL: BASE, ignoreHTTPSErrors: true, storageState: stolen });
  expect((await ctx.get('/api/me/profile/')).status()).toBe(403);
  await ctx.dispose();
});

test('promjena lozinke odjavljuje ostale sesije', async ({ page }) => {
  const other = await loginApi(USERS.password);
  expect((await other.get('/api/me/profile/')).status()).toBe(200);

  await loginOk(page, USERS.password);
  await page.goto('/profil');
  await page.getByLabel('Trenutna lozinka').fill(PASSWORD);
  await page.getByLabel('Nova lozinka', { exact: true }).fill('Nova-Planinska-Lozinka-9');
  await page.getByLabel('Ponovite novu lozinku').fill('Nova-Planinska-Lozinka-9');
  await page.getByRole('button', { name: 'Promijeni lozinku' }).click();
  await expect(page.getByText('Lozinka je promijenjena.')).toBeVisible();

  expect((await other.get('/api/me/profile/')).status()).toBe(403);        // druga sesija je ugašena
  expect((await page.request.get('/api/me/profile/')).status()).toBe(200);  // tekuća ostaje
  const old = await apiAs(null);
  expect((await old.post('/api/auth/login/', { email: USERS.password, password: PASSWORD })).status()).toBe(400);
});
