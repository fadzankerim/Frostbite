// E2E testovi u pregledaču. Pokreću se nad Docker stackom s produkcijskim postavkama:
//   ./docker/e2e.sh        (iz korijena repozitorija; podigne stack, ubaci podatke, pokrene testove)
// Testovi mijenjaju podatke (prijave, odobrenja, blokade), pa rade redom, s jednim radnikom,
// nad svježom bazom koju skripta pravi svaki put.
import { defineConfig, devices } from '@playwright/test';

const BASE = process.env.E2E_BASE_URL ?? 'https://localhost:8443';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: true,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'e2e-report' }]],
  outputDir: 'e2e-results',
  use: {
    baseURL: BASE,
    ignoreHTTPSErrors: true,          // samopotpisani certifikat E2E stacka
    locale: 'bs-BA',
    timezoneId: 'Europe/Sarajevo',
    actionTimeout: 10_000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'setup', testMatch: /auth\.setup\.ts/ },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
      testIgnore: /auth\.setup\.ts/,
    },
  ],
});
