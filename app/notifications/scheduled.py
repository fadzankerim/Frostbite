"""Zakazana obavještenja (ne izaziva ih radnja, nego vrijeme). Ključ (Outbox.key) sprečava da se
isto obavještenje upiše dvaput, pa se schedule_due može pokretati svake minute."""
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from badges.rules import club_admin_users
from tours.models import Tour, TourGuide, TourRegistration

from .models import Outbox
from .services import link, notify, tour_context

REMINDER_BEFORE = timedelta(hours=24)
NO_GUIDE_WARNING_BEFORE = timedelta(days=3)


def _once(key, users, category, template, ctx, **kw):
    """Upisuje obavještenje svakom korisniku najviše jednom (ključ = događaj + korisnik)."""
    existing = set(Outbox.objects.filter(key__startswith=f'{key}:').values_list('key', flat=True))
    n = 0
    for u in users:
        k = f'{key}:{u.pk}'
        if k in existing:
            continue
        try:
            with transaction.atomic():
                n += notify([u], category, template, ctx, key=k, **kw)
        except IntegrityError:          # istovremeno pokretanje je već upisalo isti ključ
            pass
    return n


def schedule_due(now=None):
    now = now or timezone.now()
    count = 0
    active = [Tour.Status.PUBLISHED, Tour.Status.CLOSED]

    # podsjetnik planinarima 24 h prije polaska
    for t in Tour.objects.filter(status__in=active, start_at__gt=now, start_at__lte=now + REMINDER_BEFORE).select_related('club'):
        users = [r.user for r in TourRegistration.objects.filter(tour=t, status=TourRegistration.Status.REGISTERED)
                 .select_related('user')]
        ctx = tour_context(t, url=link(f'/ture/{t.pk}'), equipment=t.required_equipment[:300])
        count += _once(f'podsjetnik:{t.pk}', users, 'moje_ture', 'podsjetnik', ctx, expires_at=t.start_at)

    # upozorenje adminu: tura nema vodiča 3 dana prije polaska
    no_guide = (Tour.objects.filter(status__in=active, start_at__gt=now, start_at__lte=now + NO_GUIDE_WARNING_BEFORE)
                .exclude(guide_assignments__status=TourGuide.Status.APPROVED).select_related('club'))
    for t in no_guide:
        ctx = tour_context(t, url=link(f'/upravljanje/{t.club_id}/ture/{t.pk}'))
        count += _once(f'bez_vodica:{t.pk}', club_admin_users(t.club), 'drustvo', 'tura_bez_vodica_upozorenje', ctx,
                       expires_at=t.start_at)
    return count
