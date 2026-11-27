// Planinar: prijava na turu, odjava, ture samo za članove, profil, bedževi.
import { test as plainTest, expect } from '@playwright/test';

import { apiAs, loginOk, statePath, tourId, USERS, type Json, test } from './helpers';

test.describe('planinar2', () => {
  test.use({ storageState: statePath('hiker2') });

  test('prijava na turu i odjava do roka', async ({ page }) => {
    await page.goto('/ture');
    await page.getByText('Igman zimska šetnja').first().click();
    await page.getByRole('button', { name: /^Prijavi se/ }).click();
    await expect(page.getByText('Prijavljeni ste! Vidimo se na stazi.')).toBeVisible();

    await page.getByRole('link', { name: 'Moje prijave' }).first().click();
    const row = page.locator('li').filter({ hasText: 'Igman zimska šetnja' });
    await row.getByRole('button', { name: 'Odjavi se' }).click();
    await row.getByRole('button', { name: 'Da, odjavi' }).click();
    await expect(page.getByRole('region', { name: /Historija/ }).or(page.locator('section').filter({ has: page.getByRole('heading', { name: 'Historija' }) }))
      .getByText('Igman zimska šetnja')).toBeVisible();
  });

  test('tura samo za članove: nečlan se ne može prijaviti', async ({ page }) => {
    // planinar2 dobija članstvo u admin testu, pa se ovdje provjerava preko vodiča drugog društva (nije član)
    const api = await apiAs('guideB');
    await page.context().addCookies((await api.ctx.storageState()).cookies);
    const id = await tourId(api, 'Treskavica: Pakleni zub');
    await page.goto(`/ture/${id}`);
    await expect(page.getByRole('heading', { name: 'Treskavica: Pakleni zub' })).toBeVisible();
    await expect(page.getByRole('button', { name: /^Prijavi se/ })).toHaveCount(0);
    await expect(page.getByText('Ova tura je samo za članove društva PD Bjelašnica')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Zatraži članstvo u društvu' })).toHaveAttribute('href', /\/drustva\/\d+$/);
    const r = await api.post(`/api/tours/${id}/register/`);
    expect(r.status()).toBe(400);
    expect((await r.json() as Json).detail).toContain('samo za članove');
  });

  test('profil: izmjena telefona', async ({ page }) => {
    await page.goto('/profil');
    await page.getByLabel('Telefon', { exact: true }).fill('061 555 444');
    await page.getByRole('button', { name: 'Sačuvaj profil' }).click();
    await expect(page.getByText('Profil je sačuvan.')).toBeVisible();
    await page.reload();
    await expect(page.getByLabel('Telefon', { exact: true })).toHaveValue('061 555 444');
  });
});

test.describe('planinar1', () => {
  test.use({ storageState: statePath('hiker') });

  test('profil prikazuje osvojene bedževe i napredak', async ({ page }) => {
    await page.goto('/profil');
    const section = page.locator('#bedzevi');
    await expect(section.getByRole('heading', { name: 'Bedževi' })).toBeVisible();
    await expect(section.locator('.badge-card.is-earned').filter({ hasText: 'Prvi vrh' })).toBeVisible();
    await expect(section.locator('.badge-card.is-locked').filter({ hasText: 'Planinar 25' }).getByRole('progressbar')).toBeVisible();
    await expect(section.getByText('Vodič', { exact: true })).toHaveCount(0);   // planinar ne vidi bedževe vodiča
  });
});

plainTest('novi bedž: modal nakon prve prijave na turu, pa se više ne pojavljuje', async ({ page }) => {
  await loginOk(page, USERS.badge);
  const api = await apiAs(null);
  await page.goto(`/ture/${await tourId(api, 'Igman zimska šetnja')}`);
  await page.getByRole('button', { name: /^Prijavi se/ }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('heading', { name: 'Bedž „Prvi korak“ je tvoj!' })).toBeVisible();
  await dialog.getByRole('button', { name: 'Super!' }).click();
  await expect(dialog).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole('dialog')).toHaveCount(0);
});
