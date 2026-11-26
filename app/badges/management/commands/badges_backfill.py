"""Dodjeljuje bedževe za postojeću istoriju. Pokreće se jednom nakon migracije (idempotentno):

    manage.py badges_backfill            (na serveru: frostbite-manage badges_backfill)
"""
from django.core.management.base import BaseCommand

from accounts.models import User
from badges.services import evaluate


class Command(BaseCommand):
    help = 'Dodjeljuje bedževe na osnovu postojećih podataka.'

    def handle(self, *args, **opts):
        total = 0
        for user in User.objects.filter(is_active=True).iterator():
            total += len(evaluate(user))
        self.stdout.write(self.style.SUCCESS(f'Dodijeljeno novih bedževa: {total}'))
