# Frostbite

Web aplikacija za planinarska društva, ture i vodiče. 

Planinarska društva objavljuju ture, upravljaju vodičima i članovima. Planinari pronalaze ture na mapi, prijavljuju se na jednu ili više njih i učlanjuju se u društva. Vodiči vode ture i imaju uvid u podatke o učesnicima, a sistemski admin odobrava društva i prati sigurnost platforme.


---

## Sadržaj

- [Funkcionalnosti](#funkcionalnosti)
- [Tehnologije](#tehnologije)
- [Struktura projekta](#struktura-projekta)
- [Lokalno pokretanje](#lokalno-pokretanje)
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
| Backend | Python 3.12+ (server: 3.14), Django 6.1, Gunicorn |
| Baza | PostgreSQL 18 (produkcija), SQLite (lokalni razvoj) |
| Web server | Nginx (TLS 1.2/1.3, sigurnosna zaglavlja, CSP) |
| Frontend | Django predlošci, vlastiti CSS, mali JavaScript moduli bez okvira |
| Mape | Leaflet 1.9.4 (lokalno), podloge Esri World Topo, OpenTopoMap, OpenStreetMap |
| Ikonice | Lucide (lokalni SVG sprite) |
| Infrastruktura | AWS (VPC, EC2), Ubuntu Server 26.04 LTS, OpenVPN |


## Struktura projekta

```
.
├── app/                        Django aplikacija
│   ├── frostbite/              postavke, glavni URL-ovi
│   ├── accounts/               korisnici, prijava, zaključavanje naloga, pravila pristupa
│   ├── clubs/                  društva i članstva
│   ├── tours/                  ture, prijave, mapa, GPX, ilustracije tura
│   ├── panel/                  vodič, admin društva, sistemski admin, analitika
│   ├── audit/                  evidencija aktivnosti (samo dodavanje)
│   ├── templates/              HTML predlošci
│   ├── static/                 CSS, JavaScript, ikonice, Leaflet
│   └── requirements.txt
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
- `app/frostbite/settings.py`: sve sigurnosne postavke Django-a

## Lokalno pokretanje

Potrebno: **Python 3.12 ili noviji** i `git`. PostgreSQL nije potreban; lokalno se koristi SQLite.

```bash
# 1. Preuzmite projekat i uđite u folder aplikacije
git clone <adresa-repozitorija> frostbite
cd frostbite/app

# 2. Virtualno okruženje i paketi
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 3. Baza i demo podaci
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo

# 4. Pokretanje
.venv/bin/python manage.py runserver
```

Aplikacija je dostupna na **http://127.0.0.1:8000**.

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

Demo podaci postoje samo lokalno: `seed_demo` odbija da se pokrene u produkciji i na PostgreSQL bazi. Nalozi za recenzente na serveru kreiraju se posebno, sa jakim lozinkama.

## Testovi

```bash
cd app
.venv/bin/python manage.py test
```

Postoji 94 automatska testa. Pored ispravnog rada provjeravaju i sigurnosna pravila:

- izolaciju društava (admin jednog društva ne vidi drugo),
- pristup ličnim podacima (samo odobreni vodič, u vremenskom prozoru),
- zaključavanje naloga i neotkrivanje postojanja naloga,
- podmetanje polja u formama (mass assignment),
- XSS u nazivima tura (mapa, GPX),
- odsustvo umetnutog JavaScript-a (CSP),
- otvoreno preusmjeravanje nakon prijave.

Test koji provjerava PostgreSQL trigger za evidenciju aktivnosti preskače se lokalno (SQLite) i izvršava se na serveru.

## Postavljanje na AWS

### Arhitektura

```
Internet ── UDP 1194 ──> fb-vpn (javna podmreža, Elastic IP)
                           │  OpenVPN, NAT, SSH jump host
                           │  VPN klijenti vide SAMO aplikaciju na 80/443
                           ▼
                         fb-app (privatna podmreža, bez javne IP adrese)
                            Nginx (HTTPS) -> Gunicorn -> Django -> PostgreSQL (samo localhost)
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

Skripta prvo pokreće testove (ako padnu, ništa se ne postavlja), zatim kopira kod na server i pokreće `04-deploy-app.sh`: Python okruženje, migracije, statičke datoteke, systemd servis i Nginx. Zadana adresa aplikacije je `10.0.143.199`; druga se zadaje sa `APP_IP=<adresa> ./infra/deploy.sh`.

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
- **Web:** samo HTTPS, stroga CSP (`script-src 'self'`, bez umetnutog JavaScript-a), HSTS i zaštita od clickjackinga. Ograničenje broja zahtjeva na prijavi i registraciji.
- **Datoteke:** aplikacija ne prima datoteke. GPX ruta se čita u pregledniku i na server se šalju samo koordinate.
- **Server:** baza sluša samo na localhost i aplikacijski korisnik baze nije superuser. Gunicorn radi kao ograničen systemd servis, a kod je za aplikaciju samo za čitanje. SSH je dozvoljen samo ključem, a VPN klijenti vide samo aplikaciju.

## Česti problemi

| Problem | Rješenje |
|---|---|
| `ssh fb-vpn` ne radi (timeout) | Lab sesija je istekla (pokrenite lab) ili se promijenila vaša javna IP adresa: u `fb-vpn-sg` za port 22 ponovo izaberite **My IP**. |
| Server nema pristup internetu | Odlazno pravilo u sigurnosnoj grupi, ruta `0.0.0.0/0 -> fb-vpn` u privatnoj tabeli ruta i isključen source/destination check na `fb-vpn`. |
| Mapa je siva | Pločice mape se učitavaju sa interneta; provjerite konekciju. Na serveru domeni podloga moraju biti u CSP-u (`img-src`). |
| Promjene CSS-a se ne vide | Osvježite stranicu bez keša: `Ctrl+Shift+R`. |
| `'ui' is not a registered tag library` | Restartujte razvojni server nakon dodavanja novih modula. |
