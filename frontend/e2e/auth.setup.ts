// Jednom po pokretanju: prijava za svaku ulogu i čuvanje sesije (e2e/.auth/*.json).
// Testovi zatim ne prolaze kroz prijavu svaki put (Nginx ograničava broj prijava u minuti).
// Postojeći bedževi se označe kao viđeni, da modal "novi bedž" ne prekriva stranice u testovima.
import { test as setup } from '@playwright/test';

import { loginApi, statePath, USERS, type Role } from './helpers';

const ROLES: Role[] = ['hiker', 'hiker2', 'guide', 'guideB', 'admin', 'adminB', 'sys'];

for (const role of ROLES) {
  setup(`prijava: ${role}`, async () => {
    const api = await loginApi(USERS[role]);
    await api.post('/api/me/badges/seen/');
    await api.ctx.storageState({ path: statePath(role) });
    await api.ctx.dispose();
  });
}
