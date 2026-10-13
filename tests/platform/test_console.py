"""Consola de plataforma: métricas, empresas, planes, suscripciones y soporte de solo lectura."""
import datetime

import pytest
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from gestorpro.core.access.models import SupportSession
from gestorpro.core.audit.models import AuditLog
from gestorpro.core.tenancy.models import Tenant
from gestorpro.platform.console.models import PlatformEvent
from gestorpro.platform.subscriptions.models import Plan, Subscription
from tests import support as s

pytestmark = pytest.mark.django_db

URLS = ['/api/platform/overview/', '/api/platform/tenants/', '/api/platform/plans/', '/api/platform/events/']


@pytest.fixture
def staff():
    user = s._user('soporte@gestorpro.co')
    call_command('platform_admin', user.email)
    user.refresh_from_db()
    return user, s.api_for(user)


@pytest.fixture
def shop():
    tenant = s.make_tenant('Panadería Norte', plan_code='starter')
    owner = s.make_user(tenant, 'duena@norte.co', 'OWNER')
    s.make_customer(tenant)
    return tenant, owner, s.api_for(owner)


def test_only_platform_staff_can_use_the_console(shop):
    _, _, owner_api = shop
    for url in URLS:
        assert owner_api.get(url).status_code == 403, url
        assert APIClient().get(url).status_code == 401, url


def test_overview_counts_usage_without_exposing_business_amounts(staff, shop):
    _, api = staff
    tenant, _, _ = shop
    Subscription.objects.filter(tenant=tenant).update(trial_ends_at=timezone.now() + datetime.timedelta(days=3))
    data = api.get('/api/platform/overview/').data
    assert data['tenants']['total'] == 1 and data['tenants']['active'] == 1
    assert data['subscriptions']['by_status'] == {'trialing': 1}
    assert [t['name'] for t in data['trials_ending']] == ['Panadería Norte']
    assert 'sales_total' not in str(data) and 'revenue' not in str(data)
    Subscription.objects.filter(tenant=tenant).update(trial_ends_at=timezone.now() - datetime.timedelta(days=1))
    data = api.get('/api/platform/overview/').data
    assert data['subscriptions']['by_status'] == {'trial_expired': 1}
    assert data['attention'] == [{'id': tenant.id, 'name': 'Panadería Norte', 'kind': 'trial_expired'}]


def test_tenants_can_be_searched_by_owner_email_and_inspected(staff, shop):
    _, api = staff
    tenant, _, _ = shop
    s.make_tenant('Lavandería Sur')
    rows = api.get('/api/platform/tenants/', {'q': 'duena@norte'}).data['results']
    assert [r['name'] for r in rows] == ['Panadería Norte']
    assert rows[0]['plan']['code'] == 'starter' and rows[0]['members'] >= 2
    detail = api.get(f'/api/platform/tenants/{tenant.id}/').data
    assert {m['email'] for m in detail['members']} >= {'duena@norte.co'}
    assert {u['key'] for u in detail['usage']} == {'users', 'locations', 'products', 'custom_roles'}
    # La consola no expone clientes, ventas ni facturas de la empresa
    assert 'customers' not in detail and 'sales' not in detail


def test_onboarding_from_the_console_creates_company_and_owner_link(staff):
    _, api = staff
    res = api.post('/api/platform/tenants/', {'name': 'Panadería Sol', 'owner_email': 'sol@pan.co',
                                              'vertical': 'bakery', 'plan': 'business'}, format='json')
    assert res.status_code == 201
    assert '/invitation/' in res.data['invitation_url']
    tenant = Tenant.objects.get(name='Panadería Sol')
    assert tenant.modules == ['production', 'waste']
    assert PlatformEvent.objects.filter(action='tenant.created', tenant=tenant).exists()
    again = api.post('/api/platform/tenants/', {'name': 'panadería sol', 'owner_email': 'x@x.co',
                                                'vertical': 'generic', 'plan': 'business'}, format='json')
    assert again.status_code == 400


def test_subscription_changes_are_logged_for_platform_and_for_the_company(staff, shop):
    _, api = staff
    tenant, _, _ = shop
    end = (timezone.now() + datetime.timedelta(days=30)).isoformat()
    res = api.patch(f'/api/platform/tenants/{tenant.id}/subscription/',
                    {'plan': 'business', 'status': 'active', 'current_period_end': end, 'note': 'Pago de octubre'},
                    format='json')
    assert res.status_code == 200 and res.data['plan']['code'] == 'business'
    assert res.data['subscription_status'] == 'active'
    event = PlatformEvent.objects.get(action='subscription.changed')
    assert event.details['changes']['plan'] == ['starter', 'business'] and event.details['note'] == 'Pago de octubre'
    assert s.globally(lambda: AuditLog.all_tenants.filter(tenant=tenant,
                                                          action='platform.subscription.changed').exists())
    assert api.patch(f'/api/platform/tenants/{tenant.id}/subscription/', {'plan': 'galactico'},
                     format='json').status_code == 400


