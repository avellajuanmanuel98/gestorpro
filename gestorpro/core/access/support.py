"""
Acceso de soporte (impersonación) de SOLO LECTURA.

El personal de la plataforma no tiene membresía en las empresas. Para ayudar a
un cliente abre una sesión de soporte (motivo obligatorio, 30 minutos). Con ese
token:
  - ve la empresa con un rol virtual "Soporte GestorPro" que solo tiene
    permisos de consulta (`*.view`);
  - cualquier método que no sea GET/HEAD/OPTIONS se rechaza (403), incluso en
    vistas que no usan permisos por rol;
  - el inicio y el fin quedan en la auditoría DE LA EMPRESA (la ve el dueño) y
    en la bitácora de la plataforma; cada petición actualiza `last_seen_at`.
"""
import datetime

from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied

SUPPORT_CLAIM = 'sup'
SUPPORT_MINUTES = 30
SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')
# Únicas escrituras permitidas con un token de soporte: cerrar la propia sesión
WRITE_ALLOWLIST = ('/api/auth/logout/', '/api/platform/support/end/')


def support_permission_codes() -> frozenset[str]:
    from .models import Permission
    return frozenset(c for c in Permission.objects.values_list('code', flat=True)
                     if c.endswith('.view') or c.endswith('.view_costs'))


class SupportRole:
    code = 'SUPPORT'
    name = 'Soporte GestorPro (solo lectura)'
    is_system = True
    grants_all = False


class SupportMembership:
    """Se comporta como una Membership de solo lectura (no se guarda en la base de datos)."""
    is_support = True
    status = 'active'

    def __init__(self, session, user):
        self.session = session
        self.user = user
        self.user_id = user.id
        self.tenant = session.tenant
        self.tenant_id = session.tenant_id
        self.role = SupportRole()
        self.pk = self.id = None
        self.permission_codes = support_permission_codes()

    def has_perm(self, code: str) -> bool:
        return code in self.permission_codes


def resolve(request, user, session_id) -> SupportMembership:
    """Valida la sesión de soporte del token en cada petición (fail-closed)."""
    from .models import SupportSession
    session = SupportSession.objects.select_related('tenant').filter(pk=session_id, agent=user).first()
    now = timezone.now()
    if (session is None or session.ended_at is not None or session.expires_at <= now
            or not (user.is_active and user.is_platform_admin)):
        raise AuthenticationFailed('La sesión de soporte terminó.', code='support_ended')
    method = request.method.upper()
    if method not in SAFE_METHODS and request.path not in WRITE_ALLOWLIST:
        raise PermissionDenied('Modo soporte: solo lectura. No se puede modificar nada de la empresa.')
    SupportSession.objects.filter(pk=session.pk).update(last_seen_at=now, request_count=F('request_count') + 1)
    return SupportMembership(session, user)


def expiry() -> datetime.datetime:
    return timezone.now() + datetime.timedelta(minutes=SUPPORT_MINUTES)
