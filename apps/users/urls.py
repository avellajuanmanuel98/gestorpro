from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import RegisterView, ProfileView, ChangePasswordView

urlpatterns = [
    # Registro y login son públicos y no usan cookies — exentos de CSRF
    path('register/',      csrf_exempt(RegisterView.as_view()),        name='auth-register'),
    path('login/',         csrf_exempt(TokenObtainPairView.as_view()), name='auth-login'),
    path('token/refresh/', csrf_exempt(TokenRefreshView.as_view()),    name='auth-token-refresh'),

    # Rutas autenticadas con JWT
    path('profile/',         ProfileView.as_view(),        name='auth-profile'),
    path('change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
]
