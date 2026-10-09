from django.urls import path

from .views import CurrentTenantView, LocationListView, PlanView

urlpatterns = [
    path('', CurrentTenantView.as_view(), name='tenant-current'),
    path('locations/', LocationListView.as_view(), name='tenant-locations'),
    path('plan/', PlanView.as_view(), name='tenant-plan'),
]
