from django.db.models import Count, F, ProtectedError, Q
from rest_framework import generics
from rest_framework.exceptions import ValidationError

from gestorpro.core import entitlements
from gestorpro.core.access.permissions import HasTenantPermission
from gestorpro.core.api.views import TenantDetailView, TenantListCreateView

from . import services
from .models import Category, Item, UnitOfMeasure
from .serializers import CategorySerializer, ItemListSerializer, ItemSerializer, UnitSerializer

LIST_PERMS = {'GET': 'catalog.view', 'POST': 'catalog.manage'}
DETAIL_PERMS = {'GET': 'catalog.view', 'PUT': 'catalog.manage', 'PATCH': 'catalog.manage',
                'DELETE': 'catalog.manage'}

# ?group=products | ingredients: las dos pantallas del catálogo
GROUPS = {
    'products': Q(kind__in=Item.PRODUCT_KINDS),
    'ingredients': Q(kind=Item.Kind.RAW_MATERIAL),
}


def _low_stock(qs):
    return qs.exclude(kind=Item.Kind.SERVICE).filter(minimum_stock__gt=0, stock__lte=F('minimum_stock'))


class UnitListView(generics.ListAPIView):
    """Unidades de medida (globales). Cualquier miembro puede listarlas."""
    serializer_class = UnitSerializer
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'catalog.view'}
    pagination_class = None
    queryset = UnitOfMeasure.objects.all()


class CategoryListCreateView(TenantListCreateView):
    model = Category
    serializer_class = CategorySerializer
    required_permissions = LIST_PERMS
    search_fields = ['name']
    ordering = ['name']

    def get_queryset(self):
        qs = super().get_queryset().annotate(items_count=Count('items'))
        if self.request.query_params.get('kind') in Category.Kind.values:
            qs = qs.filter(kind=self.request.query_params['kind'])
        return qs


class CategoryDetailView(TenantDetailView):
    model = Category
    serializer_class = CategorySerializer
    required_permissions = DETAIL_PERMS

    def get_queryset(self):
        return super().get_queryset().annotate(items_count=Count('items'))


class ItemListCreateView(TenantListCreateView):
    model = Item
    required_permissions = LIST_PERMS
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'price', 'stock', 'avg_cost', 'created_at']
    ordering = ['name', 'id']

    def get_queryset(self):
        qs = super().get_queryset().select_related('category', 'unit')
        params = self.request.query_params
        if params.get('group') in GROUPS:
            qs = qs.filter(GROUPS[params['group']])
        if params.get('kind') in Item.Kind.values:
            qs = qs.filter(kind=params['kind'])
        if params.get('category'):
            qs = qs.filter(category_id=params['category'])
        if params.get('is_sellable') is not None:
            qs = qs.filter(is_sellable=params['is_sellable'].lower() == 'true')
        if params.get('is_active') is not None:
            qs = qs.filter(is_active=params['is_active'].lower() == 'true')
        if params.get('low_stock') == 'true':
            qs = _low_stock(qs)
        return qs

    def get_serializer_class(self):
        return ItemListSerializer if self.request.method == 'GET' else ItemSerializer

    def perform_create(self, serializer):
        if serializer.validated_data['kind'] in Item.PRODUCT_KINDS:
            entitlements.check_limit(self.request.membership.tenant_id, 'products', services.products_count())
        super().perform_create(serializer)


class ItemDetailView(TenantDetailView):
    model = Item
    serializer_class = ItemSerializer
    required_permissions = DETAIL_PERMS

    def get_queryset(self):
        return super().get_queryset().select_related('category', 'unit')

    def perform_update(self, serializer):
        becomes_product = (serializer.instance.kind == Item.Kind.RAW_MATERIAL
                           and serializer.validated_data.get('kind') in Item.PRODUCT_KINDS)
        if becomes_product:
            entitlements.check_limit(self.request.membership.tenant_id, 'products', services.products_count())
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        try:
            super().perform_destroy(instance)
        except ProtectedError:
            raise ValidationError('El ítem aparece en documentos; desactívalo en lugar de eliminarlo.')


class LowStockView(TenantListCreateView):
    """Productos e ingredientes activos en o por debajo de su existencia mínima."""
    model = Item
    serializer_class = ItemListSerializer
    required_permissions = {'GET': 'catalog.view'}
    http_method_names = ['get', 'head', 'options']
    ordering = ['stock', 'name']

    def get_queryset(self):
        qs = _low_stock(super().get_queryset().select_related('category', 'unit').filter(is_active=True))
        if self.request.query_params.get('group') in GROUPS:
            qs = qs.filter(GROUPS[self.request.query_params['group']])
        return qs
