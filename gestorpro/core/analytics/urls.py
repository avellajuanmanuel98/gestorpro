from django.urls import path

from .views import BreakdownView, CashReportView, CoverageView, HourlyView, ProductsView, SummaryView

urlpatterns = [
    path('summary/', SummaryView.as_view(), name='analytics-summary'),
    path('hourly/', HourlyView.as_view(), name='analytics-hourly'),
    path('breakdown/', BreakdownView.as_view(), name='analytics-breakdown'),
    path('products/', ProductsView.as_view(), name='analytics-products'),
    path('cash/', CashReportView.as_view(), name='analytics-cash'),
    path('coverage/', CoverageView.as_view(), name='analytics-coverage'),
]
