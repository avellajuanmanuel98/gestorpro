from django.urls import path

from .views import (
    InvoiceDetailView,
    InvoiceListCreateView,
    InvoiceSummaryView,
    MonthlyRevenueView,
    RecentInvoicesView,
)

urlpatterns = [
    path('invoices/', InvoiceListCreateView.as_view(), name='invoice-list'),
    path('invoices/<int:pk>/', InvoiceDetailView.as_view(), name='invoice-detail'),
    path('summary/', InvoiceSummaryView.as_view(), name='billing-summary'),
    path('monthly-revenue/', MonthlyRevenueView.as_view(), name='billing-monthly-revenue'),
    path('recent/', RecentInvoicesView.as_view(), name='billing-recent'),
]
