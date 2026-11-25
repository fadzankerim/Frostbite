# Frostbite web: Nginx terminira TLS, servira statičke datoteke i prosljeđuje ostalo backendu.
# Build context je korijen repozitorija (vidi docker-compose.yml).
FROM nginx:1.29-alpine

RUN apk add --no-cache openssl \
 && rm -f /etc/nginx/conf.d/default.conf

COPY docker/nginx/default.conf /etc/nginx/conf.d/frostbite.conf
COPY docker/nginx/fb-proxy.inc /etc/nginx/conf.d/fb-proxy.inc
COPY --chmod=755 docker/nginx/10-self-signed-cert.sh /docker-entrypoint.d/10-self-signed-cert.sh

# Projekat koristi zadani StaticFilesStorage i nema statičkih datoteka iz drugih aplikacija,
# pa je rezultat collectstatic identičan folderu app/static. Ako se uvede ManifestStaticFilesStorage,
# ovdje treba dodati build korak sa collectstatic.
COPY app/static /srv/static
