from django.urls import path

from . import views

urlpatterns = [
    path('overview/', views.OverviewView.as_view(), name='platform-overview'),
    path('tenants/', views.TenantListView.as_view(), name='platform-tenants'),
    path('tenants/<int:pk>/', views.TenantDetailView.as_view(), name='platform-tenant'),
    path('tenants/<int:pk>/status/', views.TenantStatusView.as_view(), name='platform-tenant-status'),
    path('tenants/<int:pk>/subscription/', views.TenantSubscriptionView.as_view(), name='platform-tenant-subscription'),
    path('tenants/<int:pk>/reinvite/', views.TenantReinviteView.as_view(), name='platform-tenant-reinvite'),
    path('tenants/<int:pk>/support/', views.SupportStartView.as_view(), name='platform-support-start'),
    path('support/end/', views.SupportEndView.as_view(), name='platform-support-end'),
    path('plans/', views.PlanListView.as_view(), name='platform-plans'),
    path('plans/<int:pk>/', views.PlanDetailView.as_view(), name='platform-plan'),
    path('events/', views.EventListView.as_view(), name='platform-events'),
]
