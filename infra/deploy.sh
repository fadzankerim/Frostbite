#!/usr/bin/env bash
# Frostbite - postavljanje aplikacije sa vašeg računara na fb-app.
#   ./infra/deploy.sh            (pokrenuti iz foldera projekta ili bilo gdje)
#
# 1. pokrene testove lokalno (ako padnu, ništa se ne postavlja)
# 2. kopira kod na server (rsync preko SSH jump hosta)
# 3. pokrene 04-deploy-app.sh na serveru
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_IP="${APP_IP:-10.0.143.199}"
HOST="${HOST:-fb-app}"

echo "[1/3] Testovi..."
(cd "$ROOT/app" && .venv/bin/python manage.py test --verbosity 0)

echo "[2/3] Kopiranje koda na $HOST..."
rsync -az --delete \
  --exclude '.venv' --exclude '__pycache__' --exclude '*.pyc' --exclude 'dev.sqlite3' --exclude 'staticfiles' \
  "$ROOT/app/" "$HOST:frostbite-src/"
scp -q "$ROOT/infra/app/04-deploy-app.sh" "$HOST:"

echo "[3/3] Postavljanje na serveru..."
ssh "$HOST" "chmod +x 04-deploy-app.sh && sudo ./04-deploy-app.sh ~/frostbite-src $APP_IP"
