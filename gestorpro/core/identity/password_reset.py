"""
Recuperar o restablecer una contraseña sin que nadie más la conozca.

Siempre es un ENLACE de un solo uso (24 h) con el que la propia persona escribe su
contraseña nueva; nadie la ve ni la elige por ella. El enlace llega de tres formas:

1. por correo, si la persona lo pide en "¿Olvidaste tu contraseña?" y la instalación
   tiene correo configurado (EMAIL_HOST);
2. de manos del dueño o un administrador de su empresa (Usuarios), para quien no
   tiene correo, como en la edición local;
3. de manos del soporte de GestorPro (consola de plataforma).

Reglas contra la toma de cuentas en (2): no se genera para uno mismo, ni para un
propietario si quien lo pide no es propietario, ni para el personal de la
plataforma, ni para alguien que también usa OTRA empresa (con ese enlace un
administrador de una empresa podría entrar a la cuenta que esa persona tiene en
otra). Esas personas usan el correo o el soporte.

El enlace usa el generador de Django: se invalida al cambiar la contraseña o al
iniciar sesión, así que sirve una sola vez.
"""
import logging

from django.conf import settings
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from gestorpro.core.audit import services as audit
from gestorpro.core.audit.models import SecurityEvent

logger = logging.getLogger('gestorpro.identity')
HOURS = settings.PASSWORD_RESET_TIMEOUT // 3600


def make_link(user) -> str:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return f"{settings.FRONTEND_URL.rstrip('/')}/reset-password/{uid}/{token}"


def user_from(uidb64: str, token: str):
    """El usuario del enlace si sigue siendo válido; si no, None."""
    try:
        user = get_user_model().objects.get(pk=force_str(urlsafe_base64_decode(uidb64)), is_active=True)
    except (ValueError, TypeError, OverflowError, get_user_model().DoesNotExist):
        return None
    return user if default_token_generator.check_token(user, token) else None


def mask(email: str) -> str:
    name, _, domain = email.partition('@')
    return f'{name[:2]}{"•" * max(1, len(name) - 2)}@{domain}'


@transaction.atomic
def reset(user, password: str, password2: str):
    if password != password2:
        raise ValidationError({'password2': 'Las contraseñas no coinciden.'})
    try:
        password_validation.validate_password(password, user)
    except Exception as exc:  # ValidationError de Django → la de DRF, con sus mensajes
        raise ValidationError({'password': list(getattr(exc, 'messages', [str(exc)]))}) from exc
    user.set_password(password)
    user.save(update_fields=['password'])
    # Las sesiones abiertas con la contraseña anterior se cierran
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)
    audit.security_event(SecurityEvent.Kind.PASSWORD_RESET, user=user)


def request_by_email(email: str) -> None:
    """'¿Olvidaste tu contraseña?'. No revela si el correo existe: siempre responde igual."""
    audit.security_event(SecurityEvent.Kind.PASSWORD_RESET_REQUESTED, email=email)
    if not getattr(settings, 'EMAIL_ENABLED', False):
        return
    user = get_user_model().objects.filter(email__iexact=email.strip(), is_active=True).first()
    if user is None:
        return
    body = (f'Hola {user.first_name or ""},\n\n'
            f'Recibimos una solicitud para crear una contraseña nueva en GestorPro. Ábrela aquí:\n\n'
            f'{make_link(user)}\n\n'
            f'El enlace sirve una sola vez y vence en {HOURS} horas. Si no fuiste tú, ignora este correo: '
            f'tu contraseña actual sigue igual.\n')
    try:
        send_mail('Tu contraseña de GestorPro', body, None, [user.email])
    except Exception:  # un fallo del correo no debe revelar nada ni romper la respuesta
        logger.exception('password_reset_email_failed user=%s', user.pk)


def link_for_member(actor, member) -> str:
    """Enlace que entrega el dueño o un administrador a una persona de SU empresa (ver reglas arriba)."""
    from gestorpro.core.access.models import Membership

    target = member.user
    if target.pk == actor.user_id:
        raise ValidationError({'detail': 'Para tu propia cuenta usa "Cambiar contraseña" en tu perfil.'})
    if target.is_platform_admin:
        raise PermissionDenied('Esta cuenta es del equipo de GestorPro.')
    if member.role.grants_all and not actor.role.grants_all:
        raise PermissionDenied('Solo un propietario puede generar este enlace para otro propietario.')
    elsewhere = Membership.all_tenants.filter(user=target, status=Membership.Status.ACTIVE) \
        .exclude(tenant_id=member.tenant_id).exists()
    if elsewhere:
        raise ValidationError({'detail': 'Esta persona también usa otra empresa en GestorPro: debe recuperar su '
                                         'contraseña con "¿Olvidaste tu contraseña?" o con el soporte de GestorPro.'})
    audit.security_event(SecurityEvent.Kind.PASSWORD_RESET_LINK, user=target, tenant_id=member.tenant_id)
    audit.record('access.password_reset_link', target=member,
                 summary=f'Generó un enlace para que {target.email} cree una contraseña nueva')
    return make_link(target)
