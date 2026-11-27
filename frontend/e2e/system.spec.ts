// Sistemski admin: odobravanje društva, blokiranje naloga, evidencija; nema funkcija planinara.
import { expect } from '@playwright/test';

import { apiAs, GENERIC_LOGIN_ERROR, PASSWORD, statePath, USERS, type Json, test } from './helpers';

test.use({ storageState: statePath('sys') });

test('odobreno društvo postaje javno', async ({ page }) => {
  await page.goto('/sistem/drustva');
  const row = page.locator('li').filter({ hasText: 'PD Na čekanju' });
  await row.getByRole('button', { name: 'Odobri' }).click();
  await row.getByRole('button', { name: 'Da' }).click();
  await expect(page.getByText(/PD Na čekanju“: odobreno/)).toBeVisible();
  const anon = await apiAs(null);
  const clubs = (await (await anon.get('/api/clubs/')).json() as Json).results as { name: string }[];
  expect(clubs.map((c) => c.name)).toContain('PD Na čekanju');
});

test('blokiran nalog se ne može prijaviti (ista generička poruka)', async ({ page }) => {
  await page.goto('/sistem/korisnici');
  await page.getByLabel('Pretraga korisnika').fill(USERS.blocked);
  await page.getByRole('button', { name: 'Traži' }).click();
  const row = page.locator('li').filter({ hasText: USERS.blocked });
  await row.getByRole('button', { name: 'Blokiraj' }).click();
  await row.getByRole('button', { name: 'Da, blokiraj' }).click();
  await expect(row.getByText('Blokiran')).toBeVisible();

  const anon = await apiAs(null);
  const r = await anon.post('/api/auth/login/', { email: USERS.blocked, password: PASSWORD });
  expect(r.status()).toBe(400);
  expect((await r.json() as Json).detail).toBe(GENERIC_LOGIN_ERROR);
});

test('evidencija aktivnosti bilježi blokiranje', async ({ page }) => {
  await page.goto('/sistem/evidencija');
  await expect(page.getByRole('cell', { name: 'nalog blokiran', exact: true }).first()).toBeVisible();
  // i pokušaj prijave blokiranog naloga je zabilježen
  const blockedLogin = page.getByRole('row').filter({ hasText: 'login blokiran' }).filter({ hasText: USERS.blocked });
  await expect(blockedLogin.first()).toBeVisible();
});

test('sistemski admin nema funkcije planinara', async ({ page }) => {
  await page.goto('/moje-prijave');
  await expect(page).toHaveURL('/zabranjeno');
});
