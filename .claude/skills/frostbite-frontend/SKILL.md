---
name: frostbite-frontend
description: Pravila dizajna i sigurnosti za React frontend Frostbite aplikacije (frontend/). Učitati PRIJE pisanja ili mijenjanja bilo koje React stranice, komponente, stila ili animacije u frontend/ - moderan minimalistički dizajn bez gradijenata, Geist font, animacije na temu planinarenja, futuristički detalji i maksimalna sigurnost.
---

# Frostbite frontend - dizajn i sigurnost

Frontend je React + TypeScript (Vite) u `frontend/`. Backend je Django API pod `/api/`
(vidi README, sekcija JSON API). Ova pravila su obavezna; `npm run check` provjerava dio njih.

## Dizajn

**Pravac:** moderan, minimalistički, s malo futurističkih detalja. Puno praznog prostora,
jasna tipografija, malo boja, a detalji podsjećaju na instrumente (altimetar, GPS, topografska karta).

1. **Bez gradijenata, nigdje.** Ni `linear-`, `radial-` ni `conic-gradient`, ni u CSS-u ni u SVG-u
   (`<linearGradient>`), ni "glow" efekti koji ih imitiraju. Samo pune boje. `npm run check` pada ako nađe "gradient".
2. **Font:** Geist (tekst) i Geist Mono (brojevi, koordinate, visine, oznake). Fontovi su lokalni
   (`@fontsource-variable/*`), nikad sa CDN-a (CSP `default-src 'self'` i privatnost).
3. **Boje:** isključivo kroz tokene u `src/styles/tokens.css` (`--ink`, `--paper`, `--line`, `--accent`...).
   Jedan akcent (`--accent`, ledeno plava). Svijetla i tamna tema preko `prefers-color-scheme`.
   Nikad hardkodirane boje u komponentama.
4. **Oblik:** tanke linije (1px `--line`), mali radijusi (`--radius` 6-10px), bez teških sjena.
   Hijerarhija tipografijom i razmakom, ne bojom.
5. **Animacije na temu aplikacije:** topografske izohipse koje se iscrtavaju (`ContourField`),
   brojač visine (`AltitudeTicker`), "altimetar" koji prati kursor, linije profila rute, puls statusa.
   - Trajanje 150-400ms za UI, sporije (do ~2s) samo za ukrasne crteže.
   - Animirati `transform` i `opacity` (i `stroke-dashoffset` za SVG), ne `width`/`top`.
   - **Obavezno poštovati `prefers-reduced-motion`**: ukrasne animacije se gase, sadržaj ostaje.
6. **Futuristički detalji (umjereno):** mono oznake u VELIKIM slovima s razmakom (`.label-mono`),
   koordinate i visine (npr. `43.7155° N · 18.2565° E · 2067 m`), statusne tačke, tanka mreža,
   indikator sesije. Najviše 1-2 takva detalja po ekranu.
7. **Interaktivnost:** hover i focus stanja na svemu što je klikabilno; vidljiv `:focus-visible`
   prsten (pristupačnost nije opcionalna); stanja učitavanja i greške za svaki zahtjev.
8. **Responzivno:** radi od 360px širine; mobilno prvo.
9. **Jezik:** sav tekst na bosanskom (ijekavica), kao postojeće Django stranice.

## Sigurnost

1. **Autentikacija samo preko sesije** (HttpOnly kolačić). Nikad JWT, nikad token, lozinka ili
   lični podaci u `localStorage`/`sessionStorage`/IndexedDB. CSRF token živi samo u memoriji
   (`src/api/client.ts`) i obnavlja se nakon prijave (server ga mijenja).
2. **Svi pozivi API-ja idu kroz `api()` iz `src/api/client.ts`**: samo putanje `/api/...`,
   `credentials: 'same-origin'`, `X-CSRFToken` za POST/PUT/PATCH/DELETE, bez keširanja.
   Nikad `fetch` direktno, nikad apsolutni URL na drugi domen.
3. **Bez `dangerouslySetInnerHTML`, `innerHTML`, `eval`, `new Function`, `javascript:` linkova.**
   ESLint ih zabranjuje. Korisnički sadržaj se prikazuje samo kao tekst (React ga escapuje).
4. **Preusmjeravanje nakon prijave** samo kroz `safeNext()` (samo relativne putanje, bez `//`, `\` i shema).
5. **CSP mora ostati strog** (`default-src 'self'`): bez inline `<script>`, bez vanjskih skripti, fontova i CDN-a.
   Nova vanjska domena (npr. podloge mape) traži izmjenu CSP-a u `docker/nginx/default.conf`
   i `infra/app/04-deploy-app.sh`, i to samo za `img-src`.
6. **Prava provjerava server.** Uloge iz `/api/auth/me/` služe samo za prikaz menija i rute;
   `RequireAuth`/`RequireRole` su UX, ne zaštita. Svaki API endpoint provjerava prava ponovo.
7. **Greške:** prikazivati poruke koje vrati server (generičke su namjerno). Ne otkrivati da li
   nalog postoji, ne logovati lozinke ni lične podatke u konzolu.
8. **Forme:** ispravni `autocomplete` atributi (`email`, `current-password`, `new-password`),
   `maxLength` kao na serveru, lozinka se nikad ne vraća u polje nakon greške.
9. **Ovisnosti:** tačne verzije (`save-exact`), `package-lock.json` u gitu, `ignore-scripts=true`,
   nove verzije tek kad su starije od 14 dana (`npm install --before=<datum>`), `npm audit` prije commita.
   Dodati paket samo kad je zaista potreban.
10. **Produkcijski build** bez source mapa; sesija ističe nakon 30 min neaktivnosti i frontend
    to prikazuje (`SessionIndicator`) i odjavljuje korisnika.

## Provjera prije završetka

```bash
cd frontend && npm run check && npm test && npm run build
```
