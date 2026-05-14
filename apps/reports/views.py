from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


class BillingReportView(APIView):
    """
    GET /api/reports/billing/
    Métricas avanzadas de facturación: tendencia 12 meses,
    desglose por estado y top 5 clientes por ingreso.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.billing.models import Invoice

        company  = request.user.company
        invoices = Invoice.objects.filter(company=company)

        # ── Tendencia mensual (últimos 12 meses) ────────────────
        since = timezone.now() - timedelta(days=365)
        MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

        monthly_rows = (
            invoices
            .filter(status='paid', issue_date__gte=since)
            .annotate(month=TruncMonth('issue_date'))
            .values('month')
            .annotate(total=Sum('total'), count=Count('id'))
            .order_by('month')
        )
        monthly_trend = [
            {
                'mes':   MESES[r['month'].month - 1],
                'total': float(r['total'] or 0),
                'count': r['count'],
            }
            for r in monthly_rows
        ]

        # ── Desglose por estado ─────────────────────────────────
        STATUS_LABELS = {
            'draft': 'Borrador', 'sent': 'Enviada',
            'paid': 'Pagada', 'overdue': 'Vencida', 'cancelled': 'Cancelada',
        }
        status_rows = (
            invoices
            .filter(invoice_type='invoice')
            .values('status')
            .annotate(count=Count('id'), total=Sum('total'))
            .order_by('status')
        )
        status_breakdown = [
            {
                'status': r['status'],
                'label':  STATUS_LABELS.get(r['status'], r['status']),
                'count':  r['count'],
                'total':  float(r['total'] or 0),
            }
            for r in status_rows
        ]

        # ── Top 5 clientes por facturación pagada ───────────────
        top_clients_rows = (
            invoices
            .filter(status='paid')
            .values('client__first_name', 'client__last_name', 'client__company_name')
            .annotate(total=Sum('total'), count=Count('id'))
            .order_by('-total')[:5]
        )
        top_clients = []
        for r in top_clients_rows:
            name = f"{r['client__first_name']} {r['client__last_name']}".strip()
            if r['client__company_name']:
                name = r['client__company_name']
            top_clients.append({
                'name':  name or '—',
                'total': float(r['total'] or 0),
                'count': r['count'],
            })

        return Response({
            'monthly_trend':    monthly_trend,
            'status_breakdown': status_breakdown,
            'top_clients':      top_clients,
        })


class InventoryReportView(APIView):
    """
    GET /api/reports/inventory/
    Stock por categoría, valor del inventario y productos con bajo stock.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.inventory.models import Product

        company  = request.user.company
        products = Product.objects.filter(company=company, is_active=True)

        # ── Stock por categoría ─────────────────────────────────
        category_rows = (
            products
            .filter(product_type='product')
            .values('category__name')
            .annotate(stock=Sum('stock'), count=Count('id'))
            .order_by('-stock')
        )
        by_category = [
            {
                'categoria': r['category__name'] or 'Sin categoría',
                'stock':     r['stock'] or 0,
                'productos': r['count'],
            }
            for r in category_rows
        ]

        # ── Productos con bajo stock ────────────────────────────
        low_stock = list(
            products
            .filter(product_type='product', stock__lte=models_minimum_stock())
            .order_by('stock')
            .values('name', 'code', 'stock', 'minimum_stock')[:10]
        )

        # ── Totales generales ───────────────────────────────────
        totals = products.aggregate(
            total_productos=Count('id', filter=Q(product_type='product')),
            total_servicios=Count('id', filter=Q(product_type='service')),
            valor_inventario=Sum('price', filter=Q(product_type='product')),
        )

        return Response({
            'by_category':       by_category,
            'low_stock':         low_stock,
            'total_productos':   totals['total_productos'] or 0,
            'total_servicios':   totals['total_servicios'] or 0,
            'valor_inventario':  float(totals['valor_inventario'] or 0),
        })


def models_minimum_stock():
    """Helper para filtrar productos cuyo stock <= minimum_stock usando F()."""
    from django.db.models import F
    return F('minimum_stock')


class HRReportView(APIView):
    """
    GET /api/reports/hr/
    Empleados por departamento, estado activo/inactivo
    y proveedores por categoría.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.employees.models import Employee
        from apps.suppliers.models import Supplier

        company = request.user.company

        # ── Empleados por departamento ──────────────────────────
        DEPT_LABELS = {
            'admin': 'Administración', 'sales': 'Ventas',
            'operations': 'Operaciones', 'finance': 'Finanzas',
            'it': 'Tecnología', 'hr': 'RR.HH.', 'other': 'Otro',
        }
        dept_rows = (
            Employee.objects
            .filter(company=company)
            .values('department')
            .annotate(total=Count('id'))
            .order_by('-total')
        )
        by_department = [
            {
                'departamento': DEPT_LABELS.get(r['department'], r['department']),
                'total':        r['total'],
            }
            for r in dept_rows
        ]

        # ── Empleados activos / inactivos ───────────────────────
        emp_totals = Employee.objects.filter(company=company).aggregate(
            activos=Count('id', filter=Q(status='active')),
            inactivos=Count('id', filter=Q(status='inactive')),
        )

        # ── Proveedores por categoría ───────────────────────────
        CAT_LABELS = {
            'materials': 'Materiales', 'services': 'Servicios',
            'technology': 'Tecnología', 'logistics': 'Logística',
            'marketing': 'Marketing', 'other': 'Otro',
        }
        cat_rows = (
            Supplier.objects
            .filter(company=company)
            .values('category')
            .annotate(total=Count('id'))
            .order_by('-total')
        )
        suppliers_by_category = [
            {
                'categoria': CAT_LABELS.get(r['category'], r['category']),
                'total':     r['total'],
            }
            for r in cat_rows
        ]

        return Response({
            'by_department':        by_department,
            'employees_active':     emp_totals['activos'] or 0,
            'employees_inactive':   emp_totals['inactivos'] or 0,
            'suppliers_by_category': suppliers_by_category,
        })
