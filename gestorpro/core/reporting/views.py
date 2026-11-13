"""
Reportes base del Core.

Nota: estos reportes heredados se reconstruirán en la fase de analítica
(períodos configurables, comparaciones). En esta fase se garantiza que estén
aislados por empresa, protegidos por permiso y con importes exactos.
"""
from django.db.models import Case, Count, DecimalField, ExpressionWrapper, F, Q, Sum, Value, When
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from gestorpro.core.access.permissions import HasTenantPermission
from gestorpro.core.billing.models import Invoice
from gestorpro.core.billing.views import MONTHS, month_starts
from gestorpro.core.catalog.models import Item
from gestorpro.kernel.money import ZERO, money_str


class ReportView(APIView):
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'reports.view'}


class BillingReportView(ReportView):
    """GET /api/reports/billing/ — tendencia 12 meses, estados y top clientes."""

    def get(self, request):
        invoices = Invoice.objects.filter(invoice_type=Invoice.InvoiceType.INVOICE)
        months = month_starts(12, timezone.localdate())
        rows = (
            invoices.filter(status=Invoice.Status.PAID, issue_date__gte=months[0])
            .annotate(month=TruncMonth('issue_date')).values('month')
            .annotate(total=Sum('total'), count=Count('id'))
        )
        by_month = {r['month']: r for r in rows}
        monthly_trend = [
            {'month': m.isoformat()[:7], 'mes': MONTHS[m.month - 1],
             'total': money_str(by_month.get(m, {}).get('total') or ZERO),
             'count': by_month.get(m, {}).get('count', 0)}
            for m in months
        ]

        labels = dict(Invoice.Status.choices)
        status_breakdown = [
            {'status': r['status'], 'label': labels.get(r['status'], r['status']),
             'count': r['count'], 'total': money_str(r['total'] or ZERO)}
            for r in invoices.values('status').annotate(count=Count('id'), total=Sum('total')).order_by('status')
        ]

        top_clients = [
            {'name': r['customer__company_name'] or f"{r['customer__first_name']} {r['customer__last_name']}".strip(),
             'total': money_str(r['total']), 'count': r['count']}
            for r in (
                invoices.filter(status=Invoice.Status.PAID)
                .values('customer_id', 'customer__first_name', 'customer__last_name', 'customer__company_name')
                .annotate(total=Sum('total'), count=Count('id')).order_by('-total')[:5]
            )
        ]
        return Response({'monthly_trend': monthly_trend, 'status_breakdown': status_breakdown,
                         'top_clients': top_clients})


class InventoryReportView(ReportView):
    """
    GET /api/reports/inventory/

    El valor del inventario es a COSTO: Σ(existencia × costo por unidad) de los
    ítems activos con existencias. No se suman cantidades entre ítems porque
    pueden estar en unidades distintas (kg, l, und). Los valores solo se
    incluyen si el usuario tiene `catalog.view_costs`; si no, van en null.
    """

    def get(self, request):
        items = Item.objects.filter(is_active=True)
        stocked = items.exclude(kind=Item.Kind.SERVICE)
        is_ingredient = Q(kind=Item.Kind.RAW_MATERIAL)
        value = ExpressionWrapper(F('stock') * F('avg_cost'),
                                  output_field=DecimalField(max_digits=28, decimal_places=8))
        show_costs = request.membership.has_perm('catalog.view_costs')

        by_category = [
            {'categoria': r['category__name'] or 'Sin categoría',
             'grupo': 'ingredientes' if r['group_kind'] == Item.Kind.RAW_MATERIAL else 'productos',
             'items': r['count'],
             'valor': money_str(r['valor'] or ZERO) if show_costs else None}
            for r in (
                stocked.annotate(group_kind=Case(When(is_ingredient, then=Value(Item.Kind.RAW_MATERIAL)),
                                                 default=Value('product')))
                .values('category__name', 'group_kind')
                .annotate(count=Count('id'), valor=Sum(value))
                .order_by('-valor' if show_costs else '-count')
            )
        ]
        low_stock = [
            {'id': r['id'], 'name': r['name'], 'code': r['code'], 'stock': str(r['stock'].normalize()),
             'minimum_stock': str(r['minimum_stock'].normalize()), 'unit': r['unit__symbol']}
            for r in stocked.filter(minimum_stock__gt=0, stock__lte=F('minimum_stock')).order_by('stock')
            .values('id', 'name', 'code', 'stock', 'minimum_stock', 'unit__symbol')[:10]
        ]
        totals = items.aggregate(
            total_productos=Count('id', filter=Q(kind__in=Item.PRODUCT_KINDS)),
            total_ingredientes=Count('id', filter=is_ingredient),
            valor_productos=Sum(value, filter=~is_ingredient & ~Q(kind=Item.Kind.SERVICE)),
            valor_ingredientes=Sum(value, filter=is_ingredient),
        )
        costs = (lambda v: money_str(v or ZERO)) if show_costs else (lambda v: None)
        return Response({
            'by_category': by_category,
            'low_stock': low_stock,
            'total_productos': totals['total_productos'],
            'total_ingredientes': totals['total_ingredientes'],
            'valor_productos': costs(totals['valor_productos']),
            'valor_ingredientes': costs(totals['valor_ingredientes']),
            'valor_inventario': costs((totals['valor_productos'] or ZERO) + (totals['valor_ingredientes'] or ZERO)),
            'valor_inventario_base': 'cost',
        })
