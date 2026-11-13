"""
Aislamiento entre tenants: lectura, escritura y referencias cruzadas.

Cada test documenta el hallazgo de la auditoría (docs/miga/01-*.md, §5.1)
que reproduce.
"""
import pytest

from tests import support as s

pytestmark = [pytest.mark.isolation, pytest.mark.django_db]


# ── S1: referencias cruzadas (la vulnerabilidad principal) ─────────────────────

def test_invoice_cannot_reference_customer_of_other_tenant(world):
    api = s.api_for(world['admin_a'])
    res = api.post(s.ENDPOINTS['invoices'],
                   s.invoice_payload(world['customer_b'].id, world['product_a'].id), format='json')
    assert res.status_code == 400
    assert 'Secreto' not in res.content.decode()


def test_invoice_cannot_reference_product_of_other_tenant(world):
    api = s.api_for(world['admin_a'])
    res = api.post(s.ENDPOINTS['invoices'],
                   s.invoice_payload(world['customer_a'].id, world['product_b'].id), format='json')
    assert res.status_code == 400


def test_product_cannot_reference_category_of_other_tenant(world):
    api = s.api_for(world['admin_a'])
    res = api.post(s.ENDPOINTS['products'],
                   {'name': 'Pan', 'code': 'X-1', 'price': '1000', 'category': world['category_b'].id},
                   format='json')
    assert res.status_code == 400


# ── S2: la unicidad no puede filtrar ni bloquear datos de otro tenant ──────────

def test_customer_email_and_document_are_unique_per_tenant_only(world):
    api = s.api_for(world['admin_a'])
    b = world['customer_b']
    res = api.post(s.ENDPOINTS['customers'],
                   {'first_name': 'Otro', 'last_name': 'Cliente', 'email': b.email,
                    'document_number': b.document_number}, format='json')
    assert res.status_code == 201, res.content


def test_product_code_is_unique_per_tenant_only(world):
    api = s.api_for(world['admin_a'])
    res = api.post(s.ENDPOINTS['products'],
                   {'name': 'Pan', 'code': world['product_b'].code, 'price': '1000'}, format='json')
    assert res.status_code == 201, res.content


# ── Acceso directo por ID y listados ──────────────────────────────────────────

@pytest.mark.parametrize('resource,key', [
    ('customers', 'customer_b'),
    ('products', 'product_b'),
    ('categories', 'category_b'),
    ('invoices', 'invoice_b'),
    ('suppliers', 'supplier_b'),
    ('employees', 'employee_b'),
])
@pytest.mark.parametrize('method', ['get', 'patch', 'delete'])
def test_objects_of_other_tenant_are_invisible(world, resource, key, method):
    api = s.api_for(world['admin_a'])
    url = f"{s.ENDPOINTS[resource]}{world[key].id}/"
    res = getattr(api, method)(url, {}, format='json')
    assert res.status_code == 404


@pytest.mark.parametrize('resource', ['customers', 'products', 'categories', 'invoices', 'suppliers', 'employees'])
def test_listings_only_contain_own_tenant(world, resource):
    api = s.api_for(world['admin_a'])
    res = api.get(s.ENDPOINTS[resource])
    assert res.status_code == 200
    ids = {row['id'] for row in s.results(res)}
    foreign = {world[k].id for k in ('customer_b', 'product_b', 'category_b', 'invoice_b', 'supplier_b', 'employee_b')}
    # Los IDs son por tabla; comparamos solo contra el objeto del mismo recurso.
    own_key = {'customers': 'customer_b', 'products': 'product_b', 'categories': 'category_b',
               'invoices': 'invoice_b', 'suppliers': 'supplier_b', 'employees': 'employee_b'}[resource]
    assert world[own_key].id not in ids
    assert foreign  # sanity


def test_aggregates_exclude_other_tenant(world):
    api = s.api_for(world['admin_a'])
    res = api.get(s.ENDPOINTS['billing_summary'])
    assert res.status_code == 200
    # La empresa B tiene una factura pagada de 999.000; A no tiene ninguna.
    from decimal import Decimal
    assert Decimal(str(res.data['paid_total'])) == Decimal('0')


# ── Fail-closed ───────────────────────────────────────────────────────────────

def test_user_without_tenant_cannot_read_business_data(world):
    lonely = s.make_user_without_tenant('nadie@x.co')
    api = s.api_for(lonely)
    for resource in ('customers', 'products', 'invoices', 'report_billing', 'report_inventory', 'billing_summary'):
        res = api.get(s.ENDPOINTS[resource])
        assert res.status_code in (401, 403), (resource, res.status_code)


def test_query_without_tenant_context_fails_closed(world):
    """Sin contexto de tenant, una consulta de negocio debe fallar, no devolver todo."""
    with pytest.raises(Exception):
        s.scoped_query_without_context()
