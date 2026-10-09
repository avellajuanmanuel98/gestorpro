from django.urls import path

from .views import StarterCatalogView

urlpatterns = [
    path('starter-catalog/', StarterCatalogView.as_view(), name='bakery-starter-catalog'),
]
