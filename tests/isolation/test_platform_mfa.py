"""
Fase 12: verificación en dos pasos del personal de la plataforma (core/identity/mfa.py).
Quien puede entrar a cualquier empresa en modo soporte no entra solo con contraseña.
"""
import io

import pytest
from django.core.management import call_command
from django.test import Client
from rest_framework.test import APIClient

from gestorpro.core.audit.models import SecurityEvent
from gestorpro.core.identity import mfa
from tests import support as s

pytestmark = [pytest.mark.isolation, pytest.mark.django_db]

LOGIN, VERIFY = '/api/auth/login/', '/api/auth/mfa/verify/'


@pytest.fixture
def staff():
    user = s._user('equipo@gestorpro.co')
    out = io.StringIO()
    call_command('platform_admin', user.email, stdout=out)
    user.refresh_from_db()
    return user, out.getvalue()


def password_step(client, user, password=s.PASSWORD):
    return client.post(LOGIN, {'email': user.email, 'password': password}, format='json')


def test_the_rfc_6238_reference_vector():
    # RFC 6238, apéndice B (SHA-1, T=59 s → 94287082; 6 dígitos = 287082)
    secret = '12345678901234567890'
    import base64
    b32 = base64.b32encode(secret.encode()).decode().rstrip('=')
    assert mfa.code_at(b32, 59 // 30) == '287082'


def test_the_key_is_created_by_the_server_command_and_shown_once(staff):
    user, output = staff
    assert user.is_platform_admin and user.totp_secret and user.totp_confirmed_at is None
    assert 'otpauth://totp/GestorPro' in output and 'UNA sola vez' in output
    again = io.StringIO()
    call_command('platform_admin', user.email, stdout=again)
    assert 'ya está configurada' in again.getvalue()  # repetir el comando no cambia la clave
    assert type(user).objects.get(pk=user.pk).totp_secret == user.totp_secret


def test_the_password_alone_gives_no_tokens(staff):
    user, _ = staff
    res = password_step(APIClient(), user)
    assert res.status_code == 200 and res.data['mfa'] == 'verify'
    assert 'access' not in res.data and 'gp_refresh' not in res.cookies
    # El mfa_token no sirve como sesión
    api = APIClient()
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['mfa_token']}")
    assert api.get('/api/platform/overview/').status_code == 401


def test_the_right_code_logs_in_and_cannot_be_replayed(staff):
    user, _ = staff
    client = APIClient()
    token = password_step(client, user).data['mfa_token']
    code = s.current_code(user)
    ok = client.post(VERIFY, {'mfa_token': token, 'code': code}, format='json')
    assert ok.status_code == 200 and 'access' in ok.data and 'gp_refresh' in ok.cookies
    user.refresh_from_db()
    assert user.totp_confirmed_at is not None
    # Mismo código otra vez (alguien que lo vio por encima del hombro): no
    again = password_step(APIClient(), user).data['mfa_token']
    assert APIClient().post(VERIFY, {'mfa_token': again, 'code': code}, format='json').status_code == 400


def test_wrong_codes_count_toward_the_account_lockout(staff, settings):
    settings.LOGIN_LOCKOUT_FAILURES = 3
    user, _ = staff
    for _ in range(3):
        token = password_step(APIClient(), user).data['mfa_token']
        assert APIClient().post(VERIFY, {'mfa_token': token, 'code': '000000'}, format='json').status_code == 400
    assert SecurityEvent.objects.filter(user=user, kind=SecurityEvent.Kind.MFA_FAILED).count() == 3
    assert password_step(APIClient(), user).status_code == 429  # ni la contraseña se verifica ya


def test_a_tampered_or_stale_mfa_token_is_rejected(staff):
    user, _ = staff
    token = password_step(APIClient(), user).data['mfa_token']
    code = s.current_code(user)
    assert APIClient().post(VERIFY, {'mfa_token': token[:-2] + 'xx', 'code': code}, format='json').status_code == 400
    user.set_password('Otra-Clave-Segura-2026')
    user.save()
    res = APIClient().post(VERIFY, {'mfa_token': token, 'code': code}, format='json')
    assert res.status_code == 400 and res.data['code'] == 'mfa_expired'  # cambió la contraseña: el puente muere


def test_staff_without_a_key_cannot_log_in_and_is_told_how_to_fix_it():
    user = s._user('nuevo@gestorpro.co')
    type(user).objects.filter(pk=user.pk).update(is_platform_admin=True, is_staff=True)
    res = password_step(APIClient(), user)
    assert res.status_code == 403 and res.data['code'] == 'mfa_not_enrolled'


def test_lost_phone_reset_invalidates_the_old_key(staff):
    user, _ = staff
    old = user.totp_secret
    call_command('platform_admin', user.email, '--reset-2fa', stdout=io.StringIO())
    user.refresh_from_db()
    assert user.totp_secret and user.totp_secret != old
    token = password_step(APIClient(), user).data['mfa_token']
    old_code = mfa.code_at(old, mfa.current_step())
    assert APIClient().post(VERIFY, {'mfa_token': token, 'code': old_code}, format='json').status_code == 400


def test_regular_users_are_not_asked_for_a_code():
    t = s.make_tenant('Sin MFA')
    user = s.make_user(t, 'cajera@sinmfa.co', 'CASHIER')
    res = password_step(APIClient(), user)
    assert res.status_code == 200 and 'access' in res.data and 'mfa' not in res.data


def test_the_django_admin_also_requires_the_code(staff):
    user, _ = staff
    browser = Client()
    page = browser.get('/admin/login/')
    assert 'name="code"' in page.content.decode()
    no_code = browser.post('/admin/login/', {'username': user.email, 'password': s.PASSWORD, 'code': '000000'})
    assert no_code.status_code == 200 and '_auth_user_id' not in browser.session
    ok = browser.post('/admin/login/', {'username': user.email, 'password': s.PASSWORD,
                                        'code': s.current_code(user)})
    assert ok.status_code == 302 and browser.session['_auth_user_id'] == str(user.pk)
