from django.db.models import Count, Q
from rest_framework.response import Response
from rest_framework.views import APIView

from gestorpro.core.access.permissions import HasTenantPermission
from gestorpro.core.api.views import TenantDetailView, TenantListCreateView
from gestorpro.core.suppliers.models import Supplier

from .models import Employee
from .serializers import EmployeeListSerializer, EmployeeSerializer


class EmployeeListCreateView(TenantListCreateView):
    model = Employee
    required_feature = 'module.hr'
    required_permissions = {'GET': 'hr.view', 'POST': 'hr.manage'}
    search_fields = ['first_name', 'last_name', 'email', 'position', 'document_number']
    ordering_fields = ['first_name', 'hire_date', 'department']
    ordering = ['first_name', 'id']

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if params.get('status'):
            qs = qs.filter(status=params['status'])
        if params.get('department'):
            qs = qs.filter(department=params['department'])
        return qs

    def get_serializer_class(self):
        return EmployeeListSerializer if self.request.method == 'GET' else EmployeeSerializer


class EmployeeDetailView(TenantDetailView):
    model = Employee
    required_feature = 'module.hr'
    serializer_class = EmployeeSerializer
    required_permissions = {'GET': 'hr.view', 'PUT': 'hr.manage', 'PATCH': 'hr.manage', 'DELETE': 'hr.manage'}


class HRReportView(APIView):
    """GET /api/reports/hr/ — empleados por área/estado y proveedores por categoría."""
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'hr.view'}
    required_feature = 'module.hr'

    def get(self, request):
        departments = dict(Employee.Department.choices)
        categories = dict(Supplier.Category.choices)
        totals = Employee.objects.aggregate(
            activos=Count('id', filter=Q(status=Employee.Status.ACTIVE)),
            inactivos=Count('id', filter=Q(status=Employee.Status.INACTIVE)),
        )
        return Response({
            'by_department': [
                {'departamento': departments.get(r['department'], r['department']), 'total': r['total']}
                for r in Employee.objects.values('department').annotate(total=Count('id')).order_by('-total')
            ],
            'employees_active': totals['activos'],
            'employees_inactive': totals['inactivos'],
            'suppliers_by_category': [
                {'categoria': categories.get(r['category'], r['category']), 'total': r['total']}
                for r in Supplier.objects.values('category').annotate(total=Count('id')).order_by('-total')
            ],
        })
