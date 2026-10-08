"""
Autenticación JWT con resolución de empresa.

El access token lleva el claim `tid` (empresa activa). En CADA petición se
verifica en base de datos que la membresía siga activa, de modo que suspender
a un usuario o a una empresa surte efecto inmediato, sin esperar a que el
token expire. Solo después de esa verificación se activa el contexto de tenant.
"""
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from gestorpro.core.access.services import active_memberships_for
from gestorpro.core.tenancy.context import activate

TENANT_CLAIM = 'tid'


class TenantJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, token = result
        membership = None
        tenant_id = token.get(TENANT_CLAIM)
        if tenant_id is not None:
            membership = active_memberships_for(user).filter(tenant_id=tenant_id).first()
            if membership is None:
                raise AuthenticationFailed('Tu acceso a esta empresa ya no está activo.', code='membership_inactive')
            activate(membership.tenant_id)
        # Disponible tanto en el Request de DRF como en el HttpRequest subyacente
        for target in (request, getattr(request, '_request', None)):
            if target is not None:
                target.membership = membership
                target.tenant = membership.tenant if membership else None
        return user, token
