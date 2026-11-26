"""Katalog bedževa. Mijenja se samo novom migracijom (nikad kroz API)."""
from django.db import migrations

CATALOG = [
    # (šifra, naziv, opis, uloga, nivo, ikona)
    ('prvi-korak', 'Prvi korak', 'Prijavio si se na svoju prvu turu.', 'PLANINAR', 1, 'boot'),
    ('prvi-vrh', 'Prvi vrh', 'Bio si na prvoj turi (prisustvo potvrdio vodič).', 'PLANINAR', 1, 'peak'),
    ('planinar-5', 'Planinar 5', 'Bio si na 5 tura.', 'PLANINAR', 1, 'backpack'),
    ('planinar-10', 'Planinar 10', 'Bio si na 10 tura.', 'PLANINAR', 2, 'backpack'),
    ('planinar-25', 'Planinar 25', 'Bio si na 25 tura.', 'PLANINAR', 3, 'backpack'),
    ('visinac-5000', 'Visinac 5.000', 'Savladao si ukupno 5.000 m uspona.', 'PLANINAR', 2, 'altitude'),
    ('visinac-10000', 'Visinac 10.000', 'Savladao si ukupno 10.000 m uspona.', 'PLANINAR', 3, 'altitude'),
    ('svestrani', 'Svestrani', 'Bio si na turama sve četiri težine.', 'PLANINAR', 2, 'compass'),
    ('clan-drustva', 'Član društva', 'Postao si član planinarskog društva.', 'PLANINAR', 1, 'people'),
    ('prvi-put-na-celu', 'Prvi put na čelu', 'Vodio si svoju prvu održanu turu.', 'VODIC', 1, 'flag'),
    ('iskusni-vodic-5', 'Iskusni vodič 5', 'Vodio si 5 održanih tura.', 'VODIC', 2, 'flag'),
    ('iskusni-vodic-20', 'Iskusni vodič 20', 'Vodio si 20 održanih tura.', 'VODIC', 3, 'flag'),
    ('uredan-dnevnik', 'Uredan dnevnik', 'Predao si izvještaj za 10 tura.', 'VODIC', 2, 'book'),
    ('osnivac', 'Osnivač', 'Tvoje društvo je odobreno.', 'ADMIN_DRUSTVA', 1, 'house'),
    ('prva-objava', 'Prva objava', 'Društvo je objavilo prvu turu.', 'ADMIN_DRUSTVA', 1, 'megaphone'),
    ('puna-kuca', 'Puna kuća', 'Tura društva je popunjena do posljednjeg mjesta.', 'ADMIN_DRUSTVA', 2, 'tent'),
    ('sto-planinara', '100 planinara', 'Na turama društva je bilo ukupno 100 prisutnih.', 'ADMIN_DRUSTVA', 3, 'people'),
    ('cuvar-planine', 'Čuvar planine', 'Donio si prvu odluku o zahtjevu društva.', 'SISTEM', 1, 'shield'),
    ('budno-oko', 'Budno oko', 'Donio si 50 odluka o zahtjevima društava.', 'SISTEM', 2, 'eye'),
]


def load(apps, schema_editor):
    Badge = apps.get_model('badges', 'Badge')
    for i, (code, name, desc, role, tier, icon) in enumerate(CATALOG):
        Badge.objects.update_or_create(code=code, defaults=dict(
            name=name, description=desc, role=role, tier=tier, icon=icon, order=i))


def unload(apps, schema_editor):
    apps.get_model('badges', 'Badge').objects.filter(code__in=[c[0] for c in CATALOG]).delete()


class Migration(migrations.Migration):
    dependencies = [('badges', '0001_initial')]
    operations = [migrations.RunPython(load, unload)]
