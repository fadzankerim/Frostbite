// Admin društva: nova tura (nacrt -> objava), odobravanje članstva i vodiča; tuđe društvo nije dostupno.
import { expect } from '@playwright/test';

import { apiAs, clubId, statePath, type Json, test } from './helpers';

test.use({ storageState: statePath('admin') });

function local(daysFromNow: number): string {
  const d = new Date(Date.now() + daysFromNow * 86_400_000);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T08:00`;
}

test('nova tura: nacrt nije javan dok se ne objavi', async ({ page }) => {
  const name = `E2E tura ${Date.now()}`;
  await page.goto('/upravljanje');
  await page.getByRole('navigation', { name: 'Panel društva' }).getByRole('link', { name: 'Ture', exact: true }).click();
  await page.getByRole('link', { name: /Nova tura/ }).click();
  await page.getByLabel('Naziv ture').fill(name);
  await page.getByLabel('Regija').fill('Igman');
  await page.getByLabel('Polazak').fill(local(10));
  await page.getByLabel('Rok prijave').fill(local(9));
  await page.getByLabel('Mjesto okupljanja').fill('Parking Malo polje');
  await page.getByLabel('Dužina (km)').fill('9');
  await page.getByLabel('Uspon (m)').fill('400');
  await page.getByLabel('Trajanje (h)').fill('4');
  await page.getByLabel('Maks. učesnika').fill('12');
  await page.getByRole('button', { name: /Sačuvaj|Kreiraj/ }).click();
  await expect(page.getByText('Tura je sačuvana kao nacrt.', { exact: false })).toBeVisible();

  const anon = await apiAs(null);
  const before = (await (await anon.get('/api/tours/')).json() as Json).results as { name: string }[];
  expect(before.map((t) => t.name)).not.toContain(name);

  await page.getByRole('button', { name: 'Objavi turu' }).click();
  await page.getByRole('button', { name: 'Da' }).click();
  await expect(page.getByText('Tura je objavljena.')).toBeVisible();
  const after = (await (await anon.get('/api/tours/')).json() as Json).results as { name: string }[];
  expect(after.map((t) => t.name)).toContain(name);
});

test('odobravanje zahtjeva za članstvo', async ({ page }) => {
  await page.goto('/upravljanje');
  await page.getByRole('navigation', { name: 'Panel društva' }).getByRole('link', { name: 'Članovi', exact: true }).click();
  const row = page.locator('li').filter({ hasText: 'Kerim Planinar' });
  await row.getByRole('button', { name: 'Odobri' }).click();
  await expect(page.getByText('Odluka je sačuvana.')).toBeVisible();
  await expect(page.getByRole('heading', { name: /Zahtjevi/ })).toContainText('(0)');
});

test('odobravanje prijave vodiča za turu', async ({ page }) => {
  await page.goto('/upravljanje');
  await page.getByRole('navigation', { name: 'Panel društva' }).getByRole('link', { name: 'Ture', exact: true }).click();
  await page.getByText('Igman zimska šetnja').first().click();
  await page.locator('li').filter({ hasText: 'Vedad Vodič' }).getByRole('button', { name: 'Odobri' }).click();
  await expect(page.getByText('Odluka je sačuvana.')).toBeVisible();
});

test('panel tuđeg društva nije dostupan', async ({ page }) => {
  const prenj = await clubId(await apiAs(null), 'PD Prenj');
  await page.goto(`/upravljanje/${prenj}`);
  await expect(page.getByRole('heading', { name: /Ova staza ne postoji|Pristup nije dozvoljen/ })).toBeVisible();
  await expect(page.getByText('Zelena glava')).toHaveCount(0);
});
