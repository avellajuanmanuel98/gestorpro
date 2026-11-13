from django.urls import path

from .views import EmployeeDetailView, EmployeeListCreateView

urlpatterns = [
    path('', EmployeeListCreateView.as_view(), name='employee-list'),
    path('<int:pk>/', EmployeeDetailView.as_view(), name='employee-detail'),
]
