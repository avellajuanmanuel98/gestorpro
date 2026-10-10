from django.db.models import Sum
from rest_framework import generics, status
from rest_framework.response import Response

from gestorpro.core.access.permissions import HasTenantPermission
from gestorpro.kernel.money import money_str

from . import services
from .models import WasteReason, WasteRecord
from .serializers import WasteInputSerializer, WasteReasonSerializer, WasteRecordSerializer


class ReasonListView(generics.ListAPIView):
    serializer_class = WasteReasonSerializer
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'waste.register'}
    pagination_class = None

    def get_queryset(self):
        return WasteReason.objects.filter(is_active=True)


class WasteListCreateView(generics.ListCreateAPIView):
    serializer_class = WasteRecordSerializer
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'waste.view', 'POST': 'waste.register'}

    def get_queryset(self):
        qs = WasteRecord.objects.select_related('item__unit', 'reason', 'created_by')
        p = self.request.query_params
        if p.get('date_from'):
            qs = qs.filter(created_at__date__gte=p['date_from'])
        if p.get('date_to'):
            qs = qs.filter(created_at__date__lte=p['date_to'])
        return qs

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if request.membership.has_perm('catalog.view_costs'):
            total = self.filter_queryset(self.get_queryset()).aggregate(t=Sum('total_cost'))['t']
            response.data['total_cost'] = money_str(total or 0)
        return response

    def create(self, request, *args, **kwargs):
        data = WasteInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        d = data.validated_data
        record = services.register_waste(user=request.user, item_id=d['item'], quantity=d['quantity'],
                                         reason=d['reason'], notes=d.get('notes', ''))
        return Response(WasteRecordSerializer(record, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)
