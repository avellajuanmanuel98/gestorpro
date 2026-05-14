from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated
from apps.companies.mixins import CompanyFilterMixin

from .models import Supplier
from .serializers import SupplierSerializer, SupplierListSerializer


class SupplierListCreateView(CompanyFilterMixin, generics.ListCreateAPIView):
    """
    GET  /api/suppliers/  → lista proveedores de la empresa
    POST /api/suppliers/  → crea un proveedor
    """
    queryset           = Supplier.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['company_name', 'contact_name', 'email', 'document_number']
    ordering_fields    = ['company_name', 'category', 'created_at']
    ordering           = ['company_name']

    def get_queryset(self):
        queryset = super().get_queryset()
        status   = self.request.query_params.get('status')
        category = self.request.query_params.get('category')
        if status:
            queryset = queryset.filter(status=status)
        if category:
            queryset = queryset.filter(category=category)
        return queryset

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return SupplierListSerializer
        return SupplierSerializer

    def perform_create(self, serializer):
        serializer.save(
            company=self.request.user.company,
            created_by=self.request.user,
        )


class SupplierDetailView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/DELETE /api/suppliers/{id}/
    Solo permite acceder a proveedores de la propia empresa.
    """
    queryset           = Supplier.objects.all()
    serializer_class   = SupplierSerializer
    permission_classes = [IsAuthenticated]
