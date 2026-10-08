from django.urls import path

from .views import (
    CategoryDetailView,
    CategoryListCreateView,
    LowStockView,
    ProductDetailView,
    ProductListCreateView,
)

urlpatterns = [
    path('categories/', CategoryListCreateView.as_view(), name='category-list'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),
    path('products/', ProductListCreateView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('low-stock/', LowStockView.as_view(), name='low-stock'),
]
