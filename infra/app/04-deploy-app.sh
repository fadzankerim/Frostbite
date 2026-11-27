#!/usr/bin/env bash
# Frostbite - postavljanje / ažuriranje aplikacije (Django API + React interfejs).
#   sudo ./04-deploy-app.sh <izvorni-folder> <privatna-IP-ove-instance> <react-build-folder>
# Obično se ne pokreće ručno, nego preko infra/deploy.sh sa vašeg računara.
#
# Raspored na serveru:
#   /opt/frostbite/app     kod (vlasnik root, aplikacija ga može samo čitati)
#   /opt/frostbite/venv    Python okruženje (root)
#   /opt/frostbite/web     React aplikacija (build iz frontend/; servira je Nginx)
#   /etc/frostbite/*.env   tajne (root:frostbite 640)
#   /run/frostbite.sock    Gunicorn socket (dostupan samo korisniku www-data, tj. Nginx-u)
set -euo pipefail

USAGE="Upotreba: sudo $0 <izvorni-folder> <privatna-IP> <react-build-folder>"
SRC="${1:?$USAGE}"
APP_IP="${2:?$USAGE}"
WEB="${3:?$USAGE}"
APP_USER=frostbite
BASE=/opt/frostbite
ENV_DIR=/etc/frostbite
CERT=/etc/ssl/certs/frostbite.crt
KEY=/etc/ssl/private/frostbite.key

[[ $EUID -eq 0 ]] || { echo "Pokrenite sa sudo."; exit 1; }
if [[ -d /etc/openvpn/server ]] || systemctl is-active --quiet openvpn-server@server 2>/dev/null; then
  echo "[!] Ovo je VPN server. Skripta je namijenjena instanci fb-app."; exit 1
fi
id "$APP_USER" >/dev/null 2>&1 || { echo "[!] Prvo pokrenite 01-osnova.sh"; exit 1; }
[[ -f $ENV_DIR/db.env ]] || { echo "[!] Prvo pokrenite 02-postgresql.sh"; exit 1; }
[[ -f $CERT ]] || { echo "[!] Prvo pokrenite 03-nginx-https.sh"; exit 1; }
[[ -f $SRC/manage.py ]] || { echo "[!] $SRC ne sadrži Django projekat (manage.py)."; exit 1; }
[[ -f $WEB/index.html ]] || { echo "[!] $WEB ne sadrži React build (index.html)."; exit 1; }

export DEBIAN_FRONTEND=noninteractive
apt-get install -y -qq python3-venv rsync >/dev/null

# --- Kod -------------------------------------------------------------------
# 751: Nginx (www-data) smije samo proći kroz folder do web/, ne i čitati sadržaj
install -d -o root -g "$APP_USER" -m 751 "$BASE"
install -d -o root -g "$APP_USER" -m 750 "$BASE/app"
rsync -a --delete --exclude '.venv' --exclude '__pycache__' --exclude '*.pyc' \
      --exclude 'dev.sqlite3' --exclude 'staticfiles' "$SRC/" "$BASE/app/"
chown -R root:"$APP_USER" "$BASE/app"
find "$BASE/app" -type d -exec chmod 750 {} +
find "$BASE/app" -type f -exec chmod 640 {} +
echo "[i] Kod kopiran u $BASE/app (samo za čitanje aplikaciji)."

# --- Python okruženje ------------------------------------------------------
[[ -x $BASE/venv/bin/python ]] || python3 -m venv "$BASE/venv"
"$BASE/venv/bin/pip" install -q --upgrade pip
"$BASE/venv/bin/pip" install -q -r "$BASE/app/requirements.txt"
chmod -R o-rwx "$BASE/venv"; chgrp -R "$APP_USER" "$BASE/venv"; chmod -R g+rX "$BASE/venv"
"$BASE/venv/bin/python" -m compileall -q "$BASE/app" >/dev/null
chown -R root:"$APP_USER" "$BASE/app"; find "$BASE/app" -name '*.pyc' -exec chmod 640 {} +; find "$BASE/app" -type d -exec chmod 750 {} +

# --- Tajne aplikacije ------------------------------------------------------
if [[ ! -f $ENV_DIR/app.env ]]; then
  umask 027
  cat > "$ENV_DIR/app.env" <<EOF
FROSTBITE_ENV=production
DJANGO_SECRET_KEY=$(openssl rand -base64 64 | tr -d '\n=+/' | head -c 64)
DJANGO_ALLOWED_HOSTS=$APP_IP
DJANGO_LOG_DIR=/var/log/frostbite
EOF
  chown root:"$APP_USER" "$ENV_DIR/app.env"; chmod 640 "$ENV_DIR/app.env"
  echo "[i] Generisan $ENV_DIR/app.env (SECRET_KEY)."
