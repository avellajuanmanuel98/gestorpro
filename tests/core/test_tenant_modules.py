"""Módulos opcionales por empresa: una lavandería no ve producción ni mermas; una panadería sí."""
import pytest

from gestorpro.core.access.services import provision_tenant
from tests import support as s

pytestmark = pytest.mark.django_db

GATED = ['/api/production/recipes/', '/api/production/batches/', '/api/waste/', '/api/waste/reasons/',
         '/api/waste/summary/']


def test_a_generic_business_starts_without_production_or_waste():
    laundry = provision_tenant(name='Lavandería RainClean', owner=s._user('rain@lav.co'), plan_code='business')
    bakery = provision_tenant(name='Panadería Sol', owner=s._user('sol@pan.co'), vertical='bakery',
                              plan_code='business')
    assert laundry.modules == []
    assert bakery.modules == ['production', 'waste']


def test_disabled_modules_are_closed_in_the_backend_not_only_hidden():
    tenant = s.make_tenant('Lavandería', modules=())
    api = s.api_for(s.make_user(tenant, 'adm@lav.co', 'ADMIN'))
    for url in GATED:
        res = api.get(url)
        assert res.status_code == 403 and res.data['detail'].code == 'module_disabled', url
    assert api.post('/api/waste/', {}, format='json').status_code == 403
    session = api.get('/api/auth/me/').data
    assert session['tenant']['modules'] == []


def test_the_owner_can_turn_a_module_on_and_off():
    tenant = s.make_tenant('Restaurante', modules=())
    api = s.api_for(s.make_user(tenant, 'adm@res.co', 'ADMIN'))
    res = api.patch('/api/tenant/', {'modules': ['production', 'production']}, format='json')
    assert res.status_code == 200 and res.data['modules'] == ['production']
    assert api.get('/api/production/recipes/').status_code == 200
    assert api.get('/api/waste/').status_code == 403
    assert api.patch('/api/tenant/', {'modules': ['production', 'hackeo']}, format='json').status_code == 400
    assert api.patch('/api/tenant/', {'modules': []}, format='json').status_code == 200
    assert api.get('/api/production/recipes/').status_code == 403


def test_only_who_manages_the_company_can_change_modules():
    tenant = s.make_tenant('Cafetería', modules=())
    supervisor = s.api_for(s.make_user(tenant, 'sup@caf.co', 'SUPERVISOR'))
    assert supervisor.patch('/api/tenant/', {'modules': ['waste']}, format='json').status_code == 403
    tenant.refresh_from_db()
    assert tenant.modules == []


def test_production_suggestion_also_respects_the_module():
    tenant = provision_tenant(name='Panadería Luna', owner=s._user('luna@pan.co'), vertical='bakery',
                              plan_code='business')
    api = s.api_for(s.make_user(tenant, 'adm@luna.co', 'ADMIN'))
    assert api.get('/api/bakery/production-suggestion/').status_code == 200
    api.patch('/api/tenant/', {'modules': ['waste']}, format='json')
    assert api.get('/api/bakery/production-suggestion/').status_code == 403
