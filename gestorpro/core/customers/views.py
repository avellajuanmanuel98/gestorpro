from django.db.models import ProtectedError
from rest_framework.exceptions import ValidationError

from gestorpro.core.api.views import TenantDetailView, TenantListCreateView, crud_permissions

from .models import Customer
from .serializers import CustomerListSerializer, CustomerSerializer

LIST_PERMS, DETAIL_PERMS = crud_permissions('customers')


class CustomerListCreateView(TenantListCreateView):
    model = Customer
    required_permissions = LIST_PERMS
    search_fields = ['first_name', 'last_name', 'email', 'company_name', 'document_number']
    ordering_fields = ['first_name', 'created_at']
    ordering = ['first_name', 'id']

    def get_queryset(self):
        qs = super().get_queryset()
        status = self.request.query_params.get('status')
        return qs.filter(status=status) if status else qs

    def get_serializer_class(self):
        return CustomerListSerializer if self.request.method == 'GET' else CustomerSerializer


class CustomerDetailView(TenantDetailView):
    model = Customer
    serializer_class = CustomerSerializer
    required_permissions = DETAIL_PERMS

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError('El cliente tiene documentos asociados; márcalo como inactivo.')
