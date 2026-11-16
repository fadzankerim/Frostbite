"""Kreiranje naloga sistemskog admina. Jedini način - ne postoji kroz web aplikaciju (politika 4.2).

    sudo -u frostbite /opt/frostbite/venv/bin/python manage.py create_system_admin
"""
import getpass

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from audit.log import audit


class Command(BaseCommand):
    help = 'Kreira nalog sistemskog admina (interaktivno).'

    def handle(self, *args, **opts):
        email = input('Email: ').strip().lower()
        first = input('Ime: ').strip()
        last = input('Prezime: ').strip()
        if not (email and first and last):
            raise CommandError('Email, ime i prezime su obavezni.')
        if User.objects.filter(email=email).exists():
            raise CommandError('Nalog sa tim emailom već postoji.')
        pw = getpass.getpass('Lozinka: ')
        if pw != getpass.getpass('Ponovite lozinku: '):
            raise CommandError('Lozinke se ne podudaraju.')
        try:
            password_validation.validate_password(pw, User(email=email, first_name=first, last_name=last))
        except ValidationError as e:
            raise CommandError(' '.join(e.messages))
        user = User.objects.create_system_admin(email=email, password=pw, first_name=first, last_name=last)
        audit(None, 'SYSADMIN_KREIRAN', 'user', user.pk, user=user, details='manage.py')
        self.stdout.write(self.style.SUCCESS(f'Kreiran sistemski admin {email}.'))
