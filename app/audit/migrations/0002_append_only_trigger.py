"""PostgreSQL trigger: audit_log je append-only i na nivou baze (politika 4.7 i 4.8).
Čak ni direktan SQL iz aplikacije (UPDATE/DELETE/TRUNCATE) ne može izmijeniti evidenciju."""
from django.db import migrations

CREATE = """
CREATE OR REPLACE FUNCTION audit_log_readonly() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_log je samo za dodavanje (%%)', TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_no_update_delete
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_readonly();

CREATE TRIGGER audit_log_no_truncate
    BEFORE TRUNCATE ON audit_log
    FOR EACH STATEMENT EXECUTE FUNCTION audit_log_readonly();
"""

DROP = """
DROP TRIGGER IF EXISTS audit_log_no_truncate ON audit_log;
DROP TRIGGER IF EXISTS audit_log_no_update_delete ON audit_log;
DROP FUNCTION IF EXISTS audit_log_readonly();
"""


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute(CREATE)


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute(DROP)


class Migration(migrations.Migration):
    dependencies = [('audit', '0001_initial')]
    operations = [migrations.RunPython(forwards, backwards)]
