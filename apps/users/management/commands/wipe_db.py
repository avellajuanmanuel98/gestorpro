"""
Resetea la base de datos antes de cada deploy.

- SQLite  → borra el archivo db.sqlite3
- PostgreSQL → DROP SCHEMA public CASCADE + recreación limpia

Esto garantiza que las migraciones siempre partan de cero,
eliminando errores de InconsistentMigrationHistory o duplicate columns.
"""
import pathlib
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connections, connection


class Command(BaseCommand):
    help = 'Resetea la BD completa para garantizar migraciones limpias en cada deploy'

    def handle(self, *args, **kwargs):
        db = settings.DATABASES.get('default', {})
        engine = db.get('ENGINE', '')

        if 'sqlite3' in engine:
            self._wipe_sqlite(db)
        elif 'postgresql' in engine or 'postgis' in engine:
            self._wipe_postgres()
        else:
            self.stdout.write(f'Motor desconocido ({engine}) — no se hace nada.')

    # ── SQLite ────────────────────────────────────────────────────────────────

    def _wipe_sqlite(self, db):
        for conn in connections.all():
            conn.close()

        db_path = pathlib.Path(str(db['NAME']))
        if db_path.exists():
            db_path.unlink()
            self.stdout.write(self.style.SUCCESS(f'[SQLite] Borrado: {db_path}'))
        else:
            self.stdout.write(f'[SQLite] No encontrado: {db_path} (ya estaba limpio)')

    # ── PostgreSQL ────────────────────────────────────────────────────────────

    def _wipe_postgres(self):
        """
        Elimina y recrea el esquema público.
        Equivalente a borrar todas las tablas + historial de migraciones.
        """
        with connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA public CASCADE;")
            cursor.execute("CREATE SCHEMA public;")
            cursor.execute("GRANT ALL ON SCHEMA public TO PUBLIC;")
            cursor.execute("GRANT ALL ON SCHEMA public TO postgres;")

        self.stdout.write(self.style.SUCCESS(
            '[PostgreSQL] Schema public recreado — BD limpia.'
        ))
