from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.companies.mixins import CompanyFilterMixin

from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer, ProductListSerializer


class CategoryListCreateView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset           = Category.objects.all()
    serializer_class   = CategorySerializer
    permission_classes = [IsAuthenticated]


class CategoryDetailView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset           = Category.objects.all()
    serializer_class   = CategorySerializer
    permission_classes = [IsAuthenticated]


class ProductListCreateView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset           = Product.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['name', 'code', 'description']
    ordering_fields    = ['name', 'price', 'stock', 'created_at']
    ordering           = ['name']

    def get_queryset(self):
        queryset = super().get_queryset().select_related('category', 'created_by')

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
            from django.db.models import F
            queryset = queryset.filter(product_type='product', stock__lte=F('minimum_stock'))
        return queryset

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ProductListSerializer
        return ProductSerializer


class ProductDetailView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset           = Product.objects.all()
    serializer_class   = ProductSerializer
    permission_classes = [IsAuthenticated]


class LowStockView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import F
        products = Product.objects.filter(
            company=request.user.company,
            product_type='product',
            stock__lte=F('minimum_stock'),
            is_active=True
        ).select_related('category')

        serializer = ProductListSerializer(products, many=True)
        return Response({'count': products.count(), 'results': serializer.data})
