from django.db.models import Count, F, ProtectedError
from rest_framework.exceptions import ValidationError

from gestorpro.core import entitlements
from gestorpro.core.api.views import TenantDetailView, TenantListCreateView

from .models import Category, Product
from .serializers import CategorySerializer, ProductListSerializer, ProductSerializer

LIST_PERMS = {'GET': 'catalog.view', 'POST': 'catalog.manage'}
DETAIL_PERMS = {'GET': 'catalog.view', 'PUT': 'catalog.manage', 'PATCH': 'catalog.manage',
                'DELETE': 'catalog.manage'}


class CategoryListCreateView(TenantListCreateView):
    model = Category
    serializer_class = CategorySerializer
    required_permissions = LIST_PERMS
    search_fields = ['name']
    ordering = ['name']

    def get_queryset(self):
        return super().get_queryset().annotate(products_count=Count('products'))


class CategoryDetailView(TenantDetailView):
    model = Category
    serializer_class = CategorySerializer
    required_permissions = DETAIL_PERMS

    def get_queryset(self):
        return super().get_queryset().annotate(products_count=Count('products'))


class ProductListCreateView(TenantListCreateView):
    model = Product
    required_permissions = LIST_PERMS
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'price', 'stock', 'created_at']
    ordering = ['name', 'id']

    def get_queryset(self):
        qs = super().get_queryset().select_related('category')
        params = self.request.query_params
        if params.get('category'):
            qs = qs.filter(category_id=params['category'])
        if params.get('product_type'):
            qs = qs.filter(product_type=params['product_type'])
        if params.get('is_active') is not None:
            qs = qs.filter(is_active=params['is_active'].lower() == 'true')
        if params.get('low_stock') == 'true':
            qs = qs.filter(product_type=Product.ProductType.PRODUCT, stock__lte=F('minimum_stock'))
        return qs

    def get_serializer_class(self):
        return ProductListSerializer if self.request.method == 'GET' else ProductSerializer

    def perform_create(self, serializer):
        entitlements.check_limit(self.request.membership.tenant_id, 'products', Product.objects.count())
        super().perform_create(serializer)


class ProductDetailView(TenantDetailView):
    model = Product
    serializer_class = ProductSerializer
    required_permissions = DETAIL_PERMS

    def perform_destroy(self, instance):
        try:
            super().perform_destroy(instance)
        except ProtectedError:
            raise ValidationError('El producto aparece en documentos; desactívalo en lugar de eliminarlo.')


class LowStockView(TenantListCreateView):
    model = Product
    serializer_class = ProductListSerializer
    required_permissions = {'GET': 'catalog.view'}
    http_method_names = ['get', 'head', 'options']
    ordering = ['stock', 'name']

    def get_queryset(self):
        return super().get_queryset().select_related('category').filter(
            product_type=Product.ProductType.PRODUCT, is_active=True, stock__lte=F('minimum_stock'),
        )
