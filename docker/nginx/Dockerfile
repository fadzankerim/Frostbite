# Frostbite web: Nginx terminira TLS, servira React aplikaciju i prosljeđuje /api/ backendu.
# Build context je korijen repozitorija.

# --- 1. React build ----------------------------------------------------------
FROM node:24-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json frontend/.npmrc ./
# npm ci: tačno ono što je u lockfile-u; bez install skripti paketa (.npmrc: ignore-scripts)
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY frontend/ ./
# build uključuje tsc, eslint (sigurnosna pravila) i provjeru dizajna; pada ako nešto nije u redu
RUN npm run build

# --- 2. Nginx ------------------------------------------------------------------
FROM nginx:1.29-alpine

RUN apk add --no-cache openssl \
 && rm -f /etc/nginx/conf.d/default.conf

COPY docker/nginx/default.conf /etc/nginx/conf.d/frostbite.conf
COPY docker/nginx/fb-proxy.inc /etc/nginx/conf.d/fb-proxy.inc
COPY --chmod=755 docker/nginx/10-self-signed-cert.sh /docker-entrypoint.d/10-self-signed-cert.sh
COPY --from=frontend /build/dist /srv/web
