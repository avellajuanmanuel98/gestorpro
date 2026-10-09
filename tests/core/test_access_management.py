"""Usuarios, invitaciones y roles: reglas de seguridad y límites del plan."""
import datetime

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from gestorpro.core.access.models import Invitation, Membership, Role
from gestorpro.core.tenancy.context import tenant_context
from tests import support as s

pytestmark = pytest.mark.django_db


@pytest.fixture
def org():
    t = s.make_tenant('Panadería Equipo')
    owner = Membership.all_tenants.get(tenant=t, role__code='OWNER').user
    admin = s.make_user(t, 'admin@eq.co', 'ADMIN')
    cashier = s.make_user(t, 'caja@eq.co', 'CASHIER')
    with tenant_context(t):
        roles = {r.code: r for r in Role.objects.all()}
        members = {m.user.email: m for m in Membership.objects.select_related('user')}
    return {'t': t, 'owner': _api(owner),
            'admin': s.api_for(admin), 'cashier': s.api_for(cashier), 'roles': roles, 'members': members,
            'owner_user': owner}


def _api(user):
    """Login real (los owners de make_tenant usan la misma contraseña de prueba)."""
    client = APIClient()
    tokens = client.post(s.ENDPOINTS['login'], {'email': user.email, 'password': s.PASSWORD}, format='json').data
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


def invite(api, email, role):
    return api.post('/api/access/invitations/', {'email': email, 'role': role.id}, format='json')


# ── Invitaciones ─────────────────────────────────────────────────────────────

def test_invitation_flow_creates_account_and_membership(org):
    res = invite(org['admin'], 'nuevo@eq.co', org['roles']['CASHIER'])
    assert res.status_code == 201
    token = res.data['invite_url'].rsplit('/', 1)[1]
    preview = APIClient().get(f'/api/auth/invitation/{token}/').data
    assert preview == {'email': 'nuevo@eq.co', 'tenant_name': 'Panadería Equipo', 'role_name': 'Cajero',
                       'account_exists': False}
    accepted = APIClient().post('/api/auth/accept-invitation/', {
        'token': token, 'password': 'Pan-de-yuca-2026', 'first_name': 'Nuevo', 'last_name': 'Cajero',
    }, format='json')
    assert accepted.status_code == 201
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {accepted.data['access']}")
    me = client.get('/api/auth/me/').data
    assert me['tenant']['name'] == 'Panadería Equipo' and me['role']['code'] == 'CASHIER'
    # El token es de un solo uso
    again = APIClient().post('/api/auth/accept-invitation/', {'token': token, 'password': 'x'}, format='json')
    assert again.status_code == 400


def test_token_is_not_stored_in_clear(org):
    res = invite(org['admin'], 'hash@eq.co', org['roles']['CASHIER'])
    token = res.data['invite_url'].rsplit('/', 1)[1]
    assert not Invitation.all_tenants.filter(token_hash=token).exists()


def test_existing_account_must_prove_identity(org):
    other = s.make_tenant('Otra')
    existing = s.make_user(other, 'existe@x.co', 'ADMIN')
    token = invite(org['admin'], existing.email, org['roles']['CASHIER']).data['invite_url'].rsplit('/', 1)[1]
    wrong = APIClient().post('/api/auth/accept-invitation/', {'token': token, 'password': 'mala'}, format='json')
    assert wrong.status_code == 400
    ok = APIClient().post('/api/auth/accept-invitation/', {'token': token, 'password': s.PASSWORD}, format='json')
    assert ok.status_code == 201
    assert Membership.all_tenants.filter(user=existing).count() == 2  # ahora es multiempresa


