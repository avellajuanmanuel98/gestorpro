from django.urls import path

from .views import (
    CategoryDetailView,
    CategoryListCreateView,
    ItemDetailView,
    ItemListCreateView,
    LowStockView,
    UnitListView,
)

urlpatterns = [
    path('units/', UnitListView.as_view(), name='unit-list'),
    path('categories/', CategoryListCreateView.as_view(), name='category-list'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),
    path('items/', ItemListCreateView.as_view(), name='item-list'),
    path('items/<int:pk>/', ItemDetailView.as_view(), name='item-detail'),
    path('low-stock/', LowStockView.as_view(), name='low-stock'),
]
