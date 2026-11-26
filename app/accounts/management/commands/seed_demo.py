"""Demo podaci za LOKALNI razvoj. U produkciji odbija da se pokrene.

    .venv/bin/python manage.py seed_demo
"""
from datetime import timedelta

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from clubs.models import Club, ClubAdmin, ClubGuide, ClubMembership
from audit.models import AuditLog
from tours.models import Tour, TourGuide, TourRegistration, TourReport

DEMO_PASSWORD = 'Demo-Lozinka-2026'

# Približne trase (demo), tačke su [geografska širina, geografska dužina].
ROUTES = {
    'bjelasnica': [[43.7238, 18.2841], [43.7206, 18.2802], [43.7171, 18.2761], [43.7138, 18.2722],
                   [43.7112, 18.2679], [43.7091, 18.2628], [43.7077, 18.2590], [43.7068, 18.2566]],
    'treskavica': [[43.6262, 18.4289], [43.6188, 18.4207], [43.6113, 18.4121], [43.6052, 18.4038],
                   [43.5991, 18.3960], [43.5938, 18.3887], [43.5889, 18.3811], [43.5856, 18.3748]],
    'igman': [[43.7524, 18.2617], [43.7571, 18.2659], [43.7622, 18.2702], [43.7668, 18.2741],
              [43.7709, 18.2783], [43.7662, 18.2830], [43.7604, 18.2788], [43.7551, 18.2700], [43.7524, 18.2617]],
    'prenj': [[43.4612, 17.9151], [43.4724, 17.9122], [43.4851, 17.9083], [43.4977, 17.9041],
              [43.5089, 17.9007], [43.5181, 17.8978], [43.5262, 17.8955], [43.5309, 17.8946]],
    'cvrsnica': [[43.6190, 17.5550], [43.6129, 17.5571], [43.6064, 17.5589], [43.6003, 17.5598],
                 [43.5948, 17.5601], [43.5902, 17.5598], [43.5869, 17.5594]],
}