def test_expired_and_revoked_invitations_are_rejected(org):
    res = invite(org['admin'], 'vence@eq.co', org['roles']['CASHIER'])
    token = res.data['invite_url'].rsplit('/', 1)[1]
    Invitation.all_tenants.filter(pk=res.data['id']).update(expires_at=timezone.now() - datetime.timedelta(seconds=1))
    assert APIClient().get(f'/api/auth/invitation/{token}/').status_code == 404
    res = invite(org['admin'], 'revoca@eq.co', org['roles']['CASHIER'])
    token = res.data['invite_url'].rsplit('/', 1)[1]
    assert org['admin'].delete(f"/api/access/invitations/{res.data['id']}/").status_code == 204
    assert APIClient().post('/api/auth/accept-invitation/', {'token': token, 'password': 'Pan-de-yuca-2026',
                                                              'first_name': 'X'}, format='json').status_code == 400


def test_cashier_cannot_invite(org):
    assert invite(org['cashier'], 'x@eq.co', org['roles']['CASHIER']).status_code == 403


# ── Anti-escalada y protección de propietarios ───────────────────────────────

def test_admin_cannot_grant_owner_role(org):
    assert invite(org['admin'], 'jefe@eq.co', org['roles']['OWNER']).status_code == 403
    cashier = org['members']['caja@eq.co']
    res = org['admin'].patch(f'/api/access/members/{cashier.id}/', {'role': org['roles']['OWNER'].id}, format='json')
    assert res.status_code == 403


def test_admin_cannot_touch_owner_nor_self(org):
    owner_m = org['members'][org['owner_user'].email]
    admin_m = org['members']['admin@eq.co']
    assert org['admin'].patch(f'/api/access/members/{owner_m.id}/', {'status': 'suspended'},
                              format='json').status_code == 403
    assert org['admin'].delete(f'/api/access/members/{admin_m.id}/').status_code == 403


def test_owner_can_demote_another_owner_but_not_themselves(org):
    second_owner = s.make_user(org['t'], 'socio@eq.co', 'OWNER')
    first = org['members'][org['owner_user'].email]
    api = s.api_for(second_owner)
    assert api.patch(f'/api/access/members/{first.id}/', {'role': org['roles']['ADMIN'].id},
                     format='json').status_code == 200
    me = Membership.all_tenants.get(user=second_owner)
    assert api.patch(f'/api/access/members/{me.id}/', {'role': org['roles']['ADMIN'].id},
                     format='json').status_code == 403


def test_service_never_leaves_company_without_active_owner(org):
    """
    Por la API esta regla no se alcanza (quien modifica a un propietario es otro
    propietario activo), pero el servicio la garantiza igualmente: defensa en profundidad.
    """
    from rest_framework.exceptions import ValidationError

    from gestorpro.core.access.services import _assert_keeps_an_owner
    with tenant_context(org['t']):
        only_owner = Membership.objects.select_related('role').get(role__grants_all=True)
        with pytest.raises(ValidationError):
            _assert_keeps_an_owner(only_owner, removing=True)
        with pytest.raises(ValidationError):
            _assert_keeps_an_owner(only_owner, new_status=Membership.Status.SUSPENDED)
        _assert_keeps_an_owner(only_owner, new_status=Membership.Status.ACTIVE)  # sin cambios: permitido


def test_suspending_a_member_cuts_access_immediately(org):
    cashier_m = org['members']['caja@eq.co']
    assert org['admin'].patch(f'/api/access/members/{cashier_m.id}/', {'status': 'suspended'},
                              format='json').status_code == 200
    assert org['cashier'].get(s.ENDPOINTS['customers']).status_code == 401


def test_custom_role_cannot_exceed_creator_permissions(org):
    with tenant_context(org['t']):
        supervisor = Role.objects.get(code='SUPERVISOR')
        supervisor.permissions.add('access.manage_roles', 'access.view')
    sup_api = s.api_for(s.make_user(org['t'], 'sup@eq.co', 'SUPERVISOR'))
    res = sup_api.post('/api/access/roles/', {'name': 'Hornero', 'permissions': ['catalog.view', 'catalog.manage']},
                       format='json')
    assert res.status_code == 403  # el supervisor no tiene catalog.manage
    res = sup_api.post('/api/access/roles/', {'name': 'Hornero', 'permissions': ['catalog.view']}, format='json')
    assert res.status_code == 201 and res.data['permissions'] == ['catalog.view']


