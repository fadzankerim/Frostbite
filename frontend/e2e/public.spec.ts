// Javnost (bez prijave): šta se vidi, a šta ne, i da zaštićene stranice traže prijavu.
import { expect } from '@playwright/test';

import { apiAs, type Json, test } from './helpers';

test('početna: vodič u koracima radi mišem i tastaturom', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Četiri koraka za svaku ulogu' })).toBeVisible();
  const tabs = page.getByRole('tablist', { name: 'Uloga' });
  await tabs.getByRole('tab', { name: 'Vodič' }).click();
  await expect(tabs.getByRole('tab', { name: 'Vodič' })).toHaveAttribute('aria-selected', 'true');
  await page.keyboard.press('ArrowRight');
  await expect(tabs.getByRole('tab', { name: 'Društvo' })).toHaveAttribute('aria-selected', 'true');
  await expect(tabs.getByRole('tab', { name: 'Društvo' })).toBeFocused();
  for (let i = 0; i < 3; i++) await page.getByRole('button', { name: /Dalje/ }).click();
  await expect(page.getByRole('link', { name: /Registruj društvo/ })).toBeVisible();
});

test('početna: galerija bedževa i često postavljana pitanja', async ({ page }) => {
  const api = await apiAs(null);
  const catalog = (await (await api.get('/api/badges/')).json() as Json).results as unknown[];
  await page.goto('/');
  await expect(page.locator('.badge-gallery li')).toHaveCount(catalog.length);
  const q = page.locator('details').filter({ hasText: 'Ko vidi moje zdravstvene napomene' });
  await q.locator('summary').click();
  await expect(q).toHaveAttribute('open', '');
});

test('ture: objavljene su javne, nacrt nije', async ({ page }) => {
  await page.goto('/ture');
  await expect(page.getByText('Bjelašnica: Opservatorija').first()).toBeVisible();
  await expect(page.getByText('Nacrt: Visočica')).toHaveCount(0);
});

test('društva: društvo na čekanju nije javno', async ({ page }) => {
  await page.goto('/drustva');
  await expect(page.getByText('PD Bjelašnica').first()).toBeVisible();
  await expect(page.getByText('PD Na čekanju')).toHaveCount(0);
});

for (const path of ['/profil', '/moje-prijave', '/moja-clanstva', '/vodic', '/upravljanje', '/sistem', '/drustva/novo']) {
  test(`zaštićena stranica traži prijavu: ${path}`, async ({ page }) => {
    await page.goto(path);
    await expect(page).toHaveURL(`/prijava?next=${encodeURIComponent(path)}`);
  });
}

test('nepostojeća stranica daje 404 prikaz', async ({ page }) => {
  await page.goto('/ova-stranica-ne-postoji');
  await expect(page.getByRole('heading', { name: 'Ova staza ne postoji.' })).toBeVisible();
});

test('prijava na turu bez naloga vodi na prijavu i nazad na turu', async ({ page }) => {
  await page.goto('/ture');
  await page.getByText('Igman zimska šetnja').first().click();
  await page.getByRole('link', { name: /Prijavi se/ }).click();
  await expect(page).toHaveURL(/\/prijava\?next=%2Fture%2F\d+$/);
});
