from rest_framework import filters, generics, status
from rest_framework.response import Response

from gestorpro.core.access.permissions import HasTenantPermission

from . import services
from .models import PurchaseReceipt
from .serializers import PurchaseCreateSerializer, PurchaseDetailSerializer, PurchaseSerializer


class PurchaseListCreateView(generics.ListCreateAPIView):
    serializer_class = PurchaseSerializer
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'purchases.view', 'POST': 'purchases.create'}
    filter_backends = [filters.SearchFilter]
    search_fields = ['number', 'supplier_invoice', 'supplier__company_name']

    def get_queryset(self):
        return PurchaseReceipt.objects.select_related('supplier', 'created_by')

    def create(self, request, *args, **kwargs):
        data = PurchaseCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        receipt = services.register_purchase(user=request.user, **data.validated_data)
        return Response(PurchaseDetailSerializer(receipt).data, status=status.HTTP_201_CREATED)


class PurchaseDetailView(generics.RetrieveAPIView):
    serializer_class = PurchaseDetailSerializer
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'purchases.view'}

    def get_queryset(self):
        return PurchaseReceipt.objects.select_related('supplier', 'created_by').prefetch_related('lines__item__unit',
                                                                                               'lines__unit')
