"""
Verificación en dos pasos (TOTP, RFC 6238) para el personal de la plataforma.

Quien tiene `is_platform_admin` puede entrar en modo soporte a cualquier
empresa: su contraseña sola no basta. Después de la contraseña debe dar el
código de 6 dígitos de una app autenticadora (Google Authenticator, Microsoft
Authenticator, 1Password…).

La clave se crea SOLO por línea de comandos (`manage.py platform_admin <email>`),
por quien administra el servidor, y se escanea en ese momento. El login nunca
ofrece configurarla: así, quien robe solo una contraseña no puede registrar su
propio celular.

- Sin dependencias: HMAC-SHA1, pasos de 30 s, 6 dígitos (lo que usan todas las apps).
- Se acepta el paso actual y uno antes o después (desfase de reloj del celular).
- Un código no se puede reutilizar: se guarda el último paso aceptado.
- Entre la contraseña y el código, el navegador solo tiene un `mfa_token`
  firmado, de 5 minutos, que no sirve para nada más y deja de valer si cambia
  la contraseña.
- Los códigos fallidos cuentan para el bloqueo por cuenta (lockout.py).
- Si alguien del equipo pierde el celular: `manage.py platform_admin <email> --reset-2fa`
  genera una clave nueva (la anterior deja de servir).
"""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

from django.contrib.auth import get_user_model
from django.core import signing
from django.utils import timezone

STEP_SECONDS = 30
DIGITS = 6
DRIFT_STEPS = 1
TOKEN_MAX_AGE = 300
ISSUER = 'GestorPro'
_SALT = 'gestorpro.identity.mfa'


def required_for(user) -> bool:
    return bool(user.is_platform_admin)


def new_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip('=')


def provisioning_uri(user, secret: str) -> str:
    label = quote(f'{ISSUER}:{user.email}')
    return f'otpauth://totp/{label}?secret={secret}&issuer={ISSUER}&digits={DIGITS}&period={STEP_SECONDS}'


def code_at(secret: str, step: int) -> str:
    key = base64.b32decode(secret + '=' * (-len(secret) % 8))
    digest = hmac.new(key, struct.pack('>Q', step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % 10 ** DIGITS).zfill(DIGITS)


def current_step(now: float | None = None) -> int:
    return int((time.time() if now is None else now) // STEP_SECONDS)


def matching_step(secret: str, code: str, last_step: int | None, now: float | None = None) -> int | None:
    """El paso que corresponde al código, si es válido y posterior al último usado."""
    code = ''.join(ch for ch in str(code or '') if ch.isdigit())
    if len(code) != DIGITS or not secret:
        return None
    base = current_step(now)
    for step in range(base - DRIFT_STEPS, base + DRIFT_STEPS + 1):
        if last_step is not None and step <= last_step:
            continue  # ya usado (o anterior a uno usado): no se reutiliza
        if hmac.compare_digest(code_at(secret, step), code):
            return step
    return None


# ── mfa_token: el puente entre la contraseña y el código ────────────────────

def challenge_token(user) -> str:
    # El hash de la contraseña entra en la firma: si cambia, el token deja de valer
    return signing.dumps({'u': user.pk, 'p': user.password[-16:]}, salt=_SALT, compress=True)


def user_from_token(token: str):
    try:
        data = signing.loads(str(token or ''), salt=_SALT, max_age=TOKEN_MAX_AGE)
    except signing.BadSignature:
        return None
    user = get_user_model().objects.filter(pk=data.get('u'), is_active=True).first()
    if user is None or user.password[-16:] != data.get('p') or not required_for(user):
        return None
    return user


def challenge(user) -> dict | None:
    """Respuesta del login cuando falta el código; None si la cuenta aún no tiene clave."""
    if not user.totp_secret:
        return None
    return {'mfa': 'verify', 'mfa_token': challenge_token(user)}


def enroll(user) -> dict:
    """Clave nueva (reemplaza la anterior). Solo desde el comando platform_admin."""
    user.totp_secret, user.totp_last_step, user.totp_confirmed_at = new_secret(), None, None
    user.save(update_fields=['totp_secret', 'totp_last_step', 'totp_confirmed_at'])
    grouped = ' '.join(user.totp_secret[i:i + 4] for i in range(0, len(user.totp_secret), 4))
    return {'secret': grouped, 'uri': provisioning_uri(user, user.totp_secret)}


def verify(user, code: str) -> bool:
    """Valida el código y lo marca como usado; el primer código válido confirma la configuración."""
    step = matching_step(user.totp_secret, code, user.totp_last_step)
    if step is None:
        return False
    user.totp_last_step = step
    fields = ['totp_last_step']
    if not user.totp_confirmed_at:
        user.totp_confirmed_at = timezone.now()
        fields.append('totp_confirmed_at')
    user.save(update_fields=fields)
    return True


def reset(user) -> None:
    user.totp_secret, user.totp_last_step, user.totp_confirmed_at = '', None, None
    user.save(update_fields=['totp_secret', 'totp_last_step', 'totp_confirmed_at'])
