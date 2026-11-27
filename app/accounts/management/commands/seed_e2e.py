"""Podaci za E2E testove (frontend/e2e/). Radi SAMO u izolovanom E2E okruženju.

    FROSTBITE_E2E=1 python manage.py seed_e2e

Pokreće ga docker/e2e.sh nad zasebnim Docker stackom (projekat frostbite-e2e, baza frostbite_e2e,
koja se prije svakog pokretanja briše). Odbija da radi:
  - bez varijable FROSTBITE_E2E=1 (na serverima je nikad nema);
  - ako baza nije E2E baza (ime PostgreSQL baze mora završavati na _e2e);
  - ako baza već ima korisnike.
Za razliku od seed_demo, radi i s produkcijskim postavkama (Nginx, HTTPS, __Host- kolačići),
jer E2E testovi trebaju provjeriti upravo njih.
"""
import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from accounts.demo import DEMO_PASSWORD, create_demo_data
from accounts.models import User

# Nalozi koje mijenjaju "destruktivni" testovi (zaključavanje, odjava, promjena lozinke, blokada),
# da ne pokvare sesije demo naloga koje dijele ostali testovi.
E2E_USERS = [
    ('e2e-zakljucavanje@primjer.ba', 'Zaključani'),
    ('e2e-sesija@primjer.ba', 'Sesija'),
    ('e2e-lozinka@primjer.ba', 'Lozinka'),
    ('e2e-blokada@primjer.ba', 'Blokada'),
    ('e2e-bedz@primjer.ba', 'Bedž'),
]


def is_e2e_database():
    db = settings.DATABASES['default']
    if db['ENGINE'] == 'django.db.backends.sqlite3':
        return str(db['NAME']).endswith('e2e.sqlite3')
    return str(db['NAME']).endswith('_e2e')


class Command(BaseCommand):
    help = 'Ubacuje podatke za E2E testove (samo izolovano E2E okruženje).'

    def handle(self, *args, **opts):
        if os.environ.get('FROSTBITE_E2E') != '1':
            raise CommandError('seed_e2e radi samo uz FROSTBITE_E2E=1 (izolovano E2E okruženje).')
        if not is_e2e_database():
            raise CommandError('seed_e2e radi samo nad E2E bazom (ime baze mora završavati na _e2e).')
        if User.objects.exists():
            raise CommandError('Baza već ima korisnike. E2E stack se pokreće s praznom bazom (docker/e2e.sh).')
        create_demo_data()
        for email, first in E2E_USERS:
            User.objects.create_user(email, DEMO_PASSWORD, first_name=first, last_name='E2E')
        call_command('badges_backfill', stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS('E2E podaci ubačeni.'))
