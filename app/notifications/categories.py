"""Kategorije obavještenja (handoff, poglavlje 5.1).

Svaka kategorija ima publiku (uloge kojima se prikazuje u postavkama), zadani način slanja i
dozvoljene načine. Sigurnosna kategorija se ne može isključiti ni prebaciti u pregled.
"""
from dataclasses import dataclass

NOW, DIGEST, OFF = 'odmah', 'pregled', 'iskljuceno'
MODE_LABELS = {NOW: 'Odmah', DIGEST: 'Pregled', OFF: 'Isključeno'}

HIKER, GUIDE, CLUB_ADMIN, SYSTEM = 'planinar', 'vodic', 'admin_drustva', 'sistem'

DAILY, WEEKLY = 'dnevni', 'sedmicni'


@dataclass(frozen=True)
class Category:
    code: str
    label: str
    description: str
    audience: frozenset
    default: str
    modes: tuple
    digest: str = DAILY             # učestalost pregleda za način DIGEST
    security: bool = False


def _c(code, label, description, audience, default, modes, **kw):
    return Category(code, label, description, frozenset(audience), default, modes, **kw)


CATEGORIES = [
    _c('sigurnost', 'Sigurnost naloga',
       'Promjena lozinke, zaključan ili blokiran nalog, pokušaj registracije s vašim emailom.',
       {HIKER, GUIDE, CLUB_ADMIN, SYSTEM}, NOW, (NOW,), security=True),
    _c('moje_ture', 'Moje prijave na ture',
       'Potvrda prijave, dobijeno mjesto s liste čekanja, izmjena ili otkazivanje ture, podsjetnik dan prije polaska.',
       {HIKER}, NOW, (NOW, OFF)),
    _c('nove_ture', 'Nove ture mojih društava',
       'Nova tura društva u kojem imate važeće članstvo. Pregled stiže jednom sedmično.',
       {HIKER}, NOW, (NOW, DIGEST, OFF), digest=WEEKLY),
    _c('drustva', 'Članstvo i zahtjevi za društva',
       'Odluka o zahtjevu za članstvo i o zahtjevu za registraciju društva.',
       {HIKER}, NOW, (NOW, OFF)),
    _c('vodjenje', 'Vođenje tura',
       'Nova tura bez vodiča u vašem društvu, odluka o prijavi za vođenje, dodjela ture, otkazivanje ture koju vodite.',
       {GUIDE}, NOW, (NOW, DIGEST, OFF)),
    _c('ucesnici', 'Prijave na ture koje vodim',
       'Dnevni pregled prijava i odjava. Odjava u posljednja 24 sata prije polaska stiže odmah.',
       {GUIDE}, DIGEST, (DIGEST, NOW, OFF)),
    _c('drustvo', 'Upravljanje društvom',
       'Zahtjevi za članstvo, prijave vodiča, popunjene ture i ture bez vodiča pred polazak.',
       {CLUB_ADMIN}, NOW, (NOW, DIGEST, OFF)),
    _c('zahtjevi_drustava', 'Zahtjevi za registraciju društava',
       'Novi zahtjev za registraciju društva koji čeka odluku.',
       {SYSTEM}, NOW, (NOW, DIGEST, OFF)),
]
BY_CODE = {c.code: c for c in CATEGORIES}


def user_audience(user):
    """Uloge korisnika za izbor kategorija u postavkama."""
    from accounts.permissions import is_club_admin, is_guide
    if user.is_system_admin:
        return {SYSTEM}
    roles = {HIKER}
    if is_guide(user):
        roles.add(GUIDE)
    if is_club_admin(user):
        roles.add(CLUB_ADMIN)
    return roles


def categories_for(user):
    roles = user_audience(user)
    return [c for c in CATEGORIES if c.audience & roles]
