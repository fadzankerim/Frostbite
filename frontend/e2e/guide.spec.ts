// Vodič: pregled tura, lični podaci učesnika, prisustvo i izvještaj; nema pristupa tuđim panelima.
import { expect } from '@playwright/test';

import { statePath, test } from './helpers';

test.use({ storageState: statePath('guide') });

test('prisustvo i izvještaj za jučerašnju turu', async ({ page }) => {
  await page.goto('/vodic');
  await expect(page.getByRole('heading', { name: 'Vođenje tura' })).toBeVisible();
  await page.locator('li').filter({ hasText: 'Trebević: jutarnja tura' }).getByRole('link', { name: /Učesnici/ }).click();
  await expect(page.getByText('Alergija na ubode pčela.')).toBeVisible();     // lični podaci samo vodiču

  await page.getByLabel('Prisutan: Dževad Planinar').check();
  await page.getByRole('button', { name: 'Sačuvaj prisustvo' }).click();
  await expect(page.getByText('Prisustvo je sačuvano.')).toBeVisible();

  await page.getByLabel('Kako je prošlo?').fill('Lijepo vrijeme, svi su stigli na vrh.');
  await page.getByRole('button', { name: 'Pošalji izvještaj' }).click();
  await expect(page.getByText(/Izvještaj je sačuvan/)).toBeVisible();
});

for (const path of ['/sistem', '/upravljanje']) {
  test(`vodič nema pristup: ${path}`, async ({ page }) => {
    await page.goto(path);
    await expect(page).toHaveURL('/zabranjeno');
    await expect(page.getByRole('heading', { name: 'Pristup nije dozvoljen.' })).toBeVisible();
  });
}
