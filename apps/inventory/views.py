from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer, ProductListSerializer


class CategoryListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/inventory/categories/  → listar categorías
    POST /api/inventory/categories/  → crear categoría
    """
    queryset           = Category.objects.all()
    serializer_class   = CategorySerializer
    permission_classes = [IsAuthenticated]


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/inventory/categories/{id}/
    PUT    /api/inventory/categories/{id}/
    DELETE /api/inventory/categories/{id}/
    """
    queryset           = Category.objects.all()
    serializer_class   = CategorySerializer
    permission_classes = [IsAuthenticated]


class ProductListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/inventory/products/  → listar productos
    POST /api/inventory/products/  → crear producto

    Filtros disponibles:
      ?search=nombre
      ?category=1
      ?product_type=product
      ?low_stock=true  → solo productos con stock bajo
    """
    permission_classes = [IsAuthenticated]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['name', 'code', 'description']
    ordering_fields    = ['name', 'price', 'stock', 'created_at']
    ordering           = ['name']

    def get_queryset(self):
        queryset = Product.objects.select_related('category', 'created_by')

        # Filtros opcionales por query params
        category     = self.request.query_params.get('category')
        product_type = self.request.query_params.get('product_type')
        is_active    = self.request.query_params.get('is_active')
        low_stock    = self.request.query_params.get('low_stock')

        if category:
            queryset = queryset.filter(category_id=category)
        if product_type:
            queryset = queryset.filter(product_type=product_type)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        if low_stock == 'true':
            # Productos físicos con stock <= minimum_stock
            from django.db.models import F
            queryset = queryset.filter(
                product_type='product',
                stock__lte=F('minimum_stock')
            )
        return queryset

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ProductListSerializer
        return ProductSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/inventory/products/{id}/
    PUT    /api/inventory/products/{id}/
    DELETE /api/inventory/products/{id}/
    """
    queryset           = Product.objects.select_related('category', 'created_by')
    serializer_class   = ProductSerializer
    permission_classes = [IsAuthenticated]


class LowStockView(APIView):
    """
    GET /api/inventory/low-stock/
    Devuelve todos los productos con stock por debajo del mínimo.
    Útil para el dashboard de alertas.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import F
        products = Product.objects.filter(
            product_type='product',
            stock__lte=F('minimum_stock'),
            is_active=True
        ).select_related('category')

        serializer = ProductListSerializer(products, many=True)
        return Response({
            'count': products.count(),
            'results': serializer.data
        })
