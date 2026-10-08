from django.urls import path

from .views import CurrentTenantView, LocationListView

urlpatterns = [
    path('', CurrentTenantView.as_view(), name='tenant-current'),
    path('locations/', LocationListView.as_view(), name='tenant-locations'),
]
