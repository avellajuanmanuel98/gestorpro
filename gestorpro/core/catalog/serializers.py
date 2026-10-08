from rest_framework import serializers

from gestorpro.core.api.serializers import TenantModelSerializer

from .models import Category, Product


class CategorySerializer(TenantModelSerializer):
    products_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'tenant', 'name', 'description', 'products_count', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProductSerializer(TenantModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)
    created_by = serializers.StringRelatedField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'tenant', 'name', 'code', 'description', 'product_type',
            'category', 'category_name', 'image',
            'price', 'tax_rate',
            'stock', 'minimum_stock', 'is_low_stock',
            'is_active', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'code', 'product_type', 'category', 'category_name',
                  'price', 'tax_rate', 'stock', 'minimum_stock', 'is_low_stock', 'is_active']
