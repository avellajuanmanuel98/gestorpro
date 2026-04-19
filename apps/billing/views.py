from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Invoice
from .serializers import InvoiceSerializer, InvoiceListSerializer


class InvoiceListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/billing/invoices/  → listar facturas
    POST /api/billing/invoices/  → crear factura con sus líneas

    Filtros:
      ?status=draft|sent|paid|overdue|cancelled
      ?invoice_type=quote|invoice
      ?client=1
    """
    permission_classes = [IsAuthenticated]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['number', 'client__first_name', 'client__last_name', 'client__company_name']
    ordering_fields    = ['issue_date', 'due_date', 'total', 'created_at']
    ordering           = ['-created_at']

    def get_queryset(self):
        queryset = Invoice.objects.select_related('client', 'created_by')

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

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class InvoiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/billing/invoices/{id}/
    PUT    /api/billing/invoices/{id}/
    DELETE /api/billing/invoices/{id}/
    """
    queryset           = Invoice.objects.prefetch_related('items__product').select_related('client', 'created_by')
    serializer_class   = InvoiceSerializer
    permission_classes = [IsAuthenticated]


class InvoiceSummaryView(APIView):
    """
    GET /api/billing/summary/
    Estadísticas rápidas para el dashboard.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Sum, Count
        from decimal import Decimal

        invoices = Invoice.objects.all()

        summary = {
            'total_invoices' : invoices.filter(invoice_type='invoice').count(),
            'total_quotes'   : invoices.filter(invoice_type='quote').count(),
            'paid_total'     : invoices.filter(status='paid').aggregate(t=Sum('total'))['t'] or Decimal('0'),
            'pending_total'  : invoices.filter(status__in=['draft','sent']).aggregate(t=Sum('total'))['t'] or Decimal('0'),
            'overdue_count'  : invoices.filter(status='overdue').count(),
        }
        return Response(summary)
