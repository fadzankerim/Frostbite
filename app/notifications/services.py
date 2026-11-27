"""Upis obavještenja u outbox. Pozivati UNUTAR transakcije radnje (transaction.atomic), tako da
obavještenje nastane samo ako radnja uspije.

U kontekst idu samo podaci koji smiju u email (vidi tour_context). Nikad lični podaci drugih
korisnika (telefon, hitni kontakt, zdravstvene napomene).
"""
from datetime import datetime, time, timedelta

from django.conf import settings
from django.core import signing
from django.utils import timezone

from .categories import BY_CODE, DAILY, DIGEST, NOW, OFF
from .models import NotificationPreference, Outbox

UNSUBSCRIBE_SALT = 'frostbite.notifications.unsubscribe'
UNSUBSCRIBE_MAX_AGE = 180 * 24 * 3600          # link za odjavu važi 180 dana
DIGEST_HOUR = 7                                 # pregledi stižu u 07:00 (Europe/Sarajevo)
DEFAULT_TTL = timedelta(days=3)                 # neposlano obavještenje nakon toga gubi smisao


def mode_for(user, category):
    cat = BY_CODE[category]
    if cat.security:
        return NOW
    pref = NotificationPreference.objects.filter(user=user, category=category).values_list('mode', flat=True).first()
    return pref if pref in cat.modes else cat.default


def next_digest_time(category, now=None):
    """Sljedeće jutro u 07:00; za sedmični pregled sljedeći ponedjeljak u 07:00."""
    now = timezone.localtime(now or timezone.now())
    day = now.date() if now.hour < DIGEST_HOUR else now.date() + timedelta(days=1)
    if BY_CODE[category].digest != DAILY:
        day += timedelta(days=(7 - day.weekday()) % 7)
    return timezone.make_aware(datetime.combine(day, time(DIGEST_HOUR)))


def notify(users, category, template, context, *, urgent=False, send_after=None, expires_at=None, key=None):
    """Upisuje obavještenje za svakog korisnika prema njegovim postavkama. `urgent` zaobilazi
    pregled (npr. odjava u posljednja 24 h). Vraća broj upisanih redova."""
    if category not in BY_CODE:
        raise ValueError(f'Nepoznata kategorija: {category}')
    now = timezone.now()
    rows, seen = [], set()
    for user in users:
        if user is None or user.pk in seen:
            continue
        seen.add(user.pk)
        mode = mode_for(user, category)
        if mode == OFF:
            continue
        digest = mode == DIGEST and not urgent
        when = next_digest_time(category, now) if digest else (send_after or now)
        rows.append(Outbox(
            user=user, category=category, template=template, context=context, digest=digest, key=key,
            send_after=when, expires_at=expires_at or (when + (timedelta(days=8) if digest else DEFAULT_TTL)),
        ))
    Outbox.objects.bulk_create(rows)
    return len(rows)


def link(path):
    """Apsolutni link u aplikaciju (FROSTBITE_PUBLIC_URL). Link vodi na stranicu; za svaku radnju
    korisnik se prijavljuje (nema tokena za prijavu u linkovima)."""
    return settings.FROSTBITE_PUBLIC_URL.rstrip('/') + path


def tour_context(tour, **extra):
    """Podaci o turi koji smiju u email."""
    start = timezone.localtime(tour.start_at)
    return {
        'tour': tour.name, 'club': tour.club.name, 'start': start.strftime('%d.%m.%Y. u %H:%M'),
        'meeting_point': tour.meeting_point, **extra,
    }


# --- odjava jednim klikom (potpisan token: korisnik + kategorija) -------------------------
def unsubscribe_token(user, category):
    return signing.dumps({'u': user.pk, 'c': category}, salt=UNSUBSCRIBE_SALT, compress=True)


def read_unsubscribe_token(token):
    """Vraća (user_id, category) ili None za neispravan, istekao ili sigurnosni token."""
    try:
        data = signing.loads(token, salt=UNSUBSCRIBE_SALT, max_age=UNSUBSCRIBE_MAX_AGE)
    except (signing.BadSignature, TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    uid, cat = data.get('u'), data.get('c')
    if not isinstance(uid, int) or cat not in BY_CODE or BY_CODE[cat].security:
        return None
    return uid, cat


def set_mode(user, category, mode):
    cat = BY_CODE[category]
    if mode not in cat.modes:
        raise ValueError('Nedozvoljen način za ovu kategoriju.')
    NotificationPreference.objects.update_or_create(user=user, category=category, defaults={'mode': mode})
