from datetime import datetime

from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from gestorpro.core.access.permissions import HasTenantPermission
from gestorpro.core.tenancy.models import Location

from . import services
from .models import StockMovement
from .serializers import CountSerializer, StockMovementSerializer


class MovementListView(generics.ListAPIView):
    """GET /api/inventory/movements/?item=&type=&date_from=&date_to= — kardex."""
    serializer_class = StockMovementSerializer
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'inventory.view'}

    def get_queryset(self):
        qs = StockMovement.objects.select_related('item__unit', 'location', 'created_by')
        p = self.request.query_params
        if p.get('item'):
            qs = qs.filter(item_id=p['item'])
        if p.get('type') in StockMovement.Type.values:
            qs = qs.filter(type=p['type'])
        for key, lookup in (('date_from', 'created_at__date__gte'), ('date_to', 'created_at__date__lte')):
            if p.get(key):
                try:
                    qs = qs.filter(**{lookup: datetime.strptime(p[key], '%Y-%m-%d').date()})
                except ValueError as exc:
                    raise ValidationError({key: 'Fecha inválida (AAAA-MM-DD).'}) from exc
        return qs


class PhysicalCountView(APIView):
    """POST /api/inventory/counts/ — aplica un conteo físico (ajustes por diferencia)."""
    permission_classes = [HasTenantPermission]
    required_permissions = {'POST': 'inventory.adjust'}

    def post(self, request):
        data = CountSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        location_id = data.validated_data.get('location')
        location = (Location.objects.filter(pk=location_id).first() if location_id else services.default_location())
        if location is None:
            raise ValidationError({'location': 'Sucursal inexistente.'})
        movements = services.physical_count(user=request.user, location=location,
                                            counts=data.validated_data['counts'],
                                            note=data.validated_data.get('note', ''))
        body = StockMovementSerializer(movements, many=True, context={'request': request}).data
        return Response({'adjustments': body}, status=status.HTTP_201_CREATED)
