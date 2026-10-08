"""Autenticación multiempresa: membresías, cambio de empresa, revocación."""
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
    return {c['full_name'].split()[0] for c in s.results(api.get(s.ENDPOINTS['customers']))}


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
    Membership.all_tenants.filter(user=user, tenant_id=tid).update(status=Membership.Status.SUSPENDED)
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
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert client.post('/api/auth/logout/', {'refresh': tokens['refresh']}, format='json').status_code == 204
    res = APIClient().post('/api/auth/token/refresh/', {'refresh': tokens['refresh']}, format='json')
    assert res.status_code == 401


def test_refreshed_access_token_keeps_tenant(setup):
    from rest_framework.test import APIClient
    _, b, user = setup
    api = s.api_for(user)
    tokens = api.post('/api/auth/switch-tenant/', {'tenant_id': b.id}, format='json').data
    refreshed = APIClient().post('/api/auth/token/refresh/', {'refresh': tokens['refresh']}, format='json').data
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
    from gestorpro.core.identity.models import User
    User.objects.create_superuser(email='staff@gestorpro.co', password=s.PASSWORD, first_name='S', last_name='S')
    from rest_framework.test import APIClient
    client = APIClient()
    tokens = client.post('/api/auth/login/', {'email': 'staff@gestorpro.co', 'password': s.PASSWORD},
                         format='json').data
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert client.get(s.ENDPOINTS['customers']).status_code == 403
