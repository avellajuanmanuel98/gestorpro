"""
Bloqueo por cuenta ante intentos de contraseña repetidos.

El límite por IP (throttle `auth`) no frena a quien prueba contraseñas contra
UN correo desde muchas IP. Por eso, además: con LOGIN_LOCKOUT_FAILURES intentos
fallidos para un mismo correo en LOGIN_LOCKOUT_MINUTES, ese correo queda
bloqueado ese tiempo, venga de donde venga el intento.

- Se cuenta en la base (SecurityEvent), así que vale entre procesos y reinicios.
- Mientras está bloqueado, la contraseña NI SIQUIERA se verifica: no se puede
  seguir adivinando.
- Aplica a cualquier correo, exista o no la cuenta: no revela cuáles existen.
- Un inicio de sesión exitoso o una contraseña restablecida con enlace
  reinician el conteo; el enlace de "¿Olvidaste tu contraseña?" sigue
  funcionando durante el bloqueo.
"""
import datetime

from django.conf import settings
from django.utils import timezone

from gestorpro.core.audit.models import SecurityEvent

RESETS = (SecurityEvent.Kind.LOGIN_SUCCEEDED, SecurityEvent.Kind.PASSWORD_RESET)
# Contraseña equivocada o código de verificación en dos pasos equivocado
FAILURES = (SecurityEvent.Kind.LOGIN_FAILED, SecurityEvent.Kind.MFA_FAILED)


def normalize(email: str) -> str:
    return str(email or '').strip().lower()[:254]


def failures_allowed() -> int:
    return int(getattr(settings, 'LOGIN_LOCKOUT_FAILURES', 5))


def window() -> datetime.timedelta:
    return datetime.timedelta(minutes=int(getattr(settings, 'LOGIN_LOCKOUT_MINUTES', 15)))


def is_locked(email: str) -> bool:
    email = normalize(email)
    if not email:
        return False
    since = timezone.now() - window()
    last_reset = (SecurityEvent.objects.filter(email=email, kind__in=RESETS, created_at__gte=since)
                  .order_by('-created_at').values_list('created_at', flat=True).first())
    failures = SecurityEvent.objects.filter(email=email, kind__in=FAILURES,
                                            created_at__gte=last_reset or since).count()
    return failures >= failures_allowed()
