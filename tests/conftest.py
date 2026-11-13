"""
Ajustes de pytest para Row-Level Security (ver gestorpro/core/tenancy/rls.py).

La aplicación consulta con el rol `gestorpro_rls`, que no puede vaciar tablas
(TRUNCATE) ni crear bases ni ver datos sin empresa activa. Crear y destruir la
base de pruebas y restaurarla entre tests transaccionales es mantenimiento:
corre como dueño. (`flush` ya lo es en la aplicación.)
"""
import pytest
from django.db.backends.base import creation

from gestorpro.core.tenancy.rls import maintenance


def _as_maintenance(fn):
    def wrapper(*args, **kwargs):
        with maintenance():
            return fn(*args, **kwargs)
    wrapper.__wrapped__ = fn
    return wrapper


@pytest.fixture(scope='session', autouse=True)
def _rls_maintenance_for_test_housekeeping():
    patches = [(creation.BaseDatabaseCreation, 'create_test_db'),
               (creation.BaseDatabaseCreation, 'destroy_test_db'),
               (creation.BaseDatabaseCreation, 'serialize_db_to_string'),
               (creation.BaseDatabaseCreation, 'deserialize_db_from_string')]
    originals = [(owner, name, getattr(owner, name)) for owner, name in patches]
    for owner, name, fn in originals:
        setattr(owner, name, _as_maintenance(fn))
    yield
    for owner, name, fn in originals:
        setattr(owner, name, fn)
