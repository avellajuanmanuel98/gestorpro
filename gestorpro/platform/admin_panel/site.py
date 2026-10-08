"""
Admin de Django como consola interna de la PLATAFORMA (personal de GestorPro).

- Solo entra quien tiene `is_platform_admin` + `is_staff`.
- Muestra entidades de plataforma (empresas, usuarios, membresías, roles).
  Deliberadamente NO registra datos de negocio de las empresas (clientes,
  facturas, etc.): el soporte que requiera verlos se hará con impersonación
  explícita y auditada (fase de administración SaaS).
- Las empresas no se pueden eliminar desde aquí: se suspenden.
"""
from django.contrib import admin


class PlatformAdminSite(admin.AdminSite):
    site_header = 'GestorPro — Plataforma'
    site_title = 'GestorPro Plataforma'
    index_title = 'Administración global'

    def has_permission(self, request):
        user = request.user
        return bool(user.is_active and user.is_staff and getattr(user, 'is_platform_admin', False))


platform_admin_site = PlatformAdminSite(name='platform_admin')


class UnscopedReadOnlyAdmin(admin.ModelAdmin):
    """Vista global de solo lectura para modelos con tenant."""

    def get_queryset(self, request):
        return self.model.all_tenants.select_related('tenant')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
