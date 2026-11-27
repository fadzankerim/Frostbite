"""Demo podaci za LOKALNI razvoj. U produkciji odbija da se pokrene.

    .venv/bin/python manage.py seed_demo
"""
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from accounts.demo import DEMO_EMAILS, DEMO_PASSWORD, create_demo_data
from accounts.models import User


class Command(BaseCommand):
    help = 'Ubacuje demo podatke (samo lokalno).'

    def handle(self, *args, **opts):
        if settings.PRODUCTION or settings.DATABASES['default']['ENGINE'] != 'django.db.backends.sqlite3':
            raise CommandError('seed_demo je samo za lokalni razvoj (SQLite).')
        if User.objects.exists():
            raise CommandError('Baza već ima korisnike. Obrišite app/dev.sqlite3 i pokrenite migrate ponovo.')
        create_demo_data()
        call_command('badges_backfill', stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS(f'Demo podaci ubačeni. Lozinka za sve naloge: {DEMO_PASSWORD}'))
        for e in DEMO_EMAILS:
            self.stdout.write(f'  {e}')
