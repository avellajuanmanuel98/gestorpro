from rest_framework import serializers

from gestorpro.core.tenancy.context import get_active_tenant_id


class CurrentTenantDefault:
    """Valor por defecto = tenant activo. Nunca proviene del cliente."""
    requires_context = False

    def __call__(self):
        from gestorpro.core.tenancy.models import Tenant
        return Tenant.objects.get(pk=get_active_tenant_id())

    def __repr__(self):
        return 'CurrentTenantDefault()'


class TenantModelSerializer(serializers.ModelSerializer):
    """
    - `tenant` es un HiddenField: el cliente no puede enviarlo ni verlo, y
      permite a DRF validar las restricciones únicas (tenant, campo) con un 400
      claro en vez de un error de base de datos.
    - Las FKs generadas automáticamente usan el manager por defecto del modelo
      relacionado, que filtra por tenant: un ID de otra empresa es "inexistente".
    """
    tenant = serializers.HiddenField(default=CurrentTenantDefault())
