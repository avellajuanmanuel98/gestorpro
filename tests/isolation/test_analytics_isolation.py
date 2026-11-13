"""Aislamiento de la analítica: ningún número, fila ni CSV incluye datos de otra empresa."""
import uuid

import pytest

from gestorpro.capabilities.waste.models import WasteReason
from gestorpro.core.cash.models import CashRegister
from gestorpro.core.sales.models import PaymentMethod
from gestorpro.core.tenancy.context import tenant_context
from gestorpro.core.tenancy.models import Location
from tests import support as s

pytestmark = [pytest.mark.isolation, pytest.mark.django_db]


@pytest.fixture
def two():
    from gestorpro.core.access.services import provision_tenant
    a = provision_tenant(name='Ana A', owner=s._user('owner@ana-a.co'), vertical='bakery', plan_code='pro')
    b = provision_tenant(name='Ana B', owner=s._user('owner@ana-b.co'), vertical='bakery', plan_code='pro')
    api_a = s.api_for(s.make_user(a, 'adm@ana-a.co', 'ADMIN'))
    api_b = s.api_for(s.make_user(b, 'adm@ana-b.co', 'ADMIN'))
    with tenant_context(b):
        reg_b, cash_b = CashRegister.objects.get(), PaymentMethod.objects.get(code='cash')
        reason_b, location_b = WasteReason.objects.first(), Location.objects.get()
    flour_b = api_b.post('/api/catalog/items/', {'name': 'Harina B', 'kind': 'raw_material', 'unit': 'kg',
                                                 'avg_cost': '1000', 'stock': '10'}, format='json').data['id']
    item_b = s.make_product(b, code='B-1')
    api_b.post('/api/cash/sessions/', {'register': reg_b.id, 'opening_amount': '0'}, format='json')
    sale = api_b.post('/api/sales/', {'client_uuid': str(uuid.uuid4()), 'lines': [{'item': item_b.id, 'quantity': '3'}],
                                      'payments': [{'method': cash_b.id, 'amount': '100000'}]}, format='json')
    assert sale.status_code == 201
    api_b.post('/api/waste/', {'item': flour_b, 'quantity': '1', 'reason': reason_b.id}, format='json')
    return locals()


def test_company_b_sees_its_own_numbers(two):
    """Control: los datos de B existen y se reportan (si no, los demás tests no probarían nada)."""
    kpis = two['api_b'].get('/api/analytics/summary/', {'period': 'today'}).data['kpis']
    assert kpis['transactions']['value'] == 1
    assert two['api_b'].get('/api/analytics/products/', {'period': 'today'}).data['rows']


def test_reports_of_company_a_never_include_company_b(two):
    api = two['api_a']
    kpis = api.get('/api/analytics/summary/', {'period': 'today'}).data['kpis']
    assert kpis['transactions']['value'] == 0 and kpis['sales']['value'] == '0.00'
    assert kpis['waste_cost']['value'] == '0.00'
    assert all(h['transactions'] == 0 for h in api.get('/api/analytics/hourly/', {'period': 'today'}).data['hours'])
    for by in ('day', 'weekday', 'method', 'cashier', 'category'):
        assert api.get('/api/analytics/breakdown/', {'period': 'today', 'by': by}).data['rows'] == [], by
    assert api.get('/api/analytics/products/', {'period': 'today'}).data['rows'] == []
    assert api.get('/api/analytics/cash/', {'period': 'today'}).data['sessions'] == []
    names = {r['name'] for r in api.get('/api/analytics/coverage/').data['rows']}
    assert 'Harina B' not in names
    waste = api.get('/api/waste/summary/', {'period': 'today'}).data
    assert waste['by_reason'] == [] and waste['by_item'] == []
    rows = api.get('/api/bakery/production-suggestion/').data['rows']
    assert all(r['item'] != two['item_b'].id for r in rows)


def test_csv_export_of_company_a_never_includes_company_b(two):
    res = two['api_a'].get('/api/analytics/products/', {'period': 'today', 'export': 'csv'})
    assert res.status_code == 200
    body = b''.join(res.streaming_content) if getattr(res, 'streaming', False) else res.content
    assert two['item_b'].name.encode() not in body


def test_filtering_by_a_location_of_another_company_is_rejected(two):
    res = two['api_a'].get('/api/analytics/summary/', {'period': 'today', 'location': two['location_b'].id})
    assert res.status_code == 400
