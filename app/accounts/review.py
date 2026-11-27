"""Nalozi i testni podaci za recenzente (politika, poglavlje 5.2).

Politika obećava najmanje: jednog sistemskog admina, dva admina dva različita društva, po dva vodiča
u svakom društvu, tri planinara i ture u svim statusima. Svaki nalog dobija vlastitu jaku nasumičnu
lozinku; lozinke se vraćaju samo pozivaocu (komanda ih ispiše jednom) i nigdje se ne čuvaju.

Imena društava i email adrese su namjerno izmišljeni (domen .test je rezervisan za testiranje),
da se ne mogu zamijeniti sa stvarnim društvima ili osobama.
"""
import secrets
from datetime import date, timedelta

from django.contrib.auth import password_validation
from django.db import transaction
from django.utils import timezone

from clubs.models import Club, ClubAdmin, ClubGuide, ClubMembership
from tours.models import Tour, TourGuide, TourRegistration, TourReport

from .demo import ROUTES
from .models import User

DOMAIN = 'frostbite.test'

# (email, ime, prezime, uloga za ispis, dodatna polja)
ACCOUNTS = [
    ('sistem', 'Sara', 'Sistem', 'sistemski admin', {}),
    ('admin.alfa', 'Adnan', 'Alfa', 'admin društva PD Alfa (test)', {}),
    ('admin.beta', 'Belma', 'Beta', 'admin društva PD Beta (test)', {}),
    ('vodic1.alfa', 'Vedran', 'Alfa', 'vodič, PD Alfa (test)', {'phone': '061 000 101'}),
    ('vodic2.alfa', 'Vesna', 'Alfa', 'vodič, PD Alfa (test)', {'phone': '061 000 102'}),
    ('vodic1.beta', 'Vahid', 'Beta', 'vodič, PD Beta (test)', {'phone': '061 000 201'}),
    ('vodic2.beta', 'Vildana', 'Beta', 'vodič, PD Beta (test)', {'phone': '061 000 202'}),
    ('planinar1', 'Petar', 'Planinar', 'planinar, član PD Alfa (test)', {
        'phone': '062 000 001', 'emergency_contact_name': 'Testni kontakt Jedan',
        'emergency_contact_phone': '062 100 001', 'health_notes': 'TESTNI PODATAK: alergija na penicilin.'}),
    ('planinar2', 'Lejla', 'Planinar', 'planinar, zahtjev za članstvo u PD Alfa (test) na čekanju', {
        'phone': '062 000 002', 'emergency_contact_name': 'Testni kontakt Dva',
        'emergency_contact_phone': '062 100 002', 'health_notes': 'TESTNI PODATAK: astma, nosi inhalator.'}),
    ('planinar3', 'Mirza', 'Planinar', 'planinar, član PD Beta (test), podnio zahtjev za PD Gama (test)', {
        'phone': '062 000 003', 'emergency_contact_name': 'Testni kontakt Tri',
        'emergency_contact_phone': '062 100 003'}),
]


def email_for(key):
    return f'{key}@{DOMAIN}'


def new_password(user):
    """Nasumična lozinka koja prolazi sva pravila politike (provjerava se istim validatorima)."""
    while True:
        pw = secrets.token_urlsafe(15)          # 20 znakova, ~120 bita
        try:
            password_validation.validate_password(pw, user)
            return pw
        except Exception:                       # praktično nemoguće; samo za svaki slučaj
            continue


