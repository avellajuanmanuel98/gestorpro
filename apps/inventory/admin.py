from django.contrib import admin
from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ['name', 'description', 'created_at']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display   = ['code', 'name', 'category', 'price', 'stock', 'is_active']
    list_filter    = ['product_type', 'category', 'is_active']
    search_fields  = ['name', 'code']
    readonly_fields = ['created_by', 'created_at', 'updated_at']
    list_editable  = ['is_active']
