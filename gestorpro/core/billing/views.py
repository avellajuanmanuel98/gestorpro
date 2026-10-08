import datetime

from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from gestorpro.core.access.permissions import HasTenantPermission
from gestorpro.core.api.views import TenantDetailView, TenantListCreateView, crud_permissions
from gestorpro.kernel.money import ZERO, money_str

from . import services
from .models import Invoice
from .serializers import InvoiceListSerializer, InvoiceSerializer

LIST_PERMS, DETAIL_PERMS = crud_permissions('billing')
MONTHS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']


def _split(validated):
    lines = validated.pop('items', None)
    validated.pop('tenant', None)
    return validated, lines


class InvoiceListCreateView(TenantListCreateView):
    model = Invoice
    required_permissions = LIST_PERMS
    search_fields = ['number', 'customer__first_name', 'customer__last_name', 'customer__company_name']
    ordering_fields = ['issue_date', 'due_date', 'total', 'created_at']
    ordering = ['-created_at', '-id']

    def get_queryset(self):
        qs = super().get_queryset().select_related('customer')
        params = self.request.query_params
        for param, field in (('status', 'status'), ('invoice_type', 'invoice_type'), ('customer', 'customer_id')):
            if params.get(param):
                qs = qs.filter(**{field: params[param]})
        return qs

    def get_serializer_class(self):
        return InvoiceListSerializer if self.request.method == 'GET' else InvoiceSerializer

    def perform_create(self, serializer):
        header, lines = _split(dict(serializer.validated_data))
        serializer.instance = services.save_invoice(
            membership=self.request.membership, user=self.request.user, header=header, lines=lines,
        )


class InvoiceDetailView(TenantDetailView):
    model = Invoice
    serializer_class = InvoiceSerializer
    required_permissions = DETAIL_PERMS

    def get_queryset(self):
        return super().get_queryset().select_related('customer', 'created_by').prefetch_related('lines__product')

    def perform_update(self, serializer):
        header, lines = _split(dict(serializer.validated_data))
        serializer.instance = services.save_invoice(
            membership=self.request.membership, user=self.request.user,
            header=header, lines=lines, invoice=serializer.instance,
        )

    def perform_destroy(self, instance):
        services.delete_invoice(instance)


class InvoiceSummaryView(APIView):
    """GET /api/billing/summary/ — cartera de la empresa activa (importes como string)."""
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'billing.view'}

    def get(self, request):
        invoices = Invoice.objects.filter(invoice_type=Invoice.InvoiceType.INVOICE)
        agg = invoices.aggregate(
            paid=Sum('total', filter=Q(status=Invoice.Status.PAID)),
            pending=Sum('total', filter=Q(status__in=[Invoice.Status.DRAFT, Invoice.Status.SENT,
                                                      Invoice.Status.OVERDUE])),
        )
        return Response({
            'total_invoices': invoices.count(),
            'total_quotes': Invoice.objects.filter(invoice_type=Invoice.InvoiceType.QUOTE).count(),
            'paid_total': money_str(agg['paid'] or ZERO),
            'pending_total': money_str(agg['pending'] or ZERO),
            'overdue_count': invoices.filter(status=Invoice.Status.OVERDUE).count(),
        })


def month_starts(count: int, today: datetime.date):
    first = today.replace(day=1)
    months = []
    for _ in range(count):
        months.append(first)
        first = (first - datetime.timedelta(days=1)).replace(day=1)
    return list(reversed(months))


class MonthlyRevenueView(APIView):
    """
    GET /api/billing/monthly-revenue/ — facturas pagadas por mes (últimos 6),
    incluidos los meses en cero, para que la gráfica no oculte meses sin ventas.
    """
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'billing.view'}

    def get(self, request):
        months = month_starts(6, timezone.localdate())
        rows = (
            Invoice.objects
            .filter(status=Invoice.Status.PAID, invoice_type=Invoice.InvoiceType.INVOICE,
                    issue_date__gte=months[0])
            .annotate(month=TruncMonth('issue_date')).values('month').annotate(total=Sum('total'))
        )
        by_month = {row['month']: row['total'] for row in rows}
        return Response([
            {'month': m.isoformat()[:7], 'mes': MONTHS[m.month - 1], 'total': money_str(by_month.get(m, ZERO))}
            for m in months
        ])


class RecentInvoicesView(APIView):
    """GET /api/billing/recent/ — últimos 5 documentos."""
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'billing.view'}

    def get(self, request):
        invoices = Invoice.objects.select_related('customer').order_by('-created_at', '-id')[:5]
        return Response([
            {'id': inv.id, 'number': inv.number, 'customer': str(inv.customer),
             'total': money_str(inv.total), 'status': inv.status}
            for inv in invoices
        ])