@transaction.atomic
def create_review_data():
    """Kreira naloge i podatke. Vraća listu (email, uloga, lozinka) za predaju recenzentima."""
    users, out = {}, []
    for key, first, last, role, extra in ACCOUNTS:
        u = User(email=email_for(key), first_name=first, last_name=last, **extra)
        pw = new_password(u)
        create = User.objects.create_system_admin if key == 'sistem' else User.objects.create_user
        users[key] = create(email_for(key), pw, first_name=first, last_name=last, **extra)
        out.append((email_for(key), role, pw))

    alfa = Club.objects.create(name='PD Alfa (test)', city='Sarajevo', status=Club.Status.APPROVED,
                               created_by=users['admin.alfa'], email=f'kontakt.alfa@{DOMAIN}',
                               description='Testno društvo za recenziju aplikacije.')
    beta = Club.objects.create(name='PD Beta (test)', city='Mostar', status=Club.Status.APPROVED,
                               created_by=users['admin.beta'], email=f'kontakt.beta@{DOMAIN}',
                               description='Drugo testno društvo, za provjeru razdvojenosti društava.')
    gama = Club.objects.create(name='PD Gama (test)', city='Tuzla', created_by=users['planinar3'],
                               description='Zahtjev za registraciju društva koji čeka odluku sistemskog admina.')
    ClubAdmin.objects.create(club=alfa, user=users['admin.alfa'])
    ClubAdmin.objects.create(club=beta, user=users['admin.beta'])
    ClubAdmin.objects.create(club=gama, user=users['planinar3'])     # postaje admin tek kad se društvo odobri
    for club, keys in [(alfa, ['vodic1.alfa', 'vodic2.alfa']), (beta, ['vodic1.beta', 'vodic2.beta'])]:
        for i, k in enumerate(keys, start=1):
            ClubGuide.objects.create(club=club, user=users[k], license_number=f'TEST-{club.name[3]}{i}')

    end_of_year = date(timezone.localdate().year, 12, 31)
    ClubMembership.objects.create(club=alfa, user=users['planinar1'], status=ClubMembership.Status.APPROVED,
                                  valid_until=end_of_year, decided_by=users['admin.alfa'], decided_at=timezone.now())
    ClubMembership.objects.create(club=alfa, user=users['planinar2'])          # zahtjev na čekanju
    ClubMembership.objects.create(club=beta, user=users['planinar3'], status=ClubMembership.Status.APPROVED,
                                  valid_until=end_of_year, decided_by=users['admin.beta'], decided_at=timezone.now())

    now = timezone.now().replace(minute=0, second=0, microsecond=0)

    def tour(club, name, days, status, diff=Tour.Difficulty.MEDIUM, maxp=10, route=None, **kw):
        start = (now + timedelta(days=days)).replace(hour=7)
        deadline = start - timedelta(days=1)
        return Tour.objects.create(
            club=club, name=name, start_at=start, registration_deadline=deadline, status=status,
            meeting_point=kw.pop('meeting', 'Parking ispred planinarskog doma'), difficulty=diff,
            length_km=kw.pop('km', 12), elevation_gain_m=kw.pop('elev', 800), duration_h=kw.pop('hours', 6),
            max_participants=maxp, price=kw.pop('price', 10), region=kw.pop('region', 'Testna regija'),
            required_equipment='Planinarske cipele, voda, kabanica.', route=route or [],
            created_by=club.created_by, **kw)

    def guide(t, key, status=TourGuide.Status.APPROVED):
        return TourGuide.objects.create(tour=t, user=users[key], status=status,
                                        decided_at=None if status == TourGuide.Status.APPLIED else timezone.now())

    def reg(t, key, status=TourRegistration.Status.REGISTERED, attendance=''):
        return TourRegistration.objects.create(tour=t, user=users[key], status=status, attendance=attendance)

    S, D, R, A = Tour.Status, Tour.Difficulty, TourRegistration.Status, TourRegistration.Attendance

    # --- PD Alfa: ture u svim statusima ---
    a1 = tour(alfa, 'Alfa: Objavljena tura', 7, S.PUBLISHED, route=ROUTES['bjelasnica'], region='Bjelašnica')
    guide(a1, 'vodic1.alfa')
    reg(a1, 'planinar1')
    reg(a1, 'planinar2')

    a2 = tour(alfa, 'Alfa: Samo za članove', 10, S.PUBLISHED, D.HARD, route=ROUTES['treskavica'],
              region='Treskavica', members_only=True)
    guide(a2, 'vodic2.alfa', TourGuide.Status.APPLIED)                  # prijava vodiča čeka admina
    reg(a2, 'planinar1')

    a3 = tour(alfa, 'Alfa: Popunjena tura s listom čekanja', 12, S.PUBLISHED, D.EASY, maxp=2,
              route=ROUTES['igman'], region='Igman', price=0)
    reg(a3, 'planinar1')
    reg(a3, 'planinar3')
    reg(a3, 'planinar2', R.WAITLIST)

    tour(alfa, 'Alfa: Nacrt ture', 20, S.DRAFT)
    cancelled = tour(alfa, 'Alfa: Otkazana tura', 15, S.CANCELLED, D.VERY_HARD)
    reg(cancelled, 'planinar1')

    # jučerašnja tura: vodič može evidentirati prisustvo i poslati izvještaj (lični podaci još 6 dana)
    a5 = tour(alfa, 'Alfa: Jučerašnja tura (prijave zatvorene)', -1, S.CLOSED, D.EASY, route=ROUTES['bjelasnica'])
    guide(a5, 'vodic1.alfa')
    reg(a5, 'planinar1')
    reg(a5, 'planinar2')

    # održana tura prije 20 dana: izvještaj predan, lični podaci vodiču više nisu dostupni
    a6 = tour(alfa, 'Alfa: Održana tura', -20, S.DONE)
    guide(a6, 'vodic2.alfa')
    reg(a6, 'planinar1', attendance=A.PRESENT)
    reg(a6, 'planinar2', attendance=A.ABSENT)
    TourReport.objects.create(tour=a6, guide=users['vodic2.alfa'], text='Testni izvještaj: tura je prošla bez poteškoća.',
                              attendees_count=1)

    # --- PD Beta ---
    b1 = tour(beta, 'Beta: Objavljena tura', 8, S.PUBLISHED, D.VERY_HARD, route=ROUTES['prenj'], region='Prenj',
              meeting='Konjic, autobuska stanica')
    guide(b1, 'vodic1.beta')
    reg(b1, 'planinar3')
    reg(b1, 'planinar1')

    b2 = tour(beta, 'Beta: Prijave zatvorene', 3, S.CLOSED, D.HARD, route=ROUTES['cvrsnica'], region='Čvrsnica')
    guide(b2, 'vodic2.beta')
    reg(b2, 'planinar3')

    tour(beta, 'Beta: Objavljena tura bez vodiča', 18, S.PUBLISHED, D.MEDIUM)
    tour(beta, 'Beta: Nacrt ture', 25, S.DRAFT)
    tour(beta, 'Beta: Otkazana tura', 9, S.CANCELLED)
    b6 = tour(beta, 'Beta: Održana tura', -30, S.DONE)
    guide(b6, 'vodic1.beta')
    reg(b6, 'planinar3', attendance=A.PRESENT)
    TourReport.objects.create(tour=b6, guide=users['vodic1.beta'], text='Testni izvještaj za drugo društvo.',
                              attendees_count=1)
    return out
