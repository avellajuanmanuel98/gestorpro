"""
Permisos DRF del Core + permisos propios del módulo de acceso.

Las vistas de negocio declaran `required_permissions` por método HTTP. Si un
método no está declarado, se deniega (fail-closed): olvidar declarar un
permiso nunca abre un endpoint.
"""
from rest_framework.permissions import BasePermission

from gestorpro.core.tenancy.context import get_active_tenant_id

PERMISSIONS = {
    'tenant.view': 'Ver los datos de la empresa',
    'tenant.manage': 'Editar los datos de la empresa',
    'access.manage_users': 'Invitar usuarios y asignar roles',
}


class IsTenantMember(BasePermission):
    """Autenticado + membresía activa verificada + tenant activo en contexto."""
    message = 'Tu cuenta no tiene una empresa activa.'

    def has_permission(self, request, view):
        membership = getattr(request, 'membership', None)
        return bool(
            request.user and request.user.is_authenticated
            and membership is not None
            and get_active_tenant_id(required=False) == membership.tenant_id
        )


class HasTenantPermission(IsTenantMember):
    """
    Requiere el permiso declarado en `view.required_permissions[METHOD]`.
    HEAD/OPTIONS heredan el permiso de GET.
    """
    message = 'No tienes permiso para realizar esta acción.'

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        method = 'GET' if request.method in ('HEAD', 'OPTIONS') else request.method
        code = getattr(view, 'required_permissions', {}).get(method)
        if code is None:
            return False
        return request.membership.has_perm(code)


class IsPlatformAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_platform_admin)
