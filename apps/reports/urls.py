from django.urls import path
from .views import BillingReportView, InventoryReportView, HRReportView

urlpatterns = [
    path('billing/',   BillingReportView.as_view(),   name='report-billing'),
    path('inventory/', InventoryReportView.as_view(),  name='report-inventory'),
    path('hr/',        HRReportView.as_view(),         name='report-hr'),
]
