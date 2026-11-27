# Frostbite

Web aplikacija za planinarska društva, ture i vodiče. 

Planinarska društva objavljuju ture, upravljaju vodičima i članovima. Planinari pronalaze ture na mapi, prijavljuju se na jednu ili više njih i učlanjuju se u društva. Vodiči vode ture i imaju uvid u podatke o učesnicima, a sistemski admin odobrava društva i prati sigurnost platforme.


---

## Sadržaj

- [Funkcionalnosti](#funkcionalnosti)
- [Tehnologije](#tehnologije)
- [Struktura projekta](#struktura-projekta)
- [Lokalno pokretanje](#lokalno-pokretanje)
- [Pokretanje u Dockeru](#pokretanje-u-dockeru)
- [JSON API](#json-api)
- [Frontend (React)](#frontend-react)
- [Demo nalozi](#demo-nalozi)
- [Testovi](#testovi)
- [Postavljanje na AWS](#postavljanje-na-aws)
- [Sigurnost](#sigurnost)
- [Česti problemi](#česti-problemi)

---

## Funkcionalnosti

| Uloga | Šta može |
|---|---|
| **Javnost** (bez prijave) | Pregled tura u narednih 30 dana na mapi i u listi, pretraga i filteri, detalji ture sa rutom, GPS koordinatama i GPX izvozom, pregled društava, registracija |
| **Planinar** | Prijava na jednu ili više tura (lista čekanja kad je tura puna), odjava do roka, zahtjev za članstvo, zahtjev za registraciju društva, profil sa hitnim kontaktom i zdravstvenim napomenama |
| **Vodič** | Prijava za vođenje tura svog društva, lista učesnika sa ličnim podacima (samo za ture koje vodi, do 7 dana nakon ture), zatvaranje prijava, evidencija prisustva, izvještaj sa ture |
| **Admin društva** | Analitika društva, ture (crtanje rute klikom na mapu ili uvoz GPX), objava i otkazivanje, vodiči (odobravanje i direktna dodjela), članstva, profil društva |
| **Sistemski admin** | Analitika platforme i sigurnosni pokazatelji, odobravanje i suspenzija društava, blokiranje naloga, evidencija aktivnosti |

Detaljna prava svake uloge (funkcionalnosti F01 do F31) definisana su u sigurnosnoj politici, u dokumentu *Definicija aplikacije, sigurnosna politika i plan izvedbe*.

## Tehnologije

| Sloj | Tehnologija |
|---|---|
| Backend | Python 3.12+ (server: 3.14), Django 6.1 + Django REST Framework (samo JSON API), Gunicorn |
| Baza | PostgreSQL 18 (produkcija), SQLite (lokalni razvoj) |
| Web server | Nginx (TLS 1.2/1.3, sigurnosna zaglavlja, CSP) |
| Frontend | React 19, TypeScript, Vite, React Router, TanStack Query; vlastiti CSS (tokeni, svijetla i tamna tema), fontovi Geist |
| Mape | Leaflet 1.9.4 (npm paket, dio builda), podloge Esri World Topo, OpenTopoMap, OpenStreetMap |
| Grafika | crtani SVG elementi iz koda: maskota Frosti, generisane ilustracije planina, grafikoni |
| Infrastruktura | AWS (VPC, EC2), Ubuntu Server 26.04 LTS, OpenVPN |


## Struktura projekta

```
.
├── app/                        Django: samo JSON API (/api/)
│   ├── frostbite/              postavke, glavni URL-ovi, zajednička API pravila
│   ├── accounts/               korisnici, prijava, zaključavanje naloga, pravila pristupa
│   ├── clubs/                  društva i članstva
│   ├── tours/                  ture, prijave, lista čekanja, odabir, GPX
│   ├── panel/                  vodič, admin društva, sistemski admin, analitika (*_service.py)
│   ├── audit/                  evidencija aktivnosti (samo dodavanje)
│   └── requirements.txt
├── frontend/                   React aplikacija (cijeli interfejs)
│   ├── src/api/                pozivi API-ja (jedan klijent: same-origin, CSRF)
│   ├── src/pages/              stranice po ulogama
│   ├── src/components/         mapa, kartice, maskota, ilustracije, grafikoni
│   └── src/styles/tokens.css   sve boje (bez gradijenata)
├── docker/nginx/               Nginx za Docker (TLS, zaglavlja, CSP, React + /api/)
├── docker-compose.yml          Nginx + Django/Gunicorn + PostgreSQL
├── infra/
│   ├── deploy.sh               postavljanje aplikacije sa vašeg računara na server
│   ├── vpn/vpn-hardening.sh    NAT, split tunnel i firewall na VPN serveru
│   └── app/                    skripte za aplikacijski server (01 do 04)
└── primjer-ruta.gpx            primjer GPX datoteke za testiranje uvoza rute
```

Važna mjesta u kodu:

- `app/accounts/permissions.py`: centralna pravila pristupa (koje društvo, koja tura, koja uloga)
- `app/accounts/backends.py`: prijava i zaključavanje naloga
- `app/tours/services.py`: prijava i odjava sa ture (transakcije i lista čekanja)
- `app/panel/*_service.py`: pravila panela vodiča, admina društva i sistemskog admina
- `app/frostbite/settings.py`: sve sigurnosne postavke Django-a
- `frontend/src/api/client.ts`: jedini HTTP klijent (samo `/api/`, CSRF token u memoriji)
- `.claude/skills/frostbite-frontend/SKILL.md`: pravila dizajna i sigurnosti za frontend

## Lokalno pokretanje

Potrebno: **Python 3.12 ili noviji**, **Node.js 24** i `git`. PostgreSQL nije potreban; lokalno se koristi SQLite.

```bash
# 1. Preuzmite projekat
git clone <adresa-repozitorija> frostbite
cd frostbite

# 2. Django API: okruženje, paketi, baza i demo podaci
cd app
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
.venv/bin/python manage.py runserver          # API na :8000 (terminal 1)

# 3. React interfejs (terminal 2)
cd frontend
npm ci
npm run dev
```

Aplikacija je dostupna na **http://localhost:5173**. Vite prosljeđuje `/api` na Django, pa sve radi
na istom originu kao u produkciji (kolačići i CSRF bez CORS-a).

Na Windowsu umjesto `.venv/bin/python` koristite `.venv\Scripts\python`.

**Ponovno postavljanje demo podataka:**

```bash
rm dev.sqlite3
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
```

**Nalog sistemskog admina bez demo podataka** (jedini način; ne može se kreirati kroz web aplikaciju):

```bash
.venv/bin/python manage.py create_system_admin
```

## Pokretanje u Dockeru

Potrebno: Docker sa Compose pluginom. Aplikacija radi u produkcijskom režimu (PostgreSQL, HTTPS, `__Host-` kolačići).

```bash
cp .env.example .env          # upišite DJANGO_SECRET_KEY i DB_PASSWORD
docker compose up -d --build
docker compose exec backend python manage.py create_system_admin
```

Aplikacija je na `https://localhost` (samopotpisani certifikat, pregledač će tražiti potvrdu).

| Servis | Uloga | Izložen |
|---|---|---|
| `web` | Nginx: TLS, sigurnosna zaglavlja, CSP, rate limit, React aplikacija, `/api/` -> backend | 80, 443 |
| `backend` | Django + Gunicorn, ne-root korisnik, datotečni sistem samo za čitanje | ne |
| `db` | PostgreSQL 18 na internoj mreži bez izlaza na internet | ne |

Backend pri svakom pokretanju izvrši `check --deploy`, migracije i `clearsessions`.
Pravi certifikat: stavite `fullchain.crt` i `privkey.key` u `./certs` i u `docker-compose.yml`
zamijenite volume `certs` sa `./certs:/etc/nginx/certs:ro`.

Korisne komande:

```bash
docker compose logs -f backend                    # logovi
docker compose exec backend python manage.py shell
docker compose down                               # zaustavljanje (podaci ostaju)
docker compose down -v                            # zaustavljanje i BRISANJE baze
```

`seed_demo` ne radi u Dockeru jer odbija PostgreSQL bazu. Demo podaci su samo za lokalni razvoj.

## JSON API

Django služi samo JSON API pod `/api/` (Django REST Framework); interfejs je React aplikacija.
Autentikacija: Django sesija u `HttpOnly` kolačiću, bez JWT-a i bez tokena u pregledaču.
Svaki zahtjev koji mijenja stanje mora imati zaglavlje `X-CSRFToken`, i za neprijavljene
korisnike (zaštita od login CSRF-a). API prima i vraća samo JSON, i ništa nije dozvoljeno bez prijave
osim endpointa koji to izričito dozvoljavaju.

| Metoda | Putanja | Opis |
|---|---|---|
| GET | `/api/auth/csrf/` | `{"csrfToken"}`; CSRF kolačić je HttpOnly, pa se token dobija ovdje |
| GET | `/api/auth/me/` | `{"authenticated", "user": {id, email, firstName, lastName, roles}}` |
| POST | `/api/auth/login/` | `{"email", "password"}` → podaci korisnika i **novi** `csrfToken` |
| POST | `/api/auth/logout/` | 204, sesija se briše |
| POST | `/api/auth/register/` | `{"email", "firstName", "lastName", "phone", "password", "passwordConfirm"}` → 201 |
| GET | `/api/tours/` | javne ture (`?q, difficulty, club, date_from, date_to`; neispravan filter → 400) |
| GET | `/api/tours/<id>/` | detalji javne ture (ruta, vodiči samo imenom, vlastita prijava) |
| GET | `/api/tours/<id>/gpx/` | ruta javne ture kao GPX datoteka |
| GET | `/api/tours/filters/` | težine i odobrena društva za filtere |
| GET | `/api/tours/stats/` | zbirne brojke za početnu |
| GET | `/api/clubs/`, `/api/clubs/<id>/` | odobrena društva, javni profil i njihove ture |
| POST | `/api/tours/<id>/register/` | prijava na turu (puna tura → lista čekanja) · planinar |
| GET | `/api/me/registrations/` | vlastite prijave (predstojeće sa `canCancel`, historija) · planinar |
| POST | `/api/me/registrations/<id>/cancel/` | odjava do roka; prvi sa liste čekanja dobija mjesto · planinar |
| GET, POST | `/api/selection/` | odabir više tura (sesija, dijeli se sa starim stranicama); POST `{"tourId"}` |
| DELETE | `/api/selection/<id>/` | ukloni turu iz odabira |
| POST | `/api/selection/confirm/` | prijava na sve odabrane ture, rezultat po turi · planinar |
| POST | `/api/clubs/<id>/membership/` | zahtjev za članstvo · planinar |
| GET | `/api/me/memberships/` | vlastita članstva i zahtjevi · planinar |
| GET, POST | `/api/clubs/request/` | zahtjev za registraciju društva (najviše jedan na čekanju) · planinar |
| GET, PUT | `/api/me/profile/` | vlastiti profil (email, uloge i status se ne mogu mijenjati) |
| POST | `/api/me/password/` | promjena lozinke uz staru; ostale sesije se odjavljuju |
| GET | `/api/badges/` | katalog bedževa (javno) i ukupan broj dodijeljenih |
| GET | `/api/me/badges/` | vlastiti bedževi uloga korisnika: `earned`, `seen`, `progress`/`goal` |
| POST | `/api/me/badges/seen/` | označi nove bedževe kao viđene |
| GET | `/api/guide/` | ture koje vodič vodi i ture vlastitih društava bez vodiča · vodič |
| GET | `/api/guide/tours/<id>/` | učesnici sa ličnim podacima (samo odobreni vodič, do 7 dana nakon ture; pristup se bilježi) |
| POST | `/api/guide/tours/<id>/apply/` · `close/` · `attendance/` · `report/` | prijava za vođenje, zatvaranje prijava, prisustvo `{"present": [id]}`, izvještaj `{"text"}` |
| GET | `/api/manage/` | društva kojima korisnik upravlja · admin društva |
| GET | `/api/manage/<c>/` | analitika društva (faze, popunjenost, procjena prihoda, serije po mjesecu) |
| GET, POST | `/api/manage/<c>/tours/` | ture društva; kreiranje (uvijek NACRT; ruta kao lista `[lat, lng]`, najviše 500 tačaka) |
| GET, PUT | `/api/manage/<c>/tours/<id>/` | detalji (prijave samo imenom i statusom) i izmjena (samo nacrt/objavljena/zatvorena) |
| POST | `/api/manage/<c>/tours/<id>/transition/` · `guides/assign/` · `guides/<app>/decide/` | objava/zatvaranje/otkazivanje, dodjela i odobravanje vodiča |
| GET, POST | `/api/manage/<c>/guides/` · `guides/<id>/remove/` | vodiči društva (dodavanje po emailu - ista poruka bez obzira na nalog) |
| GET, POST | `/api/manage/<c>/members/` · `members/<id>/decide/` | zahtjevi za članstvo i aktivni članovi |
| GET, PUT | `/api/manage/<c>/profile/` | profil društva (naziv i status mijenja samo sistemski admin) |
| GET | `/api/system/` | analitika platforme i sigurnosni događaji (samo zbirni podaci) · sistemski admin |
| GET, POST | `/api/system/clubs/` · `clubs/<id>/decide/` | društva; odobravanje, odbijanje, suspenzija `{"action"}` |
| GET, POST | `/api/system/users/?q=&page=` · `users/<id>/toggle/` | nalozi (ime, email, status); blokiranje gasi sve sesije; vlastiti nalog ne |
| GET | `/api/system/audit/?action=&page=` | evidencija aktivnosti, samo čitanje |

""Admin društva" vidi samo društva kojima upravlja: tuđe društvo, tura, vodič ili članstvo daju 404
(i preko URL-a vlastitog društva). Pravila su u `panel/club_service.py`, `panel/guide_service.py` i `panel/system_service.py`,
zajednička za stare stranice i API.

"Planinar" znači prijavljen korisnik koji nije sistemski admin (isto pravilo kao `hiker_required`).
Pravila prijave, odjave i liste čekanja su u `tours/services.py` i ista su za stare i nove stranice.

Javni endpointi (`tours`, `clubs`) koriste `public_tours()` i `approved_clubs()`:
samo objavljene ture odobrenih društava u narednih 30 dana; sve ostalo je 404. Odgovori sadrže samo
izričito nabrojana polja (bez učesnika, kreatora i kontakata korisnika).

Prijava i registracija koriste Django forme i `LockoutEmailBackend` (zaključavanje naloga,
generička poruka greške, validatori lozinke, audit log, isti odgovor za postojeći email).
Nepoznate putanje i greške vraćaju JSON (`{"detail": ...}`) bez internih detalja.

## Frontend (React)

Cijeli interfejs je u `frontend/` (React 19, TypeScript, Vite, React Router, TanStack Query).
Pravila dizajna i sigurnosti su u `.claude/skills/frostbite-frontend/SKILL.md`.

Stare adrese iz Django verzije (`/nalog/prijava/`, `/nalog/profil/`, `/ture/<id>/ruta.gpx`) i adrese
iz perioda migracije (`/novo/...`) Nginx trajno preusmjerava na nove.

Interfejs ima svijetlu i tamnu temu (prekidač u zaglavlju; bez izbora prati sistem), maskotu Frosti
i generisane crtane ilustracije planina na karticama tura i društava (`SceneArt`, isti crtež za isti ID).

| Komanda | Šta radi |
|---|---|
| `npm run check` | TypeScript, ESLint (sigurnosna pravila) i provjera dizajna (bez gradijenata, boje samo iz tokena) |
| `npm test` | unit testovi (open redirect, ID-jevi i filteri iz URL-a, sesija, formatiranje, ruta, grafikon) |
| `npm run build` | `check` + produkcijski build bez source mapa |

U Dockeru se frontend gradi u Nginx image-u (`npm ci`, pa `npm run build`); build pada ako `check` ne prođe.
Nove pakete instalirati samo u verzijama starijim od 14 dana: `npm install --before=YYYY-MM-DD <paket>`.

## Demo nalozi

Komanda `seed_demo` kreira sljedeće naloge. Lozinka za sve je `Demo-Lozinka-2026`.

| Email | Uloga |
|---|---|
| `sysadmin@frostbite.ba` | sistemski admin |
| `admin@pd-bjelasnica.ba` | admin društva PD Bjelašnica |
| `admin@pd-prenj.ba` | admin društva PD Prenj |
| `vodic1@pd-bjelasnica.ba` | vodič (PD Bjelašnica) |
| `vodic@pd-prenj.ba` | vodič (PD Prenj) |
| `planinar1@primjer.ba` | planinar, član PD Bjelašnica |
| `planinar2@primjer.ba` | planinar |

Demo podaci postoje samo lokalno: `seed_demo` odbija da se pokrene u produkciji i na PostgreSQL bazi.

### Nalozi za recenzente (server)

Politika (poglavlje 5.2) predviđa naloge za sve grupe korisnika i ture u svim statusima. Na serveru
ih kreira komanda `seed_review`, **jednom**, nad bazom bez korisničkih podataka (ranije kreirani
sistemski admini su dozvoljeni):

```bash
ssh fb-app 'sudo frostbite-manage seed_review --potvrdi'
```

| Nalog | Uloga |
|---|---|
| `sistem@frostbite.test` | sistemski admin |
| `admin.alfa@frostbite.test`, `admin.beta@frostbite.test` | admin društva PD Alfa (test) i PD Beta (test) |
| `vodic1.alfa`, `vodic2.alfa`, `vodic1.beta`, `vodic2.beta` `@frostbite.test` | po dva vodiča u svakom društvu |
| `planinar1@frostbite.test` | planinar, član PD Alfa, ima zdravstvenu napomenu (testni podatak) |
| `planinar2@frostbite.test` | planinar, zahtjev za članstvo u PD Alfa čeka odluku |
| `planinar3@frostbite.test` | planinar, član PD Beta, podnio zahtjev za registraciju PD Gama |

Svaki nalog dobija vlastitu nasumičnu lozinku od 20 znakova. Lozinke se **ispišu samo jednom** i
nigdje se ne čuvaju (u bazi je samo hash), pa ispis treba odmah sačuvati van servera (npr. u
`users.txt`, koji je u `.gitignore`) i predati recenzentima. Ture pokrivaju sve statuse: nacrt,
objavljena (i samo za članove, i popunjena s listom čekanja), prijave zatvorene (jučerašnja tura,
za evidenciju prisustva), održana (s izvještajem) i otkazana. Domen `.test` i nazivi društava su
izmišljeni, da se ne mogu zamijeniti sa stvarnim osobama ili društvima.

## Testovi

```bash
cd app && .venv/bin/python manage.py test       # 132 testa API-ja
cd frontend && npm run check && npm test         # TypeScript, ESLint, dizajn + 59 unit testova
./docker/e2e.sh                                  # E2E testovi u pregledaču (Playwright) nad Dockerom
```

Pored ispravnog rada testovi provjeravaju i sigurnosna pravila:

- izolaciju društava i IDOR (tuđe društvo, tura, prijava ili članstvo daju 404),
- pristup ličnim podacima (samo odobreni vodič, u vremenskom prozoru, uz audit),
- zaključavanje naloga i neotkrivanje postojanja naloga,
- CSRF za svaki zahtjev koji mijenja stanje (i bez prijave),
- podmetanje polja (mass assignment: status, društvo, uloge),
- XSS u nazivima tura, napomenama i evidenciji (sadržaj ostaje tekst),
- blokiranje naloga i promjenu lozinke (gašenje ostalih sesija),
- otvoreno preusmjeravanje nakon prijave (frontend).

Test koji provjerava PostgreSQL trigger za evidenciju aktivnosti preskače se lokalno (SQLite) i izvršava se na serveru.

### E2E testovi (`frontend/e2e/`)

`./docker/e2e.sh` podigne **zaseban** Docker stack (projekat `frostbite-e2e`, baza `frostbite_e2e`,
portovi samo na `127.0.0.1:8080` i `127.0.0.1:8443`), ubaci podatke komandom `seed_e2e` i pokrene
Playwright u Chromiumu. Postavke su iste kao u produkciji: Nginx, HTTPS, `__Host-` kolačići,
sigurnosna zaglavlja. Baza se briše prije svakog pokretanja, a razvojni stack ostaje netaknut.

Prvi put: `cd frontend && npm ci && npx playwright install chromium`.

```bash
./docker/e2e.sh                          # svi testovi, pa gašenje stacka
./docker/e2e.sh e2e/security.spec.ts     # jedan fajl (argumenti idu Playwrightu)
E2E_KEEP=1 ./docker/e2e.sh               # stack ostaje na https://localhost:8443
cd frontend && npx playwright show-report e2e-report    # izvještaj s tragovima grešaka
```

| Fajl | Šta provjerava |
|---|---|
| `public.spec.ts` | javni dio; nacrti i društva na čekanju nisu javni; zaštićene stranice traže prijavu |
| `auth.spec.ts` | generička poruka greške, zaključavanje naloga, registracija bez otkrivanja naloga, odjava gasi sesiju, promjena lozinke gasi ostale sesije, `?next=` ne vodi na drugi domen |
| `security.spec.ts` | HTTP→HTTPS, sigurnosna zaglavlja (bez duplikata), kolačići, CSRF i Origin, samo JSON, prava po ulogama, IDOR (404), nacrt nije javan, sistemski admin ne vidi lične podatke, nema source mapa ni skrivenih datoteka |
| `hiker.spec.ts`, `guide.spec.ts`, `admin.spec.ts`, `system.spec.ts` | glavni tokovi svake uloge u pregledaču i zabranjene stranice za tu ulogu |

`seed_e2e` odbija da radi bez `FROSTBITE_E2E=1` i nad bazom čije ime ne završava na `_e2e`, pa se
ne može slučajno pokrenuti nad pravom bazom.

## Postavljanje na AWS

### Arhitektura

```
Internet ── UDP 1194 ──> fb-vpn (javna podmreža, Elastic IP)
                           │  OpenVPN, NAT, SSH jump host
                           │  VPN klijenti vide SAMO aplikaciju na 80/443
                           ▼
                         fb-app (privatna podmreža, bez javne IP adrese)
                            Nginx (HTTPS): React aplikacija (/) i /api/ -> Gunicorn -> Django -> PostgreSQL (samo localhost)
```

### Prvo postavljanje (jednom)

1. **AWS konzola (Learner Lab, us-east-1):** VPC sa javnom i privatnom podmrežom, sigurnosne grupe `fb-vpn-sg` i `fb-app-sg`, instance `fb-vpn` (t3.micro, javna podmreža, Elastic IP, isključen source/destination check) i `fb-app` (t3.small, privatna podmreža), ruta `0.0.0.0/0 -> fb-vpn` u tabeli ruta privatne podmreže. **Obje sigurnosne grupe moraju imati odlazno pravilo za sav saobraćaj.**
2. **SSH konfiguracija** (`~/.ssh/config`):
   ```
   Host fb-vpn
       HostName <ELASTIC_IP>
       User ubuntu
       IdentityFile ~/.ssh/fb-key.pem

   Host fb-app
       HostName <PRIVATNA_IP_APLIKACIJE>
       User ubuntu
       IdentityFile ~/.ssh/fb-key.pem
       ProxyJump fb-vpn
   ```
3. **VPN server:**
   ```bash
   ssh fb-vpn
   curl -O https://raw.githubusercontent.com/angristan/openvpn-install/master/openvpn-install.sh
   chmod +x openvpn-install.sh && sudo ./openvpn-install.sh   # DNS: npr. Cloudflare, ne Unbound
   exit
   scp infra/vpn/vpn-hardening.sh fb-vpn:
   ssh fb-vpn 'sudo ./vpn-hardening.sh <PRIVATNA_IP_APLIKACIJE> <CIDR_PRIVATNE_PODMREŽE>'
   ```
4. **Aplikacijski server:**
   ```bash
   scp infra/app/*.sh fb-app:
   ssh fb-app 'chmod +x *.sh'
   ssh fb-app 'sudo ./01-osnova.sh <PRIVATNA_IP_VPN_SERVERA>'
   ssh fb-app 'sudo ./02-postgresql.sh'
   ssh fb-app 'sudo ./03-nginx-https.sh <PRIVATNA_IP_APLIKACIJE>'
   ```

Skripte za aplikaciju odbijaju da se pokrenu na VPN serveru, a `vpn-hardening.sh` odbija pogrešne adrese.

### Postavljanje nove verzije aplikacije

```bash
./infra/deploy.sh
```

Skripta prvo pokreće testove API-ja i frontenda i pravi React build na vašem računaru (potreban je Node.js; ako išta padne, ništa se ne postavlja), zatim kopira kod i build na server i pokreće `04-deploy-app.sh`: Python okruženje, migracije, React aplikacija, systemd servis i Nginx. Na serveru Node.js nije potreban. Zadana adresa aplikacije je `10.0.143.199`; druga se zadaje sa `APP_IP=<adresa> ./infra/deploy.sh`.

Prvi put nakon postavljanja kreirajte sistemskog admina:

```bash
ssh fb-app 'sudo frostbite-manage create_system_admin'
```

### Pristup aplikaciji

1. Uvezite `.ovpn` datoteku u OpenVPN klijent i spojite se.
2. Otvorite `https://<PRIVATNA_IP_APLIKACIJE>`. Upozorenje preglednika o certifikatu je očekivano, jer je certifikat self-signed (izdat na privatnu IP adresu).

Svaka grupa recenzenata dobija vlastitu `.ovpn` datoteku (`sudo ./openvpn-install.sh` na VPN serveru, opcija "Add a new user"). Recenzenti nemaju SSH pristup ni pristup bazi.

> **Learner Lab gasi instance kad istekne sesija.** Za vrijeme pregleda aplikacija mora biti upaljena dok druge grupe testiraju. Privatne IP adrese i Elastic IP ostaju iste nakon gašenja i paljenja.

## Sigurnost

Sažetak mjera; potpuna pravila su u sigurnosnoj politici.

- **Pristup:** svaki objekat se dohvata kroz ograničen upit (vlastito društvo, ture koje vodič vodi), pa tuđi objekat daje 404, isto kao nepostojeći. Django admin panel nije uključen.
- **Nalozi:** lozinke od najmanje 10 znakova uz provjeru čestih lozinki. Zaključavanje nakon 5 neuspjeha na 15 minuta, vezano za nalog, ne za IP adresu, jer svi korisnici VPN-a dijele istu adresu. Ista poruka za svaki neuspjeh prijave i isti odgovor pri registraciji postojećeg emaila. Sesija ističe nakon 30 minuta, a kolačići su `Secure`, `HttpOnly` i s prefiksom `__Host-`.
- **Lični podaci:** telefon, hitni kontakt i zdravstvene napomene vidi samo odobreni vodič ture, najkasnije 7 dana nakon nje. Svaki pristup se bilježi.
- **Evidencija aktivnosti:** samo dodavanje; izmjenu i brisanje blokiraju i aplikacija i PostgreSQL trigger.
- **Web:** samo HTTPS, stroga CSP (`default-src 'self'`, bez umetnutog JavaScript-a), HSTS i zaštita od clickjackinga. Ograničenje broja zahtjeva na prijavi, registraciji i promjeni lozinke.
- **Frontend:** sesija samo u `HttpOnly` kolačiću (bez tokena u pregledaču), CSRF token samo u memoriji, jedan API klijent (same-origin), ESLint zabranjuje `innerHTML`, `eval` i pohranu u pregledaču (osim izbora teme), produkcijski build bez source mapa, ovisnosti u tačnim verzijama bez install skripti.
- **Datoteke:** aplikacija ne prima datoteke. GPX ruta se čita u pregledniku i na server se šalju samo koordinate.
- **Server:** baza sluša samo na localhost i aplikacijski korisnik baze nije superuser. Gunicorn radi kao ograničen systemd servis, a kod je za aplikaciju samo za čitanje. SSH je dozvoljen samo ključem, a VPN klijenti vide samo aplikaciju.

## Česti problemi

| Problem | Rješenje |
|---|---|
| `ssh fb-vpn` ne radi (timeout) | Lab sesija je istekla (pokrenite lab) ili se promijenila vaša javna IP adresa: u `fb-vpn-sg` za port 22 ponovo izaberite **My IP**. |
| Server nema pristup internetu | Odlazno pravilo u sigurnosnoj grupi, ruta `0.0.0.0/0 -> fb-vpn` u privatnoj tabeli ruta i isključen source/destination check na `fb-vpn`. |
| Mapa je siva | Pločice mape se učitavaju sa interneta; provjerite konekciju. Na serveru domeni podloga moraju biti u CSP-u (`img-src`). |
| Nova verzija se ne vidi | `index.html` se ne kešira, a ostale datoteke imaju hash u imenu; osvježite stranicu (`Ctrl+Shift+R`). |
| `npm run dev`: greške u konzoli za `/api` | Django API nije pokrenut: `cd app && .venv/bin/python manage.py runserver`. |
| Build pada na „Provjera dizajna“ | U kodu je gradijent ili boja van `tokens.css`; poruka navodi datoteku i red. |
