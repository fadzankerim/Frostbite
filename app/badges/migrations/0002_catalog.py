"""Katalog bedževa. Mijenja se samo novom migracijom (nikad kroz API)."""
from django.db import migrations

CATALOG = [
    # (šifra, naziv, opis, uloga, nivo, ikona)
    ('prvi-korak', 'Prvi korak', 'Prva prijava na turu.', 'PLANINAR', 1, 'boot'),
    ('prvi-vrh', 'Prvi vrh', 'Prva tura s prisustvom koje je potvrdio vodič.', 'PLANINAR', 1, 'peak'),
    ('planinar-5', 'Planinar 5', '5 tura s potvrđenim prisustvom.', 'PLANINAR', 1, 'backpack'),
    ('planinar-10', 'Planinar 10', '10 tura s potvrđenim prisustvom.', 'PLANINAR', 2, 'backpack'),
    ('planinar-25', 'Planinar 25', '25 tura s potvrđenim prisustvom.', 'PLANINAR', 3, 'backpack'),
    ('visinac-5000', 'Visinac 5.000', 'Ukupno 5.000 m uspona na turama s prisustvom.', 'PLANINAR', 2, 'altitude'),
    ('visinac-10000', 'Visinac 10.000', 'Ukupno 10.000 m uspona na turama s prisustvom.', 'PLANINAR', 3, 'altitude'),
    ('svestrani', 'Svestrani', 'Prisustvo na turama sve četiri težine.', 'PLANINAR', 2, 'compass'),
    ('clan-drustva', 'Član društva', 'Odobreno članstvo u planinarskom društvu.', 'PLANINAR', 1, 'people'),
    ('prvi-put-na-celu', 'Prvi put na čelu', 'Prva održana tura pod tvojim vođstvom.', 'VODIC', 1, 'flag'),
    ('iskusni-vodic-5', 'Iskusni vodič 5', '5 održanih tura pod tvojim vođstvom.', 'VODIC', 2, 'flag'),
    ('iskusni-vodic-20', 'Iskusni vodič 20', '20 održanih tura pod tvojim vođstvom.', 'VODIC', 3, 'flag'),
    ('uredan-dnevnik', 'Uredan dnevnik', 'Izvještaj predan za 10 tura.', 'VODIC', 2, 'book'),
    ('osnivac', 'Osnivač', 'Tvoje društvo je odobreno.', 'ADMIN_DRUSTVA', 1, 'house'),
    ('prva-objava', 'Prva objava', 'Društvo je objavilo prvu turu.', 'ADMIN_DRUSTVA', 1, 'megaphone'),
    ('puna-kuca', 'Puna kuća', 'Tura društva je popunjena do posljednjeg mjesta.', 'ADMIN_DRUSTVA', 2, 'tent'),
    ('sto-planinara', '100 planinara', 'Na turama društva je bilo ukupno 100 prisutnih.', 'ADMIN_DRUSTVA', 3, 'people'),
    ('cuvar-planine', 'Čuvar planine', 'Prva odluka o zahtjevu za registraciju društva.', 'SISTEM', 1, 'shield'),
    ('budno-oko', 'Budno oko', '50 odluka o zahtjevima za registraciju društava.', 'SISTEM', 2, 'eye'),
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
