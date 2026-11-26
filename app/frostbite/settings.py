"""
Postavke aplikacije Frostbite.

Sve tajne i postavke okruženja dolaze iz varijabli okruženja.
U produkciji ih učitava systemd iz /etc/frostbite/app.env i /etc/frostbite/db.env.
Bez tih varijabli aplikacija radi u razvojnom režimu (SQLite, DEBUG).
"""
import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

PRODUCTION = os.environ.get('FROSTBITE_ENV') == 'production'


def env(name, default=None, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        raise ImproperlyConfigured(f'Nedostaje varijabla okruženja {name}')
    return value


# --- Osnovno ---------------------------------------------------------------
if PRODUCTION:
    SECRET_KEY = env('DJANGO_SECRET_KEY', required=True)
    DEBUG = False
    ALLOWED_HOSTS = [h.strip() for h in env('DJANGO_ALLOWED_HOSTS', required=True).split(',') if h.strip()]
else:
    SECRET_KEY = env('DJANGO_SECRET_KEY', 'dev-samo-lokalno-nikad-u-produkciji')
    DEBUG = env('DJANGO_DEBUG', '1') == '1'
    ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'testserver']

INSTALLED_APPS = [
    # django.contrib.admin namjerno NIJE uključen (manja površina napada).
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'rest_framework',
    'accounts',
    'clubs',
    'tours',
    'audit',
    'panel',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'frostbite.urls'

# Bez HTML predložaka: Django služi samo JSON API. (Prazna konfiguracija ostaje jer je
# koriste ugrađene greške i DRF.)
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {'context_processors': []},
    },
]

WSGI_APPLICATION = 'frostbite.wsgi.application'

# --- Baza podataka ---------------------------------------------------------
if env('DB_NAME'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('DB_NAME'),
            'USER': env('DB_USER', required=True),
            'PASSWORD': env('DB_PASSWORD', required=True),
            'HOST': env('DB_HOST', '127.0.0.1'),
            'PORT': env('DB_PORT', '5432'),
            'CONN_MAX_AGE': 60,
            'OPTIONS': {'connect_timeout': 5},
        }
    }
elif PRODUCTION:
    raise ImproperlyConfigured('U produkciji je obavezna PostgreSQL baza (DB_NAME).')
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'dev.sqlite3'}}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Autentikacija ---------------------------------------------------------
AUTH_USER_MODEL = 'accounts.User'
AUTHENTICATION_BACKENDS = ['accounts.backends.LockoutEmailBackend']

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
     'OPTIONS': {'user_attributes': ('email', 'first_name', 'last_name')}},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Testovi: brzo heširanje (samo za 'manage.py test', nikad u produkciji)
if 'test' in sys.argv[1:2] and not PRODUCTION:
    PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# Zaključavanje naloga (politika 4.6): 5 neuspješnih pokušaja -> 15 minuta.
# Vezano za NALOG, ne za IP: svi recenzenti dolaze sa iste IP adrese (VPN NAT).
LOCKOUT_MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

# --- Sesije i kolačići -----------------------------------------------------
SESSION_COOKIE_AGE = 30 * 60            # 30 minuta neaktivnosti
SESSION_SAVE_EVERY_REQUEST = True       # svaki zahtjev produžava sesiju
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_FAILURE_VIEW = 'frostbite.views.csrf_failure'

if PRODUCTION:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # __Host- prefiks: kolačić važi samo za ovaj host, samo preko HTTPS-a, path=/
    SESSION_COOKIE_NAME = '__Host-sessionid'
    CSRF_COOKIE_NAME = '__Host-csrftoken'
    CSRF_TRUSTED_ORIGINS = [f'https://{h}' for h in ALLOWED_HOSTS]
    # Nginx terminira TLS i postavlja X-Forwarded-Proto
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HSTS, CSP i ostala zaglavlja postavlja Nginx; ovdje samo ono što Django dodaje sam.
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

DATA_UPLOAD_MAX_MEMORY_SIZE = 256 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 200
FILE_UPLOAD_MAX_MEMORY_SIZE = 0          # aplikacija ne prima datoteke

# --- JSON API (/api/) -------------------------------------------------------
# Samo sesija (bez tokena), samo JSON (bez "browsable API" stranica), zabranjeno po defaultu.
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['frostbite.authentication.StrictSessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_PARSER_CLASSES': ['rest_framework.parsers.JSONParser'],
}

# --- Lokalizacija ----------------------------------------------------------
LANGUAGE_CODE = 'bs'
LANGUAGES = [('bs', 'Bosanski')]
TIME_ZONE = 'Europe/Sarajevo'
USE_I18N = True
USE_TZ = True

# --- Logovanje -------------------------------------------------------------
LOG_DIR = env('DJANGO_LOG_DIR')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'std': {'format': '{asctime} {levelname} {name} {message}', 'style': '{'}},
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'std'},
        **({'file': {'class': 'logging.handlers.RotatingFileHandler', 'formatter': 'std',
                     'filename': os.path.join(LOG_DIR, 'django.log'),
                     'maxBytes': 5 * 1024 * 1024, 'backupCount': 5}} if LOG_DIR else {}),
    },
    'root': {'handlers': ['console'] + (['file'] if LOG_DIR else []), 'level': 'INFO'},
    'loggers': {
        # neispravni Host zaglavlja ne pune log
        'django.security.DisallowedHost': {'handlers': [], 'propagate': False},
    },
}