def test_suspending_requires_a_reason_and_locks_the_company_out(staff, shop):
    _, api = staff
    tenant, _, owner_api = shop
    url = f'/api/platform/tenants/{tenant.id}/status/'
    assert api.post(url, {'status': 'suspended'}, format='json').status_code == 400
    assert api.post(url, {'status': 'suspended', 'reason': 'Solicitud del cliente'}, format='json').status_code == 200
    assert owner_api.get('/api/customers/').status_code == 401
    assert s.globally(lambda: AuditLog.all_tenants.filter(tenant=tenant, action='platform.tenant.suspended').exists())
    assert api.post(url, {'status': 'active'}, format='json').status_code == 200
    assert s.api_for(shop[1]).get('/api/customers/').status_code == 200


def test_plans_are_edited_with_validated_features_and_limits(staff, shop):
    _, api = staff
    plan = Plan.objects.get(code='starter')
    res = api.patch(f'/api/platform/plans/{plan.id}/', {'price_monthly': '49000', 'features': ['module.hr'],
                                                         'limits': {'users': 4, 'products': None}}, format='json')
    assert res.status_code == 200
    assert res.data['price_monthly'] == '49000.00' and res.data['features'] == ['module.hr']
    assert res.data['limits']['users'] == 4 and res.data['limits']['products'] is None
    assert api.patch(f'/api/platform/plans/{plan.id}/', {'features': ['volar']}, format='json').status_code == 400
    assert api.patch(f'/api/platform/plans/{plan.id}/', {'limits': {'naves': 1}}, format='json').status_code == 400
    assert api.patch(f'/api/platform/plans/{plan.id}/', {'is_active': False}, format='json').status_code == 400
    assert PlatformEvent.objects.filter(action='plan.updated').count() == 1


def _support(api, tenant, reason='El cliente no ve sus ventas de ayer'):
    res = api.post(f'/api/platform/tenants/{tenant.id}/support/', {'reason': reason}, format='json')
    assert res.status_code == 201, res.content
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    return client, res.data


def test_support_access_is_read_only_audited_and_visible_to_the_company(staff, shop):
    user, api = staff
    tenant, _, owner_api = shop
    assert api.post(f'/api/platform/tenants/{tenant.id}/support/', {'reason': 'ver'}, format='json').status_code == 400
    sup, data = _support(api, tenant)
    assert sup.get('/api/customers/', {'exclude_final_consumer': 'true'}).data['count'] == 1  # puede consultar
    me = sup.get('/api/auth/me/').data
    assert me['role']['code'] == 'SUPPORT' and me['support']['reason'].startswith('El cliente')
    assert all(p.endswith('.view') or p.endswith('.view_costs') for p in me['permissions'])
    # Ninguna escritura, ni siquiera en vistas sin permisos por rol
    assert sup.post('/api/customers/', {'first_name': 'X'}, format='json').status_code == 403
    assert sup.patch('/api/tenant/', {'name': 'Hackeada'}, format='json').status_code == 403
    assert sup.post('/api/auth/switch-tenant/', {'tenant_id': tenant.id}, format='json').status_code == 403
    assert sup.post('/api/auth/change-password/', {}, format='json').status_code == 403
    tenant.refresh_from_db()
    assert tenant.name == 'Panadería Norte'
    # La empresa lo ve en SU auditoría
    actions = [a['action'] for a in owner_api.get('/api/audit/').data['results']]
    assert 'platform.support.started' in actions
    # Cerrar la sesión invalida el token de inmediato
    assert sup.post('/api/platform/support/end/', format='json').data == {'ended': True}
    assert sup.get('/api/customers/').status_code == 401
    session = SupportSession.objects.get(pk=data['session'])
    assert session.ended_at is not None and session.request_count >= 3
    assert PlatformEvent.objects.filter(action='support.ended', tenant=tenant).exists()


def test_support_token_dies_when_expired_or_when_staff_access_is_revoked(staff, shop):
    user, api = staff
    tenant, _, _ = shop
    sup, data = _support(api, tenant)
    SupportSession.objects.filter(pk=data['session']).update(expires_at=timezone.now() - datetime.timedelta(seconds=1))
    assert sup.get('/api/customers/').status_code == 401
    sup2, _ = _support(api, tenant)
    call_command('platform_admin', user.email, '--revoke')
    assert sup2.get('/api/customers/').status_code == 401


def test_only_staff_can_open_support_and_suspended_companies_cannot_be_entered(staff, shop):
    _, api = staff
    tenant, _, owner_api = shop
    assert owner_api.post(f'/api/platform/tenants/{tenant.id}/support/', {'reason': 'x' * 20},
                          format='json').status_code == 403
    sup, _ = _support(api, tenant)
    api.post(f'/api/platform/tenants/{tenant.id}/status/', {'status': 'suspended', 'reason': 'Mora'}, format='json')
    assert sup.get('/api/customers/').status_code == 401   # suspender cierra el soporte abierto
    assert api.post(f'/api/platform/tenants/{tenant.id}/support/', {'reason': 'x' * 20},
                    format='json').status_code == 400


def test_platform_log_is_immutable(staff, shop):
    user, _ = staff
    event = PlatformEvent.objects.create(actor=user, actor_label=user.email, action='x', summary='y')
    event.summary = 'cambiada'
    with pytest.raises(ValueError):
        event.save()
    with pytest.raises(ValueError):
        event.delete()
