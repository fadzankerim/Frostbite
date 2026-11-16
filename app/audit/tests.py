from django.db import connection
from django.test import TestCase

from .models import AuditLog


class AuditAppendOnlyTests(TestCase):
    def setUp(self):
        self.entry = AuditLog.objects.create(action='TEST')

    def test_cannot_modify_instance(self):
        self.entry.action = 'IZMIJENJENO'
        with self.assertRaises(PermissionError):
            self.entry.save()

    def test_cannot_delete_instance(self):
        with self.assertRaises(PermissionError):
            self.entry.delete()

    def test_cannot_bulk_update_or_delete(self):
        with self.assertRaises(PermissionError):
            AuditLog.objects.all().update(action='X')
        with self.assertRaises(PermissionError):
            AuditLog.objects.all().delete()

    def test_database_trigger_blocks_raw_sql(self):
        if connection.vendor != 'postgresql':
            self.skipTest('Trigger postoji samo u PostgreSQL-u')
        from django.db import DatabaseError, transaction
        with self.assertRaises(DatabaseError), transaction.atomic():
            with connection.cursor() as c:
                c.execute('UPDATE audit_log SET action = %s', ['X'])
        with self.assertRaises(DatabaseError), transaction.atomic():
            with connection.cursor() as c:
                c.execute('DELETE FROM audit_log')
