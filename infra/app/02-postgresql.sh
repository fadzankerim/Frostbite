#!/usr/bin/env bash
# Frostbite - instalacija i podešavanje PostgreSQL baze.
#   sudo ./02-postgresql.sh
#
# - PostgreSQL sluša samo na localhost (nije dostupan preko mreže)
# - lozinke se čuvaju kao SCRAM-SHA-256
# - aplikacijski korisnik baze nije superuser, ne može kreirati baze ni uloge
# - pristupni podaci se upisuju u /etc/frostbite/db.env (čitljivo samo root i aplikaciji)
set -euo pipefail

DB_NAME="frostbite"
DB_USER="fb_app"
ENV_FILE="/etc/frostbite/db.env"
APP_USER="frostbite"

[[ $EUID -eq 0 ]] || { echo "Pokrenite sa sudo."; exit 1; }
if [[ -d /etc/openvpn/server ]] || systemctl is-active --quiet openvpn-server@server 2>/dev/null; then
  echo "[!] Ovo je VPN server ($(hostname -I | awk '{print $1}')). Skripta je namijenjena instanci fb-app - provjerite HostName za fb-app u ~/.ssh/config."
  exit 1
fi
id "$APP_USER" >/dev/null 2>&1 || { echo "[!] Prvo pokrenite 01-osnova.sh"; exit 1; }

export DEBIAN_FRONTEND=noninteractive
apt-get install -y -qq postgresql >/dev/null

PG_VER=$(ls /etc/postgresql | sort -V | tail -1)
CONF_DIR="/etc/postgresql/$PG_VER/main"
echo "[i] PostgreSQL verzija: $PG_VER"

cat > "$CONF_DIR/conf.d/99-fb.conf" <<'EOF'
listen_addresses = 'localhost'
password_encryption = 'scram-sha-256'
log_connections = on
log_disconnections = on
log_line_prefix = '%m [%p] %u@%d %r '
EOF

# pg_hba: samo lokalne konekcije
cp -n "$CONF_DIR/pg_hba.conf" "$CONF_DIR/pg_hba.conf.orig" || true
cat > "$CONF_DIR/pg_hba.conf" <<EOF
# TYPE  DATABASE        USER            ADDRESS          METHOD
local   all             postgres                         peer
local   $DB_NAME        $DB_USER                         scram-sha-256
host    $DB_NAME        $DB_USER        127.0.0.1/32     scram-sha-256
host    $DB_NAME        $DB_USER        ::1/128          scram-sha-256
EOF
chmod 640 "$CONF_DIR/pg_hba.conf"

systemctl restart postgresql

if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
  echo "[i] Korisnik $DB_USER već postoji - lozinka i $ENV_FILE se ne mijenjaju."
else
  DB_PASS=$(openssl rand -base64 36 | tr -dc 'A-Za-z0-9' | head -c 40)
  sudo -u postgres psql -v ON_ERROR_STOP=1 -q <<SQL
CREATE ROLE $DB_USER LOGIN PASSWORD '$DB_PASS'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION CONNECTION LIMIT 20;
CREATE DATABASE $DB_NAME OWNER $DB_USER ENCODING 'UTF8' TEMPLATE template0;
REVOKE ALL ON DATABASE $DB_NAME FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE $DB_NAME TO $DB_USER;
SQL
  sudo -u postgres psql -v ON_ERROR_STOP=1 -q -d "$DB_NAME" <<SQL
REVOKE ALL ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO $DB_USER;
SQL
  umask 027
  cat > "$ENV_FILE" <<EOF
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASS
DB_HOST=127.0.0.1
DB_PORT=5432
EOF
  chown root:"$APP_USER" "$ENV_FILE"
  chmod 640 "$ENV_FILE"
  echo "[i] Kreirani baza $DB_NAME i korisnik $DB_USER. Pristupni podaci: $ENV_FILE"
fi

echo "[i] Provjera da baza ne sluša na mreži:"
ss -ltnp | grep 5432

echo
echo "[OK] PostgreSQL podešen. Tabele kreira aplikacija (Django migracije) u sljedećoj fazi."
echo "     Sljedeće: sudo ./03-nginx-https.sh <privatna-IP-ove-instance>"
