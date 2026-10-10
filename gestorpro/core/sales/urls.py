from django.urls import path

from .views import (
    PaymentMethodListView,
    POSCatalogView,
    SaleDetailView,
    SaleListCreateView,
    SalesTodayView,
    SaleVoidView,
)

urlpatterns = [
    path('', SaleListCreateView.as_view(), name='sale-list'),
    path('<int:pk>/', SaleDetailView.as_view(), name='sale-detail'),
    path('<int:pk>/void/', SaleVoidView.as_view(), name='sale-void'),
    path('catalog/', POSCatalogView.as_view(), name='pos-catalog'),
    path('payment-methods/', PaymentMethodListView.as_view(), name='payment-methods'),
    path('today/', SalesTodayView.as_view(), name='sales-today'),
]
