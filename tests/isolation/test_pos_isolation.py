"""Aislamiento del POS y la caja: nada de otra empresa se ve, se usa ni se modifica."""
import uuid

import pytest

from gestorpro.core.cash.models import CashRegister
from gestorpro.core.sales.models import PaymentMethod
from gestorpro.core.tenancy.context import tenant_context
from tests import support as s

pytestmark = [pytest.mark.isolation, pytest.mark.django_db]


@pytest.fixture
def two():
    a, b = s.make_tenant('POS A'), s.make_tenant('POS B')
    api_a = s.api_for(s.make_user(a, 'sup@a.co', 'SUPERVISOR'))
    api_b = s.api_for(s.make_user(b, 'sup@b.co', 'SUPERVISOR'))
    with tenant_context(a):
        reg_a, cash_a = CashRegister.objects.get(), PaymentMethod.objects.get(code='cash')
    with tenant_context(b):
        reg_b, cash_b = CashRegister.objects.get(), PaymentMethod.objects.get(code='cash')
    item_a, item_b = s.make_product(a, code='A-1'), s.make_product(b, code='B-1')
    session_b = api_b.post('/api/cash/sessions/', {'register': reg_b.id, 'opening_amount': '0'}, format='json').data
    sale_b = api_b.post('/api/sales/', sale_body(item_b, cash_b), format='json').data
    return locals()


def sale_body(item, method):
    return {'client_uuid': str(uuid.uuid4()), 'lines': [{'item': item.id, 'quantity': '1'}],
            'payments': [{'method': method.id, 'amount': '1000'}]}


def test_cannot_open_a_register_of_another_company(two):
    res = two['api_a'].post('/api/cash/sessions/', {'register': two['reg_b'].id, 'opening_amount': '0'}, format='json')
    assert res.status_code == 400


def test_cannot_sell_items_or_use_payment_methods_of_another_company(two):
    two['api_a'].post('/api/cash/sessions/', {'register': two['reg_a'].id, 'opening_amount': '0'}, format='json')
    assert two['api_a'].post('/api/sales/', sale_body(two['item_b'], two['cash_a']), format='json').status_code == 400
    assert two['api_a'].post('/api/sales/', sale_body(two['item_a'], two['cash_b']), format='json').status_code == 400
    assert two['api_a'].post('/api/sales/', sale_body(two['item_a'], two['cash_a']), format='json').status_code == 201


def test_sales_and_sessions_of_another_company_are_invisible(two):
    api = two['api_a']
    assert api.get('/api/sales/').data['count'] == 0
    assert api.get(f"/api/sales/{two['sale_b']['id']}/").status_code == 404
    assert api.post(f"/api/sales/{two['sale_b']['id']}/void/", {'reason': 'x'}, format='json').status_code == 404
    assert api.get('/api/cash/sessions/').data['count'] == 0
    sid = two['session_b']['id']
    assert api.get(f'/api/cash/sessions/{sid}/').status_code == 404
    assert api.post(f'/api/cash/sessions/{sid}/close/', {'counted_amount': '1000'}, format='json').status_code == 404
    assert api.post(f'/api/cash/sessions/{sid}/movements/', {'type': 'income', 'amount': '1', 'reason': 'x'},
                    format='json').status_code == 404
    ids = {i['id'] for i in api.get('/api/sales/catalog/').data['items']}
    assert two['item_b'].id not in ids


def test_reusing_a_client_uuid_from_another_company_creates_an_independent_sale(two):
    api = two['api_a']
    api.post('/api/cash/sessions/', {'register': two['reg_a'].id, 'opening_amount': '0'}, format='json')
    body = sale_body(two['item_a'], two['cash_a'])
    body['client_uuid'] = two['sale_b'].get('client_uuid') or str(uuid.uuid4())
    res = api.post('/api/sales/', body, format='json')
    assert res.status_code == 201 and res.data['id'] != two['sale_b']['id']
