from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.companies.mixins import CompanyFilterMixin

from .models import Invoice
from .serializers import InvoiceSerializer, InvoiceListSerializer


class InvoiceListCreateView(CompanyFilterMixin, generics.ListCreateAPIView):
    """
    GET  /api/billing/invoices/  → facturas de la empresa del usuario
    POST /api/billing/invoices/  → crear factura
    """
    queryset           = Invoice.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['number', 'client__first_name', 'client__last_name', 'client__company_name']
    ordering_fields    = ['issue_date', 'due_date', 'total', 'created_at']
    ordering           = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset().select_related('client', 'created_by')

        status       = self.request.query_params.get('status')
        invoice_type = self.request.query_params.get('invoice_type')
        client       = self.request.query_params.get('client')

        if status:
            queryset = queryset.filter(status=status)
        if invoice_type:
            queryset = queryset.filter(invoice_type=invoice_type)
        if client:
            queryset = queryset.filter(client_id=client)
        return queryset

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return InvoiceListSerializer
        return InvoiceSerializer


class InvoiceDetailView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset           = Invoice.objects.all()
    serializer_class   = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return super().get_queryset().prefetch_related('items__product').select_related('client', 'created_by')


class InvoiceSummaryView(APIView):
    """
    GET /api/billing/summary/
    Solo muestra métricas de la empresa del usuario autenticado.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Sum
        from decimal import Decimal

        # Filtramos por empresa — datos aislados por tenant
        invoices = Invoice.objects.filter(company=request.user.company)

        summary = {
            'total_invoices': invoices.filter(invoice_type='invoice').count(),
            'total_quotes':   invoices.filter(invoice_type='quote').count(),
            'paid_total':     invoices.filter(status='paid').aggregate(t=Sum('total'))['t'] or Decimal('0'),
            'pending_total':  invoices.filter(status__in=['draft', 'sent']).aggregate(t=Sum('total'))['t'] or Decimal('0'),
            'overdue_count':  invoices.filter(status='overdue').count(),
        }
        return Response(summary)


class MonthlyRevenueView(APIView):
    """
    GET /api/billing/monthly-revenue/
    Devuelve las ventas pagadas agrupadas por mes (últimos 6 meses).
    Usada para la gráfica de barras del dashboard.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Sum
        from django.db.models.functions import TruncMonth
        from django.utils import timezone
        from datetime import timedelta
        from decimal import Decimal

        # Últimos 6 meses
        since = timezone.now() - timedelta(days=180)

        rows = (
            Invoice.objects
            .filter(company=request.user.company, status='paid', issue_date__gte=since)
            .annotate(month=TruncMonth('issue_date'))
            .values('month')
            .annotate(total=Sum('total'))
            .order_by('month')
        )

        MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

        data = [
            {
                'mes': MESES[row['month'].month - 1],
                'total': float(row['total'] or Decimal('0')),
            }
            for row in rows
        ]

        return Response(data)


class RecentInvoicesView(APIView):
    """
    GET /api/billing/recent/
    Devuelve las últimas 5 facturas de la empresa para el dashboard.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        invoices = (
            Invoice.objects
            .filter(company=request.user.company)
            .select_related('client')
            .order_by('-created_at')[:5]
        )
        data = [
            {
                'id':     inv.id,
                'number': inv.number,
                'client': str(inv.client) if inv.client else '—',
                'total':  float(inv.total),
                'status': inv.status,
            }
            for inv in invoices
        ]
        return Response(data)
