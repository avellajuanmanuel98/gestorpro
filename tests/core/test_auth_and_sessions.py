"""Autenticación multiempresa: membresías, cambio de empresa, revocación."""
import io

import pytest

from gestorpro.core.access.models import Membership
from gestorpro.core.tenancy.context import tenant_context
from gestorpro.core.tenancy.models import Tenant
from tests import support as s

pytestmark = [pytest.mark.isolation, pytest.mark.django_db]


@pytest.fixture
def setup():
    a, b = s.make_tenant('Sede A'), s.make_tenant('Sede B')
    user = s.make_user(a, 'multi@x.co', 'ADMIN')
    from gestorpro.core.access.services import add_member
    with tenant_context(b):
        add_member(user=user, role_code='CASHIER')
    s.make_customer(a, first_name='SoloA')
    s.make_customer(b, first_name='SoloB')
    return a, b, user


def names(api):
    # El "Consumidor final" lo crea el alta de cada empresa; no distingue entre ellas
    return {c['full_name'].split()[0] for c in s.results(api.get(s.ENDPOINTS['customers']))} - {'Consumidor'}


def test_multi_company_user_only_sees_active_company(setup):
    a, b, user = setup
    api = s.api_for(user)
    me = api.get('/api/auth/me/').data
    assert me['tenant']['id'] in (a.id, b.id)
    assert len(me['memberships']) == 2
    assert names(api) == ({'SoloA'} if me['tenant']['id'] == a.id else {'SoloB'})


def test_switch_tenant_changes_scope_and_role(setup):
    a, b, user = setup
    api = s.api_for(user)
    res = api.post('/api/auth/switch-tenant/', {'tenant_id': b.id}, format='json')
    assert res.status_code == 200
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    me = api.get('/api/auth/me/').data
    assert me['tenant']['id'] == b.id and me['role']['code'] == 'CASHIER'
    assert names(api) == {'SoloB'}
    # En B es cajero: no puede borrar clientes
    cid = s.results(api.get(s.ENDPOINTS['customers']))[0]['id']
    assert api.delete(f"{s.ENDPOINTS['customers']}{cid}/").status_code == 403


def test_cannot_switch_to_company_without_membership(setup):
    _, _, user = setup
    other = s.make_tenant('Ajena')
    res = s.api_for(user).post('/api/auth/switch-tenant/', {'tenant_id': other.id}, format='json')
    assert res.status_code == 403


def test_suspended_membership_is_revoked_immediately(setup):
    a, b, user = setup
    api = s.api_for(user)
    tid = api.get('/api/auth/me/').data['tenant']['id']
    s.globally(lambda: Membership.all_tenants.filter(user=user, tenant_id=tid)
               .update(status=Membership.Status.SUSPENDED))
    assert api.get(s.ENDPOINTS['customers']).status_code == 401


def test_suspended_tenant_is_revoked_immediately(setup):
    a, b, user = setup
    api = s.api_for(user)
    tid = api.get('/api/auth/me/').data['tenant']['id']
    Tenant.objects.filter(pk=tid).update(status=Tenant.Status.SUSPENDED)
    assert api.get(s.ENDPOINTS['customers']).status_code == 401


def test_logout_revokes_refresh_token(setup):
    from rest_framework.test import APIClient
    _, _, user = setup
    client = APIClient()
    tokens = client.post('/api/auth/login/', {'email': user.email, 'password': s.PASSWORD}, format='json').data
    stolen = client.cookies['gp_refresh'].value
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert client.post('/api/auth/logout/').status_code == 204
    assert client.cookies['gp_refresh'].value == ''  # el navegador la borra
    replay = APIClient()
    replay.cookies['gp_refresh'] = stolen
    assert replay.post('/api/auth/token/refresh/').status_code == 401


def test_refreshed_access_token_keeps_tenant(setup):
    from rest_framework.test import APIClient
    _, b, user = setup
    api = s.api_for(user)
    api.post('/api/auth/switch-tenant/', {'tenant_id': b.id}, format='json')
    refreshed = api.post('/api/auth/token/refresh/').data  # el refresh viaja en la cookie del cliente
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refreshed['access']}")
    assert client.get('/api/auth/me/').data['tenant']['id'] == b.id


def test_wrong_password_is_rejected():
    from rest_framework.test import APIClient
    res = APIClient().post('/api/auth/login/', {'email': 'nadie@x.co', 'password': 'x'}, format='json')
    assert res.status_code == 400


def test_register_provisions_company_with_owner_roles_and_location():
    from rest_framework.test import APIClient
    client = APIClient()
    res = client.post('/api/auth/register/', {
        'email': 'duena@miga.co', 'first_name': 'Ana', 'last_name': 'Pérez',
        'password': 'Pan-de-bono-2026', 'password2': 'Pan-de-bono-2026', 'company_name': 'Panadería La Espiga',
    }, format='json')
    assert res.status_code == 201, res.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    me = client.get('/api/auth/me/').data
    assert me['tenant']['name'] == 'Panadería La Espiga'
    assert me['role']['code'] == 'OWNER'
    assert 'billing.override_price' in me['permissions']
    locations = client.get('/api/tenant/locations/').data
    assert [loc['name'] for loc in locations] == ['Principal']


