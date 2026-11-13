"""
Fase 12: Row-Level Security de PostgreSQL (gestorpro/core/tenancy/rls.py).

Estos tests saltan A PROPÓSITO las capas de la aplicación (manager filtrado,
save() con verificación) y hablan con la base directamente: SQL crudo y el
manager sin filtro. Lo que prueban es que, aunque el código tuviera un error,
PostgreSQL mismo no deja ver ni escribir datos de otra empresa.
"""
import pytest
from django.db import connection, transaction
from django.db.utils import ProgrammingError

from gestorpro.core.customers.models import Customer
from gestorpro.core.tenancy.context import tenant_context
from gestorpro.core.tenancy.rls import APP_ROLE, POLICY, rls_bypass, tenant_tables
from tests import support as s

pytestmark = [pytest.mark.isolation, pytest.mark.django_db]


@pytest.fixture
def two():
    a, b = s.make_tenant('RLS A'), s.make_tenant('RLS B')
    return {'a': a, 'b': b, 'ca': s.make_customer(a), 'cb': s.make_customer(b)}


def raw(sql, params=()):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def test_the_app_queries_with_a_role_that_cannot_skip_rls():
    with tenant_context(1):
        user, = raw('SELECT current_user')[0]
        flags = raw('SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user')[0]
    assert user == APP_ROLE
    assert flags == (False, False)


def test_every_company_table_has_rls_and_the_policy():
    tables = tenant_tables()
    assert len(tables) >= 30
    rows = dict(raw('SELECT relname, relrowsecurity FROM pg_class WHERE relname = ANY(%s)', [tables]))
    assert {t for t in tables if not rows.get(t)} == set()
    with_policy = {r[0] for r in raw('SELECT tablename FROM pg_policies WHERE policyname = %s', [POLICY])}
    assert set(tables) - with_policy == set()


def test_raw_sql_inside_a_company_only_sees_that_company(two):
    with tenant_context(two['a']):
        ids = {r[0] for r in raw('SELECT id FROM customers_customer')}
        tenants = {r[0] for r in raw('SELECT DISTINCT tenant_id FROM customers_customer')}
    assert two['cb'].id not in ids and two['ca'].id in ids
    assert tenants == {two['a'].id}


def test_the_unfiltered_manager_inside_a_company_cannot_reach_another(two):
    """Ni siquiera `all_tenants` (el manager base de las relaciones) cruza empresas con una empresa activa."""
    with tenant_context(two['a']):
        assert not Customer.all_tenants.filter(pk=two['cb'].pk).exists()
        assert Customer.all_tenants.filter(tenant=two['b']).count() == 0


def test_without_a_company_nothing_is_visible_fail_closed(two):
    assert Customer.all_tenants.count() == 0
    assert raw('SELECT count(*) FROM customers_customer')[0][0] == 0


def test_a_declared_global_access_sees_every_company(two):
    with rls_bypass():
        assert Customer.all_tenants.filter(pk__in=[two['ca'].pk, two['cb'].pk]).count() == 2


def test_inserts_into_another_company_are_rejected(two):
    """bulk_create con el manager sin filtro se salta save(): la base igual lo rechaza."""
    intruder = Customer(tenant=two['b'], first_name='X', last_name='X', email='x@x.co', document_number='RLS-1')
    with tenant_context(two['a']), pytest.raises(ProgrammingError, match='row-level security'), \
            transaction.atomic():
        Customer.all_tenants.bulk_create([intruder])


def test_raw_updates_and_deletes_cannot_touch_another_company(two):
    with tenant_context(two['a']):
        with connection.cursor() as cursor:
            cursor.execute("UPDATE customers_customer SET first_name = 'Hackeado' WHERE id = %s", [two['cb'].id])
            assert cursor.rowcount == 0
            cursor.execute('DELETE FROM customers_customer WHERE id = %s', [two['cb'].id])
            assert cursor.rowcount == 0
    with tenant_context(two['b']):
        assert Customer.objects.get(pk=two['cb'].pk).first_name == two['cb'].first_name


def test_moving_a_row_to_another_company_is_rejected(two):
    with tenant_context(two['a']), pytest.raises(ProgrammingError, match='row-level security'), \
            transaction.atomic():
        raw('UPDATE customers_customer SET tenant_id = %s WHERE id = %s', [two['b'].id, two['ca'].id])


def test_the_app_role_cannot_truncate_nor_change_the_schema(two):
    with tenant_context(two['a']):
        for statement in ('TRUNCATE customers_customer', 'ALTER TABLE customers_customer DISABLE ROW LEVEL SECURITY',
                          'DROP TABLE customers_customer'):
            with pytest.raises(ProgrammingError), transaction.atomic():
                raw(statement)


def test_switching_companies_switches_what_the_database_shows(two):
    """El contexto viaja a PostgreSQL en cada cambio, también dentro de una misma transacción."""
    with transaction.atomic():
        for tenant, own, other in ((two['a'], 'ca', 'cb'), (two['b'], 'cb', 'ca'), (two['a'], 'ca', 'cb')):
            with tenant_context(tenant):
                ids = {r[0] for r in raw('SELECT id FROM customers_customer')}
                assert two[own].id in ids and two[other].id not in ids


def test_a_rolled_back_savepoint_does_not_leave_the_wrong_company_active(two):
    """PostgreSQL revierte set_config con el savepoint: el contexto se vuelve a enviar."""
    with transaction.atomic(), tenant_context(two['a']):
        assert raw('SELECT count(*) FROM customers_customer WHERE id = %s', [two['ca'].id])[0][0] == 1
        try:
            with transaction.atomic(), tenant_context(two['b']):
                assert raw('SELECT count(*) FROM customers_customer WHERE id = %s', [two['cb'].id])[0][0] == 1
                raise RuntimeError('revertir el savepoint')
        except RuntimeError:
            pass
        # De vuelta en A: debe ver A, y no B
        assert raw('SELECT count(*) FROM customers_customer WHERE id = %s', [two['ca'].id])[0][0] == 1
        assert raw('SELECT count(*) FROM customers_customer WHERE id = %s', [two['cb'].id])[0][0] == 0
