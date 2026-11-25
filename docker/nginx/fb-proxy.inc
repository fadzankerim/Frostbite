proxy_pass http://frostbite_backend;
proxy_set_header Host $host;
proxy_set_header X-Forwarded-Proto https;
# Zaglavlja se POSTAVLJAJU (ne dodaju), pa ih klijent ne može podmetnuti.
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $remote_addr;
proxy_redirect off;
proxy_read_timeout 30s;
