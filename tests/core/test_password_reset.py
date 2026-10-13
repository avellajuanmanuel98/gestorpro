"""Recuperar o restablecer la contraseña con un enlace de un solo uso, sin que nadie más la conozca."""
import re

import pytest
from django.core import mail
from django.core.management import call_command
from rest_framework.test import APIClient

from gestorpro.core.access.services import add_member
from gestorpro.core.audit.models import AuditLog, SecurityEvent
from gestorpro.core.tenancy.context import tenant_context
from tests import support as s

pytestmark = pytest.mark.django_db
NEW = 'Clave-Nueva-Segura-2026'


def parts(url):
    uid, token = re.search(r'/reset-password/([^/]+)/([^/]+)$', url).groups()
    return f'/api/auth/password/reset/{uid}/{token}/'


def login(email, password):
    return APIClient().post('/api/auth/login/', {'email': email, 'password': password}, format='json').status_code


@pytest.fixture
def shop():
    tenant = s.make_tenant('Contraseñas')
    owner = s.make_user(tenant, 'duena@cla.co', 'OWNER')
    admin = s.make_user(tenant, 'adm@cla.co', 'ADMIN')
    cashier = s.make_user(tenant, 'caja@cla.co', 'CASHIER')
    return {'t': tenant, 'owner': owner, 'admin': admin, 'cashier': cashier}


def member_id(api, email):
    return next(m['id'] for m in api.get('/api/access/members/').data['results'] if m['email'] == email)


def test_admin_gives_a_one_time_link_and_never_learns_the_password(shop):
    api = s.api_for(shop['admin'])
    old = APIClient()  # una sesión abierta antes del cambio (su refresh queda en la cookie)
    old.post('/api/auth/login/', {'email': 'caja@cla.co', 'password': s.PASSWORD}, format='json')
    res = api.post(f"/api/access/members/{member_id(api, 'caja@cla.co')}/reset-link/")
    assert res.status_code == 200 and res.data['hours'] == 24
    url = parts(res.data['url'])
    anon = APIClient()
    assert anon.get(url).data == {'valid': True, 'email': 'ca••@cla.co'}
    assert anon.post(url, {'password': NEW, 'password2': 'otra'}, format='json').status_code == 400
    assert anon.post(url, {'password': '123', 'password2': '123'}, format='json').status_code == 400
    assert anon.post(url, {'password': NEW, 'password2': NEW}, format='json').status_code == 200
    assert login('caja@cla.co', NEW) == 200 and login('caja@cla.co', s.PASSWORD) == 400
    # Un solo uso, y la sesión que tenía abierta se cierra
    assert anon.get(url).data['valid'] is False
    assert anon.post(url, {'password': NEW, 'password2': NEW}, format='json').status_code == 400
    assert old.post('/api/auth/token/refresh/').status_code == 401
    assert s.globally(lambda: AuditLog.all_tenants.filter(tenant=shop['t'],
                                                          action='access.password_reset_link').exists())
    assert SecurityEvent.objects.filter(kind='password_reset', user=shop['cashier']).exists()


def test_links_cannot_be_used_to_take_over_accounts(shop):
    admin = s.api_for(shop['admin'])
    owner = s.api_for(shop['owner'])
    # Un administrador no puede para un propietario; el propietario sí para otro propietario
    assert admin.post(f"/api/access/members/{member_id(admin, 'duena@cla.co')}/reset-link/").status_code == 403
    # Nadie para sí mismo
    assert admin.post(f"/api/access/members/{member_id(admin, 'adm@cla.co')}/reset-link/").status_code == 400
    # Quien también usa otra empresa: solo por correo o soporte
    other = s.make_tenant('Otra empresa')
    with tenant_context(other):
        add_member(user=shop['cashier'], role_code='OWNER')
    res = owner.post(f"/api/access/members/{member_id(owner, 'caja@cla.co')}/reset-link/")
    assert res.status_code == 400 and 'otra empresa' in str(res.data)
    # Sin permiso de gestionar usuarios
    supervisor = s.api_for(s.make_user(shop['t'], 'sup@cla.co', 'SUPERVISOR'))
    assert supervisor.post(f"/api/access/members/{member_id(admin, 'adm@cla.co')}/reset-link/").status_code == 403


def test_forgot_password_never_reveals_who_has_an_account(shop, settings):
    settings.EMAIL_ENABLED = True
    anon = APIClient()
    for email in ('caja@cla.co', 'nadie@cla.co'):
        res = anon.post('/api/auth/password/forgot/', {'email': email}, format='json')
        assert res.status_code == 200 and res.data == {'email_enabled': True}
    assert len(mail.outbox) == 1 and mail.outbox[0].to == ['caja@cla.co']
    url = parts(re.search(r'http\S+/reset-password/\S+', mail.outbox[0].body).group(0))
    assert anon.post(url, {'password': NEW, 'password2': NEW}, format='json').status_code == 200
    assert login('caja@cla.co', NEW) == 200


def test_without_email_configured_nothing_is_sent(shop, settings):
    settings.EMAIL_ENABLED = False
    res = APIClient().post('/api/auth/password/forgot/', {'email': 'caja@cla.co'}, format='json')
    assert res.data == {'email_enabled': False} and len(mail.outbox) == 0


def test_platform_support_can_send_a_link_audited_in_both_logs(shop):
    staff = s._user('soporte@gestorpro.co')
    call_command('platform_admin', staff.email)
    api = s.api_for(staff)
    url = f"/api/platform/tenants/{shop['t'].id}/reset-link/"
    res = api.post(url, {'email': 'duena@cla.co'}, format='json')
    assert res.status_code == 200 and '/reset-password/' in res.data['invitation_url']
    assert api.post(url, {'email': 'extrano@otro.co'}, format='json').status_code == 400
    assert s.globally(lambda: AuditLog.all_tenants.filter(tenant=shop['t'],
                                                          action='platform.password_reset_link').exists())
    assert s.api_for(shop['owner']).post(url, {'email': 'caja@cla.co'}, format='json').status_code == 403


def test_a_tampered_link_is_rejected(shop):
    api = s.api_for(shop['admin'])
    url = parts(api.post(f"/api/access/members/{member_id(api, 'caja@cla.co')}/reset-link/").data['url'])
    bad = url.replace(url.rsplit('/', 2)[1], 'x' + url.rsplit('/', 2)[1][1:])
    assert APIClient().get(bad).data['valid'] is False
    assert APIClient().get('/api/auth/password/reset/zzz/zzz/').data['valid'] is False
