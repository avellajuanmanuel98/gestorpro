"""
Permisos DRF del Core + permisos propios del módulo de acceso.

Las vistas de negocio declaran `required_permissions` por método HTTP. Si un
método no está declarado, se deniega (fail-closed): olvidar declarar un
permiso nunca abre un endpoint.
"""
from rest_framework.permissions import BasePermission

from gestorpro.core import entitlements
from gestorpro.core.tenancy.context import get_active_tenant_id

PERMISSIONS = {
    'access.view': 'Ver usuarios y roles de la empresa',
    'access.manage_users': 'Invitar usuarios, cambiar su rol y suspenderlos',
    'access.manage_roles': 'Crear y editar roles personalizados',
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

    Si la vista declara `required_feature`, además exige que el plan de la
    empresa incluya esa funcionalidad (403 `feature_not_in_plan`).
    """
    message = 'No tienes permiso para realizar esta acción.'

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        method = 'GET' if request.method in ('HEAD', 'OPTIONS') else request.method
        code = getattr(view, 'required_permissions', {}).get(method)
        if code is None or not request.membership.has_perm(code):
            return False
        feature = getattr(view, 'required_feature', None)
        if feature:
            entitlements.require_feature(request.membership.tenant_id, feature)
        return True


class IsPlatformAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_platform_admin)
