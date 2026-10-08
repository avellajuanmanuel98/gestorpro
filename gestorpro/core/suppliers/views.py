from gestorpro.core.api.views import TenantDetailView, TenantListCreateView, crud_permissions

from .models import Supplier
from .serializers import SupplierListSerializer, SupplierSerializer

LIST_PERMS, DETAIL_PERMS = crud_permissions('suppliers')


class SupplierListCreateView(TenantListCreateView):
    model = Supplier
    required_permissions = LIST_PERMS
    search_fields = ['company_name', 'contact_name', 'email', 'document_number']
    ordering_fields = ['company_name', 'category', 'created_at']
    ordering = ['company_name', 'id']

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if params.get('status'):
            qs = qs.filter(status=params['status'])
        if params.get('category'):
            qs = qs.filter(category=params['category'])
        return qs

    def get_serializer_class(self):
        return SupplierListSerializer if self.request.method == 'GET' else SupplierSerializer


class SupplierDetailView(TenantDetailView):
    model = Supplier
    serializer_class = SupplierSerializer
    required_permissions = DETAIL_PERMS
