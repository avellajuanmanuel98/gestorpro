from rest_framework import serializers
from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    # Contamos cuántos productos tiene cada categoría
    products_count = serializers.IntegerField(source='products.count', read_only=True)

    class Meta:
        model  = Category
        fields = ['id', 'name', 'description', 'products_count', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProductSerializer(serializers.ModelSerializer):
    category_name  = serializers.CharField(source='category.name', read_only=True)
    created_by     = serializers.StringRelatedField(read_only=True)
    is_low_stock   = serializers.BooleanField(read_only=True)
    price_with_tax = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model  = Product
        fields = [
            'id', 'name', 'code', 'description', 'product_type',
            'category', 'category_name', 'image',
            'price', 'tax_rate', 'price_with_tax',
            'stock', 'minimum_stock', 'is_low_stock',
            'is_active', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class ProductListSerializer(serializers.ModelSerializer):
    """Versión reducida para el listado."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_low_stock  = serializers.BooleanField(read_only=True)

    class Meta:
        model  = Product
        fields = [
            'id', 'name', 'code', 'product_type',
            'category_name', 'price', 'stock', 'is_low_stock', 'is_active',
        ]
