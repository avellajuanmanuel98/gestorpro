from django.db import transaction
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from gestorpro.core.access.permissions import HasTenantPermission
from gestorpro.core.audit import services as audit

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

    @transaction.atomic
    def perform_update(self, serializer):
        before = audit.snapshot(serializer.instance)
        audit.record_updated(serializer.save(), before)


class LocationListView(generics.ListAPIView):
    """GET /api/tenant/locations/ — sucursales de la empresa activa."""
    serializer_class = LocationSerializer
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'tenant.view'}
    pagination_class = None

    def get_queryset(self):
        return Location.objects.filter(is_active=True)


class PlanView(APIView):
    """GET /api/tenant/plan/ — plan actual, funcionalidades y consumo de límites."""
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'tenant.view'}

    def get(self, request):
        from gestorpro.core.usage import plan_summary
        return Response(plan_summary())
