#!/usr/bin/env bash
# E2E testovi u pregledaču (Playwright) nad Docker stackom s produkcijskim postavkama.
#
#   ./docker/e2e.sh                     # svi testovi
#   ./docker/e2e.sh e2e/security.spec.ts   # dodatni argumenti idu Playwrightu
#   E2E_KEEP=1 ./docker/e2e.sh          # stack ostaje upaljen nakon testova (https://localhost:8443)
#
# Tajne ovdje su namjerno lažne i važe samo za ovaj izolovani stack (baza se briše svaki put).
set -euo pipefail
cd "$(dirname "$0")/.."

export COMPOSE_PROJECT_NAME=frostbite-e2e
export DB_NAME=frostbite_e2e DB_USER=frostbite DB_PASSWORD=e2e-samo-za-testove
export DJANGO_SECRET_KEY="e2e-$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')"
# localhost:8443 je potreban samo za CSRF_TRUSTED_ORIGINS (pregledač šalje Origin s portom)
export DJANGO_ALLOWED_HOSTS=localhost,localhost:8443 TLS_CN=localhost
compose() { docker compose -f docker-compose.yml -f docker-compose.e2e.yml "$@"; }

echo '--- E2E: prazna baza i novi build'
compose down -v --remove-orphans >/dev/null 2>&1 || true
compose up -d --build

echo '--- E2E: čekam aplikaciju'
for _ in $(seq 1 60); do
  if curl -ksf -o /dev/null https://localhost:8443/api/auth/csrf/; then break; fi
  sleep 2
done
curl -ksf -o /dev/null https://localhost:8443/api/auth/csrf/ || { compose logs --tail=50; exit 1; }

echo '--- E2E: podaci'
compose exec -T -e FROSTBITE_E2E=1 backend python manage.py seed_e2e

echo '--- E2E: testovi'
set +e
(cd frontend && E2E_BASE_URL=https://localhost:8443 npx playwright test "$@")
status=$?
set -e

if [ "${E2E_KEEP:-0}" = 1 ]; then
  echo "Stack ostaje upaljen: https://localhost:8443  (gašenje: COMPOSE_PROJECT_NAME=frostbite-e2e docker compose -f docker-compose.yml -f docker-compose.e2e.yml down -v)"
else
  compose down -v --remove-orphans >/dev/null
fi
exit $status
