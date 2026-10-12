"""Configuración de cajas y medios de pago desde la pantalla (Configuración → Caja y pagos)."""
import uuid

import pytest

from gestorpro.core.cash.models import CashRegister
from gestorpro.core.sales.models import PaymentMethod
from gestorpro.core.tenancy.context import tenant_context
from tests import support as s

pytestmark = pytest.mark.django_db


@pytest.fixture
def shop():
    tenant = s.make_tenant('Caja Config')
    return {'t': tenant, 'admin': s.api_for(s.make_user(tenant, 'adm@cfg.co', 'ADMIN')),
            'sup': s.api_for(s.make_user(tenant, 'sup@cfg.co', 'SUPERVISOR'))}


def test_admin_adds_renames_and_deactivates_registers(shop):
    api = shop['admin']
    created = api.post('/api/cash/registers/config/', {'name': 'Caja 2'}, format='json')
    assert created.status_code == 201 and created.data['location_name']
    assert api.post('/api/cash/registers/config/', {'name': 'caja 2'}, format='json').status_code == 400
    rid = created.data['id']
    renamed = api.patch(f'/api/cash/registers/config/{rid}/', {'name': 'Mostrador'}, format='json')
    assert renamed.data['name'] == 'Mostrador'
    # Con turno abierto no se puede desactivar
    api.post('/api/cash/sessions/', {'register': rid, 'opening_amount': '0'}, format='json')
    res = api.patch(f'/api/cash/registers/config/{rid}/', {'is_active': False}, format='json')
    assert res.status_code == 400 and 'turno abierto' in str(res.data)
    with tenant_context(shop['t']):
        assert CashRegister.objects.count() == 2


def test_inactive_register_disappears_from_the_cash_screen(shop):
    api = shop['admin']
    rid = api.post('/api/cash/registers/config/', {'name': 'Temporal'}, format='json').data['id']
    api.patch(f'/api/cash/registers/config/{rid}/', {'is_active': False}, format='json')
    assert rid not in {r['id'] for r in api.get('/api/cash/registers/').data}
    assert api.post('/api/cash/sessions/', {'register': rid, 'opening_amount': '0'}, format='json').status_code == 400


def test_payment_methods_are_configurable_with_safe_rules(shop):
    api = shop['admin']
    new = api.post('/api/sales/payment-methods/config/', {'name': 'Bold', 'kind': 'card'}, format='json')
    assert new.status_code == 201 and new.data['code'] == 'bold'
    assert api.post('/api/sales/payment-methods/config/', {'name': 'bold', 'kind': 'card'},
                    format='json').status_code == 400
    with tenant_context(shop['t']):
        cash = PaymentMethod.objects.get(code='cash')
    url = f'/api/sales/payment-methods/config/{cash.id}/'
    assert api.patch(url, {'kind': 'card'}, format='json').status_code == 400
    # Desactivar uno: el POS deja de ofrecerlo y el servidor lo rechaza
    nequi = next(m for m in api.get('/api/sales/payment-methods/config/').data if m['code'] == 'nequi')
    api.patch(f"/api/sales/payment-methods/config/{nequi['id']}/", {'is_active': False}, format='json')
    assert 'nequi' not in {m['code'] for m in api.get('/api/sales/payment-methods/').data}
    item = s.make_product(shop['t'], code='CFG-1')
    with tenant_context(shop['t']):
        register = CashRegister.objects.first()
    api.post('/api/cash/sessions/', {'register': register.id, 'opening_amount': '0'}, format='json')
    sale = api.post('/api/sales/', {'client_uuid': str(uuid.uuid4()), 'lines': [{'item': item.id, 'quantity': '1'}],
                                    'payments': [{'method': nequi['id'], 'amount': '1000'}]}, format='json')
    assert sale.status_code == 400


def test_the_last_active_payment_method_cannot_be_turned_off(shop):
    api = shop['admin']
    methods = api.get('/api/sales/payment-methods/config/').data
    for m in methods[:-1]:
        assert api.patch(f"/api/sales/payment-methods/config/{m['id']}/", {'is_active': False},
                         format='json').status_code == 200
    last = api.patch(f"/api/sales/payment-methods/config/{methods[-1]['id']}/", {'is_active': False}, format='json')
    assert last.status_code == 400


def test_only_who_manages_the_company_configures_registers_and_methods(shop):
    sup = shop['sup']
    for url in ('/api/cash/registers/config/', '/api/sales/payment-methods/config/'):
        assert sup.get(url).status_code == 403
        assert sup.post(url, {'name': 'X', 'kind': 'card'}, format='json').status_code == 403
