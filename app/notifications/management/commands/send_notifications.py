"""Šalje dospjela obavještenja iz outboxa. Pokreće ga systemd timer (frostbite-notify.timer)
svake minute; prije slanja dodaje zakazana obavještenja (podsjetnici, upozorenja).

Bez EMAIL_HOST u produkciji slanje je isključeno: redovi ostaju u outboxu (i ističu po roku),
ništa se ne šalje i ne ispisuje u log.
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from notifications.scheduled import schedule_due
from notifications.sender import send_due


class Command(BaseCommand):
    help = 'Šalje dospjela obavještenja (email).'

    def handle(self, *args, **opts):
        scheduled = schedule_due()
        if not settings.NOTIFICATIONS_ENABLED:
            self.stdout.write(f'Slanje je isključeno (EMAIL_HOST nije postavljen). Zakazano: {scheduled}.')
            return
        sent, deferred, failed = send_due()
        if sent or deferred or failed or scheduled:
            self.stdout.write(f'Zakazano: {scheduled}, poslano: {sent}, odgođeno: {deferred}, greške: {failed}.')
