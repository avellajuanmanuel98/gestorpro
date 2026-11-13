from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from gestorpro.core.access.permissions import HasTenantPermission
from gestorpro.core.tenancy.models import Location

from . import services
from .export import csv_response
from .periods import resolve


class AnalyticsView(APIView):
    """Base: período (?period=today|…|custom&from=&to=), sucursal (?location=) y ?export=csv."""
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'reports.view'}

    def setup_query(self, request):
        p = request.query_params
        period = resolve(request.tenant, p.get('period', 'today'), p.get('from'), p.get('to'))
        location = None
        if p.get('location'):
            location = Location.objects.filter(pk=p['location']).first()
            if location is None:
                raise ValidationError({'location': 'Sucursal inexistente.'})
        return period, location, request.membership.has_perm('catalog.view_costs')

    @staticmethod
    def wants_csv(request) -> bool:
        return request.query_params.get('export') == 'csv'


class SummaryView(AnalyticsView):
    """KPIs del período contra el período comparable + qué requiere atención."""

    def get(self, request):
        period, location, costs = self.setup_query(request)
        return Response({'period': period.as_dict(), 'kpis': services.kpis(period, location, costs),
                         'attention': services.attention(costs)})


class HourlyView(AnalyticsView):
    def get(self, request):
        period, location, _ = self.setup_query(request)
        return Response({'period': period.as_dict(), 'hours': services.by_hour(period, location)})


class BreakdownView(AnalyticsView):
    BY = {'day': 'Día', 'weekday': 'Día de la semana', 'method': 'Medio de pago', 'cashier': 'Cajero',
          'category': 'Categoría'}

    def get(self, request):
        period, location, _ = self.setup_query(request)
        by = request.query_params.get('by', 'day')
        if by not in self.BY:
            raise ValidationError({'by': f'Usa uno de: {", ".join(self.BY)}.'})
        rows = services.breakdown(period, by, location)
        if self.wants_csv(request):
            return csv_response(f'ventas-por-{by}', [('label', self.BY[by]), ('sales', 'Ventas'),
                                                     ('transactions', 'Transacciones')], rows)
        return Response({'period': period.as_dict(), 'by': by, 'rows': rows})


class ProductsView(AnalyticsView):
    """Rentabilidad por producto, producido vs. vendido vs. merma, y matriz volumen × margen."""

    def get(self, request):
        period, location, costs = self.setup_query(request)
        rows = services.products(period, location, costs)
        if self.wants_csv(request):
            columns = [('name', 'Producto'), ('category', 'Categoría'), ('unit', 'Unidad'), ('units', 'Vendido'),
                       ('revenue', 'Ingreso sin IVA'), ('produced', 'Producido'), ('wasted', 'Merma'),
                       ('waste_rate_pct', 'Tasa de merma %')]
            if costs:
                columns += [('cost', 'Costo'), ('gross_profit', 'Utilidad bruta'), ('margin_pct', 'Margen %'),
                            ('quadrant_label', 'Clasificación')]
            return csv_response('rentabilidad-por-producto', columns, rows)
        return Response({'period': period.as_dict(), 'rows': rows, 'costs': costs})


class CashReportView(AnalyticsView):
    required_permissions = {'GET': 'cash.manage'}

    def get(self, request):
        period, location, _ = self.setup_query(request)
        data = services.cash_sessions(period, location)
        if self.wants_csv(request):
            return csv_response('cierres-de-caja', [
                ('register', 'Caja'), ('cashier', 'Cajero'), ('opened_at', 'Apertura'), ('closed_at', 'Cierre'),
                ('expected', 'Esperado'), ('counted', 'Contado'), ('difference', 'Diferencia'), ('note', 'Nota')],
                data['sessions'])
        return Response({'period': period.as_dict(), **data})


class CoverageView(AnalyticsView):
    """Días de cobertura de los ingredientes según el consumo de los últimos 30 días."""
    required_permissions = {'GET': 'inventory.view'}

    def get(self, request):
        return Response({'rows': services.coverage()})
