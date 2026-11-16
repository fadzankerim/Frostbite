#!/usr/bin/env bash
# Frostbite - Nginx sa HTTPS-om.
#   sudo ./03-nginx-https.sh <privatna-IP-ove-instance>
#
# - self-signed certifikat izdat na privatnu IP adresu (aplikacija se otvara preko IP-a kroz VPN)
# - samo TLS 1.2 i 1.3, moderne šifre
# - HTTP se preusmjerava na HTTPS
# - sigurnosna HTTP zaglavlja, sakrivena verzija Nginx-a
# - privremena stranica "u izradi" dok se ne postavi Django aplikacija
set -euo pipefail

APP_IP="${1:?Upotreba: sudo $0 <privatna-IP-ove-instance>}"
CERT=/etc/ssl/certs/frostbite.crt
KEY=/etc/ssl/private/frostbite.key
WEBROOT=/var/www/fb-placeholder

[[ $EUID -eq 0 ]] || { echo "Pokrenite sa sudo."; exit 1; }
if [[ -d /etc/openvpn/server ]] || systemctl is-active --quiet openvpn-server@server 2>/dev/null; then
  echo "[!] Ovo je VPN server ($(hostname -I | awk '{print $1}')). Skripta je namijenjena instanci fb-app - provjerite HostName za fb-app u ~/.ssh/config."
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get install -y -qq nginx openssl >/dev/null

if [[ ! -f $CERT ]]; then
  openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -days 365 \
    -keyout "$KEY" -out "$CERT" \
    -subj "/C=BA/O=Frostbite/CN=$APP_IP" \
    -addext "subjectAltName=IP:$APP_IP" \
    -addext "keyUsage=digitalSignature" \
    -addext "extendedKeyUsage=serverAuth"
  chmod 600 "$KEY"
  echo "[i] Kreiran certifikat za IP $APP_IP (važi 365 dana)."
fi

install -d -m 755 "$WEBROOT"
cat > "$WEBROOT/index.html" <<'EOF'
<!DOCTYPE html>
<html lang="bs"><head><meta charset="utf-8"><title>Frostbite</title></head>
<body><h1>Frostbite</h1><p>Aplikacija je u izradi.</p></body></html>
EOF

# server_tokens: novije verzije Nginx-a ga već postavljaju u nginx.conf (npr. "build"),
# pa se mijenja na mjestu da ne bi bio duplikat.
if grep -qE '^\s*#?\s*server_tokens\s' /etc/nginx/nginx.conf; then
  sed -i -E 's/^(\s*)#?\s*server_tokens\s+[^;]+;.*/\1server_tokens off;/' /etc/nginx/nginx.conf
else
  sed -i -E 's/^(\s*)http\s*\{/&\n\1\tserver_tokens off;/' /etc/nginx/nginx.conf
fi

cat > /etc/nginx/conf.d/00-fb-hardening.conf <<'EOF'
client_max_body_size 1m;
client_body_timeout 15s;
client_header_timeout 15s;
EOF

cat > /etc/nginx/sites-available/frostbite <<EOF
# HTTP -> HTTPS. Koristi se \$server_addr umjesto \$host da se spriječi
# preusmjeravanje na adresu iz zaglavlja Host koje kontroliše klijent.
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

    # Skriveni fajlovi (.git, .env ...) nikad se ne serviraju
    location ~ /\. { deny all; return 404; }

    # Privremeno: statična stranica. Kad se postavi Django, ovaj blok se
    # zamjenjuje proxy_pass prema Gunicorn socketu.
    root $WEBROOT;
    index index.html;
    location / {
        try_files \$uri \$uri/ =404;
    }
}
EOF

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/frostbite /etc/nginx/sites-enabled/frostbite
nginx -t
systemctl enable nginx >/dev/null
systemctl reload nginx || systemctl restart nginx
sleep 2   # reload je asinhron; sačekati prije provjere

echo "[i] Provjera:"
curl -sk -o /dev/null -w "  HTTPS: %{http_code}\n" "https://127.0.0.1/"
curl -s  -o /dev/null -w "  HTTP:  %{http_code} -> %{redirect_url}\n" "http://127.0.0.1/"

echo
echo "[OK] Nginx sa HTTPS-om radi. Spojite se na VPN i otvorite https://$APP_IP"
echo "     Otisak certifikata (za provjeru u pregledniku):"
openssl x509 -in "$CERT" -noout -fingerprint -sha256
