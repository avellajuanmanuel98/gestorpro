from django.db.models import Count, Sum
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


class WasteSummaryView(generics.GenericAPIView):
    """GET /api/waste/summary/?period= — mermas por motivo y por ítem, con costo si hay permiso."""
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'waste.view'}

    def get(self, request):
        from gestorpro.core.analytics.periods import resolve

        p = request.query_params
        period = resolve(request.tenant, p.get('period', '30d'), p.get('from'), p.get('to'))
        qs = WasteRecord.objects.filter(created_at__gte=period.current.start, created_at__lt=period.current.end)
        costs = request.membership.has_perm('catalog.view_costs')
        by_reason = qs.values('reason__name').annotate(n=Count('id'), cost=Sum('total_cost')).order_by('-cost')
        by_item = (qs.values('item__name', 'item__unit__symbol').annotate(q=Sum('quantity'), cost=Sum('total_cost'))
                   .order_by('-cost')[:15])
        return Response({
            'period': period.as_dict(),
            'total_cost': money_str(qs.aggregate(t=Sum('total_cost'))['t'] or 0) if costs else None,
            'by_reason': [{'reason': r['reason__name'], 'records': r['n'],
                           'cost': money_str(r['cost']) if costs else None} for r in by_reason],
            'by_item': [{'item': r['item__name'], 'unit': r['item__unit__symbol'], 'quantity': str(r['q']),
                         'cost': money_str(r['cost']) if costs else None} for r in by_item],
        })
