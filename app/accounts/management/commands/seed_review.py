"""Nalozi i testni podaci za recenzente (politika 5.2). Pokreće se JEDNOM na serveru, nad bazom bez
korisničkih podataka (dozvoljeni su samo već kreirani sistemski admini):

    sudo frostbite-manage seed_review --potvrdi

Ispisuje email, ulogu i lozinku svakog naloga. Lozinke su nasumične i nigdje se ne čuvaju (u bazi je
samo hash), pa ispis odmah sačuvajte na sigurno mjesto van servera i predajte recenzentima.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from accounts.review import ACCOUNTS, email_for, create_review_data
from audit.log import audit
from clubs.models import Club


class Command(BaseCommand):
    help = 'Kreira naloge i testne podatke za recenzente (jednom, nad praznom bazom).'

    def add_arguments(self, parser):
        parser.add_argument('--potvrdi', action='store_true',
                            help='Potvrda da se podaci kreiraju (bez nje komanda ništa ne radi).')

    def handle(self, *args, **opts):
        if not opts['potvrdi']:
            raise CommandError('Dodajte --potvrdi. Komanda kreira naloge i testne podatke za recenzente.')
        if User.objects.filter(is_system_admin=False).exists() or Club.objects.exists():
            raise CommandError('Baza već ima korisnike ili društva. seed_review radi samo nad praznom bazom '
                               '(dozvoljeni su samo ranije kreirani sistemski admini).')
        taken = User.objects.filter(email__in=[email_for(a[0]) for a in ACCOUNTS])
        if taken.exists():
            raise CommandError(f'Nalog već postoji: {taken.first().email}')

        rows = create_review_data()
        audit(None, 'RECENZENTI_KREIRANI', 'user', '', details=f'nalozi={len(rows)}')
        call_command('badges_backfill', stdout=self.stdout)

        width = max(len(e) for e, _, _ in rows)
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Lozinke se prikazuju SAMO SADA i nigdje se ne čuvaju. '
                                             'Sačuvajte ih van servera.'))
        self.stdout.write('')
        self.stdout.write(f'{"Email":<{width}}  {"Lozinka":<20}  Uloga')
        for email, role, pw in rows:
            self.stdout.write(f'{email:<{width}}  {pw:<20}  {role}')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Kreirano naloga: {len(rows)}. Društva: PD Alfa (test), PD Beta (test); '
                                             'PD Gama (test) čeka odobrenje.'))