fi
# Obavještenja: adresa za linkove u emailovima. SMTP se upisuje ručno u app.env kad bude spreman
# (EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL); bez EMAIL_HOST
# slanje je isključeno, a obavještenja ostaju u outboxu dok im ne istekne rok.
grep -q '^FROSTBITE_PUBLIC_URL=' "$ENV_DIR/app.env" || echo "FROSTBITE_PUBLIC_URL=https://$APP_IP" >> "$ENV_DIR/app.env"

# Pomoćna komanda za manage.py sa produkcijskim okruženjem, kao korisnik aplikacije:
#   sudo frostbite-manage migrate | create_system_admin | shell ...
cat > /usr/local/sbin/frostbite-manage <<EOF
#!/usr/bin/env bash
set -a; . $ENV_DIR/db.env; . $ENV_DIR/app.env; set +a
export PYTHONDONTWRITEBYTECODE=1
cd $BASE/app && exec runuser -u $APP_USER -- $BASE/venv/bin/python manage.py "\$@"
EOF
chmod 750 /usr/local/sbin/frostbite-manage

# React aplikacija: vlasnik root, Nginx (www-data) je smije samo čitati
install -d -o root -g www-data -m 750 "$BASE/web"
rsync -a --delete "$WEB/" "$BASE/web/"
chown -R root:www-data "$BASE/web"; find "$BASE/web" -type d -exec chmod 750 {} +; find "$BASE/web" -type f -exec chmod 640 {} +
rm -rf "$BASE/static"          # ostatak starih Django stranica (više se ne koristi)
install -d -o "$APP_USER" -g "$APP_USER" -m 750 /var/log/frostbite

# --- Baza -------------------------------------------------------------------
frostbite-manage check --deploy --fail-level ERROR
frostbite-manage migrate --noinput
frostbite-manage badges_backfill          # idempotentno: bedževi za postojeću istoriju
frostbite-manage clearsessions

# --- systemd: socket + servis ----------------------------------------------
cat > /etc/systemd/system/frostbite.socket <<'EOF'
[Unit]
Description=Frostbite Gunicorn socket

[Socket]
ListenStream=/run/frostbite.sock
# Socket smije koristiti samo Nginx
SocketUser=www-data
SocketGroup=www-data
SocketMode=0600

[Install]
WantedBy=sockets.target
EOF

cat > /etc/systemd/system/frostbite.service <<EOF
[Unit]
Description=Frostbite (Gunicorn + Django)
Requires=frostbite.socket
After=network.target postgresql.service

[Service]
Type=notify
NotifyAccess=main
User=$APP_USER
Group=$APP_USER
EnvironmentFile=$ENV_DIR/db.env
EnvironmentFile=$ENV_DIR/app.env
Environment=PYTHONDONTWRITEBYTECODE=1
WorkingDirectory=$BASE/app
ExecStart=$BASE/venv/bin/gunicorn frostbite.wsgi:application --workers 3 --timeout 30 --access-logfile - --error-logfile -
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
Restart=on-failure

# Ograničenja procesa (sandbox)
NoNewPrivileges=yes
CapabilityBoundingSet=
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectKernelLogs=yes
ProtectControlGroups=yes
ProtectClock=yes
ProtectHostname=yes
RestrictNamespaces=yes
RestrictRealtime=yes
RestrictSUIDSGID=yes
LockPersonality=yes
SystemCallArchitectures=native
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
ReadWritePaths=/var/log/frostbite
UMask=0027

[Install]
WantedBy=multi-user.target
EOF

# Slanje obavještenja: oneshot servis svake minute (systemd ne pokreće novi dok stari radi)
cat > /etc/systemd/system/frostbite-notify.service <<EOF
[Unit]
Description=Frostbite - slanje obavještenja iz outboxa
After=network-online.target postgresql.service

[Service]
Type=oneshot
User=$APP_USER
Group=$APP_USER
EnvironmentFile=$ENV_DIR/db.env
EnvironmentFile=$ENV_DIR/app.env
Environment=PYTHONDONTWRITEBYTECODE=1
WorkingDirectory=$BASE/app
ExecStart=$BASE/venv/bin/python manage.py send_notifications
TimeoutStartSec=5min
NoNewPrivileges=yes
CapabilityBoundingSet=
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictNamespaces=yes
RestrictSUIDSGID=yes
LockPersonality=yes
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
ReadWritePaths=/var/log/frostbite
UMask=0027
EOF

cat > /etc/systemd/system/frostbite-notify.timer <<'EOF'
[Unit]
Description=Frostbite - obavještenja svake minute

