from django.conf import settings
from django.db import models
from django.utils import timezone


class Outbox(models.Model):
    """Transakcijski outbox: red se upisuje u istoj transakciji kao radnja koja ga izaziva, pa se
    obavještenje ne gubi ako server padne i ne šalje se ako radnja nije uspjela. Šalje ga komanda
    send_notifications (systemd timer svake minute).

    Kontekst sadrži samo podatke koji smiju u email: naziv ture i društva, termin, mjesto polaska,
    link. Nikad zdravstvene napomene, hitni kontakt ni telefone drugih korisnika."""

    class Status(models.TextChoices):
        PENDING = 'NA_CEKANJU', 'Na čekanju'
        SENT = 'POSLANO', 'Poslano'
        FAILED = 'GRESKA', 'Greška'
        SKIPPED = 'PRESKOCENO', 'Preskočeno'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    category = models.CharField(max_length=30)
    template = models.CharField(max_length=60)
    context = models.JSONField(default=dict)
    digest = models.BooleanField(default=False)
    key = models.CharField(max_length=120, unique=True, null=True, blank=True)   # zakazana: bez duplikata
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    send_after = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'notification_outbox'
        ordering = ['send_after', 'pk']
        indexes = [models.Index(fields=['status', 'send_after'], name='outbox_due')]


class NotificationPreference(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    category = models.CharField(max_length=30)
    mode = models.CharField(max_length=10)

    class Meta:
        db_table = 'notification_preferences'
        constraints = [models.UniqueConstraint(fields=['user', 'category'], name='uniq_notification_pref')]
