// Obavještenja: postavke na profilu (samo kategorije vlastitih uloga, sigurnosna se ne može isključiti)
// i stranica za odjavu iz emaila (neispravan token, odjava tek na klik).
import { expect } from '@playwright/test';

import { apiAs, statePath, test, type Json } from './helpers';

test.describe('planinar', () => {
  test.use({ storageState: statePath('hiker2') });

  test('postavke obavještenja: promjena se čuva, sigurnosna je zaključana', async ({ page }) => {
    // admin test je planinaru2 odobrio članstvo (novi bedž): modal bi se otvorio usred klika
    await (await apiAs('hiker2')).post('/api/me/badges/seen/');
    await page.goto('/profil#obavjestenja');
    const section = page.locator('#obavjestenja');
    await expect(section.getByRole('heading', { name: 'Obavještenja na email' })).toBeVisible();
    await expect(section.getByText('Uvijek uključeno')).toBeVisible();
    await expect(section.getByText('Upravljanje društvom')).toHaveCount(0);       // nije admin
    const row = section.locator('li').filter({ hasText: 'Nove ture mojih društava' });
    await row.getByRole('radio', { name: 'Pregled' }).check();
    await page.reload();
    await expect(page.locator('#obavjestenja li').filter({ hasText: 'Nove ture mojih društava' })
      .getByRole('radio', { name: 'Pregled' })).toBeChecked();

    const api = await apiAs('hiker2');
    const r = await api.ctx.put('/api/me/notifications/', {
      data: { sigurnost: 'iskljuceno' },
      headers: { 'X-CSRFToken': api.csrf, Origin: new URL(page.url()).origin, Referer: page.url() },
    });
    expect(r.status()).toBe(400);
    const cats = (await (await api.get('/api/me/notifications/')).json() as Json).results as { code: string; mode: string }[];
    expect(cats.find((c) => c.code === 'sigurnost')?.mode).toBe('odmah');
  });
});

test('odjava iz emaila: neispravan link ne radi ništa', async ({ page }) => {
  await page.goto('/obavjestenja/odjava?t=lazni-token');
  await page.getByRole('button', { name: 'Odjavi me' }).click();
  await expect(page.getByText('Link za odjavu nije ispravan ili je istekao.')).toBeVisible();
  await page.goto('/obavjestenja/odjava');
  await expect(page.getByText('Link za odjavu nije potpun.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Odjavi me' })).toHaveCount(0);
});
