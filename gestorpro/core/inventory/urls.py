from django.urls import path

from .views import MovementListView, PhysicalCountView

urlpatterns = [
    path('movements/', MovementListView.as_view(), name='inventory-movements'),
    path('counts/', PhysicalCountView.as_view(), name='inventory-counts'),
]
