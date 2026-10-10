from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import filters, generics, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from gestorpro.core.access.permissions import HasTenantPermission
from gestorpro.core.catalog.models import Category, Item
from gestorpro.kernel.money import ZERO, money, money_str

from . import services
from .models import Payment, PaymentMethod, Sale
from .serializers import (
    PaymentMethodSerializer,
    POSItemSerializer,
    SaleCreateSerializer,
    SaleListSerializer,
    SaleSerializer,
    VoidSerializer,
)

POS_CATALOG_MAX = 2000


def visible_sales(request):
    """Sin `sales.view_all` cada persona solo ve sus propias ventas."""
    qs = Sale.objects.select_related('cashier', 'customer', 'voided_by', 'location', 'cash_session__register')
    if not request.membership.has_perm('sales.view_all'):
        qs = qs.filter(cashier=request.user)
    return qs


def local_day_bounds(tenant, day):
    tz = ZoneInfo(tenant.timezone)
    start = datetime.combine(day, time.min, tzinfo=tz)
    return start, start + timedelta(days=1)


class POSCatalogView(APIView):
    """GET /api/sales/catalog/ — todo lo vendible y activo, en una sola respuesta para que el POS sea instantáneo."""
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'sales.sell'}

    def get(self, request):
        items = (Item.objects.select_related('unit').filter(is_active=True, is_sellable=True)
                 .order_by('name')[:POS_CATALOG_MAX])
        used = {i.category_id for i in items}
        categories = Category.objects.filter(id__in=used).order_by('name').values('id', 'name')
        return Response({'categories': list(categories), 'items': POSItemSerializer(items, many=True).data})


class PaymentMethodListView(generics.ListAPIView):
    serializer_class = PaymentMethodSerializer
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'sales.sell'}
    pagination_class = None

    def get_queryset(self):
        return PaymentMethod.objects.filter(is_active=True)


class SaleListCreateView(generics.ListCreateAPIView):
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'sales.view', 'POST': 'sales.sell'}
    filter_backends = [filters.SearchFilter]
    search_fields = ['number', 'customer__first_name', 'customer__last_name', 'customer__company_name']

    def get_serializer_class(self):
        return SaleListSerializer

    def get_queryset(self):
        qs = visible_sales(self.request).prefetch_related('payments__method')
        params = self.request.query_params
        if params.get('status') in Sale.Status.values:
            qs = qs.filter(status=params['status'])
        if params.get('session'):
            qs = qs.filter(cash_session_id=params['session'])
        if params.get('date'):
            try:
                day = datetime.strptime(params['date'], '%Y-%m-%d').date()
            except ValueError:
                return qs.none()
            start, end = local_day_bounds(self.request.tenant, day)
            qs = qs.filter(created_at__gte=start, created_at__lt=end)
        return qs

    def create(self, request, *args, **kwargs):
        data = SaleCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        d = data.validated_data
        sale, created = services.complete_sale(
            membership=request.membership, client_uuid=d['client_uuid'], customer=d.get('customer'),
            discount=d.get('discount'), lines=d['lines'], payments=d['payments'],
        )
        body = SaleSerializer(sale, context={'request': request}).data
        return Response(body, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class SaleDetailView(generics.RetrieveAPIView):
    serializer_class = SaleSerializer
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'sales.view'}

    def get_queryset(self):
        return visible_sales(self.request).prefetch_related('lines', 'payments__method')


class SaleVoidView(APIView):
    permission_classes = [HasTenantPermission]
    required_permissions = {'POST': 'sales.void'}

    def post(self, request, pk):
        sale = visible_sales(request).filter(pk=pk).first()
        if sale is None:
            raise NotFound()
        data = VoidSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        sale = services.void_sale(membership=request.membership, sale=sale, reason=data.validated_data['reason'])
        return Response(SaleSerializer(sale, context={'request': request}).data)


class SalesTodayView(APIView):
    """GET /api/sales/today/ — ventas del día (hora de la empresa). Cifras reales, para el inicio."""
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'reports.view'}

    def get(self, request):
        today = timezone.now().astimezone(ZoneInfo(request.tenant.timezone)).date()
        start, end = local_day_bounds(request.tenant, today)
        day = Sale.objects.filter(created_at__gte=start, created_at__lt=end)
        completed = day.filter(status=Sale.Status.COMPLETED)
        totals = completed.aggregate(count=Count('id'), total=Sum('total'), cost=Sum('cost_total'))
        count, total = totals['count'], totals['total'] or ZERO
        by_method = (Payment.objects.filter(sale__in=completed).values('method__name')
                     .annotate(total=Sum('amount')).order_by('-total'))
        show_costs = request.membership.has_perm('catalog.view_costs')
        return Response({
            'date': today.isoformat(),
            'count': count,
            'total': money_str(total),
            'average_ticket': money_str(money(total / count) if count else ZERO),
            'voided': day.filter(status=Sale.Status.VOIDED).count(),
            'gross_margin': money_str(total - (totals['cost'] or ZERO)) if show_costs and count else None,
            'by_method': [{'method': r['method__name'], 'total': money_str(r['total'])} for r in by_method],
        })
