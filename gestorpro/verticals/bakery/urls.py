from django.urls import path

from .views import ProductionSuggestionView, StarterCatalogView

urlpatterns = [
    path('starter-catalog/', StarterCatalogView.as_view(), name='bakery-starter-catalog'),
    path('production-suggestion/', ProductionSuggestionView.as_view(), name='bakery-production-suggestion'),
]