[Timer]
OnCalendar=minutely
AccuracySec=10s
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now frostbite.socket >/dev/null
systemctl enable frostbite.service >/dev/null 2>&1 || true
systemctl restart frostbite.service
systemctl enable --now frostbite-notify.timer >/dev/null

# --- Nginx kao reverse proxy -----------------------------------------------
cat > /etc/nginx/conf.d/01-fb-ratelimit.conf <<'EOF'
# Ograničenje zahtjeva na prijavu i registraciju (zaštita od pogađanja lozinki).
# Svi korisnici VPN-a dolaze sa iste IP adrese, pa je limit namjerno velikodušan;
# glavna zaštita je zaključavanje naloga u aplikaciji.
limit_req_zone $binary_remote_addr zone=fb_auth:1m rate=30r/m;
limit_req_status 429;
EOF

cat > /etc/nginx/sites-available/frostbite <<EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    return 301 https://\$server_addr\$request_uri;
}

server {
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;
    http2 on;
    server_name _;

    ssl_certificate     $CERT;
    ssl_certificate_key $KEY;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "same-origin" always;
    add_header Permissions-Policy "geolocation=(), camera=(), microphone=()" always;
    add_header Content-Security-Policy "default-src 'self'; img-src 'self' data: https://server.arcgisonline.com https://tile.openstreetmap.org https://a.tile.opentopomap.org https://b.tile.opentopomap.org https://c.tile.opentopomap.org; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'" always;

    access_log /var/log/nginx/fb-access.log;
    error_log  /var/log/nginx/fb-error.log;

    location ~ /\. { deny all; return 404; }
    root $BASE/web;

    # --- JSON API (Django) -----------------------------------------------------
    location ~ ^/api/(auth/(login|register)|me/password)/\$ {
        limit_req zone=fb_auth burst=20 nodelay;
        include /etc/nginx/fb-proxy.conf;
    }
    location /api/ {
        include /etc/nginx/fb-proxy.conf;
    }

    # --- stare adrese (Django stranice i /novo/ iz perioda migracije) -> nove -----
    location ~ ^/novo/?(.*)\$ { return 301 /\$1\$is_args\$args; }
    location ~ ^/nalog/prijava/?\$ { return 301 /prijava\$is_args\$args; }
    location ~ ^/nalog/registracija/?\$ { return 301 /registracija; }
    location ~ ^/nalog/(profil|lozinka)/?\$ { return 301 /profil; }
    location ~ ^/ture/(\d+)/ruta\.gpx\$ { return 301 /api/tours/\$1/gpx/; }

    # --- React aplikacija ---------------------------------------------------------
    location /assets/ {
        access_log off;
        expires max;                       # imena datoteka sadrže hash sadržaja
        try_files \$uri =404;
    }
    location / {
        expires -1;                        # index.html se ne kešira
        try_files \$uri /index.html;       # rute React Routera -> index.html
    }
}
EOF

cat > /etc/nginx/fb-proxy.conf <<'EOF'
proxy_pass http://unix:/run/frostbite.sock;
proxy_set_header Host $host;
proxy_set_header X-Forwarded-Proto https;
# Zaglavlja se POSTAVLJAJU (ne dodaju), pa ih klijent ne može podmetnuti.
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $remote_addr;
proxy_redirect off;
# Sigurnosna zaglavlja postavlja samo Nginx (server blok); ista zaglavlja iz Djanga se skrivaju,
# inače bi odgovor API-ja imao dupla zaglavlja (npr. "X-Frame-Options: DENY, DENY").
proxy_hide_header X-Frame-Options;
proxy_hide_header X-Content-Type-Options;
proxy_hide_header Referrer-Policy;
proxy_read_timeout 30s;
EOF

nginx -t
systemctl reload nginx
sleep 2

# --- Provjera --------------------------------------------------------------
echo "[i] Provjera:"
systemctl is-active frostbite.service
curl -sk -o /dev/null -w "  Početna:      %{http_code}\n" "https://127.0.0.1/" -H "Host: $APP_IP"
curl -sk -o /dev/null -w "  Ruta (SPA):   %{http_code}\n" "https://127.0.0.1/ture" -H "Host: $APP_IP"
curl -sk -o /dev/null -w "  API:          %{http_code}\n" "https://127.0.0.1/api/tours/" -H "Host: $APP_IP"
curl -sk -o /dev/null -w "  Stara adresa: %{http_code} (očekivano 301)\n" "https://127.0.0.1/nalog/prijava/" -H "Host: $APP_IP"
curl -sk -o /dev/null -w "  Lažni Host:   %{http_code} (očekivano 400)\n" "https://127.0.0.1/api/tours/" -H "Host: zlo.example"
echo
echo "[OK] Aplikacija je postavljena: https://$APP_IP"
echo "     Sistemski admin (samo prvi put): sudo frostbite-manage create_system_admin"
