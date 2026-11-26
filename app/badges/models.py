from django.conf import settings
from django.db import models
from django.utils import timezone


class Badge(models.Model):
    """Katalog bedževa. Puni se migracijom (0002_catalog), ne kroz API ni UI."""

    class Role(models.TextChoices):
        HIKER = 'PLANINAR', 'Planinar'
        GUIDE = 'VODIC', 'Vodič'
        CLUB_ADMIN = 'ADMIN_DRUSTVA', 'Admin društva'
        SYSTEM = 'SISTEM', 'Sistemski admin'

    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=60)
    description = models.CharField(max_length=200)
    role = models.CharField(max_length=13, choices=Role.choices)
    tier = models.PositiveSmallIntegerField()        # 1 bronza, 2 srebro, 3 zlato
    icon = models.CharField(max_length=40)           # ime crteža u frontendu (BadgeArt)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'badges'
        ordering = ['order']

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    """Dodijeljen bedž. Ne oduzima se; dodjeljuje ga samo server (badges.services)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.PROTECT, related_name='+')
    awarded_at = models.DateTimeField(default=timezone.now)
    seen = models.BooleanField(default=False)

    class Meta:
        db_table = 'user_badges'
        ordering = ['awarded_at']
        constraints = [models.UniqueConstraint(fields=['user', 'badge'], name='uniq_user_badge')]
