# Frostbite backend: Django + Gunicorn.
# Kontejner radi kao ne-root korisnik, kod je samo za čitanje (vidi docker-compose.yml: read_only).
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Ovisnosti u zasebnom sloju (brži ponovni build kad se mijenja samo kod)
COPY requirements.txt .
RUN pip install -r requirements.txt

RUN groupadd --system frostbite && useradd --system --gid frostbite --no-create-home frostbite

# Kod pripada rootu; aplikacija ga može samo čitati
COPY --chmod=755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY . .
RUN python -m compileall -q . && chmod -R a+rX,go-w /app

USER frostbite
EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["gunicorn", "frostbite.wsgi:application", \
     "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "30", \
     "--worker-tmp-dir", "/dev/shm", "--no-control-socket", \
     "--access-logfile", "-", "--error-logfile", "-"]
