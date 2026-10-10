from django.urls import path

from .views import BatchListCreateView, RecipeDetailView, RecipeListCreateView, RecipePlanView

urlpatterns = [
    path('recipes/', RecipeListCreateView.as_view(), name='recipe-list'),
    path('recipes/<int:pk>/', RecipeDetailView.as_view(), name='recipe-detail'),
    path('recipes/<int:pk>/plan/', RecipePlanView.as_view(), name='recipe-plan'),
    path('batches/', BatchListCreateView.as_view(), name='production-batches'),
]
