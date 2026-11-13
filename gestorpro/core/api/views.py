from django.db import transaction
from rest_framework import filters, generics

from gestorpro.core.access.permissions import HasTenantPermission
from gestorpro.core.audit import services as audit


class TenantScopedMixin:
    """
    Queryset por petición desde `model.objects` (filtrado por tenant),
    permisos por método HTTP mediante `required_permissions` y auditoría
    automática de altas, cambios y bajas.

        class CustomerList(TenantListCreateView):
            model = Customer
            required_permissions = {'GET': 'customers.view', 'POST': 'customers.create'}
    """
    model = None
    permission_classes = [HasTenantPermission]
    required_permissions: dict[str, str] = {}

    def get_queryset(self):
        return self.model.objects.all()

    # El cambio y su registro de auditoría se confirman juntos o no se confirma ninguno.

    @transaction.atomic
    def perform_create(self, serializer):
        extra = {}
        if any(f.name == 'created_by' for f in self.model._meta.fields):
            extra['created_by'] = self.request.user
        audit.record_created(serializer.save(**extra))

    @transaction.atomic
    def perform_update(self, serializer):
        before = audit.snapshot(serializer.instance)
        audit.record_updated(serializer.save(), before)

    @transaction.atomic
    def perform_destroy(self, instance):
        before, pk = audit.snapshot(instance), instance.pk
        instance.delete()
        audit.record_deleted(instance, before, pk)


class TenantListCreateView(TenantScopedMixin, generics.ListCreateAPIView):
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]


class TenantDetailView(TenantScopedMixin, generics.RetrieveUpdateDestroyAPIView):
    pass


def crud_permissions(module: str) -> tuple[dict, dict]:
    """Mapa estándar de permisos (lista/creación, detalle) para un módulo CRUD."""
    return (
        {'GET': f'{module}.view', 'POST': f'{module}.create'},
        {'GET': f'{module}.view', 'PUT': f'{module}.update', 'PATCH': f'{module}.update',
         'DELETE': f'{module}.delete'},
    )
