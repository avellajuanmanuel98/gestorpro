from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated
from apps.companies.mixins import CompanyFilterMixin

from .models import Employee
from .serializers import EmployeeSerializer, EmployeeListSerializer


class EmployeeListCreateView(CompanyFilterMixin, generics.ListCreateAPIView):
    """
    GET  /api/employees/  → lista empleados de la empresa
    POST /api/employees/  → crea un empleado
    """
    queryset           = Employee.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['first_name', 'last_name', 'email', 'position', 'document_number']
    ordering_fields    = ['first_name', 'hire_date', 'department']
    ordering           = ['first_name']

    def get_queryset(self):
        queryset = super().get_queryset()
        status     = self.request.query_params.get('status')
        department = self.request.query_params.get('department')
        if status:
            queryset = queryset.filter(status=status)
        if department:
            queryset = queryset.filter(department=department)
        return queryset

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return EmployeeListSerializer
        return EmployeeSerializer

    def perform_create(self, serializer):
        serializer.save(
            company=self.request.user.company,
            created_by=self.request.user,
        )


class EmployeeDetailView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/DELETE /api/employees/{id}/
    Solo permite acceder a empleados de la propia empresa.
    """
    queryset           = Employee.objects.all()
    serializer_class   = EmployeeSerializer
    permission_classes = [IsAuthenticated]