class Command(BaseCommand):
    help = 'Ubacuje demo podatke (samo lokalno).'

    def handle(self, *args, **opts):
        if settings.PRODUCTION or settings.DATABASES['default']['ENGINE'] != 'django.db.backends.sqlite3':
            raise CommandError('seed_demo je samo za lokalni razvoj (SQLite).')
        if User.objects.exists():
            raise CommandError('Baza već ima korisnike. Obrišite app/dev.sqlite3 i pokrenite migrate ponovo.')

        with transaction.atomic():
            def user(email, first, last, **kw):
                return User.objects.create_user(email, DEMO_PASSWORD, first_name=first, last_name=last, **kw)

            User.objects.create_system_admin('sysadmin@frostbite.ba', DEMO_PASSWORD, first_name='Sistemski', last_name='Admin')
            a1 = user('admin@pd-bjelasnica.ba', 'Amra', 'Admin')
            a2 = user('admin@pd-prenj.ba', 'Edin', 'Admin')
            g1 = user('vodic1@pd-bjelasnica.ba', 'Vedad', 'Vodič', phone='061 111 111')
            g2 = user('vodic@pd-prenj.ba', 'Lejla', 'Vodič', phone='062 222 222')
            h1 = user('planinar1@primjer.ba', 'Dževad', 'Planinar', phone='063 333 333',
                      emergency_contact_name='Mika Planinar', emergency_contact_phone='063 444 444',
                      health_notes='Alergija na ubode pčela.')
            h2 = user('planinar2@primjer.ba', 'Kerim', 'Planinar')

            c1 = Club.objects.create(name='PD Bjelašnica', city='Sarajevo', status=Club.Status.APPROVED, created_by=a1,
                                     description='Planinarsko društvo sa tradicijom od 1950.')
            c2 = Club.objects.create(name='PD Prenj', city='Konjic', status=Club.Status.APPROVED, created_by=a2,
                                     description='Ture po Prenju, Čvrsnici i Čabulji.')
            Club.objects.create(name='PD Na čekanju', city='Tuzla', created_by=h2)
            ClubAdmin.objects.create(club=c1, user=a1)
            ClubAdmin.objects.create(club=c2, user=a2)
            ClubGuide.objects.create(club=c1, user=g1, license_number='VOD-001')
            ClubGuide.objects.create(club=c2, user=g2, license_number='VOD-002')
            ClubMembership.objects.create(club=c1, user=h1, status=ClubMembership.Status.APPROVED,
                                          valid_until=timezone.localdate().replace(month=12, day=31))

            now = timezone.now().replace(minute=0, second=0, microsecond=0)

            def tour(club, name, days, diff, km, elev, maxp, **kw):
                start = (now + timedelta(days=days)).replace(hour=7)
                return Tour.objects.create(
                    club=club, name=name, start_at=start, registration_deadline=start - timedelta(days=1),
                    meeting_point=kw.pop('meeting', 'Parking ispred Doma'), difficulty=diff, length_km=km,
                    elevation_gain_m=elev, duration_h=kw.pop('hours', 6), max_participants=maxp,
                    status=kw.pop('status', Tour.Status.PUBLISHED), created_by=club.admins.first().user, **kw)

            t1 = tour(c1, 'Bjelašnica: Opservatorija', 6, Tour.Difficulty.MEDIUM, 14, 900, 15, region='Bjelašnica',
                      route=ROUTES['bjelasnica'],
                      price=10, required_equipment='Planinarske cipele, štapovi, 2 l vode.')
            tour(c1, 'Treskavica: Pakleni zub', 13, Tour.Difficulty.HARD, 18, 1300, 10, region='Treskavica', members_only=True,
                 route=ROUTES['treskavica'])
            tour(c1, 'Igman zimska šetnja', 20, Tour.Difficulty.EASY, 8, 300, 25, region='Igman', route=ROUTES['igman'])
            tour(c1, 'Nacrt: Visočica', 25, Tour.Difficulty.MEDIUM, 12, 700, 12, status=Tour.Status.DRAFT)
            t2 = tour(c2, 'Prenj: Zelena glava', 9, Tour.Difficulty.VERY_HARD, 22, 1700, 8, region='Prenj', hours=10,
                      meeting='Konjic, autobuska stanica', route=ROUTES['prenj'])
            tour(c2, 'Čvrsnica: Pločno', 16, Tour.Difficulty.HARD, 19, 1400, 12, region='Čvrsnica', route=ROUTES['cvrsnica'])

            TourGuide.objects.create(tour=t1, user=g1, status=TourGuide.Status.APPROVED)
            TourGuide.objects.create(tour=t2, user=g2, status=TourGuide.Status.APPROVED)
            TourRegistration.objects.create(tour=t1, user=h1)
            TourRegistration.objects.create(tour=t1, user=h2)
            TourRegistration.objects.create(tour=t2, user=h1)

            # za isprobavanje panela: jučerašnja tura (prisustvo, izvještaj), zahtjevi na čekanju
            y = (now - timedelta(days=1)).replace(hour=7)
            past = Tour.objects.create(
                club=c1, name='Trebević: jutarnja tura', start_at=y, registration_deadline=y - timedelta(days=1),
                meeting_point='Žičara Trebević', difficulty=Tour.Difficulty.EASY, length_km=9, elevation_gain_m=550,
                duration_h=4, max_participants=20, status=Tour.Status.CLOSED, created_by=a1, region='Trebević',
                route=[[43.8513, 18.4423], [43.8461, 18.4502], [43.8410, 18.4578], [43.8378, 18.4651], [43.8366, 18.4719]])
            TourGuide.objects.create(tour=past, user=g1, status=TourGuide.Status.APPROVED)
            TourRegistration.objects.create(tour=past, user=h1)
            TourRegistration.objects.create(tour=past, user=h2)
            igman = Tour.objects.get(name='Igman zimska šetnja')
            TourGuide.objects.create(tour=igman, user=g1)                     # čeka odobrenje admina
            ClubMembership.objects.create(club=c1, user=h2)                    # zahtjev za članstvo

            # historija za analitiku: održane ture u prethodnim mjesecima, sa prisustvom i izvještajem
            extra = [user(f'planinar{i}@primjer.ba', ime, 'Demo') for i, ime in
                     enumerate(['Amar', 'Lana', 'Edin', 'Sara', 'Haris', 'Nina', 'Tarik', 'Ema'], start=3)]
            people = [h1, h2] + extra
            history = [(c1, 'Jahorina: Ogorjelica', 25, 15, 9, Tour.Difficulty.MEDIUM),
                       (c1, 'Visočica: Džamija', 55, 10, 7, Tour.Difficulty.MEDIUM),
                       (c1, 'Trebević: Pećine', 85, 0, 10, Tour.Difficulty.EASY),
                       (c1, 'Bjelašnica: Hranisava', 120, 20, 6, Tour.Difficulty.HARD),
                       (c1, 'Igman: Veliko polje', 150, 5, 8, Tour.Difficulty.EASY),
                       (c2, 'Prenj: Otiš', 40, 25, 5, Tour.Difficulty.VERY_HARD)]
            for club, name, ago, price, n, diff in history:
                start = (now - timedelta(days=ago)).replace(hour=7)
                t = Tour.objects.create(club=club, name=name, start_at=start, registration_deadline=start - timedelta(days=1),
                                        meeting_point='Parking', difficulty=diff, length_km=12, elevation_gain_m=800,
                                        duration_h=6, max_participants=12, price=price, status=Tour.Status.DONE,
                                        created_by=club.admins.first().user)
                guide = g1 if club == c1 else g2
                TourGuide.objects.create(tour=t, user=guide, status=TourGuide.Status.APPROVED)
                for i, person in enumerate(people[:n + 1]):
                    TourRegistration.objects.create(
                        tour=t, user=person, attendance=(TourRegistration.Attendance.ABSENT if i == n
                                                         else TourRegistration.Attendance.PRESENT))
                TourReport.objects.create(tour=t, guide=guide, text='Tura je protekla bez poteškoća.', attendees_count=n)

            # demo zapisi prijava (samo lokalno, za grafikon sistemskog admina)
            import random
            rng = random.Random(7)
            for d in range(14):
                day = timezone.now() - timedelta(days=d)
                for _ in range(rng.randint(2, 9)):
                    AuditLog.objects.create(user=rng.choice(people), action='LOGIN_USPJEH', entity='user', details='demo', created_at=day)
                for _ in range(rng.randint(0, 3)):
                    AuditLog.objects.create(action='LOGIN_NEUSPJEH', entity='user', details='demo', created_at=day)

        call_command('badges_backfill', stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS(f'Demo podaci ubačeni. Lozinka za sve naloge: {DEMO_PASSWORD}'))
        for e in ['sysadmin@frostbite.ba', 'admin@pd-bjelasnica.ba', 'admin@pd-prenj.ba', 'vodic1@pd-bjelasnica.ba',
                  'vodic@pd-prenj.ba', 'planinar1@primjer.ba', 'planinar2@primjer.ba']:
            self.stdout.write(f'  {e}')