def test_platform_admin_without_membership_has_no_tenant_data_access(setup):
    from django.core.management import call_command

    from gestorpro.core.identity.models import User
    staff = User.objects.create_superuser(email='staff@gestorpro.co', password=s.PASSWORD,
                                          first_name='S', last_name='S')
    call_command('platform_admin', staff.email, stdout=io.StringIO())  # su clave de verificación en dos pasos
    client = s.api_for(staff)
    assert client.get(s.ENDPOINTS['customers']).status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize('vertical,brand_category', [('bakery', True), ('generic', False), (None, False)])
def test_registration_sets_the_business_type(vertical, brand_category):
    from rest_framework.test import APIClient

    from gestorpro.core.catalog.models import Category
    from gestorpro.core.tenancy.context import tenant_context
    from gestorpro.core.tenancy.models import Tenant
    payload = {'email': f'nuevo-{vertical}@neg.co', 'first_name': 'Ana', 'last_name': 'Ruiz',
               'password': 'Pan-Nuevo-2026!', 'password2': 'Pan-Nuevo-2026!', 'company_name': f'Negocio {vertical}'}
    if vertical:
        payload['vertical'] = vertical
    res = APIClient().post('/api/auth/register/', payload, format='json')
    assert res.status_code == 201, res.content
    tenant = Tenant.objects.get(name=f'Negocio {vertical}')
    assert tenant.vertical == (vertical or 'generic')
    with tenant_context(tenant):  # solo las panaderías reciben la configuración de Miga
        assert Category.objects.filter(name='Panes').exists() is brand_category


@pytest.mark.django_db
def test_registration_rejects_unknown_business_type():
    from rest_framework.test import APIClient
    res = APIClient().post('/api/auth/register/', {
        'email': 'x@neg.co', 'first_name': 'A', 'last_name': 'B', 'password': 'Pan-Nuevo-2026!',
        'password2': 'Pan-Nuevo-2026!', 'company_name': 'X', 'vertical': 'banco'}, format='json')
    assert res.status_code == 400 and 'vertical' in res.data


# ── Bloqueo por cuenta (Fase 12) ────────────────────────────────────────────

def _try(client, email, password):
    return client.post('/api/auth/login/', {'email': email, 'password': password}, format='json')


def test_repeated_wrong_passwords_lock_the_account_whatever_the_ip(settings):
    from rest_framework.test import APIClient

    settings.LOGIN_LOCKOUT_FAILURES = 3
    user = s.make_user_without_tenant('victima@lock.co')
    for i in range(3):  # cada intento desde una IP distinta: el límite por IP no lo frenaría
        assert _try(APIClient(REMOTE_ADDR=f'10.0.0.{i}'), user.email, 'mala').status_code == 400
    locked = _try(APIClient(REMOTE_ADDR='10.9.9.9'), user.email, s.PASSWORD)
    assert locked.status_code == 429 and 'Olvidaste' in locked.data['detail']  # ni la correcta entra
    # Otro correo no se afecta, y un correo inexistente se bloquea igual (no revela cuáles existen)
    other = s.make_user_without_tenant('otra@lock.co')
    assert _try(APIClient(), other.email, s.PASSWORD).status_code == 200
    for _ in range(3):
        _try(APIClient(), 'nadie@lock.co', 'x')
    assert _try(APIClient(), 'NADIE@lock.co ', 'x').status_code == 429


def test_the_lock_expires_and_a_success_resets_the_count(settings):
    import datetime
    from unittest import mock

    from django.utils import timezone
    from rest_framework.test import APIClient

    settings.LOGIN_LOCKOUT_FAILURES = 3
    user = s.make_user_without_tenant('pasa@lock.co')
    for _ in range(2):
        _try(APIClient(), user.email, 'mala')
    assert _try(APIClient(), user.email, s.PASSWORD).status_code == 200  # éxito: el conteo vuelve a cero
    for _ in range(2):
        _try(APIClient(), user.email, 'mala')
    assert _try(APIClient(), user.email, s.PASSWORD).status_code == 200
    for _ in range(3):
        _try(APIClient(), user.email, 'mala')
    assert _try(APIClient(), user.email, s.PASSWORD).status_code == 429
    later = timezone.now() + datetime.timedelta(minutes=16)  # el registro es de solo inserción: se adelanta el reloj
    with mock.patch('gestorpro.core.identity.lockout.timezone.now', return_value=later):
        assert _try(APIClient(), user.email, s.PASSWORD).status_code == 200
