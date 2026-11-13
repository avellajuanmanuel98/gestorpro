from django.urls import path

from .views import PurchaseDetailView, PurchaseListCreateView

urlpatterns = [
    path('', PurchaseListCreateView.as_view(), name='purchase-list'),
    path('<int:pk>/', PurchaseDetailView.as_view(), name='purchase-detail'),
]
