from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditLogQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise PermissionError('Evidencija aktivnosti se ne može mijenjati.')

    def delete(self):
        raise PermissionError('Evidencija aktivnosti se ne može brisati.')


class AuditLog(models.Model):
    """Evidencija aktivnosti (politika 4.8). Samo dodavanje: izmjena i brisanje su zabranjeni
    u aplikaciji, a u PostgreSQL-u i triggerom (migracija 0002)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    action = models.CharField(max_length=50)
    entity = models.CharField(max_length=50, blank=True)
    entity_id = models.CharField(max_length=50, blank=True)
    details = models.CharField(max_length=500, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    objects = AuditLogQuerySet.as_manager()

    class Meta:
        db_table = 'audit_log'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise PermissionError('Evidencija aktivnosti se ne može mijenjati.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError('Evidencija aktivnosti se ne može brisati.')
