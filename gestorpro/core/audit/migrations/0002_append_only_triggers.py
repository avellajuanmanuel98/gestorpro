"""
Defensa en profundidad: aunque alguien salte el ORM (SQL manual, otra app),
PostgreSQL rechaza modificar filas del registro de auditoría.

DELETE no se bloquea a nivel de motor porque la eliminación de una empresa
(operación de plataforma, hoy deshabilitada en el admin) borra en cascada su
auditoría; el ORM sí bloquea cualquier borrado individual.
"""
from django.db import migrations

FUNCTION = """
CREATE OR REPLACE FUNCTION gestorpro_reject_update() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'La tabla % es de solo inserción', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;
"""

TABLES = ['audit_auditlog', 'audit_securityevent']


class Migration(migrations.Migration):
    dependencies = [('audit', '0001_initial')]

    operations = [
        migrations.RunSQL(FUNCTION, 'DROP FUNCTION IF EXISTS gestorpro_reject_update();'),
        *[
            migrations.RunSQL(
                f'CREATE TRIGGER {table}_no_update BEFORE UPDATE ON {table} '
                f'FOR EACH ROW EXECUTE FUNCTION gestorpro_reject_update();',
                f'DROP TRIGGER IF EXISTS {table}_no_update ON {table};',
            )
            for table in TABLES
        ],
    ]
