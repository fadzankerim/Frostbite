#!/bin/sh
# Pokretanje backend kontejnera: provjera produkcijskih postavki, migracije, čišćenje
# isteklih sesija, zatim Gunicorn (ili komanda proslijeđena kontejneru).
set -eu

if [ "${1:-}" = "gunicorn" ]; then
    python manage.py check --deploy --fail-level ERROR
    python manage.py migrate --noinput
    python manage.py clearsessions
fi

exec "$@"
