proxy_pass http://frostbite_backend;
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
