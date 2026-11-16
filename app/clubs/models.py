from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Club(models.Model):
    class Status(models.TextChoices):
        PENDING = 'NA_CEKANJU', 'Na čekanju'
        APPROVED = 'ODOBRENO', 'Odobreno'
        REJECTED = 'ODBIJENO', 'Odbijeno'
        SUSPENDED = 'SUSPENDOVANO', 'Suspendovano'

    name = models.CharField('naziv', max_length=120, unique=True)
    city = models.CharField('grad', max_length=80)
    description = models.TextField('opis', max_length=2000, blank=True)
    email = models.EmailField('kontakt email', max_length=254, blank=True)
    phone = models.CharField('kontakt telefon', max_length=30, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'clubs'
        ordering = ['name']

    def __str__(self):
        return self.name


class ClubAdmin(models.Model):
    club = models.ForeignKey(Club, on_delete=models.PROTECT, related_name='admins')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='admin_of')

    class Meta:
        db_table = 'club_admins'
        constraints = [models.UniqueConstraint(fields=['club', 'user'], name='uniq_club_admin')]


class ClubGuide(models.Model):
    club = models.ForeignKey(Club, on_delete=models.PROTECT, related_name='guides')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='guide_of')
    license_number = models.CharField('broj licence', max_length=40, blank=True)
    is_active = models.BooleanField(default=True)
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'club_guides'
        constraints = [models.UniqueConstraint(fields=['club', 'user'], name='uniq_club_guide')]


class ClubMembership(models.Model):
    class Status(models.TextChoices):
        REQUESTED = 'ZAHTJEV', 'Zahtjev'
        APPROVED = 'ODOBRENO', 'Odobreno'
        REJECTED = 'ODBIJENO', 'Odbijeno'
        EXPIRED = 'ISTEKLO', 'Isteklo'

    club = models.ForeignKey(Club, on_delete=models.PROTECT, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='memberships')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.REQUESTED)
    valid_until = models.DateField('važi do', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'club_memberships'
        constraints = [
            # najviše jedan aktivan zahtjev ili članstvo po društvu
            models.UniqueConstraint(fields=['club', 'user'], condition=Q(status__in=['ZAHTJEV', 'ODOBRENO']),
                                    name='uniq_active_membership'),
        ]

    def is_valid(self, today=None):
        today = today or timezone.localdate()
        return self.status == self.Status.APPROVED and (self.valid_until is None or self.valid_until >= today)
