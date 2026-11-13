from django.urls import path

from .views import BillingReportView, InventoryReportView

urlpatterns = [
    path('billing/', BillingReportView.as_view(), name='report-billing'),
    path('inventory/', InventoryReportView.as_view(), name='report-inventory'),
]
