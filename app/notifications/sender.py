"""Slanje obavještenja iz outboxa (komanda send_notifications, systemd timer svake minute).

- Redovi kojima je prošao rok (expires_at) se preskaču, da zaostala obavještenja (npr. podsjetnik
  za turu koja je već prošla) ne stignu kasnije.
- Pregled (digest): sva dospjela obavještenja istog korisnika i kategorije idu u jedan email.
- Ograničenje: najviše MAX_PER_HOUR emailova po korisniku na sat (sigurnosni se ne ograničavaju);
  višak se odgađa, ne briše.
- Greška pri slanju: ponovni pokušaj s rastućom pauzom, najviše MAX_ATTEMPTS puta.
- Audit EMAIL_POSLAN: kategorija i ID reda, bez sadržaja.
"""
import logging
from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.db import transaction
from django.utils import timezone

from audit.log import audit

from . import templates as tpl
from .categories import BY_CODE, WEEKLY
from .models import Outbox
from .services import link, unsubscribe_token

log = logging.getLogger(__name__)

BATCH = 200
MAX_ATTEMPTS = 5
MAX_PER_HOUR = 20
LEASE = timedelta(minutes=10)
P = Outbox.Status


def _base_context(user, category):
    cat = BY_CODE[category]
    return {
        'first_name': user.first_name,
        'settings_url': link('/profil#obavjestenja'),
        'unsubscribe_url': None if cat.security else link(f'/obavjestenja/odjava?t={unsubscribe_token(user, category)}'),
        'note': settings.FROSTBITE_EMAIL_NOTE,
    }


def build_message(user, category, rows):
    """Jedan email za jedan red ili za pregled više redova iste kategorije."""
    base = _base_context(user, category)
    if len(rows) == 1 and not rows[0].digest:
        r = rows[0]
        ctx = {**r.context, **base}
        subject, text = tpl.subject(r.template, ctx), tpl.render_text(r.template, ctx)
    else:
        cat = BY_CODE[category]
        period = 'Sedmični' if cat.digest == WEEKLY else 'Dnevni'
        items = [{'summary': tpl.summary(r.template, r.context), 'url': r.context.get('url')} for r in rows]
        title = f'{period} pregled: {cat.label.lower()}'
        subject = tpl.clean(f'{title} ({len(rows)})', 150)
        text = tpl.render_text('pregled', {**base, 'title': title, 'items': items})
    msg = EmailMultiAlternatives(subject=subject, body=text, from_email=settings.DEFAULT_FROM_EMAIL, to=[user.email])
    msg.attach_alternative(tpl.text_to_html(text), 'text/html')
    if base['unsubscribe_url']:
        # RFC 8058: odjava jednim klikom (Gmail i Yahoo to traže od pošiljalaca obavještenja)
        one_click = link(f'/api/notifications/unsubscribe/{unsubscribe_token(user, category)}/')
        msg.extra_headers = {'List-Unsubscribe': f'<{one_click}>', 'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click'}
    return msg


def _claim(now):
    """Dospjeli redovi za ovaj proces. Uzimaju se uz zaključavanje (SKIP LOCKED) i odmah dobijaju
    "zakup" od LEASE minuta (send_after u budućnosti), pa ih drugo istovremeno pokretanje ne uzme.
    Ako proces padne usred slanja, redovi se ponovo pokušavaju nakon isteka zakupa."""
    with transaction.atomic():
        Outbox.objects.filter(status=P.PENDING, expires_at__lt=now).update(status=P.SKIPPED, last_error='istekao rok')
        qs = Outbox.objects.select_for_update(skip_locked=True).filter(status=P.PENDING, send_after__lte=now)
        rows = list(qs.select_related('user').order_by('send_after', 'pk')[:BATCH])
        Outbox.objects.filter(pk__in=[r.pk for r in rows]).update(send_after=now + LEASE)
        return rows


def send_due(now=None):
    """Šalje dospjela obavještenja. Vraća (poslano emailova, odgođeno, greške)."""
    now = now or timezone.now()
    rows = _claim(now)
    groups = defaultdict(list)
    for r in rows:
        # pregled iste kategorije ide u jedan email; ostali redovi pojedinačno
        groups[(r.user_id, r.category, 'd' if r.digest else r.pk)].append(r)

    sent = deferred = failed = 0
    hour_ago = now - timedelta(hours=1)
    counts = defaultdict(int)
    connection = get_connection()
    for (_uid, category, _k), items in groups.items():
        user = items[0].user
        ids = [r.pk for r in items]
        security = BY_CODE[category].security
        if not user.is_active and not security:            # blokiran nalog dobija samo sigurnosne emailove
            Outbox.objects.filter(pk__in=ids).update(status=P.SKIPPED, last_error='nalog nije aktivan')
            continue
        if not security:
            if user.pk not in counts:
                counts[user.pk] = Outbox.objects.filter(user=user, status=P.SENT, sent_at__gte=hour_ago).count()
            if counts[user.pk] >= MAX_PER_HOUR:
                Outbox.objects.filter(pk__in=ids).update(send_after=now + timedelta(hours=1))
                deferred += 1
                continue
        try:
            msg = build_message(user, category, items)
            msg.connection = connection
            msg.send()
        except Exception as e:                              # noqa: BLE001 - mreža, SMTP, šablon
            attempts = items[0].attempts + 1
            done = attempts >= MAX_ATTEMPTS
            Outbox.objects.filter(pk__in=ids).update(
                attempts=attempts, last_error=type(e).__name__[:200],
                status=P.FAILED if done else P.PENDING,
                send_after=now + timedelta(minutes=2 ** attempts))
            log.warning('Slanje obavještenja nije uspjelo (redovi=%s, pokušaj=%s): %s', ids, attempts, type(e).__name__)
            failed += 1
            continue
        Outbox.objects.filter(pk__in=ids).update(status=P.SENT, sent_at=timezone.now(), last_error='')
        counts[user.pk] += 1
        sent += 1
        audit(None, 'EMAIL_POSLAN', 'notification', ids[0], user=user,
              details=f'kategorija={category} broj={len(ids)}')
    return sent, deferred, failed
