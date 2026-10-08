"""
Reportes base del Core.

Nota: estos reportes heredados se reconstruirán en la fase de analítica
(períodos configurables, comparaciones). En esta fase se garantiza que estén
aislados por empresa, protegidos por permiso y con importes exactos.
"""
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from gestorpro.core.access.permissions import HasTenantPermission
from gestorpro.core.billing.models import Invoice
from gestorpro.core.billing.views import MONTHS, month_starts
from gestorpro.core.catalog.models import Product
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

    `valor_inventario` = Σ(precio de venta × stock) de productos físicos activos.
    Es valor a PRECIO DE VENTA; el valor a costo llegará con el libro de
    inventario y el costo promedio ponderado.
    """

    def get(self, request):
        products = Product.objects.filter(is_active=True)
        physical = products.filter(product_type=Product.ProductType.PRODUCT)
        by_category = [
            {'categoria': r['category__name'] or 'Sin categoría', 'stock': r['stock'] or 0, 'productos': r['count']}
            for r in (
                physical.values('category__name').annotate(stock=Sum('stock'), count=Count('id')).order_by('-stock')
            )
        ]
        low_stock = list(
            physical.filter(stock__lte=F('minimum_stock')).order_by('stock')
            .values('id', 'name', 'code', 'stock', 'minimum_stock')[:10]
        )
        line_value = ExpressionWrapper(
            F('price') * F('stock'), output_field=DecimalField(max_digits=20, decimal_places=2),
        )
        totals = products.aggregate(
            total_productos=Count('id', filter=Q(product_type=Product.ProductType.PRODUCT)),
            total_servicios=Count('id', filter=Q(product_type=Product.ProductType.SERVICE)),
            valor=Sum(line_value, filter=Q(product_type=Product.ProductType.PRODUCT)),
        )
        return Response({
            'by_category': by_category,
            'low_stock': low_stock,
            'total_productos': totals['total_productos'],
            'total_servicios': totals['total_servicios'],
            'valor_inventario': money_str(totals['valor'] or ZERO),
            'valor_inventario_base': 'sale_price',
        })
