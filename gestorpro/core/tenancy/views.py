from rest_framework import generics

from gestorpro.core.access.permissions import HasTenantPermission

from .models import Location
from .serializers import LocationSerializer, TenantSerializer


class CurrentTenantView(generics.RetrieveUpdateAPIView):
    """
    GET/PATCH /api/tenant/ — la empresa ACTIVA. No recibe IDs: es imposible
    pedir o editar otra empresa por este endpoint.
    """
    serializer_class = TenantSerializer
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'tenant.view', 'PUT': 'tenant.manage', 'PATCH': 'tenant.manage'}

    def get_object(self):
        return self.request.tenant


class LocationListView(generics.ListAPIView):
    """GET /api/tenant/locations/ — sucursales de la empresa activa."""
    serializer_class = LocationSerializer
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'tenant.view'}
    pagination_class = None

    def get_queryset(self):
        return Location.objects.filter(is_active=True)