def test_owner_role_and_system_roles_are_protected(org):
    owner_role, cashier_role = org['roles']['OWNER'], org['roles']['CASHIER']
    assert org['admin'].patch(f'/api/access/roles/{owner_role.id}/', {'permissions': []},
                              format='json').status_code == 400
    assert org['admin'].delete(f'/api/access/roles/{cashier_role.id}/').status_code == 400
    assert org['admin'].patch(f'/api/access/roles/{cashier_role.id}/', {'name': 'Otro'},
                              format='json').status_code == 400


# ── Límites del plan ─────────────────────────────────────────────────────────

def test_user_limit_of_plan_is_enforced():
    t = s.make_tenant('Pequeña', plan_code='starter')  # starter: 3 usuarios
    with tenant_context(t):
        cashier_role = Role.objects.get(code='CASHIER')
    owner = Membership.all_tenants.get(tenant=t).user
    api = _api(owner)
    assert invite(api, 'u2@p.co', cashier_role).status_code == 201
    assert invite(api, 'u3@p.co', cashier_role).status_code == 201
    res = invite(api, 'u4@p.co', cashier_role)
    assert res.status_code == 403
    assert 'Tu plan permite 3' in str(res.data['detail'])


def test_custom_roles_require_plan_feature():
    t = s.make_tenant('SinRoles', plan_code='starter')
    api = _api(Membership.all_tenants.get(tenant=t).user)
    res = api.post('/api/access/roles/', {'name': 'Hornero', 'permissions': ['catalog.view']}, format='json')
    assert res.status_code == 403


def test_modules_outside_plan_are_blocked_in_backend():
    t = s.make_tenant('Basica', plan_code='starter')  # starter no incluye module.hr
    api = _api(Membership.all_tenants.get(tenant=t).user)
    assert api.get(s.ENDPOINTS['employees']).status_code == 403
    me = api.get('/api/auth/me/').data
    assert me['plan']['code'] == 'starter' and 'module.hr' not in me['features']
    plan = api.get('/api/tenant/plan/').data
    users = next(item for item in plan['limits'] if item['key'] == 'users')
    assert users == {'key': 'users', 'label': users['label'], 'used': 1, 'limit': 3}


def test_new_signup_starts_trial_of_default_plan():
    client = APIClient()
    res = client.post('/api/auth/register/', {
        'email': 'nueva@pan.co', 'first_name': 'N', 'last_name': 'P',
        'password': 'Pan-de-bono-2026', 'password2': 'Pan-de-bono-2026', 'company_name': 'Nueva',
    }, format='json')
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    me = client.get('/api/auth/me/').data
    assert me['plan']['code'] == 'starter' and me['plan']['status'] == 'trialing'


def test_bakery_vertical_seeds_default_categories():
    from gestorpro.core.access.services import provision_tenant
    from gestorpro.core.catalog.models import Category
    from gestorpro.core.identity.models import User
    owner = User.objects.create_user(email='p@miga.co', password=s.PASSWORD, first_name='P', last_name='M')
    t = provision_tenant(name='Miga Test', owner=owner, vertical='bakery')
    with tenant_context(t):
        assert Category.objects.filter(name='Panes rellenos').exists()
    generic = s.make_tenant('Ferreteria')
    with tenant_context(generic):
        assert not Category.objects.exists()


def test_set_plan_command_changes_plan():
    from django.core.management import call_command
    t = s.make_tenant('Cambio Plan', plan_code='starter')
    call_command('set_plan', t.slug, 'business', '--active')
    from gestorpro.core.entitlements import for_tenant
    ent = for_tenant(t.id)
    assert ent.plan_code == 'business' and ent.status == 'active' and ent.has('module.hr')
