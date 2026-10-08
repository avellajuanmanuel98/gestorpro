from rest_framework import filters, generics

from gestorpro.core.access.permissions import HasTenantPermission


class TenantScopedMixin:
    """
    Queryset por petición desde `model.objects` (filtrado por tenant) y
    permisos por método HTTP mediante `required_permissions`.

        class CustomerList(TenantListCreateView):
            model = Customer
            required_permissions = {'GET': 'customers.view', 'POST': 'customers.create'}
    """
    model = None
    permission_classes = [HasTenantPermission]
    required_permissions: dict[str, str] = {}

    def get_queryset(self):
        return self.model.objects.all()

    def perform_create(self, serializer):
        extra = {}
        if any(f.name == 'created_by' for f in self.model._meta.fields):
            extra['created_by'] = self.request.user
        serializer.save(**extra)


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
