#!/bin/sh
# Ako certifikat nije postavljen (volume /etc/nginx/certs), generiše se samopotpisani.
# Za pravi certifikat: stavite fullchain.crt i privkey.key u ./certs i promijenite volume
# u docker-compose.yml na bind mount (./certs:/etc/nginx/certs:ro).
set -eu

CERT=/etc/nginx/certs/fullchain.crt
KEY=/etc/nginx/certs/privkey.key
CN="${TLS_CN:-localhost}"

if [ ! -s "$CERT" ] || [ ! -s "$KEY" ]; then
    echo "[cert] Nema certifikata, generišem samopotpisani za $CN"
    mkdir -p /etc/nginx/certs
    umask 077
    openssl req -x509 -newkey rsa:3072 -nodes -days 825 \
        -keyout "$KEY" -out "$CERT" -subj "/CN=$CN" \
        -addext "subjectAltName=DNS:$CN,DNS:localhost,IP:127.0.0.1" 2>/dev/null
fi
