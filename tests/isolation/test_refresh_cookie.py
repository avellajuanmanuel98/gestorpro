"""
Fase 12: el refresh token vive solo en una cookie httpOnly (core/identity/tokens.py).
Un script en la página no puede leerlo; otro sitio no puede usarlo.
"""
import pytest
from rest_framework.test import APIClient

from tests import support as s

pytestmark = [pytest.mark.isolation, pytest.mark.django_db]

REFRESH = '/api/auth/token/refresh/'


@pytest.fixture
def user():
    t = s.make_tenant('Cookie SA')
    return s.make_user(t, 'cookie@sa.co', 'ADMIN')


def login(client, user):
    res = client.post('/api/auth/login/', {'email': user.email, 'password': s.PASSWORD}, format='json')
    assert res.status_code == 200
    return res


def test_the_refresh_token_never_reaches_javascript(user):
    client = APIClient()
    res = login(client, user)
    assert set(res.data) == {'access'}  # el cuerpo solo trae el token corto
    cookie = res.cookies['gp_refresh']
    assert cookie['httponly'] and cookie['secure'] and cookie['samesite'] == 'Strict'
    assert cookie['path'] == '/api/auth/' and int(cookie['max-age']) == 7 * 24 * 3600


def test_each_refresh_rotates_and_the_old_one_dies(user):
    client = APIClient()
    login(client, user)
    first = client.cookies['gp_refresh'].value
    res = client.post(REFRESH)
    assert res.status_code == 200 and set(res.data) == {'access'}
    assert client.cookies['gp_refresh'].value != first
    replay = APIClient()
    replay.cookies['gp_refresh'] = first
    res = replay.post(REFRESH)
    assert res.status_code == 401 and res.cookies['gp_refresh'].value == ''


def test_a_refresh_token_in_the_body_is_ignored(user):
    client = APIClient()
    login(client, user)
    raw = client.cookies['gp_refresh'].value
    assert APIClient().post(REFRESH, {'refresh': raw}, format='json').status_code == 401


def test_another_site_cannot_use_the_cookie(user):
    client = APIClient()
    login(client, user)
    assert client.post(REFRESH, HTTP_ORIGIN='https://sitio-malicioso.example').status_code == 403
    assert client.post(REFRESH, HTTP_ORIGIN='null').status_code == 403
    assert client.post(REFRESH, HTTP_ORIGIN='http://testserver').status_code == 200


def test_switching_company_revokes_the_previous_refresh(user):
    from gestorpro.core.access.services import add_member
    from gestorpro.core.tenancy.context import tenant_context

    other = s.make_tenant('Cookie Dos')
    with tenant_context(other):
        add_member(user=user, role_code='CASHIER')
    client = APIClient()
    access = login(client, user).data['access']
    before = client.cookies['gp_refresh'].value
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
    assert client.post('/api/auth/switch-tenant/', {'tenant_id': other.id}, format='json').status_code == 200
    replay = APIClient()
    replay.cookies['gp_refresh'] = before
    assert replay.post(REFRESH).status_code == 401
