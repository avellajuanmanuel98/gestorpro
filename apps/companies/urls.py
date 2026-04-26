from django.urls import path
from .views import MyCompanyView

urlpatterns = [
    # Endpoint único — cada usuario opera sobre SU empresa
    path('me/', MyCompanyView.as_view(), name='company-me'),
]
